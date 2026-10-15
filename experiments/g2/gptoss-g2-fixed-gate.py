#!/usr/bin/env python3
"""NCMA G2 fixed-policy review and test runner. Never executes agent-defined commands."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

LAB = Path(r"<LOCAL_LAB_ROOT>").resolve(strict=True)
BASE = LAB / "bench" / "gptoss-g2"
FILES = ("src/dispatch.py", "src/ledger.py")
MAX_SIZE = 7000
ATTRS = {
    "ledger", "deliver", "events", "get", "begin", "finish",
    "fail", "mark_failed", "record_failure", "copy", "status",
}
NAMES_CALLABLE = {"isinstance", "ValueError", "TypeError", "RuntimeError", "str", "dict"}
WHITELIST = (
    ast.Module, ast.ImportFrom, ast.alias, ast.ClassDef, ast.FunctionDef,
    ast.arguments, ast.arg, ast.Assign, ast.AugAssign, ast.Expr,
    ast.Name, ast.Load, ast.Store, ast.Constant, ast.Return, ast.If,
    ast.Compare, ast.Eq, ast.NotEq, ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.Dict,
    ast.Attribute, ast.Subscript, ast.Call, ast.Raise, ast.Try,
    ast.ExceptHandler, ast.Pass, ast.Add, ast.BinOp, ast.IfExp,
    ast.List, ast.Tuple, ast.Assert, ast.Mod,
)

def inside(child: Path, parent: Path) -> bool:
    return child == parent or parent in child.parents

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def restricted_module(file_id: str, source: str) -> dict:
    if len(source) > MAX_SIZE or "\x00" in source:
        raise ValueError("CANDIDATE_SIZE_INVALID")
    tree = ast.parse(source, filename=file_id)
    for node in ast.walk(tree):
        if not isinstance(node, WHITELIST):
            raise ValueError(f"DISALLOWED_AST_NODE_{type(node).__name__}")
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (bytes, complex)) or (
                isinstance(node.value, str) and len(node.value) > 1200
            ) or (isinstance(node.value, int) and abs(node.value) > 1_000_000):
                raise ValueError("DISALLOWED_CONSTANT")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_") or node.attr not in ATTRS:
                raise ValueError(f"DISALLOWED_ATTRIBUTE_{node.attr}")
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id not in NAMES_CALLABLE:
                    raise ValueError(f"DISALLOWED_NAMED_CALL_{func.id}")
            elif isinstance(func, ast.Attribute):
                # Only self.deliver(...), self.ledger.<known method>(...), or dict.get(...).
                if func.attr not in {"deliver", "get", "begin", "finish", "fail", "mark_failed", "record_failure", "copy"}:
                    raise ValueError(f"DISALLOWED_METHOD_CALL_{func.attr}")
                if not (
                    isinstance(func.value, ast.Name)
                    and func.value.id in {"self", "record", "event", "payload", "existing", "current"}
                    or isinstance(func.value, ast.Attribute)
                    and func.value.attr in {"ledger", "events"}
                    and isinstance(func.value.value, ast.Name)
                    and func.value.value.id == "self"
                ):
                    raise ValueError("DISALLOWED_CALL_RECEIVER")
            else:
                raise ValueError("DYNAMIC_CALL_DENIED")
        if isinstance(node, ast.Name) and (
            node.id.startswith("__") or node.id in {
                "eval", "exec", "open", "__import__", "globals", "locals",
                "compile", "input", "breakpoint", "super", "type", "getattr",
                "setattr", "delattr", "vars", "dir", "memoryview",
            }
        ):
            raise ValueError("DANGEROUS_NAME_DENIED")
        if isinstance(node, ast.BinOp) and not (
            isinstance(node.op, ast.Add)
            or (
                isinstance(node.op, ast.Mod)
                and isinstance(node.left, ast.Constant)
                and node.left.value == "payload mismatch for event id %s"
                and isinstance(node.right, ast.Name)
                and node.right.id == "event_id"
            )
        ):
            raise ValueError("UNSAFE_ARITHMETIC")
    if file_id == "src/dispatch.py":
        if len(tree.body) not in (2, 3) or not isinstance(tree.body[0], ast.ImportFrom):
            raise ValueError("DISPATCH_IMPORT_MUST_MATCH_BASELINE")
        imp = tree.body[0]
        if imp.level != 1 or imp.module != "ledger" or len(imp.names) != 1 or imp.names[0].name != "InMemoryLedger":
            raise ValueError("DISPATCH_IMPORT_CHANGED")
        if len(tree.body) == 3:
            mapping = tree.body[1]
            if not isinstance(mapping, ast.ImportFrom) or mapping.level != 0 or mapping.module != "collections.abc" or len(mapping.names) != 1 or mapping.names[0].name != "Mapping":
                raise ValueError("UNAPPROVED_IMPORT")
        cls = tree.body[-1]
        class_name = "Dispatcher"
        allowed_methods = {"__init__", "handle"}
    elif file_id == "src/ledger.py":
        if len(tree.body) != 1:
            raise ValueError("LEDGER_TOP_LEVEL_SHAPE")
        cls = tree.body[0]
        class_name = "InMemoryLedger"
        allowed_methods = {"__init__", "get", "begin", "finish", "fail", "mark_failed", "record_failure"}
    else:
        raise ValueError("UNEXPECTED_FILE_ID")
    if not isinstance(cls, ast.ClassDef) or cls.name != class_name or cls.bases or cls.decorator_list or cls.keywords:
        raise ValueError("CLASS_SHAPE_CHANGED")
    methods = set()
    for node in cls.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if not isinstance(node, ast.FunctionDef):
            raise ValueError("NON_METHOD_IN_CLASS")
        if node.name not in allowed_methods or node.name in methods:
            raise ValueError("INVALID_METHOD")
        methods.add(node.name)
        if node.decorator_list or node.returns is not None or node.args.defaults or node.args.kw_defaults:
            raise ValueError("DYNAMIC_METHOD_DEFINITION")
        if any(arg.annotation is not None and not (isinstance(arg.annotation, ast.Name) and arg.annotation.id == "InMemoryLedger") for arg in node.args.args):
            raise ValueError("METHOD_ANNOTATION_DENIED")
    if not {"__init__", "handle"}.issubset(methods) and file_id == "src/dispatch.py":
        raise ValueError("CORE_METHOD_MISSING")
    if file_id == "src/ledger.py" and not {"__init__", "get", "begin", "finish"}.issubset(methods):
        raise ValueError("CORE_METHOD_MISSING")
    return {"file": file_id, "class": class_name, "methods": sorted(methods), "sha256": hashlib.sha256(source.encode()).hexdigest()}

def validate(payload: dict, proposal_dir: Path):
    if proposal_dir.is_symlink() or not inside(proposal_dir, BASE / "proposals"):
        raise ValueError("PROPOSAL_DIR_NOT_ALLOWED")
    contents = {}
    for file_id in FILES:
        p = (proposal_dir / file_id)
        if p.is_symlink() or not p.is_file() or not inside(p.resolve(strict=True), proposal_dir):
            raise ValueError("CANDIDATE_FILE_NOT_PRESENT_OR_ESCAPE")
        content = p.read_text(encoding="utf-8")
        details = restricted_module(file_id, content)
        payload["static_check"].append(details)
        contents[file_id] = content
    return contents

def run_tests(workspace: Path, log_path: Path):
    # Fixed known unittest suite. The LLM cannot supply subprocess arguments.
    cmd = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_dispatch.py", "-v"]
    environment = {key: val for key, val in os.environ.items() if key.upper() not in {
        "PYTHONPATH", "PYTHONSTARTUP", "PYTHONHOME", "PYTHONINSPECT"
    }}
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            cmd, cwd=str(workspace), env=environment,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", timeout=20, shell=False,
            creationflags=(0x08000000 if os.name == "nt" else 0)
        )
        output = result.stdout
        log_path.write_text(output[:150_000], encoding="utf-8")
        match = re.search(r"Ran (\d+) tests", output)
        return {"exit_code": result.returncode, "test_count": int(match.group(1)) if match else 0, "tail": output[-2200:], "log": str(log_path)}
    except subprocess.TimeoutExpired:
        log_path.write_text("TIMEOUT", encoding="utf-8")
        return {"exit_code": -2, "test_count": 0, "tail": "TEST_RUN_TIMEOUT", "log": str(log_path)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal", required=True)
    args = parser.parse_args()
    props = BASE / "proposals"
    props.mkdir(parents=True, exist_ok=True)
    proposal = Path(args.proposal).resolve(strict=True)
    run_id = proposal.name
    if not re.fullmatch(r"mx-workflow_retry-[a-zA-Z0-9_-]{4,48}", run_id):
        raise ValueError("BAD_RUN_ID")
    if proposal.parent != props.resolve(strict=True):
        raise ValueError("PROPOSAL_LOCATION_INVALID")
    workspace = BASE / "verified_runs" / run_id
    if workspace.exists():
        raise ValueError("VERIFIED_WORKSPACE_ALREADY_EXISTS")
    workspace.mkdir(parents=True)
    report = {"run_id": run_id, "status": "REJECTED", "static_check": [], "modified_paths": [], "baseline_test_failures_proven": True}
    output = BASE / "verified_runs" / (run_id + ".json")
    try:
        contents = validate(report, proposal)
        baseline = BASE / "baseline" / "workflow_retry"
        shutil.copytree(baseline, workspace, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        before = {file_id: sha(workspace / file_id) for file_id in FILES}
        for file_id, content in contents.items():
            dest = workspace / file_id
            dest.write_text(content, encoding="utf-8")
            if sha(dest) != before[file_id]:
                report["modified_paths"].append(file_id)
        if not report["modified_paths"]:
            raise ValueError("NO_ACTUAL_CHANGES")
        # Ensure the tests are copied verbatim and will remain immutable.
        if sha(workspace / "tests" / "test_dispatch.py") != sha(baseline / "tests" / "test_dispatch.py"):
            raise ValueError("TEST_INTEGRITY_VIOLATION")
        report["test"] = run_tests(workspace, BASE / "verified_runs" / (run_id + ".tests.log"))
        if report["test"]["exit_code"] == 0 and report["test"]["test_count"] == 10:
            report["status"] = "PASS_TESTED"
        else:
            report["status"] = "FAIL_TESTS"
    except Exception as exc:
        report["error"] = str(exc)
        report["status"] = "REJECTED"
    finally:
        report["all_fixture_sources_untouched"] = all(
            sha(BASE / "baseline" / "workflow_retry" / file_id) == sha(LAB / "qwen-eval" / "workflow_retry" / file_id)
            for file_id in FILES
        )
        if not report["all_fixture_sources_untouched"]:
            report["status"] = "FAIL_INTEGRITY"
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"status": report["status"], "modified": report["modified_paths"], "test": report.get("test"), "error": report.get("error"), "report": str(output)}))
    return 0 if report["status"] == "PASS_TESTED" else 2

if __name__ == "__main__":
    sys.exit(main())
