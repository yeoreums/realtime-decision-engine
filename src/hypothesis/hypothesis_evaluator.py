# HypothesisEvaluator
# Evaluates market hypothesis validity after liquidation events

class HypothesisEvaluator:
    def __init__(self, no_decision_window_sec: float = 5.0):
        # Hypothesis states:
        # VALID -> normal
        # WEAKENING -> no-decision window after liquidation
        # INVALID -> (reserved for stronger conditions)
        self.no_decision_window_sec = no_decision_window_sec
        self.no_decision_until_ts: float | None = None

    def update(self, event, now_ts: float):
        """
        Update hypothesis validity based on market conditions.

        Liquidation policy:
        - After a liquidation event, enter a no-decision window (WEAKENING)
          for a fixed duration.
        - After the window expires, recover to VALID.

        Returns:
            Hypothesis state string: VALID / WEAKENING / INVALID
        """

        # Trigger no-decision window on liquidation
        if str(event.stream) == "liquidation":
            until = float(event.event_time) + self.no_decision_window_sec
            if self.no_decision_until_ts is None:
                self.no_decision_until_ts = until
            else:
                # Extend window if another liquidation arrives
                self.no_decision_until_ts = max(self.no_decision_until_ts, until)

        # If we are inside no-decision window
        if self.no_decision_until_ts is not None:
            if now_ts < self.no_decision_until_ts:
                return "WEAKENING"
            else:
                # Window expired -> recover
                self.no_decision_until_ts = None
                return "VALID"

        return "VALID"
