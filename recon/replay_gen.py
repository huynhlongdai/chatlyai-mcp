import json, httpx, uuid, sys, time

state=json.load(open("/home/ubuntu/chatly-mcp/profiles/account1_state.json"))
cookies={c["name"]:c["value"] for c in state["cookies"]}
TOKEN=cookies.get("token"); ORG=cookies.get("organization-id")
UA=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36")
H={"authorization": f"Bearer {TOKEN}", "x-org-id": ORG,
   "referer":"https://chatlyai.app/", "origin":"https://chatlyai.app",
   "user-agent": UA, "accept":"*/*"}

chat_id=str(uuid.uuid4()); msg_id=str(uuid.uuid4())
prompt = sys.argv[1] if len(sys.argv)>1 else "a cute red panda astronaut floating in space, digital art, vibrant"
data={
  "id":chat_id, "agent_mode":"thinking", "connected_accounts":{},
  "web_search":False, "project_id":None, "dashboard_id":"image",
  "dashboard_params":{"style_id":"40603","aspect_ratio":"1:1","resolution":"1K","count":1},
  "messages":[{"id":msg_id,"role":"user","content":[{"type":"text","text":prompt}]}]
}
print("chat_id",chat_id)
url="https://streaming-chatly.vyro.ai/v2/hyper-agent/completions/async"
out=open("/home/ubuntu/chatly-mcp/recon/sse_dump.txt","w")
t0=time.time()
with httpx.Client(timeout=180, headers=H) as c:
    with c.stream("POST", url, files={"data":(None, json.dumps(data))}) as r:
        print("status",r.status_code,"ct",r.headers.get("content-type"))
        for line in r.iter_lines():
            if line is None: continue
            out.write(line+"\n"); out.flush()
            ln=line.strip()
            if ln:
                print(f"[{time.time()-t0:6.1f}] {ln[:300]}")
print("chat_id for fetch:",chat_id)
