import json, httpx, uuid, sys, time
state=json.load(open("/home/ubuntu/chatly-mcp/profiles/account1_state.json"))
ck={c["name"]:c["value"] for c in state["cookies"]}
TOKEN=ck.get("token"); ORG=ck.get("organization-id")
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
H={"authorization":f"Bearer {TOKEN}","x-org-id":ORG,"referer":"https://chatlyai.app/","origin":"https://chatlyai.app","user-agent":UA,"accept":"*/*"}
chat_id=str(uuid.uuid4()); msg_id=str(uuid.uuid4())
prompt=sys.argv[1] if len(sys.argv)>1 else "Viết kịch bản video TikTok 30 giây quảng cáo quán cà phê, giọng trẻ trung."
data={"id":chat_id,"agent_mode":"thinking","connected_accounts":{},"web_search":False,"project_id":None,"dashboard_id":None,"dashboard_params":{},"messages":[{"id":msg_id,"role":"user","content":[{"type":"text","text":prompt}]}]}
url="https://streaming-chatly.vyro.ai/v2/hyper-agent/completions/async"
t0=time.time(); txt=[]
with httpx.Client(timeout=180,headers=H) as c:
  with c.stream("POST",url,files={"data":(None,json.dumps(data))}) as r:
    print("status",r.status_code,r.headers.get("content-type"))
    for line in r.iter_lines():
      if not line or not line.startswith("data:"): continue
      try: o=json.loads(line[5:].strip())
      except: continue
      ct=o.get("content"); ty=o.get("type")
      if ty=="text" and isinstance(ct,str): txt.append(ct)
      if ty in ("task_completed","metadata"): print(f"[{time.time()-t0:.1f}] {ty}")
print("\n==== ASSEMBLED TEXT (last text events) ====")
print(("".join(txt))[:1500])
