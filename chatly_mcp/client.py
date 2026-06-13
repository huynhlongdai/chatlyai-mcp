"""HTTP client for ChatlyAI's internal Vyro API.

Only the login step needs a real (stealth) browser; every content action is a
plain authenticated HTTP call, which is what this client does.

Two endpoint families exist:
  * ``/v2/hyper-agent/completions/async`` — text chat, image generation
  * ``/v2/ultra-agent/completions/async`` — video, music (and also images)

Both return Server-Sent-Events (SSE).  The newer *ultra-agent* endpoint emits
``artifact_event`` payloads that carry the generated media URLs, while the
older *hyper-agent* uses ``file`` events.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import httpx

from . import config
from .accounts import Account


class AuthExpired(RuntimeError):
    pass


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class AgentResult:
    chat_id: str
    text: str
    images: list[str] = field(default_factory=list)
    videos: list[str] = field(default_factory=list)
    audios: list[str] = field(default_factory=list)
    files: list[dict] = field(default_factory=list)
    artifacts: list[dict] = field(default_factory=list)
    raw_events: int = 0

    def to_dict(self) -> dict:
        return {
            "chat_id": self.chat_id,
            "text": self.text,
            "images": self.images,
            "videos": self.videos,
            "audios": self.audios,
            "files": self.files,
            "artifacts": self.artifacts,
            "event_count": self.raw_events,
        }


# ── Main client ────────────────────────────────────────────────────────────────

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

    # ----- SSE stream consumer (shared) ------------------------------------------
    def _stream_sse(
        self,
        url: str,
        data: dict,
        on_event: Optional[Callable[[dict], None]] = None,
        timeout: float = 300.0,
    ) -> AgentResult:
        """POST *data* as multipart form, consume the SSE stream, return result."""
        chat_id = data.get("id", "")

        text_chunks: list[str] = []
        images: list[str] = []
        videos: list[str] = []
        audios: list[str] = []
        files: list[dict] = []
        artifacts: list[dict] = []
        count = 0

        with httpx.Client(timeout=timeout, headers=self._headers()) as c:
            with c.stream("POST", url, files={"data": (None, json.dumps(data))}) as r:
                if r.status_code in (401, 403):
                    raise AuthExpired(f"{r.status_code} from {url}: re-login required")
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
                    self._consume_event(
                        evt, text_chunks, images, videos, audios, files, artifacts,
                    )

        # de-dup urls preserving order
        def _dedup(lst: list[str]) -> list[str]:
            seen: set[str] = set()
            return [u for u in lst if not (u in seen or seen.add(u))]  # type: ignore[func-returns-value]

        return AgentResult(
            chat_id=chat_id,
            text="".join(text_chunks).strip(),
            images=_dedup(images),
            videos=_dedup(videos),
            audios=_dedup(audios),
            files=files,
            artifacts=artifacts,
            raw_events=count,
        )

    @staticmethod
    def _consume_event(
        evt: dict,
        text_chunks: list,
        images: list,
        videos: list,
        audios: list,
        files: list,
        artifacts: list,
    ) -> None:
        ty = evt.get("type")
        content = evt.get("content")

        # ── text chunk ──
        if ty == "text" and isinstance(content, str):
            text_chunks.append(content)

        # ── legacy file event (hyper-agent) ──
        elif ty == "file" and isinstance(content, dict):
            meta = content.get("meta_data", {}) or {}
            url = content.get("url") or meta.get("trusted_url")
            mime = content.get("type") or content.get("mime_type") or ""
            if url:
                files.append({"url": url, "mime": mime, "name": meta.get("name")})
                if "image" in mime or url.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".webp")
                ):
                    images.append(url)
                elif "video" in mime or url.lower().endswith((".mp4", ".webm")):
                    videos.append(url)
                elif "audio" in mime or url.lower().endswith(
                    (".mp3", ".wav", ".ogg", ".m4a")
                ):
                    audios.append(url)

        # ── artifact_event (ultra-agent — images, videos, music) ──
        elif ty == "artifact_event" and isinstance(content, dict):
            artifact = content.get("artifact", {})
            kind = content.get("kind", "")  # "image" | "video" | "music"
            primary = artifact.get("primary", {})
            urls_block = artifact.get("urls", {})
            generation_urls = urls_block.get("generations", [])

            # Store the full artifact for callers who want rich metadata
            artifacts.append({
                "kind": kind,
                "primary": primary,
                "urls": urls_block,
            })

            main_url = primary.get("url")
            mime = primary.get("mime_type", "")

            # Classify into the right bucket
            if kind == "image" or "image" in mime:
                for u in generation_urls or ([main_url] if main_url else []):
                    if u:
                        images.append(u)
            elif kind == "video" or "video" in mime:
                for u in generation_urls or ([main_url] if main_url else []):
                    if u:
                        videos.append(u)
            elif kind == "music" or "audio" in mime:
                for u in generation_urls or ([main_url] if main_url else []):
                    if u:
                        audios.append(u)
            else:
                # Unknown kind — put in files
                if main_url:
                    files.append({
                        "url": main_url,
                        "mime": mime,
                        "name": primary.get("name"),
                    })

    # ── hyper-agent endpoint (chat, image — legacy) ─────────────────────────────
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

        This endpoint powers chat and image generation dashboards.
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
        return self._stream_sse(url, data, on_event=on_event, timeout=timeout)

    # ── ultra-agent endpoint (video, music, image v2) ───────────────────────────
    def ultra_agent(
        self,
        prompt: str,
        dashboard_id: Optional[str] = None,
        dashboard_params: Optional[dict] = None,
        model: str = config.DEFAULT_ULTRA_MODEL,
        agent_mode: str = config.DEFAULT_AGENT_MODE,
        web_search: bool = False,
        chat_id: Optional[str] = None,
        on_event: Optional[Callable[[dict], None]] = None,
        timeout: float = 300.0,
    ) -> AgentResult:
        """Call /v2/ultra-agent/completions/async and assemble the SSE stream.

        This newer endpoint powers video, music, and (optionally) image
        generation.  It returns ``artifact_event`` payloads with media URLs.
        """
        chat_id = chat_id or str(uuid.uuid4())
        data = {
            "id": chat_id,
            "model": model,
            "agent_mode": agent_mode,
            "connected_accounts": {},
            "web_search": web_search,
            "ask": "never",
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
        url = f"{config.STREAM_BASE}/ultra-agent/completions/async"
        return self._stream_sse(url, data, on_event=on_event, timeout=timeout)

    # ----- high level convenience tools ------------------------------------------
    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = config.DEFAULT_ASPECT,
        resolution: str = config.DEFAULT_RESOLUTION,
        count: int = config.DEFAULT_IMAGE_COUNT,
        style_id: str = config.DEFAULT_STYLE_ID,
        agent_mode: str = config.DEFAULT_AGENT_MODE,
        use_ultra: bool = True,
        on_event: Optional[Callable[[dict], None]] = None,
        max_retries: int = 1,
    ) -> AgentResult:
        """Generate image(s) from a text prompt.

        By default uses the newer ultra-agent endpoint.  Set ``use_ultra=False``
        to use the legacy hyper-agent endpoint.
        """
        params = {
            "style_id": style_id,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "count": count,
        }
        res = None
        for _ in range(max_retries + 1):
            if use_ultra:
                res = self.ultra_agent(
                    prompt,
                    dashboard_id="image",
                    dashboard_params=params,
                    agent_mode=agent_mode,
                    on_event=on_event,
                )
            else:
                res = self.hyper_agent(
                    prompt,
                    dashboard_id="image",
                    dashboard_params=params,
                    agent_mode=agent_mode,
                    on_event=on_event,
                )
            if res.images:
                break
        return res  # type: ignore[return-value]

    def generate_video(
        self,
        prompt: str,
        aspect_ratio: str = config.DEFAULT_VIDEO_ASPECT,
        resolution: str = config.DEFAULT_VIDEO_RESOLUTION,
        duration: int = config.DEFAULT_VIDEO_DURATION,
        style_id: str = config.DEFAULT_VIDEO_STYLE_ID,
        model: str = config.DEFAULT_VIDEO_MODEL,
        agent_mode: str = config.DEFAULT_AGENT_MODE,
        on_event: Optional[Callable[[dict], None]] = None,
        timeout: float = 600.0,
    ) -> AgentResult:
        """Generate a video from a text prompt via the ultra-agent endpoint.

        Video generation can take 30–120+ seconds depending on the model
        and duration.
        """
        params = {
            "style_id": style_id,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "duration": duration,
        }
        return self.ultra_agent(
            prompt,
            dashboard_id="video",
            dashboard_params=params,
            model=model,
            agent_mode=agent_mode,
            on_event=on_event,
            timeout=timeout,
        )

    def generate_music(
        self,
        prompt: str,
        style_id: str = config.DEFAULT_MUSIC_STYLE_ID,
        model: str = config.DEFAULT_MUSIC_MODEL,
        agent_mode: str = config.DEFAULT_AGENT_MODE,
        on_event: Optional[Callable[[dict], None]] = None,
        timeout: float = 300.0,
    ) -> AgentResult:
        """Generate music/audio from a text prompt via the ultra-agent endpoint."""
        params = {
            "style_id": style_id,
        }
        return self.ultra_agent(
            prompt,
            dashboard_id="music",
            dashboard_params=params,
            model=model,
            agent_mode=agent_mode,
            on_event=on_event,
            timeout=timeout,
        )

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
