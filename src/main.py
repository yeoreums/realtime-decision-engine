"""
Entry point for running the decision engine in historical or realtime mode.

Modes:
- historical: read CSV files from DATA_DIR and write logs to OUTPUT_DIR/historical/
- realtime: connect to Binance Futures WebSocket and write logs to OUTPUT_DIR/realtime/
"""

import glob
import json
import os
import sys
import time
from collections import Counter

from decision.decision_engine import DecisionEngine
from hypothesis.hypothesis_evaluator import HypothesisEvaluator
from ingest.csv_ingestor import CSVIngestor
from sanitize.sanitizer import Sanitizer
from trust.trust_manager import TrustManager


def run_historical():
    data_dir = os.getenv("DATA_DIR", "data")
    output_root = os.getenv("OUTPUT_DIR", "output")

    out_dir = os.path.join(output_root, "historical")
    os.makedirs(out_dir, exist_ok=True)

    decisions_path = os.path.join(out_dir, "decisions.jsonl")
    transitions_path = os.path.join(out_dir, "state_transitions.jsonl")
    summary_path = os.path.join(out_dir, "summary.json")

    allowed_lateness_sec = float(os.getenv("ALLOWED_LATENESS_SEC", "0.5"))
    sanitizer = Sanitizer(allowed_lateness_sec=allowed_lateness_sec)
    trust_manager = TrustManager()
    hypothesis = HypothesisEvaluator()
    decision_engine = DecisionEngine()

    start = time.time()
    events = 0
    decisions = 0
    transitions_count = 0
    errors = 0
    stream_counts = Counter()

    csv_files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    with open(decisions_path, "w") as decisions_f, open(transitions_path, "w") as transitions_f:
        def infer_stream_name(file_path: str) -> str:
            name = os.path.basename(file_path).lower()
            if "orderbook" in name or "depth" in name or "book" in name:
                return "orderbook"
            if "liquid" in name or "force" in name:
                return "liquidation"
            if "ticker" in name:
                return "ticker"
            return "trade"

        for file_path in csv_files:
            stream_name = infer_stream_name(file_path)
            ingestor = CSVIngestor(file_path=file_path, stream_name=stream_name)

            for event in ingestor.stream():
                stream_counts[str(event.stream)] += 1
                events += 1

                sanitize_result = sanitizer.sanitize(event)
                trust_state, transitions = trust_manager.update(sanitize_result, event)
                now_ts = time.time()
                hypothesis_state = hypothesis.update(event, now_ts)

                decision = decision_engine.decide(
                    trust_state=trust_state,
                    hypothesis_state=hypothesis_state,
                )
                decisions += 1

                reason = sanitize_result.trigger
                if hypothesis_state != "VALID":
                    reason = "hypothesis_" + hypothesis_state.lower()

                decision_log = {
                    "ts": event.event_time,
                    "process_ts": event.receive_time,
                    "stream": str(event.stream),
                    "data_trust": trust_state,
                    "hypothesis": hypothesis_state,
                    "decision": decision,
                    "action": decision,
                    "reason": reason,
                    "sanitize": sanitize_result.classification,
                    "trigger": sanitize_result.trigger,
                }
                decisions_f.write(json.dumps(decision_log) + "\n")

                for t in transitions:
                    transitions_f.write(json.dumps(t) + "\n")
                    transitions_count += 1

    end = time.time()
    run_seconds = round(end - start, 3)

    summary = {
        "mode": "historical",
        "run_seconds": run_seconds,
        "events": events,
        "decisions": decisions,
        "transitions": transitions_count,
        "errors": errors,
        "stream_counts": dict(stream_counts),
        "allowed_lateness_sec": allowed_lateness_sec,
        "data_dir": data_dir,
        "output_dir": out_dir,
        "started_at_unix": start,
        "ended_at_unix": end,
        "files_processed": len(csv_files),
    }
    with open(summary_path, "w") as f:
        json.dump(summary, f)


def run_realtime():
    from ingest.binance_ws_ingestor import BinanceFuturesWSIngestor
    output_root = os.getenv("OUTPUT_DIR", "output")
    out_dir = os.path.join(output_root, "realtime")
    os.makedirs(out_dir, exist_ok=True)

    decisions_path = os.path.join(out_dir, "decisions.jsonl")
    transitions_path = os.path.join(out_dir, "state_transitions.jsonl")
    summary_path = os.path.join(out_dir, "summary.json")

    run_seconds = int(os.getenv("RUN_SECONDS", "60"))
    allowed_lateness_sec = float(os.getenv("ALLOWED_LATENESS_SEC", "0.5"))
    symbol = os.getenv("SYMBOL", "btcusdt")

    sanitizer = Sanitizer(allowed_lateness_sec=allowed_lateness_sec)
    trust_manager = TrustManager()
    hypothesis = HypothesisEvaluator()
    decision_engine = DecisionEngine()

    ingestor = BinanceFuturesWSIngestor(symbol=symbol)

    start = time.time()
    events = 0
    decisions = 0
    transitions_count = 0
    stream_counts = Counter()
    errors = 0
    last_error = None

    with open(decisions_path, "w") as decisions_f, open(transitions_path, "w") as transitions_f:
        event_iter = ingestor.stream()

        while time.time() - start < run_seconds:
            try:
                event = next(event_iter)
            except KeyboardInterrupt:
                break
            except Exception as e:
                errors += 1
                last_error = f"{type(e).__name__}: {e}"
                continue

            stream_counts[str(event.stream)] += 1
            events += 1

            sanitize_result = sanitizer.sanitize(event)
            trust_state, transitions = trust_manager.update(sanitize_result, event)
            now_ts = time.time()
            hypothesis_state = hypothesis.update(event, now_ts)

            decision = decision_engine.decide(
                trust_state=trust_state,
                hypothesis_state=hypothesis_state,
            )
            decisions += 1

            reason = sanitize_result.trigger
            if hypothesis_state != "VALID":
                reason = "hypothesis_" + hypothesis_state.lower()
            decision_log = {
                "ts": event.event_time,
                "receive_ts": event.receive_time,
                "stream": str(event.stream),
                "data_trust": trust_state,
                "hypothesis": hypothesis_state,
                "decision": decision,
                "action": decision,
                "reason": reason,
                "sanitize": sanitize_result.classification,
                "trigger": sanitize_result.trigger,
            }
            decisions_f.write(json.dumps(decision_log) + "\n")

            # Stream stall detection (Phase 2 robustness)
            now_ts = time.time()
            stall_state, stall_transitions = trust_manager.detect_stall(now_ts)
            for t in stall_transitions:
                transitions_f.write(json.dumps(t) + "\n")
                transitions_count += 1

    summary = {
        "mode": "realtime",
        "symbol": symbol,
        "run_seconds": run_seconds,
        "events": events,
        "decisions": decisions,
        "transitions": transitions_count,
        "errors": errors,
        "last_error": last_error,
        "stream_counts": dict(stream_counts),
        "allowed_lateness_sec": allowed_lateness_sec,
        "output_dir": out_dir,
        "started_at_unix": start,
        "ended_at_unix": time.time(),
    }
    with open(summary_path, "w") as f:
        json.dump(summary, f)


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "historical").strip().lower()

    if mode == "historical":
        run_historical()
        return

    if mode == "realtime":
        run_realtime()
        return

    raise ValueError("Mode must be 'historical' or 'realtime'.")


if __name__ == "__main__":
    main()
