import os, json, time
from cloakbrowser import launch_persistent_context

USER_DIR = "/home/ubuntu/chatly-mcp/profiles/account1"
NETLOG = "/home/ubuntu/chatly-mcp/recon/netlog.jsonl"
SHOTS = "/home/ubuntu/chatly-mcp/recon/shots"
STATE = "/home/ubuntu/chatly-mcp/profiles/account1_state.json"
os.makedirs(USER_DIR, exist_ok=True); os.makedirs(SHOTS, exist_ok=True)

EMAIL = os.environ["CHATLYAI_EMAIL"]; PASSWORD = os.environ["CHATLYAI_PASSWORD"]

SKIP = ("google", "gstatic", "googleapis", "doubleclick", "vercel-insights",
        "sentry", "segment", "intercom", "hotjar", "clarity", "fonts.",
        "facebook", "tiktok")

def interesting(url):
    if any(h in url for h in SKIP):
        return False
    return ("vyro.ai" in url or "chatlyai" in url or "imagineart" in url
            or "/api/" in url or "graphql" in url or "challenges.cloudflare" in url)

def netlog(o):
    o["ts"] = time.time()
    with open(NETLOG, "a") as f: f.write(json.dumps(o, ensure_ascii=False)+"\n")

def wire(page):
    def on_req(req):
        if not interesting(req.url): return
        e={"k":"req","method":req.method,"url":req.url,"rtype":req.resource_type}
        try:
            pd=req.post_data
            if pd and len(pd)<5000: e["body"]=pd
        except Exception: pass
        netlog(e)
    def on_resp(resp):
        if not interesting(resp.url): return
        e={"k":"resp","status":resp.status,"url":resp.url,"ct":resp.headers.get("content-type","")}
        if "json" in e["ct"] or "text" in e["ct"]:
            try: e["body"]=resp.text()[:8000]
            except Exception: pass
        netlog(e)
    page.on("request", on_req); page.on("response", on_resp)

def shot(page,name):
    try: page.screenshot(path=f"{SHOTS}/{name}.png"); print("shot",name,page.url)
    except Exception as e: print("shot fail",name,e)

def tstoken(page):
    try:
        return page.evaluate("""()=>{const el=document.querySelector('input[name=\"cf-turnstile-response\"],textarea[name=\"cf-turnstile-response\"]');return el?(el.value||'').length:-1;}""")
    except Exception: return -2

def main():
    ctx = launch_persistent_context(USER_DIR, headless=False, humanize=True,
                                    viewport={"width":1280,"height":900})
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    wire(page); ctx.on("page", lambda p: wire(p))

    page.goto("https://accounts.vyro.ai/auth/sign-in?redirect=https%3A%2F%2Fchatlyai.app%2F&product=chatly",
              wait_until="domcontentloaded", timeout=60000)
    time.sleep(3)
    page.fill('input[name="email"]', EMAIL); time.sleep(1)
    page.click('form button:has-text("Continue")', timeout=8000)
    page.wait_for_selector('input[name="password"]', timeout=20000)
    page.fill('input[name="password"]', PASSWORD); time.sleep(1)
    shot(page,"10_pw")

    # click the turnstile checkbox by locating the cloudflare iframe bbox
    print("token before:", tstoken(page))
    box=None
    for sel in ['iframe[src*="challenges.cloudflare.com"]','div.cf-turnstile','#turnstile-widget','div[class*="turnstile"]']:
        el=page.query_selector(sel)
        if el:
            try:
                box=el.bounding_box()
                if box: print("turnstile elem",sel,box); break
            except Exception: pass
    if box:
        cx=box["x"]+28; cy=box["y"]+box["height"]/2
        print("clicking checkbox at",cx,cy)
        page.mouse.move(cx-60,cy-40); time.sleep(0.3)
        page.mouse.click(cx,cy)
    else:
        print("no turnstile box; clicking fallback 450,462")
        page.mouse.click(450,462)

    # wait for token
    got=False
    for i in range(40):
        time.sleep(2)
        t=tstoken(page)
        print(f"poll {i} token_len={t}")
        if isinstance(t,int) and t>5:
            got=True; break
    shot(page,"11_after_turnstile")
    print("token after:", tstoken(page), "got=",got)

    page.click('form button[type="submit"]', timeout=8000)
    for i in range(30):
        time.sleep(2)
        u=page.url
        print("post-submit url:",u)
        if "chatlyai.app" in u and "/auth" not in u: break
        if "/auth/sign-in/email" not in u and "accounts.vyro.ai" not in u: break
    shot(page,"12_after_submit")

    try:
        ls=page.evaluate("()=>JSON.stringify(Object.fromEntries(Object.entries(localStorage)))")
        open("/home/ubuntu/chatly-mcp/recon/localstorage.json","w").write(ls)
        print("ls saved len",len(ls))
    except Exception as e: print("ls err",e)
    try:
        ctx.storage_state(path=STATE); print("state saved",STATE)
    except Exception as e: print("state err",e)
    print("DONE; keeping browser open 900s")
    time.sleep(900)

if __name__=="__main__":
    main()
