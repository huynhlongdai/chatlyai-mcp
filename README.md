# Chatly MCP

Remote-control your **ChatlyAI** (chatlyai.app) accounts through an **MCP server** —
generate images, videos, music, write scripts/kịch bản, chat, check credits, and more.

ChatlyAI has **no public API**. It's a Next.js app on top of **Vyro AI**'s internal
services, and its login is protected by **Cloudflare Turnstile**, which blocks ordinary
automation. This project solves both:

1. **Login** once with [CloakBrowser](https://github.com/CloakHQ/cloakbrowser) (a stealth
   Chromium) to pass Turnstile, and save the session.
2. **Act** by calling Vyro's internal API directly with the captured bearer token — fast,
   scriptable, no browser needed per request.

## How it works

```
CloakBrowser login ──> cookies (token, refreshToken, organization-id)
                           │
                           ▼
        profiles/<name>_state.json  (Playwright storage_state)
                           │
                           ▼
   ChatlyClient (httpx + Bearer token + x-org-id)
                           │
          ┌────────────────┴─────────────────┐
          │                                  │
   hyper-agent endpoint               ultra-agent endpoint
   (chat, image — legacy)             (video, music, image v2)
          │                                  │
   POST streaming-chatly.vyro.ai       POST streaming-chatly.vyro.ai
   /v2/hyper-agent/completions/async   /v2/ultra-agent/completions/async
          │                                  │
          └──────────┬───────────────────────┘
                     │ (both return SSE streams)
                     ▼
        ┌────────────────────────────┐
        │  dashboard_id determines   │
        │  what gets generated:      │
        │  • "image" → images        │
        │  • "video" → videos        │
        │  • "music" → audio         │
        │  • null    → text/chat     │
        └────────────────────────────┘
```

### Key endpoints discovered

| Purpose | Endpoint |
|---|---|
| Generate (chat/image, legacy) | `POST streaming-chatly.vyro.ai/v2/hyper-agent/completions/async` |
| Generate (video/music/image v2) | `POST streaming-chatly.vyro.ai/v2/ultra-agent/completions/async` |
| Credits | `GET xipe.vyro.ai/v1/credit?org_id=…` |
| Quota | `GET streaming-chatly.vyro.ai/v2/user/quota` |
| Chats list | `GET streaming-chatly.vyro.ai/v2/chat/all-chat` |
| User preferences | `GET streaming-chatly.vyro.ai/v2/user/preferences` |
| Auth (check email) | `POST auth.vyro.ai/apis/v1/auth/custom/check-email/{email}` |

Auth headers: `authorization: Bearer <token>`, `x-org-id: <organization-id>`.

### SSE event types

The SSE streams emit these event types:

| Event type | Description |
|---|---|
| `thinking` | Agent reasoning (can be ignored) |
| `text` | Text content chunks — assemble to get the reply |
| `task_running` | A tool (image_generate, music_generate…) started |
| `task_completed` | A tool finished |
| `artifact_event` | **Media result** — contains URLs in `content.artifact` |
| `file` | Legacy media result (hyper-agent only) |

The `artifact_event` payload structure:
```json
{
  "type": "artifact_event",
  "content": {
    "kind": "image|video|music",
    "artifact": {
      "primary": {
        "url": "https://asset.imagine.art/processed/...",
        "mime_type": "image/png",
        "model": "fal-ai/nano-banana-2",
        "prompt": "..."
      },
      "urls": {
        "generations": ["https://..."],
        "thumbnails": ["https://..."],
        "variations": ["https://..."]
      }
    }
  }
}
```

## Install

```bash
cd chatlyai-mcp
pip install -e .          # installs mcp, httpx, cloakbrowser
# CloakBrowser downloads its stealth Chromium (~200MB) on first login.
```

## Log in (one-time per account)

Requires a desktop display (Turnstile fails in headless). On this VM, `DISPLAY=:0`.

```bash
export CHATLYAI_EMAIL=you@example.com
export CHATLYAI_PASSWORD=...
DISPLAY=:0 python -m chatly_mcp.login --name account1
# -> profiles/account1_state.json
```

Add more accounts by repeating with a different `--name` (and credentials). The token
lasts ~6 hours; re-run login to refresh.

## Run the MCP server

```bash
python -m chatly_mcp.server     # stdio transport
```

### Register in an MCP client (e.g. Claude Desktop / Cursor)

```json
{
  "mcpServers": {
    "chatly": {
      "command": "python",
      "args": ["-m", "chatly_mcp.server"],
      "cwd": "/path/to/chatlyai-mcp"
    }
  }
}
```

## Tools

| Tool | Description |
|---|---|
| `chatly_list_accounts()` | List accounts + token status (expiry). |
| `chatly_credits(account?)` | Remaining credits/tokens. |
| `chatly_quota(account?)` | Per-feature usage limits. |
| `chatly_generate_image(prompt, account?, aspect_ratio, resolution, count, style_id, download?)` | Generate image(s); returns URLs (+ local paths if `download`). |
| `chatly_generate_video(prompt, account?, aspect_ratio, resolution, duration, style_id, download?)` | Generate video; returns URLs (+ local paths if `download`). |
| `chatly_generate_music(prompt, account?, style_id, download?)` | Generate music/audio; returns URLs (+ local paths if `download`). |
| `chatly_create_script(prompt, account?)` | Long-form text / kịch bản. |
| `chatly_chat(prompt, account?, web_search?)` | Ask the OmniAgent. |
| `chatly_login(email, password, name?)` | Add/refresh an account (needs display). |

`account` defaults to the first configured account. Use `chatly_list_accounts` to see names.

### Video generation parameters

- **aspect_ratio**: `"16:9"`, `"9:16"`, `"1:1"`
- **resolution**: `"720p"`, `"1080p"`
- **duration**: `4`, `8`, or `16` seconds (model-dependent)
- **Available models** (selected via UI): Seedance 2, Kling 3.0 Pro, Google Veo 3.1, Runway 4.5, Wan 2.6, Pixverse v6, xAI Grok Video

### Music generation

Describe the genre, mood, instruments, tempo, and vibe you want. Available models: ElevenLabs Music, Lyria 2, MiniMax Music 2.6, CassetteAI, Ace Step.

## Multi-account

Drop one `*_state.json` per account in `profiles/`. `AccountStore.pick()` supports
round-robin selection (useful to spread load / avoid rate limits). Per-tool `account=`
lets you pin a specific one.

## Status / next steps

- ✅ Login via CloakBrowser (Turnstile bypassed), session persistence
- ✅ Image generation (via both hyper-agent and ultra-agent endpoints)
- ✅ Video generation (ultra-agent + artifact_event parsing)
- ✅ Music generation (ultra-agent + artifact_event parsing)
- ✅ Script / chat generation (text)
- ✅ Credits & quota
- ⏳ Per-model selection for video/music (need to map model IDs per provider)
- ⏳ Token auto-refresh (refresh endpoint not yet found; re-login for now)
- ⏳ Async job queue for long video renders
- ⏳ Node-based workflow automation (likely needs UI automation)

## ⚠️ Notes
- Automating multiple accounts may violate ChatlyAI's Terms of Service. Use at your own risk.
- `profiles/*_state.json` contain **live auth tokens** — treat as secrets, do not commit.
