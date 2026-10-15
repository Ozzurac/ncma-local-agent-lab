class InMemoryLedger:
    """In-memory event receipt store. Records are dicts."""
    def __init__(self):
        self.events = {}

    def get(self, event_id):
        return self.events.get(event_id)

    def begin(self, event_id, payload):
        self.events[event_id] = {
            "payload": payload,
            "status": "pending",
            "attempts": 0,
            "last_error": None,
        }
        return self.events[event_id]

    def finish(self, event_id):
        self.events[event_id]["status"] = "done"
