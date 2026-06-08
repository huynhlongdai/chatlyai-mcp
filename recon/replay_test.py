import json, httpx, sys

state=json.load(open("/home/ubuntu/chatly-mcp/profiles/account1_state.json"))
cookies={c["name"]:c["value"] for c in state["cookies"]}
TOKEN=cookies.get("token")
ORG=cookies.get("organization-id")
print("token present:", bool(TOKEN), "len", len(TOKEN or ""))
print("org-id:", ORG)

UA=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36")
H={"authorization": f"Bearer {TOKEN}", "x-org-id": ORG or "",
   "referer":"https://chatlyai.app/", "origin":"https://chatlyai.app",
   "user-agent": UA, "accept":"*/*"}

with httpx.Client(timeout=30, headers=H) as c:
    for url in ["https://streaming-chatly.vyro.ai/v2/user/quota",
                f"https://xipe.vyro.ai/v1/credit?org_id={ORG}"]:
        try:
            r=c.get(url)
            print("\nGET", url, "->", r.status_code, "ct=", r.headers.get("content-type"))
            print(r.text[:300])
        except Exception as e:
            print("ERR", url, e)
