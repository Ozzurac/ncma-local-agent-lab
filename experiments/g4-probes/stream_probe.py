#!/usr/bin/env python3
"""Probe GPT-OSS streaming reasoning intervention on one actual corpus hop."""
import json,sys,time
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from g4_checkpoint import index_corpus,get_sources,selected_valid,SYSTEM

URL="http://127.0.0.1:18991/v1/chat/completions"
idx,notes,events=index_corpus()
cid="INC-01"
cur=idx["CASE"][cid][1]["entry"]
evidence=get_sources(cur,idx,events)
prompt={
 "task":"Advance exactly one hop for this case. Answer NOW as JSON decisions array.",
 "case":cid,"current":cur,"evidence":evidence,
 "untrusted_note":notes[0],
 "required_keys":["case","node","revision","next","team","seal"]
}
body={
 "model":"ncma-gptoss","messages":[
  {"role":"system","content":SYSTEM},
  {"role":"user","content":json.dumps(prompt,separators=(",",":"))}
 ],"temperature":0,"max_tokens":1800,"stream":True,
 "reasoning_control":True
}
def post_control(request_id):
 data=json.dumps({"id":request_id,"action":"reasoning_end"}).encode()
 r=Request(URL+"/control",data=data,headers={"Content-Type":"application/json"},method="POST")
 try:
  with urlopen(r,timeout=12) as h:return json.loads(h.read())
 except HTTPError as err:return {"http_error":err.code,"body":err.read(500).decode("utf-8","replace")}
 except Exception as err:return {"error":str(err)}
req=Request(URL,data=json.dumps(body).encode(),headers={"Content-Type":"application/json"},method="POST")
reasoning_events=0
final_parts=[]
control_result=None
finish=None
request_id=None
start=time.monotonic()
try:
 with urlopen(req,timeout=160) as stream:
  for raw in stream:
   line=raw.decode("utf-8","replace").strip()
   if not line.startswith("data:"):continue
   chunk=line[5:].strip()
   if chunk=="[DONE]":break
   event=json.loads(chunk)
   request_id=event.get("id",request_id)
   for choice in event.get("choices") or []:
    delta=choice.get("delta") or {}
    if delta.get("reasoning_content"):reasoning_events+=1
    if delta.get("content"):final_parts.append(delta["content"])
    if choice.get("finish_reason"):finish=choice["finish_reason"]
   if reasoning_events>=340 and control_result is None and request_id:
    control_result=post_control(request_id)
    print("CONTROL "+json.dumps(control_result),flush=True)
except HTTPError as err:
 print("REQUEST_HTTP_ERROR "+str(err.code)+" "+err.read(900).decode("utf-8","replace"),flush=True)
 sys.exit(4)
out="".join(final_parts)
try:
 j=json.loads(out)
 decision=(j.get("decisions") or [None])[0]
 valid=selected_valid({"cursor":cur,"path":[]},decision,idx)
except Exception as err:valid=type(err).__name__+":"+str(err)
report={
 "case":cid,"cursor":cur,"high":True,"reasoning_events":reasoning_events,
 "control":control_result,"finish_reason":finish,"final_bytes":len(out.encode()),
 "elapsed":round(time.monotonic()-start,2),"decision_error":valid,
 "final_excerpt":out[:900]
}
Path(__file__).parent.joinpath("stream_probe_result.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("STREAM_PROBE "+json.dumps(report),flush=True)
sys.exit(0 if valid is None else 2)
