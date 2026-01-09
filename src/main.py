"""
Entry point for running the decision engine.

This script orchestrates the end-to-end flow:
Ingest -> Sanitize -> Trust -> Hypothesis -> Decision -> Log.
"""

import json
import os

from trust.trust_manager import TrustManager
from decision.decision_engine import DecisionEngine
from hypothesis.hypothesis_evaluator import HypothesisEvaluator
from ingest.csv_ingestor import CSVIngestor
from sanitize.sanitizer import Sanitizer


def main():
    ingestor = CSVIngestor(
        file_path="data/sample.csv",
        stream_name="trade"
    )

    sanitizer = Sanitizer(allowed_lateness_sec=0.5)
    trust_manager = TrustManager()
    hypothesis = HypothesisEvaluator()
    decision_engine = DecisionEngine()

    os.makedirs("output/historical", exist_ok=True)

    decisions_path = "output/historical/decisions.jsonl"
    transitions_path = "output/historical/state_transitions.jsonl"

    with open(decisions_path, "w") as decisions_f, open(transitions_path, "w") as transitions_f:
        # Orchestrates the end-to-end decision flow for each incoming event
        for event in ingestor.stream():
            sanitize_result = sanitizer.sanitize(event)
            trust_state, transitions = trust_manager.update(sanitize_result, event)
            hypothesis_state = hypothesis.update(event)
            decision = decision_engine.decide(
                trust_state=trust_state,
                hypothesis_state=hypothesis_state
            )

            decision_log = {
                "ts": event.event_time,
                "data_trust": trust_state,
                "hypothesis": hypothesis_state,
                "decision": decision,
                "stream": str(event.stream)
            }

            decisions_f.write(json.dumps(decision_log) + "\n")

            for t in transitions:
                transitions_f.write(json.dumps(t) + "\n")


if __name__ == "__main__":
    main()
