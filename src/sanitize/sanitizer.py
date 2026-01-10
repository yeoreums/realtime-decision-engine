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

        # Fat finger detection memory
        self.last_price_by_stream = {}
        self.last_price_time_by_stream = {}

    def _extract_price(self, payload):
        p = payload.get("price")
        if p is None:
            p = payload.get("p") or payload.get("c")
        if p is None:
            return None
        try:
            return float(p)
        except (TypeError, ValueError):
            return None

    def sanitize(self, event):
        stream = event.stream
        event_time = event.event_time
        current_price = self._extract_price(event.payload)

        classification = "ACCEPT"
        trigger = None
        details = {}

        # Out-of-order timestamp detection
        last_time = self.last_event_time_by_stream.get(stream)

        if last_time is None:
            self.last_event_time_by_stream[stream] = event_time

        else:
            delta = last_time - event_time

            if delta <= 0:
                self.last_event_time_by_stream[stream] = event_time

            elif delta <= self.allowed_lateness_sec:
                classification = "REPAIR"
                trigger = "out_of_order_timestamp"
                details = {
                    "event_time": event_time,
                    "last_event_time": last_time,
                    "lateness_sec": delta,
                    "allowed_lateness_sec": self.allowed_lateness_sec,
                }

            else:
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

        if stream not in ("trade", "ticker"):
            return SanitizeResult(classification, trigger, details)

        # Fat finger detection
        last_price = self.last_price_by_stream.get(stream)
        last_price_time = self.last_price_time_by_stream.get(stream)

        if (
            last_price is not None
            and last_price_time is not None
            and current_price is not None
        ):
            time_delta = event_time - last_price_time

            if 0 < time_delta <= 2:
                if last_price <= 0:
                    return SanitizeResult(
                        "QUARANTINE",
                        trigger="fat_finger_price",
                        details={
                            "last_price": last_price,
                            "current_price": current_price,
                            "reason": "non_positive_last_price",
                        },
                    )
                price_change_ratio = abs(current_price - last_price) / last_price

                if price_change_ratio >= 0.03:
                    return SanitizeResult(
                        "QUARANTINE",
                        trigger="fat_finger_price",
                        details={
                            "last_price": last_price,
                            "current_price": current_price,
                            "price_change_ratio": price_change_ratio,
                            "time_delta_sec": time_delta,
                        },
                    )

        # Update last seen price
        if current_price is not None:
            self.last_price_by_stream[stream] = current_price
            self.last_price_time_by_stream[stream] = event_time

        return SanitizeResult(classification, trigger, details)
