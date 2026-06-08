"""FastMCP server exposing ChatlyAI as MCP tools.

Run with:  python -m chatly_mcp.server      (stdio transport)
"""
from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import config
from .accounts import AccountStore
from .client import AuthExpired, ChatlyClient

mcp = FastMCP("chatly")
store = AccountStore()


def _client(account: Optional[str]) -> ChatlyClient:
    acct = store.get(account)
    return ChatlyClient(acct)


@mcp.tool()
def chatly_list_accounts() -> list[dict]:
    """List configured ChatlyAI accounts and their token status."""
    return [a.to_dict() for a in store.list()]


@mcp.tool()
def chatly_credits(account: Optional[str] = None) -> dict:
    """Get remaining credits/tokens for an account (defaults to the first)."""
    return _client(account).credits()


@mcp.tool()
def chatly_quota(account: Optional[str] = None) -> dict:
    """Get per-feature usage quota for an account."""
    return _client(account).quota()


@mcp.tool()
def chatly_generate_image(
    prompt: str,
    account: Optional[str] = None,
    aspect_ratio: str = config.DEFAULT_ASPECT,
    resolution: str = config.DEFAULT_RESOLUTION,
    count: int = config.DEFAULT_IMAGE_COUNT,
    style_id: str = config.DEFAULT_STYLE_ID,
    download: bool = False,
) -> dict:
    """Generate image(s) from a text prompt via Chatly's image dashboard.

    Returns the generated image URLs (and local paths if download=True).
    """
    client = _client(account)
    res = client.generate_image(
        prompt, aspect_ratio=aspect_ratio, resolution=resolution,
        count=count, style_id=style_id,
    )
    out = res.to_dict()
    if download and res.images:
        out["downloaded"] = [client.download(u) for u in res.images]
    return out


@mcp.tool()
def chatly_create_script(prompt: str, account: Optional[str] = None) -> dict:
    """Create a script / kịch bản (or any long-form text) via Chatly's agent."""
    res = _client(account).chat(prompt)
    return {"chat_id": res.chat_id, "text": res.text}


@mcp.tool()
def chatly_chat(
    prompt: str, account: Optional[str] = None, web_search: bool = False
) -> dict:
    """Ask the Chatly OmniAgent a question (optionally with web search)."""
    res = _client(account).chat(prompt, web_search=web_search)
    return {"chat_id": res.chat_id, "text": res.text, "images": res.images}


@mcp.tool()
def chatly_login(email: str, password: str, name: str = "account1") -> dict:
    """Add/refresh an account by logging in through CloakBrowser.

    Requires a desktop display on the server (DISPLAY). This passes Cloudflare
    Turnstile and saves the session for API use.
    """
    from .login import login

    path = login(email, password, name=name)
    return {"name": name, "state_path": str(path), "status": "logged_in"}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
