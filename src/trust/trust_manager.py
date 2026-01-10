class TrustManager:
    """Tracks data trust state based on sanitization results and stream stalls."""

    def __init__(self, stall_sec_by_stream=None):
        self.state = "TRUSTED"
        self.last_seen_by_stream = {}
        self.stall_sec_by_stream = stall_sec_by_stream or {
            "trade": 5.0,
            "orderbook": 2.0,
            "ticker": 10.0,
            "liquidation": 20.0,
        }

    def update(self, sanitize_result, event):
        transitions = []

        # Update last seen time per stream
        self.last_seen_by_stream[str(event.stream)] = event.receive_time

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

    def detect_stall(self, now_ts: float):
        """Detect stalled streams and escalate trust state."""
        transitions = []

        for stream, threshold in self.stall_sec_by_stream.items():
            last_seen = self.last_seen_by_stream.get(stream)
            if last_seen is None:
                continue

            if now_ts - last_seen > threshold and self.state != "UNTRUSTED":
                prev = self.state
                self.state = "UNTRUSTED"
                transitions.append({
                    "ts": now_ts,
                    "trigger": "stream_stall",
                    "previous_trust": prev,
                    "current_trust": "UNTRUSTED",
                    "details": {
                        "stream": stream,
                        "stall_sec": round(now_ts - last_seen, 3),
                        "threshold_sec": threshold,
                    },
                })

        return self.state, transitions
