import unittest
from src.ledger import InMemoryLedger
from src.dispatch import Dispatcher

class WorkflowTests(unittest.TestCase):
    def make(self, deliver=None):
        ledger=InMemoryLedger()
        calls=[]
        def successful(event_id,payload):
            calls.append((event_id,payload))
        return ledger,calls,Dispatcher(ledger, deliver or successful)

    def test_basic_delivery(self):
        ledger,calls,d=self.make()
        self.assertEqual(d.handle({"id":"x","payload":{"v":1}}),"delivered")
        self.assertEqual(len(calls),1)
        self.assertEqual(ledger.get("x")["status"],"done")

    def test_completed_duplicate_no_second_send(self):
        ledger,calls,d=self.make()
        event={"id":"x","payload":{"v":1}}
        d.handle(event)
        self.assertEqual(d.handle(event),"duplicate")
        self.assertEqual(len(calls),1)

    def test_completed_mismatched_payload_rejected(self):
        ledger,calls,d=self.make()
        d.handle({"id":"x","payload":{"v":1}})
        with self.assertRaises(ValueError):
            d.handle({"id":"x","payload":{"v":999}})
        self.assertEqual(len(calls),1)

    def test_attempt_count_on_success(self):
        ledger,calls,d=self.make()
        d.handle({"id":"x","payload":{"v":1}})
        self.assertEqual(ledger.get("x")["attempts"],1)

    def test_failure_is_recorded_and_propagated(self):
        def broken(event_id,payload):
            raise RuntimeError("upstream unreachable")
        ledger,calls,d=self.make(broken)
        with self.assertRaisesRegex(RuntimeError,"upstream"):
            d.handle({"id":"x","payload":{"v":1}})
        self.assertEqual(ledger.get("x")["status"],"failed")
        self.assertEqual(ledger.get("x")["attempts"],1)
        self.assertIn("upstream unreachable",ledger.get("x")["last_error"])

    def test_retry_after_failure_increments_attempts(self):
        tries=[]
        def flaky(event_id,payload):
            tries.append(event_id)
            if len(tries)==1:
                raise OSError("network")
        ledger,calls,d=self.make(flaky)
        event={"id":"y","payload":{"v":2}}
        with self.assertRaises(OSError):
            d.handle(event)
        self.assertEqual(d.handle(event),"delivered")
        self.assertEqual(tries,["y","y"])
        self.assertEqual(ledger.get("y")["attempts"],2)
        self.assertEqual(ledger.get("y")["status"],"done")
        self.assertIsNone(ledger.get("y")["last_error"])

    def test_mismatched_payload_on_failed_retry_rejected(self):
        def broken(event_id,payload):
            raise OSError("down")
        ledger,calls,d=self.make(broken)
        with self.assertRaises(OSError):
            d.handle({"id":"z","payload":{"v":1}})
        with self.assertRaises(ValueError):
            d.handle({"id":"z","payload":{"v":2}})
        self.assertEqual(ledger.get("z")["payload"],{"v":1})
        self.assertEqual(ledger.get("z")["attempts"],1)

    def test_empty_event_id_rejected_before_delivery(self):
        ledger,calls,d=self.make()
        with self.assertRaises(ValueError):
            d.handle({"id":"","payload":{"v":1}})
        self.assertEqual(len(calls),0)

    def test_invalid_payload_rejected_before_delivery(self):
        ledger,calls,d=self.make()
        with self.assertRaises(ValueError):
            d.handle({"id":"x","payload":"not a mapping"})
        self.assertEqual(len(calls),0)

    def test_retry_does_not_erase_original_payload(self):
        tries=[]
        def flaky(event_id,payload):
            tries.append(payload)
            if len(tries)==1:
                raise OSError("temporary")
        ledger,calls,d=self.make(flaky)
        ev={"id":"k","payload":{"batch":[1,2]}}
        with self.assertRaises(OSError):
            d.handle(ev)
        d.handle(ev)
        self.assertEqual(ledger.get("k")["payload"],{"batch":[1,2]})
        self.assertEqual(ledger.get("k")["attempts"],2)

if __name__=="__main__":
    unittest.main()
