import ast, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

LAB=Path(r"<LOCAL_LAB_ROOT>").resolve(strict=True)
G2=LAB/"bench"/"gptoss-g2"
BASE=G2/"baseline"/"nested_config"
PROPS=G2/"proposals"
VERIFIED=G2/"verified_runs"
FILES=("src/merge.py","src/settings.py")
TRUSTED=("src/merge.py","src/settings.py","tests/test_config.py")
ALLOWED_NODE_TYPES=(
 ast.Module,ast.ImportFrom,ast.Import,ast.alias,ast.FunctionDef,ast.arguments,ast.arg,
 ast.Assign,ast.AnnAssign,ast.Expr,ast.Name,ast.Load,ast.Store,ast.Constant,
 ast.Return,ast.If,ast.For,ast.Break,ast.Continue,ast.Pass,ast.Raise,
 ast.Compare,ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE,ast.Is,
 ast.IsNot,ast.In,ast.NotIn,ast.BoolOp,ast.And,ast.Or,ast.UnaryOp,ast.Not,
 ast.Dict,ast.Set,ast.List,ast.Tuple,ast.Subscript,ast.Attribute,ast.Call,
 ast.DictComp,ast.ListComp,ast.SetComp,ast.comprehension,ast.IfExp,
 ast.BinOp,ast.Add,ast.Assert,ast.Slice,ast.JoinedStr,ast.FormattedValue
)
ALLOWED_CALLS={"isinstance","ValueError","TypeError","dict","list","set","tuple","deep_merge","deepcopy","deep_copy_dict","_validate_overrides","len"}
ALLOWED_ATTRS={"items","copy","get","update","keys","deepcopy"}
DISALLOWED_NAMES={"eval","exec","open","__import__","compile","input","globals",
                  "locals","getattr","setattr","delattr","vars","dir","breakpoint"}
def digest(path):
 return hashlib.sha256(path.read_bytes()).hexdigest()
def static_check(fileid,text):
 if not (0<len(text)<=7500) or "\0" in text:raise ValueError("BAD_SOURCE_SIZE")
 root=ast.parse(text,filename=fileid)
 funcs=[]
 for node in ast.walk(root):
  if not isinstance(node,ALLOWED_NODE_TYPES):
   raise ValueError("AST_NODE_DENIED_"+type(node).__name__)
  if isinstance(node,ast.Name) and (node.id.startswith("__") or node.id in DISALLOWED_NAMES):
   raise ValueError("IDENTIFIER_DENIED_"+node.id)
  if isinstance(node,ast.Attribute) and node.attr not in ALLOWED_ATTRS:
   raise ValueError("ATTRIBUTE_DENIED_"+node.attr)
  if isinstance(node,ast.Call):
   call=node.func
   if isinstance(call,ast.Name):
    if call.id not in ALLOWED_CALLS:raise ValueError("FUNCTION_CALL_DENIED_"+call.id)
   elif isinstance(call,ast.Attribute):
    if call.attr not in ALLOWED_ATTRS:raise ValueError("METHOD_CALL_DENIED")
    if not isinstance(call.value,ast.Name):raise ValueError("COMPUTED_RECEIVER_DENIED")
    if call.value.id in DISALLOWED_NAMES:raise ValueError("CALL_RECEIVER_DENIED")
   else:raise ValueError("DYNAMIC_CALL_DENIED")
  if isinstance(node,ast.Constant) and isinstance(node.value,str) and len(node.value)>950:
   raise ValueError("LONG_LITERAL_DENIED")
  if isinstance(node,ast.FunctionDef):
   funcs.append(node.name)
   if node.decorator_list or node.args.defaults or any(v is not None for v in node.args.kw_defaults):
    raise ValueError("DYNAMIC_FUNCTION_DEFINITION_DENIED")
  if isinstance(node,ast.Import):
   if any(x.name!="copy" or x.asname for x in node.names):raise ValueError("IMPORT_NOT_ALLOWED")
  if isinstance(node,ast.ImportFrom):
   if not ((node.level==1 and node.module=="merge" and len(node.names)==1 and node.names[0].name=="deep_merge")
           or (node.level==0 and node.module=="copy" and len(node.names)==1 and node.names[0].name=="deepcopy") or (node.level==0 and node.module=="__future__" and len(node.names)==1 and node.names[0].name=="annotations")):
    raise ValueError("IMPORT_NOT_ALLOWED")
  if isinstance(node,ast.BinOp) and not isinstance(node.op,ast.Add):
   raise ValueError("ARITHMETIC_DENIED")
 if len(funcs)>5:raise ValueError("TOO_MANY_FUNCTIONS")
 if sum(isinstance(n,ast.For) for n in ast.walk(root))>4:raise ValueError("EXCESSIVE_LOOPING")
 if fileid=="src/merge.py" and "deep_merge" not in funcs:raise ValueError("CORE_MERGE_MISSING")
 if fileid=="src/settings.py" and "configure" not in funcs:raise ValueError("CORE_CONFIGURE_MISSING")
 if fileid=="src/settings.py":
  def schema_of(tree):
   for node in tree.body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=="SCHEMA":
     return ast.literal_eval(node.value)
   return None
  old=ast.parse((BASE/fileid).read_text("utf8"))
  if schema_of(root)!=schema_of(old):raise ValueError("SCHEMA_MODIFIED")
 for node in root.body:
  if isinstance(node,(ast.FunctionDef,ast.ImportFrom,ast.Import)):continue
  if fileid=="src/settings.py" and isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=="SCHEMA":continue
  if isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):continue
  raise ValueError("TOP_LEVEL_SIDE_EFFECT_DENIED")
 return {"file":fileid,"sha256":hashlib.sha256(text.encode()).hexdigest(),"functions":funcs}
