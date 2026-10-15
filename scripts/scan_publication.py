#!/usr/bin/env python3
"""Fail-closed publication review. Scans ONLY explicitly curated export directory."""
import json,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXT={".md",".py",".json",".ts",".mjs",".yml",".yaml",".ps1",".txt",".log",
     ".toml",".lock",".gitignore"}
DENIED_EXT={".gguf",".safetensors",".pt",".onnx",".pfx",".pem",".key",".exe",".dll",".db",".sqlite",".sqlite3"}
DENIED_DIRS={"models","cache","logs","node_modules",".venv",".git","runs","generated","__pycache__",".pytest_cache"}
SECRET_PATTERNS={
 "PAT_PREFIX":r"(?:ghp_|gho_|ghu_|ghs_|github_pat_)[A-Za-z0-9_]{16,}",
 "OPENAI_KEY":r"(?:sk-proj-|sk-[A-Za-z0-9]{18,})[A-Za-z0-9_-]{8,}",
 "GOOGLE_API_KEY":r"AIza[0-9A-Za-z_-]{30,}",
 "PRIVATE_KEY":r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
 "LIVE_BEARER":r"(?i)authorization[^\n]{0,24}bearer\s+[A-Za-z0-9._-]{25,}",
 "HOME_PATH":r"(?i)[A-Z]:\\(?:users|documents and settings)\\[^\s\"']+",
 "LOCAL_ABSOLUTE_LAB":r"(?i)[A-Z]:\\NCMA-Local-Agent-Lab",
 "PERSONAL_EMAIL":r"(?i)\b[A-Z0-9._%+-]+@(?:gmail|outlook|hotmail|protonmail|yahoo)\.[A-Z]{2,}\b"
}
def main():
 files=[]; issues=[]
 for f in ROOT.rglob("*"):
    rel=f.relative_to(ROOT)
    if any(part in DENIED_DIRS for part in rel.parts):continue
    if f.is_symlink():issues.append({"file":rel.as_posix(),"issue":"SYMLINK"});continue
    if not f.is_file():continue
    if f.suffix.lower() in DENIED_EXT:issues.append({"file":rel.as_posix(),"issue":"MODEL_OR_BINARY"});continue
    if f.stat().st_size>1_800_000:issues.append({"file":rel.as_posix(),"issue":"UNEXPECTED_FILE_SIZE"});continue
    if f.suffix.lower() not in EXT and f.name not in {"LICENSE","AGENTS.md","README.md","CONTRIBUTING.md","SECURITY.md",".gitignore",".gitattributes"}:
       issues.append({"file":rel.as_posix(),"issue":"UNAPPROVED_EXTENSION"});continue
    if f.name.endswith(".log") and not (rel.parts[:3]==("benchmarks","g2","evidence") and f.name.endswith(".tests.log")):
       issues.append({"file":rel.as_posix(),"issue":"RAW_LOG"});continue
    try:text=f.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
       issues.append({"file":rel.as_posix(),"issue":"NON_UTF8_FILE"});continue
    for label,pattern in SECRET_PATTERNS.items():
       if re.search(pattern,text):
          issues.append({"file":rel.as_posix(),"issue":label})
    files.append(f)
 if not (ROOT/"README.md").exists() or not (ROOT/"LICENSE").exists():
    issues.append({"file":"<repo>","issue":"MISSING_META"})
 print(json.dumps({"pass":not bool(issues),"files_reviewed":len(files),
    "bytes_reviewed":sum(p.stat().st_size for p in files),
    "issues":issues},ensure_ascii=False,indent=2))
 return 0 if not issues else 4
if __name__=="__main__":
 raise SystemExit(main())
