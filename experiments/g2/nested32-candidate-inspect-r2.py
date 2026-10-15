import importlib.util
from pathlib import Path
modpath=Path(r"<LOCAL_LAB_ROOT>\scripts\gptoss-g2-nested32-fixed-gate-r2.py")
spec=importlib.util.spec_from_file_location("gate_r2",modpath)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
proposal=Path(r"<LOCAL_LAB_ROOT>\bench\gptoss-g2\proposals\mx-nested_config-b713e92f-458")
for item in m.FILES:
 result=m.static_check(item,(proposal/item).read_text("utf8"))
 print("CANDIDATE_STATIC_PASS",result)
for text in ("import os\ndef deep_merge(a,b):return os.system('x')","def deep_merge(a,b):\n while True: pass","def deep_merge(a,b):return eval('2+2')"):
 try:m.static_check("src/merge.py",text)
 except (SyntaxError,ValueError) as e:print("DENIED",str(e))
 else:raise AssertionError("DANGEROUS_CODE_ACCEPTED")
