import copy
import unittest
from src.merge import deep_merge
from src.settings import configure

BASE={
 "network":{"timeout":30,"retries":3},
 "logging":{"level":"INFO"},
 "features":{"safe_mode":True,"plugins":["alpha","beta"]},
}

class ConfigTests(unittest.TestCase):
    def test_no_overrides(self):
        self.assertEqual(configure(BASE,{},{}), BASE)

    def test_top_level_log_override(self):
        self.assertEqual(configure(BASE,{"logging":{"level":"DEBUG"}}, {})["logging"]["level"],"DEBUG")

    def test_env_nested_merge_preserves_other_keys(self):
        result=configure(BASE,{"network":{"timeout":10}}, {})
        self.assertEqual(result["network"],{"timeout":10,"retries":3})

    def test_cli_override_has_priority(self):
        result=configure(BASE,{"network":{"timeout":10}}, {"network":{"timeout":5}})
        self.assertEqual(result["network"],{"timeout":5,"retries":3})

    def test_explicit_false_is_preserved(self):
        result=configure(BASE,{},{"features":{"safe_mode":False}})
        self.assertIs(result["features"]["safe_mode"],False)
        self.assertEqual(result["features"]["plugins"],["alpha","beta"])

    def test_zero_is_preserved(self):
        result=configure(BASE,{},{"network":{"timeout":0}})
        self.assertEqual(result["network"]["timeout"],0)

    def test_lists_replace_not_concatenate(self):
        result=configure(BASE,{"features":{"plugins":["only"]}}, {})
        self.assertEqual(result["features"]["plugins"],["only"])

    def test_deep_merge_does_not_mutate_inputs(self):
        original=copy.deepcopy(BASE)
        result=deep_merge(BASE,{"network":{"timeout":7}})
        result["network"]["retries"]=99
        self.assertEqual(BASE,original)
        self.assertEqual(result["network"]["timeout"],7)
        self.assertEqual(result["network"]["retries"],99)

    def test_reject_unknown_top_level(self):
        with self.assertRaises(ValueError):
            configure(BASE,{"secret_config":{"write":True}}, {})

    def test_reject_unknown_nested_option(self):
        with self.assertRaises(ValueError):
            configure(BASE,{},{"network":{"shell_access":True}})

    def test_preserve_original_base_data(self):
        original=copy.deepcopy(BASE)
        env={"network":{"timeout":15}}
        cli={"features":{"safe_mode":False}}
        configure(BASE,env,cli)
        self.assertEqual(BASE,original)
        self.assertEqual(env,{"network":{"timeout":15}})
        self.assertEqual(cli,{"features":{"safe_mode":False}})

if __name__=="__main__":
    unittest.main()
