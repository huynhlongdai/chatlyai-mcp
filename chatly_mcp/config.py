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

# ── Video model mappings ───────────────────────────────────────────────────────
# Extracted from ChatlyAI's Firebase Remote Config via React fiber tree.

VIDEO_MODELS: dict[str, dict] = {
    "veo-3.1":          {"styleId": "17001", "creditCount": 0, "isPro": True, "durations": [4,6,8],                        "resolutions": ["720p","1080p","4k"], "aspectRatios": ["16:9","9:16","auto"],                                "description": "Google's latest flagship video model with cinematic quality"},
    "veo-3.1-fast":     {"styleId": "17002", "creditCount": 0, "isPro": True, "durations": [4,6,8],                        "resolutions": ["720p","1080p","4k"], "aspectRatios": ["16:9","9:16"],                                      "description": "Faster variant of Veo 3.1 for quick iterations"},
    "veo-3.1-lite":     {"styleId": "17004", "creditCount": 0, "isPro": True, "durations": [8],                            "resolutions": ["720p","1080p"],      "aspectRatios": ["16:9","9:16"],                                      "description": "Lightweight Veo 3.1 for cost-effective generation"},
    "kling-3-pro":      {"styleId": "11020", "creditCount": 0, "isPro": True, "durations": list(range(3,16)),               "resolutions": ["1080p"],             "aspectRatios": ["16:9","9:16","1:1"],                                "description": "Kling's newest professional video model"},
    "kling-2.6-pro":    {"styleId": "11017", "creditCount": 0, "isPro": True, "durations": [5,10],                          "resolutions": [],                    "aspectRatios": ["16:9","9:16","1:1"],                                "description": "Kling 2.6 Pro for high-quality video generation"},
    "wan-2.6":          {"styleId": "22309", "creditCount": 0, "isPro": True, "durations": [5,10,15],                       "resolutions": ["720p","1080p"],      "aspectRatios": ["16:9","9:16","1:1","4:3","3:4"],                    "description": "Wan 2.6 video generation model"},
    "pixverse-v6":      {"styleId": "14010", "creditCount": 0, "isPro": True, "durations": list(range(5,16)),               "resolutions": ["540p","720p","1080p"],"aspectRatios": ["16:9","4:3","1:1","3:4","9:16","2:3","3:2","21:9"],"description": "Pixverse v6 for creative video generation"},
    "runway-4.5":       {"styleId": "60601", "creditCount": 0, "isPro": True, "durations": [5,8,10],                        "resolutions": ["720p"],              "aspectRatios": ["16:9","9:16","1:1"],                                "description": "Runway 4.5 for creative video generation"},
    "seedance-1.5-pro": {"styleId": "21904", "creditCount": 0, "isPro": True, "durations": list(range(4,13)),               "resolutions": ["480p","720p"],       "aspectRatios": ["auto","21:9","16:9","4:3","1:1","3:4","9:16"],      "description": "Seedance 1.5 Pro for dynamic motion video"},
    "seedance-2":       {"styleId": "21905", "creditCount": 0, "isPro": True, "durations": list(range(4,16)),               "resolutions": ["480p","720p","1080p"],"aspectRatios": ["auto","21:9","16:9","4:3","1:1","3:4","9:16"],     "description": "Seedance 2 next-generation motion model"},
    "grok-video":       {"styleId": "22801", "creditCount": 0, "isPro": True, "durations": list(range(6,16)),               "resolutions": ["480p","720p"],       "aspectRatios": ["16:9","4:3","3:2","1:1","2:3","3:4","9:16"],        "description": "xAI Grok Video generation model"},
}

# ── Music model mappings ──────────────────────────────────────────────────────

MUSIC_MODELS: dict[str, dict] = {
    "elevenlabs-music":         {"styleId": "90000", "creditCount": 0, "isPro": True, "description": "ElevenLabs Music for high-quality AI song and track generation"},
    "minimax-music-2.6":        {"styleId": "90001", "creditCount": 0, "isPro": True, "description": "MiniMax Music 2.6 for long-form music with rich style coherence"},
    "elevenlabs-sound-effects": {"styleId": "90002", "creditCount": 0, "isPro": True, "description": "ElevenLabs Sound Effects for realistic AI-generated audio and ambience"},
    "cassette-ai":              {"styleId": "90003", "creditCount": 0, "isPro": True, "description": "CassetteAI for genre and mood-directed AI music composition"},
    "ace-step":                 {"styleId": "90004", "creditCount": 0, "isPro": True, "description": "Ace Step for fast, high-fidelity open-source music generation"},
    "lyria-2":                  {"styleId": "90005", "creditCount": 0, "isPro": True, "description": "Lyria 2 by Google for expressive music with rich harmonic depth"},
}
