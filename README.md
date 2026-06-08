# Chatly MCP (PoC)

Remote-control your **ChatlyAI** (chatlyai.app) accounts through an **MCP server** —
generate images, write scripts/kịch bản, chat, check credits, and (later) video/workflow.

ChatlyAI has **no public API**. It's a Next.js app on top of **Vyro AI**'s internal
services, and its login is protected by **Cloudflare Turnstile**, which blocks ordinary
automation. This PoC solves both:

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
   POST streaming-chatly.vyro.ai/v2/hyper-agent/completions/async   (SSE)
                           │
        ┌──────────────────┴───────────────────┐
   dashboard_id="image"                  dashboard_id=null
   → image URLs (cdn.omniagent...)       → text (script/chat)
```

The `/v2/hyper-agent/completions/async` endpoint is the **unified OmniAgent**: the same
call drives images, text, and (by changing `dashboard_id` / `dashboard_params`) other
dashboards. The response is a Server-Sent-Events stream; `client.py` assembles `text`
chunks and `file`/image events.

### Key endpoints discovered
| Purpose | Endpoint |
|---|---|
| Generate (image/text/…) | `POST streaming-chatly.vyro.ai/v2/hyper-agent/completions/async` |
| Credits | `GET xipe.vyro.ai/v1/credit?org_id=…` |
| Quota | `GET streaming-chatly.vyro.ai/v2/user/quota` |
| Chats list | `GET streaming-chatly.vyro.ai/v2/chat/all-chat` |
| Auth (check email) | `POST auth.vyro.ai/apis/v1/auth/custom/check-email/{email}` |

Auth headers: `authorization: Bearer <token>`, `x-org-id: <organization-id>`.

## Install

```bash
cd chatly-mcp
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
      "cwd": "/home/ubuntu/chatly-mcp"
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
| `chatly_create_script(prompt, account?)` | Long-form text / kịch bản. |
| `chatly_chat(prompt, account?, web_search?)` | Ask the OmniAgent. |
| `chatly_login(email, password, name?)` | Add/refresh an account (needs display). |

`account` defaults to the first configured account. Use `chatly_list_accounts` to see names.

## Multi-account

Drop one `*_state.json` per account in `profiles/`. `AccountStore.pick()` supports
round-robin selection (useful to spread load / avoid rate limits). Per-tool `account=`
lets you pin a specific one.

## Status / next steps
- ✅ Login via CloakBrowser (Turnstile bypassed), session persistence
- ✅ Image generation (returns + downloads PNGs)
- ✅ Script / chat generation (text)
- ✅ Credits & quota
- ⏳ Video / music dashboards (same endpoint, different `dashboard_id`) — to map params
- ⏳ Node-based workflow automation (likely needs UI automation)
- ⏳ Token auto-refresh (refresh endpoint not yet found; re-login for now)
- ⏳ Async job queue for long video renders

## ⚠️ Notes
- Automating multiple accounts may violate ChatlyAI's Terms of Service. Use at your own risk.
- `profiles/*_state.json` contain **live auth tokens** — treat as secrets, do not commit.
