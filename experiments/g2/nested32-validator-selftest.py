import importlib.util
from pathlib import Path
f=Path(r"<LOCAL_LAB_ROOT>\scripts\gptoss-g2-nested32-fixed-gate.py")
spec=importlib.util.spec_from_file_location("nested",f)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
for rel in mod.FILES:
 s=(mod.BASE/rel).read_text("utf8")
 print("BASELINE_STATIC_PASS",mod.static_check(rel,s))
for code in ("import os\ndef deep_merge(base,overrides):return os.system('whoami')","def deep_merge(base,overrides):\n while True:pass","def deep_merge(base,overrides):return eval('2+2')"):
 try:mod.static_check("src/merge.py",code)
 except (ValueError,SyntaxError) as exc:print("UNTRUSTED_CODE_REJECTED",str(exc))
 else:raise AssertionError("UNSAFE_CODE_ACCEPTED")
print("SELFTEST_PASS")
