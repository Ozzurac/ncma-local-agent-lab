from .ledger import InMemoryLedger

class Dispatcher:
    """Delivers event payloads using deliver(event_id, payload)."""
    def __init__(self, ledger: InMemoryLedger, deliver):
        self.ledger = ledger
        self.deliver = deliver

    def handle(self, event):
        event_id = event["id"]
        payload = event["payload"]
        record = self.ledger.get(event_id)
        if record and record["status"] == "done":
            return "duplicate"
        self.ledger.begin(event_id, payload)
        self.deliver(event_id, payload)
        self.ledger.finish(event_id)
        return "delivered"
