#!/usr/bin/env python3
"""Isolated llama-server native API prefix-reuse experiment (stdlib only).

No server/model launch, downloads, shell execution, or changes to agent state.
Synthetic transport tests are NOT inference benchmarks.
"""
import argparse
import hashlib
import ipaddress
import json
import math
import platform
import re
import statistics
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

MAX_RESPONSE = 16 * 1024 * 1024


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_url(url):
    parts = urlsplit(url)
    try:
        address = ipaddress.ip_address(parts.hostname or "")
        port = parts.port
    except ValueError as exc:
        raise ValueError("Use a literal loopback IP and port") from exc
    if (parts.scheme != "http" or not address.is_loopback or not port
            or parts.username or parts.password or parts.query or parts.fragment
            or parts.path not in ("", "/")):
        raise ValueError("Only http://<literal-loopback>:<port> is supported")
    return url.rstrip("/")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirect rejected")


class Client:
    def __init__(self, base_url, timeout=900):
        self.base_url = validate_url(base_url)
        self.timeout = timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(self.base_url + path, data=data,
                                         headers={"Content-Type": "application/json"})
        with self.opener.open(request, timeout=self.timeout) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ValueError("Oversized response")
        value = json.loads(raw)
        if not isinstance(value, dict) or "error" in value:
            raise ValueError("Unexpected server response")
        return value

    def complete(self, payload):
        start = time.perf_counter()
        request = urllib.request.Request(self.base_url + "/completion",
            data=json.dumps(dict(payload, stream=True)).encode(),
            headers={"Content-Type": "application/json"})
        first_token_ms = None
        tokens, pieces = [], []
        final = None
        size = 0
        with self.opener.open(request, timeout=self.timeout) as response:
            # llama-server emits one JSON data field per SSE event; comments and
            # blank keepalive lines must not count as TTFT.
            for line in response:
                size += len(line)
                if size > MAX_RESPONSE:
                    raise ValueError("Oversized stream")
                if not line.startswith(b"data:"):
                    continue
                raw = line[5:].strip()
                if raw == b"[DONE]":
                    break
                event = json.loads(raw)
                if "error" in event:
                    raise ValueError("Inference stream error")
                emitted = event.get("tokens", [])
                content = event.get("content", "")
                if emitted or content:
                    if first_token_ms is None:
                        first_token_ms = (time.perf_counter() - start) * 1000
                    tokens.extend(emitted)
                    pieces.append(content)
                if event.get("stop") is True:
                    final = event
        if final is None or first_token_ms is None:
            raise ValueError("Missing final event or generated token")
        if final.get("truncated"):
            raise ValueError("Context truncated: comparison invalid")
        timings = final.get("timings", {})
        # tokens_cached is the remaining slot size, NOT the number reused.
        required = ("cache_n", "prompt_n", "predicted_n", "prompt_ms",
                    "predicted_ms", "prompt_per_second", "predicted_per_second")
        for key in required:
            value = timings.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError("Missing/invalid server timing: " + key)
        return {
            "ttft_ms": first_token_ms,
            "total_ms": (time.perf_counter() - start) * 1000,
            "timings": {key: timings[key] for key in required},
            "output_token_sha256": digest(tokens) if tokens else None,
            "output_text_sha256": hashlib.sha256("".join(pieces).encode()).hexdigest(),
            "returned_token_count": len(tokens),
            "stop_type": final.get("stop_type"),
            "ram_peak_bytes": None,
            "vram_peak_bytes": None,
        }


def validate_metadata(data):
    keys = {"runtime_commit", "runtime_binary_sha256", "model_sha256", "tokenizer_sha256",
            "quantization", "context_size", "batch_size", "ubatch_size", "parallel",
            "gpu_layers", "kv_type_k", "kv_type_v", "flash_attention", "backend", "hardware",
            "threads", "threads_batch", "cache_ram_mib", "speculative", "context_shift"}
    if set(data) != keys:
        raise ValueError("Metadata keys must match the documented schema")
    for key in ("runtime_binary_sha256", "model_sha256", "tokenizer_sha256", "runtime_commit"):
        length = 40 if key == "runtime_commit" else 64
        if not isinstance(data[key], str) or not re.fullmatch("[0-9a-fA-F]{%d}" % length, data[key]):
            raise ValueError("Invalid hash: " + key)
    for key in ("context_size", "batch_size", "ubatch_size", "parallel", "threads", "threads_batch"):
        if type(data[key]) is not int or data[key] <= 0:
            raise ValueError("Invalid positive integer: " + key)
    if data["parallel"] != 1 or data["ubatch_size"] > data["batch_size"]:
        raise ValueError("Use one slot and ubatch <= batch")
    if data["cache_ram_mib"] != 0 or data["speculative"] != "none" or data["context_shift"] is not False:
        raise ValueError("Disable RAM prompt cache, speculation and context shift for this experiment")
    if not isinstance(data["hardware"], dict) or not data["hardware"]:
        raise ValueError("hardware must describe the actual host")
    # Metadata is an explicit operator declaration, not hardware attestation.
    return data