def run(proposal):
 if proposal.is_symlink() or proposal.parent!=PROPS.resolve(strict=True):raise ValueError("INVALID_PROPOSAL")
 if not re.fullmatch(r"mx-nested_config-[A-Za-z0-9_-]{5,48}",proposal.name):raise ValueError("RUN_ID_NOT_ALLOWED")
 run_id=proposal.name
 report_path=VERIFIED/(run_id+".json")
 if report_path.exists() or (VERIFIED/run_id).exists():raise ValueError("RUN_ALREADY_REVIEWED")
 result={"run_id":run_id,"status":"REJECTED","checks":[]}
 workdir=VERIFIED/run_id
 try:
  sources={}
  for part in FILES:
   path=proposal/part
   if path.is_symlink() or not path.is_file() or proposal.resolve(strict=True) not in path.resolve(strict=True).parents:
    raise ValueError("PROPOSAL_SOURCE_INVALID")
   content=path.read_text("utf8")
   result["checks"].append(static_check(part,content))
   sources[part]=content
  workdir.mkdir(parents=True,exist_ok=False)
  shutil.copytree(BASE,workdir,dirs_exist_ok=True,ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
  for part in FILES:(workdir/part).write_text(sources[part],encoding="utf8")
  if digest(workdir/"tests/test_config.py")!=digest(BASE/"tests/test_config.py"):
   raise ValueError("TEST_SUITE_MODIFIED")
  env={k:v for k,v in os.environ.items() if k.upper() not in {"PYTHONPATH","PYTHONHOME","PYTHONSTARTUP","PYTHONINSPECT"}}
  env["PYTHONDONTWRITEBYTECODE"]="1"
  args=[sys.executable,"-B","-m","unittest","discover","-s","tests","-p","test_config.py","-v"]
  completed=subprocess.run(args,cwd=workdir,env=env,stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,text=True,errors="replace",timeout=20,shell=False)
  log=VERIFIED/(run_id+".tests.log")
  log.write_text(completed.stdout[:120000],"utf8")
  count=re.search(r"Ran (\d+) tests",completed.stdout)
  result["test"]={"exit":completed.returncode,"total":int(count.group(1)) if count else 0,
                  "tail":completed.stdout[-2500:],"log":str(log)}
  result["status"]="PASS_TESTED" if completed.returncode==0 and count and int(count.group(1))==11 else "FAIL_TESTS"
 except Exception as e:result["error"]=str(e)
 finally:
  result["original_intact"]=all(digest(LAB/"qwen-eval"/"nested_config"/f)==digest(BASE/f) for f in TRUSTED)
  if not result["original_intact"]:result["status"]="ORIGINAL_INTEGRITY_FAILED"
  report_path.write_text(json.dumps(result,indent=2),"utf8")
  print(json.dumps({"status":result["status"],"tests":result.get("test",{}).get("total"),
                    "error":result.get("error"),"report":str(report_path)}))
 return 0 if result["status"]=="PASS_TESTED" else 2
if __name__=="__main__":
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument("--proposal",required=True)
 opts=ap.parse_args()
 sys.exit(run(Path(opts.proposal).resolve(strict=True)))
