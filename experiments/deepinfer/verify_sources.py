#!/usr/bin/env python3
"""Verify audited source bytes at fixed commits in external checkouts; execute no upstream code."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

LOCK = Path(__file__).resolve().parents[2] / "research/deepinfer/source_lock.json"


def verify(lock, roots):
    rows = []
    for name, source in lock["sources"].items():
        root = roots[name]
        head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        if head != source["commit"]:
            raise ValueError("Unexpected source revision: " + name)
        for item in source["files"]:
            # Read committed blobs, not a possibly modified working tree.
            raw = subprocess.check_output(["git", "-C", str(root), "show", head + ":" + item["path"]])
            actual = hashlib.sha256(raw).hexdigest()
            if actual != item["sha256"]:
                raise ValueError("Unexpected blob bytes: " + name + "/" + item["path"])
            rows.append({"source": name, "path": item["path"], "sha256": actual})
    return {"status": "VERIFIED_SOURCE_BYTES", "files_verified": len(rows), "files": rows,
            "scope": "Content identity only; no build, inference, upstream tests or runtime compatibility proven"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deepinfer", type=Path, required=True)
    parser.add_argument("--llama", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    roots = {"deepinfer": args.deepinfer, "llama.cpp": args.llama, "recipe": args.recipe}
    for name in ("DeepGEMM", "FlashMLA", "DeepEP", "DeepSelect"):
        roots[name] = args.deepinfer / "vendor" / name
    result = verify(lock, roots)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "files_verified")}))


if __name__ == "__main__":
    main()
