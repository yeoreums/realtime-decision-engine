class TrustManager:
    """
    Manages the data trust state of the system.

    Trust state transitions are triggered by sanitization results,
    not by raw events themselves.
    """
    def __init__(self):
        self.state = "TRUSTED"

    def update(self, sanitize_result, event):
        """
        Updates the trust state based on sanitization outcomes.

        A QUARANTINE classification degrades the trust state,
        which may restrict or halt downstream decisions.
        """
        transitions = []

        if sanitize_result.classification == "QUARANTINE":
            if self.state == "TRUSTED":
                transitions.append({
                    "ts": event.receive_time,
                    "trigger": sanitize_result.trigger,
                    "previous_trust": "TRUSTED",
                    "current_trust": "DEGRADED",
                    "details": sanitize_result.details,
                })
                self.state = "DEGRADED"

        return self.state, transitions
