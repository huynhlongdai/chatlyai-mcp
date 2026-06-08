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

# Default image generation knobs (match the web UI defaults)
DEFAULT_STYLE_ID = "40603"
DEFAULT_ASPECT = "1:1"
DEFAULT_RESOLUTION = "1K"
DEFAULT_IMAGE_COUNT = 1
DEFAULT_AGENT_MODE = "thinking"
