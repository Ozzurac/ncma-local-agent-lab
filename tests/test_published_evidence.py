"""Offline verification of source-grounded decisions and historical evidence.

Runs with Python stdlib only. The original model was NEVER allowed to read
the synthetic oracle during G3/G4H inference.
"""
import hashlib
import importlib.util
import json
import sys
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ncma_lab import g4_checkpoint as g4  # noqa: E402

CORPUS=ROOT/"benchmarks/g3/task_corpus.txt"
ORACLE=ROOT/"benchmarks/g3/oracle_reference.json"
EVIDENCE=ROOT/"benchmarks/g4h/evidence"
EXPECTED_SHA="824F516C6916E62ABBA573DF352F0145B66DC81765D8760B07093F389BAC2591"

class TestPublishedEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index,cls.notes,cls.events=g4.index_corpus()
        cls.oracle=json.loads(ORACLE.read_text("utf-8"))
        cls.output=json.loads((EVIDENCE/"final_results.json").read_text("utf-8"))
        cls.checkpoint=json.loads((EVIDENCE/"checkpoint.json").read_text("utf-8"))

    def test_corpus_digest_and_structure(self):
        self.assertEqual(hashlib.sha256(CORPUS.read_bytes()).hexdigest().upper(),EXPECTED_SHA)
        self.assertEqual(EXPECTED_SHA,g4.SHA)
        self.assertEqual(len(self.index["NODE"]),760)
        self.assertEqual(sum(map(len,self.index["PATCH"].values())),563)
        self.assertEqual(len(self.index["TEAM"]),240)
        self.assertEqual(len(self.index["CASE"]),12)
        self.assertEqual(len(self.notes),6)
        self.assertEqual(self.oracle["records"],1745)
        self.assertEqual(self.oracle["events"],176)

    def test_generator_reproduces_the_original_corpus(self):
        gen_path=ROOT/"experiments/g3/generate_case.py"
        spec=importlib.util.spec_from_file_location("g3_benchmark_generator",gen_path)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        content,manifest=mod.make(176)
        self.assertEqual(content.replace("\n","\r\n").encode("utf-8"),CORPUS.read_bytes())
        self.assertEqual(manifest["sha256"].upper(),self.oracle["sha256"].upper())
        self.assertEqual(manifest["oracle"],self.oracle["oracle"])

    def test_twelve_results_match_all_sixty_fields(self):
        expected={x["case"]:x for x in self.oracle["oracle"]}
        received=self.output["results"]
        self.assertEqual(len(received),12)
        self.assertEqual({x["case"] for x in received},set(expected))
        count=0
        for item in received:
            ref=expected[item["case"]]
            for field in ["case","terminal","team","seal","path"]:
                self.assertEqual(item[field],ref[field],msg=item["case"]+"."+field)
                count+=1
        self.assertEqual(count,60)

    def test_every_path_hop_has_matching_authoritative_source(self):
        total=0
        for item in self.output["results"]:
            cid=item["case"]
            path=item["path"]
            self.assertEqual(path[0],self.index["CASE"][cid][1]["entry"])
            self.assertEqual(len(path),len(set(path)))
            for j,node in enumerate(path):
                node_data=self.index["NODE"][node][1]
                patches=self.index["PATCH"].get(node,[])
                rev=max((x[0] for x in patches),default=0)
                expected_next=next((x[2]["next"] for x in patches if x[0]==rev),
                                   node_data["base_next"])
                selected=path[j+1] if j+1<len(path) else "STOP"
                self.assertEqual(selected,expected_next,msg=cid+" "+node)
                team=node_data["team"] if selected=="STOP" else ""
                seal=self.index["TEAM"][team][1]["seal"] if team else ""
                decision={"node":node,"revision":rev,"next":selected,
                          "team":team,"seal":seal}
                error=g4.selected_valid({"cursor":node,"path":path[:j]},decision,self.index)
                self.assertIsNone(error,msg=cid+" "+node)
                total+=1
        self.assertEqual(total,78)

    def test_bad_revision_is_rejected(self):
        node=next(k for k,v in self.index["PATCH"].items() if any(p[0]>0 for p in v))
        verdict=g4.selected_valid({"cursor":node,"path":[]},
                {"node":node,"revision":0,"next":"STOP","team":"","seal":""},self.index)
        self.assertEqual(verdict,"MUST_SELECT_HIGHEST_NUMERIC_PATCH_REV")

    def test_checkpoint_integrity_and_completion(self):
        s=self.checkpoint
        self.assertEqual(s["checksum"],g4.seal(s))
        self.assertEqual(s["source"],EXPECTED_SHA)
        self.assertEqual(s["round"],22)
        self.assertEqual(s["calls"],44)
        self.assertTrue(s["done"])
        self.assertEqual(len(s["cases"]),12)
        self.assertTrue(all(v["status"]=="DONE" for v in s["cases"].values()))
        ref={x["case"]:x for x in self.oracle["oracle"]}
        for cid,c in s["cases"].items():
            self.assertEqual(c["path"],ref[cid]["path"])
            self.assertEqual(c["terminal"],ref[cid]["terminal"])

    def test_all_22_round_evidence_files_match_checkpoint(self):
        rounds=sorted((EVIDENCE/"rounds").glob("round_*.json"))
        self.assertEqual(len(rounds),22)
        accepted=0;rejected=0
        for i,file in enumerate(rounds,start=1):
            data=json.loads(file.read_text("utf-8"))
            self.assertEqual(data["round"],i)
            accepted+=len(data["accepted"])
            rejected+=len(data["rejected"])
        self.assertEqual(accepted,78)
        self.assertEqual(rejected,28)

    def test_honest_monolithic_and_hybrid_reports(self):
        failed=json.loads((ROOT/"benchmarks/g3/reports/monolithic_result.json").read_text("utf-8"))
        self.assertEqual(failed["finishReason"],"length")
        self.assertEqual(failed["usage"]["completion_tokens"],16384)
        self.assertEqual(failed["finalTextBytes"],0)
        self.assertEqual(failed["usage"]["prompt_tokens"],77103)
        passed=json.loads((EVIDENCE/"G4H_FINAL_AUDIT_20261015.json").read_text("utf-8"))
        self.assertEqual(passed["outcome"],"ALL_12_CASES_AND_60_FIELDS_EXACT_MATCH")
        self.assertEqual(passed["casesCompleted"],12)
        self.assertEqual(passed["fieldsCorrect"],60)
        self.assertEqual(passed["sourceVerifiedHops"],78)
        self.assertEqual(passed["rejectedCandidateHops"],28)

    def test_relevant_reference_modules_exist(self):
        md=list((ROOT/"knowledge/modules").rglob("*.md"))
        self.assertEqual(len(md),4)
        self.assertTrue(all(x.stat().st_size>80 for x in md))
        skills=list((ROOT/"skills").rglob("SKILL.md"))
        self.assertGreaterEqual(len(skills),4)

    def test_publication_manifest_matches_committed_git_blobs(self):
        if not (ROOT/".git").is_dir():
            self.skipTest("Git checkout required to verify canonical blob bytes")
        manifest=json.loads((ROOT/"PUBLICATION_MANIFEST.json").read_text("utf-8"))
        self.assertEqual(manifest["schema"],"ncma-public-allowlist-v1")
        self.assertGreaterEqual(len(manifest["files"]),110)
        for item in manifest["files"]:
            result=subprocess.run(["git","show",":"+item["path"]],
                                  cwd=ROOT,capture_output=True,check=True)
            self.assertEqual(len(result.stdout),item["bytes"],msg=item["path"])
            actual=hashlib.sha256(result.stdout).hexdigest().upper()
            self.assertEqual(actual,item["sha256"],msg=item["path"])
    def test_models_and_execution_binaries_are_excluded(self):
        forbidden={".gguf",".safetensors",".onnx",".exe",".dll",".pt",".ckpt",".pfx",".pem"}
        excluded={".git","__pycache__",".venv","node_modules","generated","runs"}
        files=[p for p in ROOT.rglob("*") if p.is_file() and not set(p.relative_to(ROOT).parts).intersection(excluded)]
        self.assertFalse([(str(f),f.stat().st_size) for f in files if f.suffix.lower() in forbidden])
        self.assertFalse([str(f) for f in files if f.stat().st_size>1800000])

if __name__=="__main__":
    unittest.main()
