class SanitizeResult:
    def __init__(self, classification, trigger=None, details=None):
        self.classification = classification  # ACCEPT | REPAIR | QUARANTINE
        self.trigger = trigger
        self.details = details or {}

class Sanitizer:
    """
    Classifies incoming events based on data quality.

    The sanitizer does not modify events.
    It categorizes them into ACCEPT, REPAIR, or QUARANTINE
    so that downstream components can decide how to react.
    """
    def __init__(self, allowed_lateness_sec=0.5):
        self.allowed_lateness_sec = allowed_lateness_sec
        self.last_event_time_by_stream = {}

    def sanitize(self, event):
        """
        Detects out-of-order events based on event_time.

        If an event arrives later than the allowed lateness threshold,
        it is classified as QUARANTINE and may trigger a trust state transition.
        """
        stream = event.stream
        event_time = event.event_time

        last_time = self.last_event_time_by_stream.get(stream)

        if last_time is None:
            self.last_event_time_by_stream[stream] = event_time
            return SanitizeResult("ACCEPT")

        delta = last_time - event_time

        # 정상 or 미래
        if delta <= 0:
            self.last_event_time_by_stream[stream] = event_time
            return SanitizeResult("ACCEPT")

        # 늦었지만 허용
        if delta <= self.allowed_lateness_sec:
            return SanitizeResult(
                "REPAIR",
                trigger="out_of_order_timestamp",
                details={
                    "event_time": event_time,
                    "last_event_time": last_time,
                    "lateness_sec": delta,
                    "allowed_lateness_sec": self.allowed_lateness_sec,
                },
            )

        # 너무 늦음 -> 신뢰 불가
        return SanitizeResult(
            "QUARANTINE",
            trigger="out_of_order_timestamp",
            details={
                "event_time": event_time,
                "last_event_time": last_time,
                "lateness_sec": delta,
                "allowed_lateness_sec": self.allowed_lateness_sec,
            },
        )
