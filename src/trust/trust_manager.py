class TrustManager:
    """ Tracks data trust state based on sanitization results. """

    def __init__(self):
        self.state = "TRUSTED"

    def update(self, sanitize_result, event):
        transitions = []

        if sanitize_result.classification == "QUARANTINE":
            if self.state == "TRUSTED":
                transitions.append({
                    "ts": event.event_time,
                    "receive_ts": event.receive_time,
                    "trigger": sanitize_result.trigger,
                    "previous_trust": "TRUSTED",
                    "current_trust": "DEGRADED",
                    "details": sanitize_result.details,
                })
                self.state = "DEGRADED"

        return self.state, transitions
