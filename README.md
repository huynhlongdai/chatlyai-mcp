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
| `chatly_list_image_models()` | List all 17 image models with options. |
| `chatly_generate_image(...)` | Generate image(s) with full model/option control. |
| `chatly_list_video_models()` | List all 11 video models with options. |
| `chatly_generate_video(...)` | Generate video with full model/option control. |
| `chatly_list_music_models()` | List all 6 music/audio models. |
| `chatly_generate_music(...)` | Generate music/audio with model selection. |
| `chatly_create_script(prompt)` | Long-form text / kịch bản. |
| `chatly_chat(prompt, web_search?)` | Ask the OmniAgent. |
| `chatly_login(email, password)` | Add/refresh account (needs display). |

---

### 🖼️ Image generation — 17 models

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

---

### 🎬 Video generation — 11 models

```python
chatly_generate_video(
    prompt="a cat walking through a garden at sunset",
    model="veo-3.1",           # see table below
    aspect_ratio="16:9",       # model-dependent
    resolution="720p",         # 480p–4k, model-dependent
    duration=8,                # seconds, model-dependent
    download=True,
)
```

| Model slug | Style ID | Durations (s) | Resolutions | Aspect Ratios |
|---|---|---|---|---|
| `veo-3.1` | 17001 | 4, 6, 8 | 720p, 1080p, 4k | 16:9, 9:16, auto |
| `veo-3.1-fast` | 17002 | 4, 6, 8 | 720p, 1080p, 4k | 16:9, 9:16 |
| `veo-3.1-lite` | 17004 | 8 | 720p, 1080p | 16:9, 9:16 |
| `kling-3-pro` | 11020 | 3–15 | 1080p | 16:9, 9:16, 1:1 |
| `kling-2.6-pro` | 11017 | 5, 10 | — | 16:9, 9:16, 1:1 |
| `wan-2.6` | 22309 | 5, 10, 15 | 720p, 1080p | 16:9, 9:16, 1:1, 4:3, 3:4 |
| `pixverse-v6` | 14010 | 5–15 | 540p, 720p, 1080p | 16:9, 4:3, 1:1, 3:4, 9:16, 2:3, 3:2, 21:9 |
| `runway-4.5` | 60601 | 5, 8, 10 | 720p | 16:9, 9:16, 1:1 |
| `seedance-1.5-pro` | 21904 | 4–12 | 480p, 720p | auto, 21:9, 16:9, 4:3, 1:1, 3:4, 9:16 |
| `seedance-2` | 21905 | 4–15 | 480p, 720p, 1080p | auto, 21:9, 16:9, 4:3, 1:1, 3:4, 9:16 |
| `grok-video` | 22801 | 6–15 | 480p, 720p | 16:9, 4:3, 3:2, 1:1, 2:3, 3:4, 9:16 |

> Video generation takes 30–120+ seconds depending on model and duration.

---

### 🎵 Music/Audio generation — 6 models

```python
chatly_generate_music(
    prompt="upbeat electronic dance track with synths and a driving bassline",
    model="elevenlabs-music",  # see table below
    download=True,
)
```

| Model slug | Style ID | Description |
|---|---|---|
| `elevenlabs-music` | 90000 | High-quality AI song and track generation |
| `minimax-music-2.6` | 90001 | Long-form music with rich style coherence |
| `elevenlabs-sound-effects` | 90002 | Realistic AI-generated sound effects & ambience |
| `cassette-ai` | 90003 | Genre and mood-directed AI music composition |
| `ace-step` | 90004 | Fast, high-fidelity open-source music generation |
| `lyria-2` | 90005 | Google Lyria 2, expressive music with rich harmonic depth |

---

## Multi-account

Drop one `*_state.json` per account in `profiles/`. Per-tool `account=` selects a specific one.

## Status

- ✅ Login via CloakBrowser (Turnstile bypassed), session persistence
- ✅ Image generation — 17 models, full options (model, resolution, aspect ratio, count)
- ✅ Video generation — 11 models, full options (model, duration, resolution, aspect ratio)
- ✅ Music/Audio generation — 6 models with model selection
- ✅ Script / chat / OmniAgent
- ✅ Credits & quota
- ⏳ Token auto-refresh (re-login for now; tokens last ~6 hours)

## ⚠️ Notes
- Automating accounts may violate ChatlyAI's Terms of Service. Use at your own risk.
- `profiles/*_state.json` contain **live auth tokens** — treat as secrets, do not commit.
