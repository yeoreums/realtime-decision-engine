import json
import os

from trust.trust_manager import TrustManager
from decision.decision_engine import DecisionEngine
from hypothesis.hypothesis_evaluator import HypothesisEvaluator
from ingest.csv_ingestor import CSVIngestor


def main():
    ingestor = CSVIngestor(
        file_path="data/sample.csv",
        stream_name="trade"
    )

    trust_manager = TrustManager()
    hypothesis = HypothesisEvaluator()
    decision_engine = DecisionEngine()

    os.makedirs("output", exist_ok=True)

    with open("output/state_transitions.jsonl", "w") as f:
        for event in ingestor.stream():
            trust_state = trust_manager.update(event)
            hypothesis_state = hypothesis.update(event)
            decision = decision_engine.decide(
                trust_state=trust_state,
                hypothesis_state=hypothesis_state
            )

            log = {
                "ts": event.event_time,
                "data_trust": trust_state,
                "hypothesis": hypothesis_state,
                "decision": decision,
                "stream": str(event.stream)
            }

            f.write(json.dumps(log) + "\n")


if __name__ == "__main__":
    main()
