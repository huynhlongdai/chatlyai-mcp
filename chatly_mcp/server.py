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


# ── Account & info tools ──────────────────────────────────────────────────────

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


# ── Image generation ──────────────────────────────────────────────────────────

@mcp.tool()
def chatly_list_image_models() -> list[dict]:
    """List all available image generation models with their options.

    Returns each model's slug, display name, styleId, creditCount,
    supported aspect ratios and resolutions.
    """
    return [
        {"slug": slug, **info}
        for slug, info in config.IMAGE_MODELS.items()
    ]


@mcp.tool()
def chatly_generate_image(
    prompt: str,
    model: str = "auto",
    aspect_ratio: str = config.DEFAULT_ASPECT,
    resolution: str = config.DEFAULT_RESOLUTION,
    count: int = config.DEFAULT_IMAGE_COUNT,
    style_id: Optional[str] = None,
    download: bool = False,
    account: Optional[str] = None,
) -> dict:
    """Generate image(s) from a text prompt via Chatly's image dashboard.

    Args:
        prompt:       Text description of the image to create.
        model:        Model slug. Use chatly_list_image_models() to see all.
                      Common choices:
                        "auto"            – let Chatly pick (free, 0 credits)
                        "nano-banana-2"   – high quality (72 credits)
                        "midjourney-v7"   – Midjourney style (60 credits)
                        "gpt-image-2"     – GPT Image 2 (132 credits)
                        "grok-image"      – xAI Grok (14 credits, free tier)
                        "imagineart-2"    – ImagineArt 2.0 (6 credits, free tier)
                        "seedream-5-lite" – Seedream 5 Lite (21 credits)
                        "seedream-4.5"    – Seedream 4.5 (24 credits)
                        "flux-2-pro"      – Flux.2 Pro (27 credits)
                        "ideogram-3"      – Ideogram 3.0 (36 credits)
                        "qwen-image"      – Qwen Image (12 credits, free tier)
                        "z-image-turbo"   – Ultra-fast (3 credits, free tier)
        aspect_ratio: "1:1", "3:4", "4:3", "16:9", or "9:16".
        resolution:   "1K", "2K", or "4K" (availability depends on model).
        count:        Number of images to generate (1–4).
        style_id:     Override model selection with a raw style_id string.
        download:     If True, also download images to local disk.
        account:      Account name (defaults to first configured account).

    Returns the generated image URLs (and local paths if download=True).
    """
    # Resolve style_id from model slug
    if style_id is None:
        model_info = config.IMAGE_MODELS.get(model)
        if model_info is None:
            available = ", ".join(sorted(config.IMAGE_MODELS.keys()))
            return {"error": f"Unknown model '{model}'. Available: {available}"}
        style_id = model_info["styleId"]
        # Validate resolution for this model
        supported_res = model_info.get("resolutions", [])
        if supported_res and resolution not in supported_res:
            resolution = supported_res[0]  # fall back to first supported

    client = _client(account)
    res = client.generate_image(
        prompt, aspect_ratio=aspect_ratio, resolution=resolution,
        count=count, style_id=style_id,
    )
    out = res.to_dict()
    out["model_used"] = model
    out["style_id"] = style_id
    if download and res.images:
        out["downloaded"] = [client.download(u) for u in res.images]
    return out


# ── Video generation ──────────────────────────────────────────────────────────

@mcp.tool()
def chatly_list_video_models() -> list[dict]:
    """List all available video generation models with their options.

    Returns each model's slug, styleId, supported durations,
    resolutions, aspect ratios, and description.
    """
    return [
        {"slug": slug, **info}
        for slug, info in config.VIDEO_MODELS.items()
    ]


