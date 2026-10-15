#!/usr/bin/env python3
import json,sys,time
from pathlib import Path
from urllib.request import Request,urlopen
sys.path.insert(0,str(Path(__file__).parent))
from g4_checkpoint import index_corpus,get_sources,selected_valid,SYSTEM
URL="http://127.0.0.1:18991"
idx,notes,events=index_corpus()
cid="INC-01"
node=idx["CASE"][cid][1]["entry"]
payload={"goal":"Choose one next hop for this case, only current node.",
         "case":cid,"cursor":node,"source_records":get_sources(node,idx,events),
         "output":"one JSON object {decisions:[{case,node,revision,next,team,seal}]}"}
messages=[{"role":"system","content":SYSTEM},
          {"role":"user","content":json.dumps(payload,separators=(",",":"))}]
def post(uri,body):
 req=Request(URL+uri,data=json.dumps(body).encode(),headers={"Content-Type":"application/json"},method="POST")
 with urlopen(req,timeout=125) as res:return json.load(res)
proof={}
for effort in ("high","medium"):
 data=post("/apply-template",{"messages":messages,"chat_template_kwargs":{"reasoning_effort":effort}})
 prompt=data.get("prompt","")
 header=prompt[:650]
 proof[effort]={"high":bool(__import__("re").search(r"(?i)reasoning:\s*high",header)),
                "medium":bool(__import__("re").search(r"(?i)reasoning:\s*medium",header)),
                "excerpt":header[:230]}
 print("TEMPLATE_"+effort+" "+json.dumps(proof[effort]),flush=True)
if not proof["high"]["high"] or not proof["medium"]["medium"]:
 raise RuntimeError("PER_REQUEST_EFFORT_OVERRIDE_UNSUPPORTED")
start=time.perf_counter()
reply=post("/v1/chat/completions",{
 "model":"ncma-gptoss","messages":messages,
 "chat_template_kwargs":{"reasoning_effort":"medium"},
 "max_tokens":2200,"temperature":0,"stream":False})
msg=reply.get("choices",[{}])[0].get("message") or {}
text=msg.get("content") or ""
try:
 out=json.loads(text)
 d=(out.get("decisions") or [None])[0]
 error=selected_valid({"cursor":node,"path":[]},d,idx)
except Exception as exc:error=repr(exc)
result={"mode":"medium-override","case":cid,"correct":error is None,
 "error":error,"finish":reply.get("choices",[{}])[0].get("finish_reason"),
 "usage":reply.get("usage"),"final":text[:750],
 "elapsed":round(time.perf_counter()-start,2),"proof":proof}
p=Path(__file__).parent/"mode_override_probe.json"
p.write_text(json.dumps(result,indent=2),encoding="utf-8")
print("MODE_OVERRIDE_RESULT "+json.dumps(result),flush=True)
sys.exit(0 if error is None else 2)