def synthetic_prompts(lines):
    prefix = "NCMA synthetic inference fixture. Preserve the numbered records.\n"
    prefix += "".join(f"Record {i:06d}: key_{i % 97:02d} value_{(i * 17) % 997:03d}.\n" for i in range(lines))
    return prefix, "\nNew synthetic user turn: list three record keys.\nAssistant:"


def tokenize(client, text, add_special):
    result = client.request("/tokenize", {"content": text, "add_special": add_special, "parse_special": False})
    tokens = result.get("tokens")
    if not tokens or any(type(token) is not int or token < 0 for token in tokens):
        raise ValueError("Invalid tokenizer response")
    return tokens


def summary(rows):
    result = {}
    for variant in sorted({row["variant"] for row in rows if not row["warmup"]}):
        group = [row for row in rows if row["variant"] == variant and not row["warmup"]]
        metrics = {}
        for key in ("ttft_ms", "total_ms"):
            values = [row["measurement"][key] for row in group]
            metrics[key] = {"n": len(values), "min": min(values), "median": statistics.median(values),
                            "max": max(values), "stdev": statistics.stdev(values) if len(values) > 1 else 0}
        result[variant] = metrics
    return result


def run(client, metadata, emit, repetitions=5, warmups=1, lines=512, n_predict=32, snapshot=False):
    validate_metadata(metadata)
    if repetitions < 2 or warmups < 1 or lines < 1 or n_predict < 1:
        raise ValueError("Need >=2 repetitions, >=1 warmup, positive lines and output")
    health = client.request("/health")
    if health.get("status") != "ok":
        raise ValueError("Server is not healthy")
    props = client.request("/props")
    if props.get("total_slots") != 1:
        raise ValueError("Dedicated single-slot server required")
    observed_context = props.get("default_generation_settings", {}).get("n_ctx")
    if observed_context != metadata["context_size"]:
        raise ValueError("Declared context differs from server /props")
    prefix_text, suffix_text = synthetic_prompts(lines)
    prefix = tokenize(client, prefix_text, True)
    # Tokenize separately by design: identical explicit token arrays in both
    # variants, independent of BPE merges at the prefix/suffix boundary.
    full = prefix + tokenize(client, suffix_text, False)
    if len(full) + n_predict + 8 >= observed_context:
        raise ValueError("Fixture would exhaust context")
    emit({"kind": "setup", "prefix_tokens": len(prefix), "request_tokens": len(full),
          "prefix_token_sha256": digest(prefix), "request_token_sha256": digest(full),
          "observed_context": observed_context, "observed_slots": props["total_slots"],
          "build_info_sha256": digest(props.get("build_info"))})
    settings = {"id_slot": 0, "temperature": 0, "seed": 42, "top_k": 1,
                "top_p": 1.0, "min_p": 0.0, "repeat_penalty": 1.0,
                "ignore_eos": True, "return_tokens": True, "n_predict": n_predict}
    rows = []
    snapshot_name = "ncma-prefix-" + uuid.uuid4().hex + ".bin"
    for iteration in range(warmups + repetitions):
        variants = ["baseline", "reuse"] + (["restored"] if snapshot else [])
        if iteration % 2:
            variants.reverse()
        for variant in variants:
            # Force a fresh prefill before EVERY observation. Warmup and order
            # are balanced; priming costs are kept separate, never hidden.
            prime = client.complete(dict(settings, prompt=prefix, n_predict=1, cache_prompt=False))
            if prime["timings"]["cache_n"] != 0:
                raise ValueError("Server ignored cache_prompt=False during prime")
            operation = {}
            if variant == "restored":
                for action in ("save", "erase", "restore"):
                    start = time.perf_counter()
                    response = client.request("/slots/0?action=" + action, {"filename": snapshot_name})
                    count_key = {"save": "n_saved", "erase": "n_erased", "restore": "n_restored"}[action]
                    if response.get(count_key, 0) <= 0:
                        raise ValueError("Slot action returned no tokens: " + action)
                    operation[action] = {"wall_ms": (time.perf_counter() - start) * 1000,
                                         "tokens": response[count_key]}
            measurement = client.complete(dict(settings, prompt=full, cache_prompt=(variant != "baseline")))
            reused = measurement["timings"]["cache_n"]
            valid_cache = reused == 0 if variant == "baseline" else reused > 0
            valid_length = measurement["timings"]["predicted_n"] == n_predict
            row = {"kind": "trial", "iteration": iteration, "warmup": iteration < warmups,
                   "variant": variant, "request_token_sha256": digest(full),
                   "prime": prime, "measurement": measurement, "slot_operations": operation,
                   "cache_condition_met": valid_cache, "output_length_condition_met": valid_length,
                   "reused_prefix_fraction": min(1, reused / len(prefix))}
            emit(row)
            rows.append(row)
            if not valid_cache:
                raise ValueError("Expected cache condition not met; retained negative evidence")
            if not valid_length:
                raise ValueError("Generation length differs from fixed budget; retained negative evidence")
    comparisons = []
    for iteration in range(warmups, warmups + repetitions):
        group = {row["variant"]: row for row in rows if row["iteration"] == iteration}
        baseline = group["baseline"]["measurement"]
        for variant in group.keys() - {"baseline"}:
            current = group[variant]["measurement"]
            comparisons.append({"iteration": iteration, "variant": variant,
                "ttft_ratio_baseline_over_variant": baseline["ttft_ms"] / current["ttft_ms"],
                "same_output_tokens": (baseline["output_token_sha256"] == current["output_token_sha256"])
                    if baseline["output_token_sha256"] and current["output_token_sha256"] else None,
                "same_output_text": baseline["output_text_sha256"] == current["output_text_sha256"]})
    return {"status": "MEASURED", "summary": summary(rows), "comparisons": comparisons,
            "snapshot_file_created": snapshot, "snapshot_requires_manual_cleanup": snapshot,
            "notes": ["Native completion synthetic fixture; not an agent or chat-template benchmark.",
                      "Restored means erase/restore in one server process, not crash/restart recovery.",
                      "RAM/VRAM peaks unavailable; null is not zero.",
                      "Changing batching/cache can change outputs; equality is measured, not presumed."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18991")
    parser.add_argument("--out", type=Path, required=True, help="New output directory, never overwritten")
    parser.add_argument("--probe", action="store_true", help="Read-only availability probe; no inference")
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--exclusive-server", action="store_true", help="Assert this is a dedicated benchmark server")
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--lines", type=int, default=512)
    parser.add_argument("--n-predict", type=int, default=32)
    parser.add_argument("--snapshot", action="store_true")
    args = parser.parse_args(argv)
    client = Client(args.base_url, timeout=5 if args.probe else 900)
    if not args.probe and (not args.exclusive_server or args.metadata is None):
        parser.error("Inference needs --exclusive-server and --metadata")
    args.out.mkdir(parents=True, exist_ok=False)
    report = {"schema": "ncma-prefix-bench-v1", "created_utc": datetime.now(timezone.utc).isoformat(),
              "python": platform.python_version(), "platform": platform.system(),
              "experiment_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "mode": "probe" if args.probe else "inference"}
    def emit(row):
        with (args.out / "trials.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    code = 0
    try:
        if args.probe:
            report["status"] = "AVAILABLE" if client.request("/health").get("status") == "ok" else "UNAVAILABLE"
            code = 0 if report["status"] == "AVAILABLE" else 2
        else:
            metadata = validate_metadata(json.loads(args.metadata.read_text(encoding="utf-8")))
            report["metadata"] = metadata
            report["parameters"] = {key: getattr(args, key) for key in
                                    ("repetitions", "warmups", "lines", "n_predict", "snapshot")}
            report.update(run(client, metadata, emit, args.repetitions, args.warmups,
                              args.lines, args.n_predict, args.snapshot))
    except Exception as exc:
        # Do not export arbitrary server error text, URLs or filesystem paths.
        report.update(status="BLOCKED_OR_FAILED", error_type=type(exc).__name__)
        code = 2
    (args.out / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "exit_code": code}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
