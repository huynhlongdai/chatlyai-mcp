import os, json, time
from cloakbrowser import launch_persistent_context

USER_DIR="/home/ubuntu/chatly-mcp/profiles/account1"
NETLOG="/home/ubuntu/chatly-mcp/recon/netlog_img.jsonl"
SHOTS="/home/ubuntu/chatly-mcp/recon/shots"
os.makedirs(SHOTS, exist_ok=True)
open(NETLOG,"w").close()

SKIP=("gstatic","googleapis","doubleclick","vercel-insights","sentry","segment",
      "intercom","hotjar","clarity","fonts.","facebook","tiktok","mixpanel",
      "growthbook","bing","/_next/","challenges.cloudflare","braze",
      "google-analytics","analytics","datadog")
def interesting(u):
    if any(h in u for h in SKIP): return False
    return ("vyro.ai" in u or "chatlyai.app/api" in u or "/apis/" in u
            or "imagineart" in u or "graphql" in u or "generate" in u)
def netlog(o):
    o["ts"]=time.time()
    with open(NETLOG,"a") as f: f.write(json.dumps(o,ensure_ascii=False)+"\n")
def wire(page):
    def on_req(req):
        if not interesting(req.url): return
        e={"k":"req","method":req.method,"url":req.url,"rtype":req.resource_type}
        try:
            h=dict(req.headers)
            e["hdr_names"]=sorted(h.keys())
            e["has_auth"]= "authorization" in h
            e["ct_req"]=h.get("content-type","")
            pd=req.post_data
            if pd and len(pd)<8000: e["body"]=pd
        except Exception as ex: e["err"]=str(ex)
        netlog(e)
    def on_resp(resp):
        if not interesting(resp.url): return
        e={"k":"resp","status":resp.status,"url":resp.url,"ct":resp.headers.get("content-type","")}
        if "json" in e["ct"] or "text" in e["ct"] or "event-stream" in e["ct"]:
            try: e["body"]=resp.text()[:12000]
            except Exception: pass
        netlog(e)
    page.on("request",on_req); page.on("response",on_resp)
def shot(page,n):
    try: page.screenshot(path=f"{SHOTS}/{n}.png"); print("shot",n,page.url)
    except Exception as e: print("shot fail",n,e)

def main():
    ctx=launch_persistent_context(USER_DIR, headless=False, humanize=True,
                                  viewport={"width":1280,"height":900})
    page=ctx.pages[0] if ctx.pages else ctx.new_page()
    wire(page); ctx.on("page",lambda p:wire(p))
    page.goto("https://chatlyai.app/agent/image", wait_until="domcontentloaded", timeout=60000)
    time.sleep(6)

    # find prompt editor
    editor=None
    for sel in ['div[contenteditable="true"]','[role="textbox"]','textarea','p[data-placeholder]']:
        el=page.query_selector(sel)
        if el: editor=el; print("editor sel",sel); break
    if not editor:
        # click near placeholder text region
        page.mouse.click(660,282)
        time.sleep(1)
    prompt="a cute red panda astronaut floating in space, digital art"
    if editor:
        editor.click()
    page.keyboard.type(prompt, delay=20)
    time.sleep(1)
    shot(page,"30_prompt_typed")
    print("submitting via Enter")
    page.keyboard.press("Enter")
    # capture for a while
    for i in range(30):
        time.sleep(2)
        if i in (3,9,20): shot(page,f"31_gen_{i}")
    shot(page,"32_gen_final")
    print("DONE image gen recon; sleeping 300s")
    time.sleep(300)

if __name__=="__main__":
    main()
