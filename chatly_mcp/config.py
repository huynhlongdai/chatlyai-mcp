"""Central paths and constants for the Chatly MCP server."""
from __future__ import annotations

import os
from pathlib import Path

# Root of the project (…/chatly-mcp)
ROOT = Path(os.environ.get("CHATLY_MCP_HOME", Path(__file__).resolve().parent.parent))

PROFILES_DIR = ROOT / "profiles"          # per-account playwright storage_state + user dirs
ACCOUNTS_FILE = PROFILES_DIR / "accounts.json"
DOWNLOADS_DIR = ROOT / "downloads"        # where generated media is saved when requested

PROFILES_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Vyro / Chatly internal API hosts (discovered via network recon)
AUTH_BASE = "https://auth.vyro.ai/apis/v1"
STREAM_BASE = "https://streaming-chatly.vyro.ai/v2"
XIPE_BASE = "https://xipe.vyro.ai/v1"
SIGN_IN_URL = (
    "https://accounts.vyro.ai/auth/sign-in"
    "?redirect=https%3A%2F%2Fchatlyai.app%2F&product=chatly"
)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)

# ── Default generation parameters ──────────────────────────────────────────────

# Image defaults (match the web UI)
DEFAULT_STYLE_ID = "40603"
DEFAULT_ASPECT = "1:1"
DEFAULT_RESOLUTION = "1K"
DEFAULT_IMAGE_COUNT = 1
DEFAULT_AGENT_MODE = "thinking"

# Video defaults (discovered via browser recon)
DEFAULT_VIDEO_STYLE_ID = "17001"
DEFAULT_VIDEO_ASPECT = "16:9"
DEFAULT_VIDEO_RESOLUTION = "720p"
DEFAULT_VIDEO_DURATION = 4          # seconds
DEFAULT_VIDEO_MODEL = "vgpt-kk-2-6"

# Music defaults (discovered via browser recon)
DEFAULT_MUSIC_STYLE_ID = "90000"
DEFAULT_MUSIC_MODEL = "vgpt-kk-2-6"

# Default model for ultra-agent endpoint
DEFAULT_ULTRA_MODEL = "vgpt-kk-2-6"

# ── Image model mappings ───────────────────────────────────────────────────────
# Extracted from ChatlyAI's Firebase Remote Config via React fiber tree.
# Each model is keyed by a friendly slug; value is a dict with
#   styleId, creditCount, isPro, aspectRatios, resolutions.

IMAGE_MODELS: dict[str, dict] = {
    "auto":              {"styleId": "41201", "creditCount": 0,   "isPro": False, "resolutions": [],              "aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "nano-banana-2":     {"styleId": "40603", "creditCount": 72,  "isPro": True,  "resolutions": ["1K","2K","4K"],"aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "nano-banana-pro":   {"styleId": "40602", "creditCount": 90,  "isPro": True,  "resolutions": ["1K","2K","4K"],"aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "nano-banana":       {"styleId": "40601", "creditCount": 24,  "isPro": True,  "resolutions": ["1K"],          "aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "midjourney-v7":     {"styleId": "80101", "creditCount": 60,  "isPro": True,  "resolutions": [],              "aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "gpt-image-2":       {"styleId": "41701", "creditCount": 132, "isPro": True,  "resolutions": ["1K","2K","4K"],"aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "grok-image":        {"styleId": "41401", "creditCount": 14,  "isPro": False, "resolutions": ["1K","2K"],     "aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "imagineart-2":      {"styleId": "41601", "creditCount": 6,   "isPro": False, "resolutions": ["1K","2K"],     "aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "seedream-5-lite":   {"styleId": "40406", "creditCount": 21,  "isPro": True,  "resolutions": [],              "aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "seedream-4.5":      {"styleId": "40405", "creditCount": 24,  "isPro": True,  "resolutions": ["4K"],          "aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "seedream-4":        {"styleId": "40404", "creditCount": 18,  "isPro": True,  "resolutions": ["4K"],          "aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "flux-2-pro":        {"styleId": "40108", "creditCount": 27,  "isPro": True,  "resolutions": ["2K"],          "aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "flux-kontext-pro":  {"styleId": "40107", "creditCount": 24,  "isPro": True,  "resolutions": [],              "aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "ideogram-3":        {"styleId": "40202", "creditCount": 36,  "isPro": True,  "resolutions": ["1K"],          "aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "z-image-turbo":     {"styleId": "41201", "creditCount": 3,   "isPro": False, "resolutions": [],              "aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "qwen-image":        {"styleId": "40501", "creditCount": 12,  "isPro": False, "resolutions": ["1K"],          "aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
    "qwen-image-edit":   {"styleId": "40502", "creditCount": 18,  "isPro": False, "resolutions": [],              "aspectRatios": ["1:1","3:4","4:3","16:9","9:16"]},
}

# Reverse lookup: styleId → model slug
STYLE_ID_TO_MODEL: dict[str, str] = {v["styleId"]: k for k, v in IMAGE_MODELS.items() if k != "auto"}

# All valid aspect ratios and resolutions
IMAGE_ASPECT_RATIOS = ["1:1", "3:4", "4:3", "16:9", "9:16"]
IMAGE_RESOLUTIONS   = ["1K", "2K", "4K"]

# ── Known model IDs (video / music) ───────────────────────────────────────────
# These map friendly names to the model slugs used in the API payload.
# Discovered by switching models in the Chatly UI and capturing the POST.

VIDEO_MODELS: dict[str, str] = {
    "seedance-2":     "vgpt-kk-2-6",
    "kling-3-pro":    "vgpt-kk-2-6",
    "veo-3.1":        "vgpt-kk-2-6",
    "runway-4.5":     "vgpt-kk-2-6",
    "wan-2.6":        "vgpt-kk-2-6",
    "pixverse-v6":    "vgpt-kk-2-6",
    "grok-video":     "vgpt-kk-2-6",
}

MUSIC_MODELS: dict[str, str] = {
    "elevenlabs":     "vgpt-kk-2-6",
    "lyria-2":        "vgpt-kk-2-6",
    "minimax-2.6":    "vgpt-kk-2-6",
    "cassette-ai":    "vgpt-kk-2-6",
    "ace-step":       "vgpt-kk-2-6",
}
