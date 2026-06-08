import os, json, time
from cloakbrowser import launch_persistent_context

USER_DIR="/home/ubuntu/chatly-mcp/profiles/account1"
NETLOG="/home/ubuntu/chatly-mcp/recon/netlog.jsonl"
SHOTS="/home/ubuntu/chatly-mcp/recon/shots"
os.makedirs(SHOTS, exist_ok=True)

SKIP=("gstatic","googleapis","doubleclick","vercel-insights","sentry","segment",
      "intercom","hotjar","clarity","fonts.","facebook","tiktok","mixpanel",
      "growthbook","bing","/_next/","challenges.cloudflare","cdn.","braze","clarity")
def interesting(u):
    if any(h in u for h in SKIP): return False
    return ("vyro.ai" in u or "chatlyai.app/api" in u or "/apis/" in u
            or "imagineart" in u or "graphql" in u)
def netlog(o):
    o["ts"]=time.time()
    with open(NETLOG,"a") as f: f.write(json.dumps(o,ensure_ascii=False)+"\n")
def wire(page):
    def on_req(req):
        if not interesting(req.url): return
        e={"k":"req","method":req.method,"url":req.url,"rtype":req.resource_type}
        try:
            h=req.headers
            e["auth"]= ("authorization" in h)
            pd=req.post_data
            if pd and len(pd)<6000: e["body"]=pd
        except Exception: pass
        netlog(e)
    def on_resp(resp):
        if not interesting(resp.url): return
        e={"k":"resp","status":resp.status,"url":resp.url,"ct":resp.headers.get("content-type","")}
        if "json" in e["ct"] or "text" in e["ct"]:
            try: e["body"]=resp.text()[:9000]
            except Exception: pass
        netlog(e)
    page.on("request",on_req); page.on("response",on_resp)
def shot(page,n):
    try: page.screenshot(path=f"{SHOTS}/{n}.png", full_page=False); print("shot",n,page.url)
    except Exception as e: print("shot fail",n,e)

def dump_inputs(page,label):
    info=page.evaluate("""()=>{
      const q=(s)=>[...document.querySelectorAll(s)].map(e=>({tag:e.tagName,type:e.type||'',ph:e.placeholder||'',aria:e.getAttribute('aria-label')||'',name:e.name||'',role:e.getAttribute('role')||'',txt:(e.innerText||'').slice(0,40)}));
      return {textareas:q('textarea'),inputs:q('input'),buttons:q('button').slice(0,40)};
    }""")
    print("== DOM",label,"==")
    print(json.dumps(info,ensure_ascii=False)[:2500])

def main():
    ctx=launch_persistent_context(USER_DIR, headless=False, humanize=True,
                                  viewport={"width":1280,"height":900})
    page=ctx.pages[0] if ctx.pages else ctx.new_page()
    wire(page); ctx.on("page",lambda p:wire(p))
    page.goto("https://chatlyai.app/agent/image", wait_until="domcontentloaded", timeout=60000)
    time.sleep(6)
    shot(page,"20_image_page")
    dump_inputs(page,"image")
    print("READY; sleeping 1200s for manual/scripted recon")
    time.sleep(1200)

if __name__=="__main__":
    main()