@mcp.tool()
def chatly_generate_video(
    prompt: str,
    model: str = "veo-3.1",
    aspect_ratio: str = config.DEFAULT_VIDEO_ASPECT,
    resolution: str = config.DEFAULT_VIDEO_RESOLUTION,
    duration: int = config.DEFAULT_VIDEO_DURATION,
    style_id: Optional[str] = None,
    download: bool = False,
    account: Optional[str] = None,
) -> dict:
    """Generate a video from a text prompt via Chatly's video dashboard.

    Args:
        prompt:       Text description of the video to create.
        model:        Model slug. Use chatly_list_video_models() to see all.
                      Common choices:
                        "veo-3.1"        – Google Veo 3.1, cinematic (default)
                        "veo-3.1-fast"   – Faster Veo variant
                        "veo-3.1-lite"   – Lightweight Veo, cost-effective
                        "kling-3-pro"    – Kling 3.0 Pro, 3–15s
                        "kling-2.6-pro"  – Kling 2.6 Pro
                        "seedance-2"     – Seedance 2, motion-heavy
                        "runway-4.5"     – Runway 4.5
                        "wan-2.6"        – Wan 2.6
                        "pixverse-v6"    – Pixverse v6, many aspect ratios
                        "grok-video"     – xAI Grok Video
                        "seedance-1.5-pro" – Seedance 1.5 Pro
        aspect_ratio: e.g. "16:9", "9:16", "1:1" (model-dependent).
        resolution:   "480p", "540p", "720p", "1080p", or "4k" (model-dependent).
        duration:     Seconds (model-dependent, e.g. 4, 5, 8, 10, 15).
        style_id:     Override model selection with a raw style_id string.
        download:     If True, also download video to local disk.
        account:      Account name (defaults to first configured account).

    Returns the generated video URL(s) (and local paths if download=True).
    Video generation can take 30–120+ seconds.
    """
    if style_id is None:
        model_info = config.VIDEO_MODELS.get(model)
        if model_info is None:
            available = ", ".join(sorted(config.VIDEO_MODELS.keys()))
            return {"error": f"Unknown model '{model}'. Available: {available}"}
        style_id = model_info["styleId"]
        # Validate duration
        supported_dur = model_info.get("durations", [])
        if supported_dur and duration not in supported_dur:
            duration = supported_dur[0]
        # Validate resolution
        supported_res = model_info.get("resolutions", [])
        if supported_res and resolution not in supported_res:
            resolution = supported_res[0]
        # Validate aspect ratio
        supported_ar = model_info.get("aspectRatios", [])
        if supported_ar and aspect_ratio not in supported_ar:
            aspect_ratio = supported_ar[0]

    client = _client(account)
    res = client.generate_video(
        prompt, aspect_ratio=aspect_ratio, resolution=resolution,
        duration=duration, style_id=style_id,
    )
    out = res.to_dict()
    out["model_used"] = model
    out["style_id"] = style_id
    if download and res.videos:
        out["downloaded"] = [client.download(u) for u in res.videos]
    return out


# ── Music generation ──────────────────────────────────────────────────────────

@mcp.tool()
def chatly_list_music_models() -> list[dict]:
    """List all available music/audio generation models with descriptions.

    Returns each model's slug, styleId, and description.
    """
    return [
        {"slug": slug, **info}
        for slug, info in config.MUSIC_MODELS.items()
    ]


@mcp.tool()
def chatly_generate_music(
    prompt: str,
    model: str = "elevenlabs-music",
    style_id: Optional[str] = None,
    download: bool = False,
    account: Optional[str] = None,
) -> dict:
    """Generate music/audio from a text prompt via Chatly's music dashboard.

    Args:
        prompt:   Describe the genre, mood, instruments, tempo, and vibe.
        model:    Model slug. Use chatly_list_music_models() to see all.
                  Common choices:
                    "elevenlabs-music"         – High-quality AI songs (default)
                    "minimax-music-2.6"        – Long-form, rich style coherence
                    "elevenlabs-sound-effects" – Realistic sound effects & ambience
                    "cassette-ai"              – Genre & mood-directed composition
                    "ace-step"                 – Fast, high-fidelity open-source
                    "lyria-2"                  – Google Lyria 2, expressive & harmonic
        style_id: Override model selection with a raw style_id string.
        download: If True, also download audio to local disk.
        account:  Account name (defaults to first configured account).

    Returns the generated audio URL(s) (and local paths if download=True).
    """
    if style_id is None:
        model_info = config.MUSIC_MODELS.get(model)
        if model_info is None:
            available = ", ".join(sorted(config.MUSIC_MODELS.keys()))
            return {"error": f"Unknown model '{model}'. Available: {available}"}
        style_id = model_info["styleId"]

    client = _client(account)
    res = client.generate_music(prompt, style_id=style_id)
    out = res.to_dict()
    out["model_used"] = model
    out["style_id"] = style_id
    if download and res.audios:
        out["downloaded"] = [client.download(u) for u in res.audios]
    return out


# ── Text / chat tools ────────────────────────────────────────────────────────

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


# ── Login ─────────────────────────────────────────────────────────────────────

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
