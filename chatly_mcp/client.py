"""HTTP client for ChatlyAI's internal Vyro API.

Only the login step needs a real (stealth) browser; every content action is a
plain authenticated HTTP call, which is what this client does.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional

import httpx

from . import config
from .accounts import Account


class AuthExpired(RuntimeError):
    pass


@dataclass
class AgentResult:
    chat_id: str
    text: str
    images: list[str] = field(default_factory=list)
    files: list[dict] = field(default_factory=list)
    raw_events: int = 0

    def to_dict(self) -> dict:
        return {
            "chat_id": self.chat_id,
            "text": self.text,
            "images": self.images,
            "files": self.files,
            "event_count": self.raw_events,
        }


class ChatlyClient:
    def __init__(self, account: Account) -> None:
        self.account = account
        if account.is_expired():
            raise AuthExpired(
                f"Token for account '{account.name}' is expired. Re-login required."
            )

    # ----- low level --------------------------------------------------------------
    def _headers(self) -> dict:
        return {
            "authorization": f"Bearer {self.account.token}",
            "x-org-id": self.account.org_id or "",
            "referer": "https://chatlyai.app/",
            "origin": "https://chatlyai.app",
            "user-agent": config.USER_AGENT,
            "accept": "*/*",
        }

    def _get(self, url: str) -> httpx.Response:
        r = httpx.get(url, headers=self._headers(), timeout=30)
        if r.status_code in (401, 403):
            raise AuthExpired(f"{r.status_code} from {url}: re-login required")
        r.raise_for_status()
        return r

    # ----- account info -----------------------------------------------------------
    def credits(self) -> dict:
        url = f"{config.XIPE_BASE}/credit?org_id={self.account.org_id}"
        return self._get(url).json()

    def quota(self) -> dict:
        return self._get(f"{config.STREAM_BASE}/user/quota").json()

    def list_chats(self) -> dict:
        return self._get(f"{config.STREAM_BASE}/chat/all-chat").json()

    # ----- the unified OmniAgent endpoint ----------------------------------------
    def hyper_agent(
        self,
        prompt: str,
        dashboard_id: Optional[str] = None,
        dashboard_params: Optional[dict] = None,
        agent_mode: str = config.DEFAULT_AGENT_MODE,
        web_search: bool = False,
        chat_id: Optional[str] = None,
        on_event: Optional[Callable[[dict], None]] = None,
        timeout: float = 300.0,
    ) -> AgentResult:
        """Call /v2/hyper-agent/completions/async and assemble the SSE stream.

        This single endpoint powers every Chatly "dashboard": pass
        ``dashboard_id="image"`` (with params) for images, ``None`` for plain
        text/chat/script, and later ``"video"`` / ``"music"`` etc.
        """
        chat_id = chat_id or str(uuid.uuid4())
        data = {
            "id": chat_id,
            "agent_mode": agent_mode,
            "connected_accounts": {},
            "web_search": web_search,
            "project_id": None,
            "dashboard_id": dashboard_id,
            "dashboard_params": dashboard_params or {},
            "messages": [
                {
                    "id": str(uuid.uuid4()),
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
        }
        url = f"{config.STREAM_BASE}/hyper-agent/completions/async"

        text_chunks: list[str] = []
        images: list[str] = []
        files: list[dict] = []
        count = 0

        with httpx.Client(timeout=timeout, headers=self._headers()) as c:
            with c.stream("POST", url, files={"data": (None, json.dumps(data))}) as r:
                if r.status_code in (401, 403):
                    raise AuthExpired(f"{r.status_code} from hyper-agent: re-login required")
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    try:
                        evt = json.loads(line[5:].strip())
                    except Exception:
                        continue
                    count += 1
                    if on_event:
                        on_event(evt)
                    self._consume_event(evt, text_chunks, images, files)

        # de-dup image urls preserving order
        seen: set[str] = set()
        uniq_imgs = [u for u in images if not (u in seen or seen.add(u))]
        return AgentResult(
            chat_id=chat_id,
            text="".join(text_chunks).strip(),
            images=uniq_imgs,
            files=files,
            raw_events=count,
        )

    @staticmethod
    def _consume_event(evt: dict, text_chunks: list, images: list, files: list) -> None:
        ty = evt.get("type")
        content = evt.get("content")
        if ty == "text" and isinstance(content, str):
            text_chunks.append(content)
        elif ty == "file" and isinstance(content, dict):
            meta = content.get("meta_data", {}) or {}
            url = content.get("url") or meta.get("trusted_url")
            mime = content.get("type") or content.get("mime_type") or ""
            if url:
                files.append({"url": url, "mime": mime, "name": meta.get("name")})
                if "image" in mime or url.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    images.append(url)

    # ----- high level convenience tools ------------------------------------------
    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = config.DEFAULT_ASPECT,
        resolution: str = config.DEFAULT_RESOLUTION,
        count: int = config.DEFAULT_IMAGE_COUNT,
        style_id: str = config.DEFAULT_STYLE_ID,
        agent_mode: str = config.DEFAULT_AGENT_MODE,
        on_event: Optional[Callable[[dict], None]] = None,
        max_retries: int = 1,
    ) -> AgentResult:
        # The OmniAgent is non-deterministic and occasionally ends a stream
        # without emitting the image; retry a couple of times if so.
        params = {
            "style_id": style_id,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "count": count,
        }
        res = None
        for _ in range(max_retries + 1):
            res = self.hyper_agent(
                prompt, dashboard_id="image", dashboard_params=params,
                agent_mode=agent_mode, on_event=on_event,
            )
            if res.images:
                break
        return res

    def chat(
        self,
        prompt: str,
        web_search: bool = False,
        agent_mode: str = config.DEFAULT_AGENT_MODE,
        on_event: Optional[Callable[[dict], None]] = None,
    ) -> AgentResult:
        return self.hyper_agent(
            prompt, dashboard_id=None, web_search=web_search,
            agent_mode=agent_mode, on_event=on_event,
        )

    # ----- media download ---------------------------------------------------------
    def download(self, url: str, dest_dir: Optional[Path] = None) -> str:
        dest_dir = Path(dest_dir or config.DOWNLOADS_DIR)
        dest_dir.mkdir(parents=True, exist_ok=True)
        name = url.split("/")[-1].split("?")[0] or f"{uuid.uuid4().hex}.bin"
        path = dest_dir / name
        with httpx.stream("GET", url, timeout=120) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        return str(path)
