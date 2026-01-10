"""
Runs the end-to-end decision flow for historical CSV input.

Ingest -> Sanitize -> Trust -> Hypothesis -> Decision -> Logs.
"""


import json
import os
import glob

from trust.trust_manager import TrustManager
from decision.decision_engine import DecisionEngine
from hypothesis.hypothesis_evaluator import HypothesisEvaluator
from ingest.csv_ingestor import CSVIngestor
from sanitize.sanitizer import Sanitizer


def main():
    data_dir = os.getenv("DATA_DIR", "data")
    output_root = os.getenv("OUTPUT_DIR", "output")

    out_dir = os.path.join(output_root, "historical")
    os.makedirs(out_dir, exist_ok=True)

    decisions_path = os.path.join(out_dir, "decisions.jsonl")
    transitions_path = os.path.join(out_dir, "state_transitions.jsonl")

    sanitizer = Sanitizer(allowed_lateness_sec=0.5)
    trust_manager = TrustManager()
    hypothesis = HypothesisEvaluator()
    decision_engine = DecisionEngine()

    csv_files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    with open(decisions_path, "w") as decisions_f, open(transitions_path, "w") as transitions_f:
        for file_path in csv_files:
            ingestor = CSVIngestor(file_path=file_path, stream_name="trade")

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
                    "stream": str(event.stream),
                    "data_trust": trust_state,
                    "hypothesis": hypothesis_state,
                    "decision": decision,
                    "sanitize": sanitize_result.classification,
                    "trigger": sanitize_result.trigger,
                }
                decisions_f.write(json.dumps(decision_log) + "\n")

                for t in transitions:
                    transitions_f.write(json.dumps(t) + "\n")


if __name__ == "__main__":
    main()
