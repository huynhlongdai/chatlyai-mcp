import asyncio, json, time, sys
from playwright.async_api import async_playwright

OUT = "/home/ubuntu/chatly-mcp/recon/netlog.jsonl"
CDP = "http://localhost:29229"

def log(obj):
    obj["ts"] = time.time()
    with open(OUT, "a") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

SKIP_HOSTS = ("google", "gstatic", "googleapis", "doubleclick", "vercel-insights",
              "sentry", "segment", "intercom", "hotjar", "clarity", "cdn-cgi",
              "fonts.", "analytics", "facebook", "tiktok")

def interesting(url):
    if any(h in url for h in SKIP_HOSTS):
        return False
    return ("chatlyai" in url or "imagineart" in url or "/api/" in url
            or "graphql" in url or "supabase" in url)

async def attach(page):
    async def on_request(req):
        try:
            if not interesting(req.url):
                return
            entry = {"k": "req", "method": req.method, "url": req.url,
                     "rtype": req.resource_type}
            pd = req.post_data
            if pd and len(pd) < 4000:
                entry["body"] = pd
            log(entry)
        except Exception as e:
            pass
    async def on_response(resp):
        try:
            if not interesting(resp.url):
                return
            ct = resp.headers.get("content-type", "")
            entry = {"k": "resp", "status": resp.status, "url": resp.url, "ct": ct}
            if "json" in ct or "text" in ct:
                try:
                    body = await resp.text()
                    entry["body"] = body[:6000]
                except Exception:
                    pass
            log(entry)
        except Exception:
            pass
    page.on("request", on_request)
    page.on("response", on_response)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP)
        print("connected; contexts:", len(browser.contexts))
        seen = set()
        async def wire(ctx):
            ctx.on("page", lambda pg: asyncio.create_task(attach(pg)))
            for pg in ctx.pages:
                await attach(pg)
        for ctx in browser.contexts:
            await wire(ctx)
        browser.on("disconnected", lambda: print("disconnected"))
        print("sniffing... writing to", OUT)
        while True:
            await asyncio.sleep(2)

asyncio.run(main())
