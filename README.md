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

| Event type | Description |
|---|---|
| `thinking` | Agent reasoning (can be ignored) |
| `text` | Text content chunks — assemble to get the reply |
| `task_running` | A tool (image_generate, music_generate…) started |
| `task_completed` | A tool finished |
| `artifact_event` | **Media result** — contains URLs in `content.artifact` |
| `file` | Legacy media result (hyper-agent only) |

## Install

```bash
cd chatlyai-mcp
pip install -e .
```

## Log in (one-time per account)

```bash
export CHATLYAI_EMAIL=you@example.com
export CHATLYAI_PASSWORD=...
DISPLAY=:0 python -m chatly_mcp.login --name account1
# -> profiles/account1_state.json
```

## Run the MCP server

```bash
python -m chatly_mcp.server     # stdio transport
```

## Tools

| Tool | Description |
|---|---|
| `chatly_list_accounts()` | List accounts + token status. |
| `chatly_credits(account?)` | Remaining credits. |
| `chatly_quota(account?)` | Per-feature usage limits. |
| `chatly_list_image_models()` | List all image models with options. |
| `chatly_generate_image(...)` | Generate image(s) with full model/option control. |
| `chatly_generate_video(...)` | Generate video. |
| `chatly_generate_music(...)` | Generate music/audio. |
| `chatly_create_script(prompt)` | Long-form text / kịch bản. |
| `chatly_chat(prompt, web_search?)` | Ask the OmniAgent. |
| `chatly_login(email, password)` | Add/refresh account (needs display). |

### Image generation — full options

```python
chatly_generate_image(
    prompt="a cyberpunk cat in neon rain",
    model="midjourney-v7",      # see table below
    aspect_ratio="16:9",        # 1:1, 3:4, 4:3, 16:9, 9:16
    resolution="2K",            # 1K, 2K, 4K (model-dependent)
    count=2,                    # 1–4 images
    download=True,              # save to local disk
)
```

#### Available image models

| Model slug | Style ID | Credits | Pro? | Resolutions |
|---|---|---|---|---|
| `auto` | 41201 | 0 | ❌ | — |
| `z-image-turbo` | 41201 | 3 | ❌ | — |
| `imagineart-2` | 41601 | 6 | ❌ | 1K, 2K |
| `qwen-image` | 40501 | 12 | ❌ | 1K |
| `grok-image` | 41401 | 14 | ❌ | 1K, 2K |
| `qwen-image-edit` | 40502 | 18 | ❌ | — |
| `seedream-4` | 40404 | 18 | ✅ | 4K |
| `seedream-5-lite` | 40406 | 21 | ✅ | — |
| `nano-banana` | 40601 | 24 | ✅ | 1K |
| `seedream-4.5` | 40405 | 24 | ✅ | 4K |
| `flux-kontext-pro` | 40107 | 24 | ✅ | — |
| `flux-2-pro` | 40108 | 27 | ✅ | 2K |
| `ideogram-3` | 40202 | 36 | ✅ | 1K |
| `midjourney-v7` | 80101 | 60 | ✅ | — |
| `nano-banana-2` | 40603 | 72 | ✅ | 1K, 2K, 4K |
| `nano-banana-pro` | 40602 | 90 | ✅ | 1K, 2K, 4K |
| `gpt-image-2` | 41701 | 132 | ✅ | 1K, 2K, 4K |

All models support aspect ratios: `1:1`, `3:4`, `4:3`, `16:9`, `9:16`.

### Video generation parameters

- **aspect_ratio**: `"16:9"`, `"9:16"`, `"1:1"`
- **resolution**: `"720p"`, `"1080p"`
- **duration**: `4`, `8`, or `16` seconds (model-dependent)

### Music generation

Describe the genre, mood, instruments, tempo, and vibe you want.

## Multi-account

Drop one `*_state.json` per account in `profiles/`. Per-tool `account=` selects a specific one.

## Status

- ✅ Login via CloakBrowser (Turnstile bypassed), session persistence
- ✅ Image generation — 17 models, full options (model, resolution, aspect ratio, count)
- ✅ Video generation (ultra-agent + artifact_event parsing)
- ✅ Music generation (ultra-agent + artifact_event parsing)
- ✅ Script / chat / OmniAgent
- ✅ Credits & quota
- ⏳ Per-model selection for video/music (need to map model IDs per provider)
- ⏳ Token auto-refresh (re-login for now)

## ⚠️ Notes
- Automating accounts may violate ChatlyAI's Terms of Service. Use at your own risk.
- `profiles/*_state.json` contain **live auth tokens** — treat as secrets, do not commit.
