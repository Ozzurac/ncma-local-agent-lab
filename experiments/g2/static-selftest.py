import importlib.util
from pathlib import Path
p=Path(r"<LOCAL_LAB_ROOT>\scripts\gptoss-g2-fixed-gate.py")
sp=importlib.util.spec_from_file_location("g2_gate",str(p))
mod=importlib.util.module_from_spec(sp)
sp.loader.exec_module(mod)
root=Path(r"<LOCAL_LAB_ROOT>\bench\gptoss-g2\baseline\workflow_retry")
for rel in mod.FILES:
    source=(root/rel).read_text(encoding="utf-8")
    meta=mod.restricted_module(rel,source)
    print("STATIC_BASELINE_OK",rel,meta["methods"])
attack_samples=[
 ("src/ledger.py",'import os\nclass InMemoryLedger:\n    pass\n'),
 ("src/ledger.py",'class InMemoryLedger:\n    def __init__(self):\n        eval("hello")\n'),
 ("src/ledger.py",'class InMemoryLedger:\n    def __init__(self):\n        while True: pass\n'),
]
for rel,source in attack_samples:
    try:
        mod.restricted_module(rel,source.replace("\n","\n"))
        raise AssertionError("GUARD_ACCEPTED_ATTACK")
    except ValueError as e:
        print("REJECTED",str(e))
print("GATE_STATIC_SELFTEST_PASS")
