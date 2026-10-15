import importlib.util
from pathlib import Path
p=Path(r"<LOCAL_LAB_ROOT>\scripts\gptoss-g2-fixed-gate.py")
sp=importlib.util.spec_from_file_location("g2",str(p))
gate=importlib.util.module_from_spec(sp)
sp.loader.exec_module(gate)
root=Path(r"<LOCAL_LAB_ROOT>\bench\gptoss-g2\proposals\mx-workflow_retry-59d04b09-b08")
for file_id in gate.FILES:
  source=(root/file_id).read_text(encoding="utf-8")
  try:
    print("STATIC_OK",gate.restricted_module(file_id,source))
  except Exception as e:
    print("STATIC_FAIL",file_id,str(e))
