import os, json, time, sys
from cloakbrowser import launch_persistent_context

USER_DIR = "/home/ubuntu/chatly-mcp/profiles/account1"
NETLOG = "/home/ubuntu/chatly-mcp/recon/netlog.jsonl"
SHOTS = "/home/ubuntu/chatly-mcp/recon/shots"
STATE = "/home/ubuntu/chatly-mcp/profiles/account1_state.json"
os.makedirs(USER_DIR, exist_ok=True)
os.makedirs(SHOTS, exist_ok=True)

EMAIL = os.environ["CHATLYAI_EMAIL"]
PASSWORD = os.environ["CHATLYAI_PASSWORD"]

SKIP = ("google", "gstatic", "googleapis", "doubleclick", "vercel-insights",
        "sentry", "segment", "intercom", "hotjar", "clarity", "fonts.",
        "facebook", "tiktok", "challenges.cloudflare")

def interesting(url):
    if any(h in url for h in SKIP):
        return False
    return ("vyro.ai" in url or "chatlyai" in url or "imagineart" in url
            or "/api/" in url or "graphql" in url)

def netlog(obj):
    obj["ts"] = time.time()
    with open(NETLOG, "a") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def wire(page):
    def on_req(req):
        if not interesting(req.url):
            return
        e = {"k": "req", "method": req.method, "url": req.url, "rtype": req.resource_type}
        try:
            pd = req.post_data
            if pd and len(pd) < 5000:
                e["body"] = pd
        except Exception:
            pass
        netlog(e)
    def on_resp(resp):
        if not interesting(resp.url):
            return
        e = {"k": "resp", "status": resp.status, "url": resp.url,
             "ct": resp.headers.get("content-type", "")}
        if "json" in e["ct"] or "text" in e["ct"]:
            try:
                e["body"] = resp.text()[:8000]
            except Exception:
                pass
        netlog(e)
    page.on("request", on_req)
    page.on("response", on_resp)

def shot(page, name):
    try:
        page.screenshot(path=f"{SHOTS}/{name}.png")
        print("shot:", name, "url=", page.url)
    except Exception as e:
        print("shot fail", name, e)

def main():
    ctx = launch_persistent_context(USER_DIR, headless=False, humanize=True,
                                    viewport={"width": 1280, "height": 900})
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    wire(page)
    ctx.on("page", lambda p: wire(p))

    print("goto sign-in")
    page.goto("https://accounts.vyro.ai/auth/sign-in?redirect=https%3A%2F%2Fchatlyai.app%2F&product=chatly",
              wait_until="domcontentloaded", timeout=60000)
    time.sleep(3)
    shot(page, "01_signin")

    # email step
    page.fill('input[name="email"]', EMAIL)
    time.sleep(1)
    shot(page, "02_email")
    # click Continue
    try:
        page.click('form button:has-text("Continue")', timeout=8000)
    except Exception as e:
        print("continue1 click err", e)
    time.sleep(4)
    shot(page, "03_after_email")

    # password step
    try:
        page.wait_for_selector('input[name="password"]', timeout=20000)
        page.fill('input[name="password"]', PASSWORD)
        time.sleep(1)
        shot(page, "04_password")
    except Exception as e:
        print("password field err", e)

    # wait for turnstile to auto-solve; poll submit enabled
    print("waiting for turnstile / submit enable ...")
    for i in range(40):
        time.sleep(2)
        try:
            btn = page.query_selector('form button[type="submit"]')
            disabled = btn.get_attribute("disabled") if btn else "no-btn"
            # turnstile token
            tok = page.evaluate("""() => {
                const el = document.querySelector('input[name="cf-turnstile-response"], textarea[name="cf-turnstile-response"]');
                return el ? (el.value||'').length : -1;
            }""")
            print(f"poll {i}: submit_disabled={disabled} tstoken_len={tok}")
            if disabled is None:
                break
        except Exception as e:
            print("poll err", e)
    shot(page, "05_before_submit")

    # submit
    try:
        page.click('form button[type="submit"]', timeout=8000)
    except Exception as e:
        print("submit click err", e)

    # wait for redirect to chatlyai
    for i in range(30):
        time.sleep(2)
        u = page.url
        print("post-submit url:", u)
        if "chatlyai.app" in u and "/auth" not in u:
            break
    shot(page, "06_after_submit")

    # try to surface auth token from localStorage
    try:
        ls = page.evaluate("() => JSON.stringify(Object.fromEntries(Object.entries(localStorage)))")
        with open("/home/ubuntu/chatly-mcp/recon/localstorage.json", "w") as f:
            f.write(ls)
        print("localStorage keys saved")
    except Exception as e:
        print("ls err", e)

    try:
        ctx.storage_state(path=STATE)
        print("storage_state saved to", STATE)
    except Exception as e:
        print("state err", e)

    print("LOGIN SCRIPT DONE; leaving browser open 600s for further recon")
    time.sleep(600)

if __name__ == "__main__":
    main()
