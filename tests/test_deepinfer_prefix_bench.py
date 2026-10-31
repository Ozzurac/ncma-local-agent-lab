"""Protocol/experiment regression tests. The HTTP fixture performs NO inference."""
import importlib.util
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prefix_bench", ROOT / "experiments/deepinfer/prefix_bench.py")
bench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bench)


def metadata():
    return dict(runtime_commit="a" * 40, runtime_binary_sha256="b" * 64,
                model_sha256="c" * 64, tokenizer_sha256="d" * 64,
                quantization="synthetic-contract-only", context_size=16384,
                batch_size=512, ubatch_size=128, parallel=1, gpu_layers=0,
                kv_type_k="f16", kv_type_v="f16", flash_attention="off",
                backend="fake-http-no-inference", hardware={"cpu": "test fixture"},
                threads=1, threads_batch=1, cache_ram_mib=0, speculative="none", context_shift=False)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_json(self, value):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(value).encode())

    def do_GET(self):
        if self.path == "/health":
            self.send_json({"status": "ok"})
        elif self.path == "/props":
            self.send_json({"total_slots": self.server.slots,
                            "default_generation_settings": {"n_ctx": 16384}})
        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "http://192.0.2.1:80/health")
            self.end_headers()
        else:
            self.send_error(404)

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append((self.path, data))
        if self.path == "/tokenize":
            # Character IDs are a transport fixture, not any model tokenizer.
            self.send_json({"tokens": ([1] if data["add_special"] else []) + list(data["content"].encode())})
        elif self.path.startswith("/slots/"):
            action = self.path.split("action=")[1]
            key = {"save": "n_saved", "erase": "n_erased", "restore": "n_restored"}[action]
            if action == "save":
                self.server.saved = list(self.server.cache)
            count = len(self.server.saved if action == "restore" else self.server.cache)
            if action == "erase":
                self.server.cache = []
            elif action == "restore":
                self.server.cache = list(self.server.saved)
            self.send_json({key: count})
        elif self.path == "/completion":
            previous = self.server.cache
            prompt = data["prompt"]
            common = 0
            if data["cache_prompt"]:
                for left, right in zip(previous, prompt):
                    if left != right:
                        break
                    common += 1
            if self.server.disable_hits:
                common = 0
            self.server.cache = list(prompt)
            n = data["n_predict"]
            timings = dict(cache_n=common, prompt_n=len(prompt) - common,
                           predicted_n=n - int(self.server.short_output), prompt_ms=1, predicted_ms=1,
                           prompt_per_second=1, predicted_per_second=1)
            if self.server.bad_timing:
                timings.pop("cache_n")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(b": keepalive\n\ndata: {" + b'"content":"","tokens":[],"stop":false}\n\n')
            self.wfile.write(b'data: {"content":"x","tokens":[0],"stop":false}\n\n')
            if not self.server.missing_final:
                event = dict(content="", tokens=[], stop=True, timings=timings,
                             truncated=self.server.truncated, stop_type="limit")
                self.wfile.write(b"data: " + json.dumps(event).encode() + b"\n\n")
        else:
            self.send_error(404)


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.client = bench.Client(f"http://127.0.0.1:{cls.server.server_port}", timeout=5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.server.cache = []
        self.server.saved = []
        self.server.requests = []
        self.server.slots = 1
        self.server.disable_hits = False
        self.server.bad_timing = False
        self.server.missing_final = False
        self.server.truncated = False
        self.server.short_output = False

    def test_ab_uses_same_tokens_balanced_order_and_fresh_priming(self):
        events = []
        result = bench.run(self.client, metadata(), events.append, repetitions=2, lines=4)
        self.assertEqual(result["status"], "MEASURED")  # Fixture protocol, NOT performance evidence.
        rows = [row for row in events if row["kind"] == "trial"]
        self.assertEqual(len(rows), 6)
        self.assertEqual([r["variant"] for r in rows], ["baseline", "reuse", "reuse", "baseline", "baseline", "reuse"])
        self.assertEqual(len({r["request_token_sha256"] for r in rows}), 1)
        for row in rows:
            self.assertEqual(row["prime"]["timings"]["cache_n"], 0)
            self.assertTrue(row["cache_condition_met"])
            self.assertIsNone(row["measurement"]["vram_peak_bytes"])
        self.assertEqual(result["summary"]["reuse"]["ttft_ms"]["n"], 2)
        self.assertTrue(all(x["same_output_tokens"] for x in result["comparisons"]))
        completions = [data for path, data in self.server.requests if path == "/completion"]
        measured = completions[1::2]
        self.assertTrue(all(data["prompt"] == measured[0]["prompt"] for data in measured))
        for data in measured:
            self.assertEqual(data["temperature"], 0)
            self.assertEqual(data["n_predict"], 32)
        self.assertEqual(len(completions), 12)

    def test_slot_save_erase_restore_order(self):
        events = []
        result = bench.run(self.client, metadata(), events.append, repetitions=2, lines=4, snapshot=True)
        actions = [path.split("action=")[1] for path, _ in self.server.requests if path.startswith("/slots/")]
        self.assertEqual(actions, ["save", "erase", "restore"] * 3)
        self.assertTrue(result["snapshot_requires_manual_cleanup"])
        self.assertEqual(len(result["comparisons"]), 4)

    def test_missing_hit_is_negative_evidence(self):
        self.server.disable_hits = True
        events = []
        with self.assertRaisesRegex(ValueError, "cache condition"):
            bench.run(self.client, metadata(), events.append, repetitions=2, lines=4)
        self.assertFalse(events[-1]["cache_condition_met"])

    def test_missing_timing_not_silently_replaced_with_zero(self):
        self.server.bad_timing = True
        with self.assertRaisesRegex(ValueError, "cache_n"):
            bench.run(self.client, metadata(), lambda row: None, repetitions=2, lines=4)

    def test_different_generation_budget_rejected_and_recorded(self):
        self.server.short_output = True
        events = []
        with self.assertRaisesRegex(ValueError, "Generation length"):
            bench.run(self.client, metadata(), events.append, repetitions=2, lines=4)
        self.assertFalse(events[-1]["output_length_condition_met"])

    def test_missing_final_rejected(self):
        self.server.missing_final = True
        with self.assertRaisesRegex(ValueError, "final event"):
            self.client.complete({"prompt": [1, 2], "cache_prompt": False, "n_predict": 1})

    def test_truncated_context_rejected(self):
        self.server.truncated = True
        with self.assertRaisesRegex(ValueError, "truncated"):
            self.client.complete({"prompt": [1, 2], "cache_prompt": False, "n_predict": 1})

    def test_multiple_slots_rejected_before_generation(self):
        self.server.slots = 2
        with self.assertRaisesRegex(ValueError, "single-slot"):
            bench.run(self.client, metadata(), lambda row: None)
        self.assertEqual(self.server.requests, [])

    def test_context_declaration_checked(self):
        data = metadata()
        data["context_size"] = 4096
        with self.assertRaisesRegex(ValueError, "context differs"):
            bench.run(self.client, data, lambda row: None)

    def test_overflow_rejected_before_generation(self):
        with self.assertRaisesRegex(ValueError, "exhaust context"):
            bench.run(self.client, metadata(), lambda row: None, lines=2048)
        self.assertFalse(any(path == "/completion" for path, _ in self.server.requests))

    def test_redirect_rejected(self):
        with self.assertRaisesRegex(ValueError, "Redirect"):
            self.client.request("/redirect")

    def test_probe_is_read_only_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            out = str(Path(directory) / "probe")
            args = ["--probe", "--out", out, "--base-url", self.client.base_url]
            self.assertEqual(bench.main(args), 0)
            self.assertEqual(self.server.requests, [])
            with self.assertRaises(FileExistsError):
                bench.main(args)

    def test_http_errors_retained_without_raw_url(self):
        with tempfile.TemporaryDirectory() as directory:
            # /health works, but this URL validates and closed port fails.
            self.assertEqual(bench.main(["--probe", "--base-url", "http://127.0.0.1:1", "--out", directory + "/probe"]), 2)
            report = json.loads(Path(directory, "probe/report.json").read_text())
            self.assertEqual(report["status"], "BLOCKED_OR_FAILED")
            self.assertNotIn("127.0.0.1", json.dumps(report))


class ValidationTests(unittest.TestCase):
    def test_loopback_urls(self):
        self.assertEqual(bench.validate_url("http://127.0.0.1:8080/"), "http://127.0.0.1:8080")
        self.assertEqual(bench.validate_url("http://[::1]:8080"), "http://[::1]:8080")

    def test_remote_credentials_paths_and_dns_rejected(self):
        for url in ("http://localhost:8080", "http://192.0.2.1:8080", "https://127.0.0.1:8080",
                    "http://a:b@127.0.0.1:8080", "http://127.0.0.1:8080/v1",
                    "http://127.0.0.1:8080?x=1", "http://127.0.0.1:8080/#fragment"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                bench.validate_url(url)

    def test_metadata_requires_identity_and_consistent_batch(self):
        for key, value in (("model_sha256", "unknown"), ("runtime_commit", "main"),
                           ("parallel", 2), ("context_size", True), ("ubatch_size", 1024)):
            data = metadata()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                bench.validate_metadata(data)

    def test_digest_stable_and_sensitive_to_order(self):
        self.assertEqual(bench.digest({"a": 1, "b": 2}), bench.digest({"b": 2, "a": 1}))
        self.assertNotEqual(bench.digest([1, 2]), bench.digest([2, 1]))

    def test_warmup_not_in_summary(self):
        rows = [dict(variant="reuse", warmup=warm, measurement=dict(ttft_ms=value, total_ms=value))
                for warm, value in ((True, 1000), (False, 1), (False, 3))]
        result = bench.summary(rows)["reuse"]["ttft_ms"]
        self.assertEqual(result["n"], 2)
        self.assertEqual(result["median"], 2)
        self.assertGreater(result["stdev"], 0)


if __name__ == "__main__":
    unittest.main()
