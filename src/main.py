from trust.trust_manager import TrustManager
from decision.decision_engine import DecisionEngine
from hypothesis.hypothesis_evaluator import HypothesisEvaluator

def main(mode: str):
    """
    mode: 'historical' or 'realtime'
    """

    ingest = Ingestor(mode=mode)
    sanitizer = Sanitizer()
    trust_manager = TrustManager()
    hypothesis = HypothesisEvaluator()
    decision_engine = DecisionEngine()

    for event in ingest.stream():
        clean_event = sanitizer.process(event)
        trust_state = trust_manager.update(clean_event)
        hypothesis_state = hypothesis.update(clean_event)
        decision = decision_engine.decide(
            trust_state=trust_state,
            hypothesis_state=hypothesis_state
        )

        log_state(event, trust_state, hypothesis_state, decision)
