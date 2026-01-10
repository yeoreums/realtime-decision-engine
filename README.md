# Realtime Decision Engine for Unreliable Market Data

This repository implements a decision gating system for unreliable market data.

The goal is not prediction or alpha generation.
The system answers a simpler operational question:

> When should the system allow, restrict, or halt decisions, and can that logic stay consistent across historical CSV and realtime WebSocket environments?

---

## What this submission proves

This submission focuses on Phase 1 (Historical Validation) and proves:

* An end-to-end pipeline runs consistently
  Ingest → Sanitize → Trust → Hypothesis → Decision → Logs
* Dirty data signals can trigger a trust state transition
* The decision permission changes accordingly and is explainable via logs

---

## Implemented vs Planned

### Implemented (this submission)

Phase

* Historical CSV execution (Docker + mounted `/data`)

Sanitization

* Out-of-order timestamps with `allowed_lateness_sec`

  * REPAIR if lateness is within the threshold
  * QUARANTINE if lateness exceeds the threshold
* Fat-finger price jump rule

  * QUARANTINE if price jump is at least 3 percent within 2 seconds

Trust

* TRUSTED → DEGRADED on QUARANTINE
* Transition is logged to `state_transitions.jsonl`

Decision

* Decision permission is derived from `(data_trust, hypothesis_state)`
* Current mapping

  * DEGRADED or WEAKENING → RESTRICTED
  * UNTRUSTED or INVALID → HALTED

Observability

* `decisions.jsonl` and `state_transitions.jsonl` are generated
* Logs distinguish event-time (`ts`) and processing-time (`receive_ts`) where relevant

### Planned (not implemented in this submission)

* Realtime WebSocket execution (Phase 2)
* Multi-stream ingestion (Trades, Orderbook, Liquidations, Ticker)
* Stream stall detection and crossed-market detection
* Hypothesis evaluator logic using liquidation and orderbook streams
* DEGRADED → UNTRUSTED escalation policy
* `summary.json` output

---

## Most dangerous uncertainty

The most dangerous uncertainty is time inconsistency.

Even if different streams show the same timestamp, it may not represent the same market time.
For this reason, the system distinguishes:

* event-time (`ts`)
* processing-time (`receive_ts`)

and uses sanitization rules to decide when an event is too late or unreliable to trust.

---

## Outputs

After running the historical mode, outputs are written under:

```
output/historical/
├── decisions.jsonl
└── state_transitions.jsonl
```

### Example logs

decisions.jsonl

```json
{"ts": 1699999999.0, "stream": "trade", "data_trust": "DEGRADED", "hypothesis": "VALID", "decision": "RESTRICTED", "sanitize": "QUARANTINE", "trigger": "out_of_order_timestamp"}
```

state_transitions.jsonl

```json
{"ts": 1699999999.0, "receive_ts": 1768019001.1418347, "trigger": "out_of_order_timestamp", "previous_trust": "TRUSTED", "current_trust": "DEGRADED", "details": {"lateness_sec": 3.0, "allowed_lateness_sec": 0.5}}
```

---

## How to run (Docker)

Build

```bash
docker build -t decision-engine .
```

Run (Historical CSV)

```bash
docker run --rm \
  -e DATA_DIR=/data \
  -e OUTPUT_DIR=/output \
  -v /path/to/challenge_data/validation:/data \
  -v "$(pwd)/output:/output" \
  decision-engine
```

---

## If I were to simplify first

I would keep the hypothesis evaluator as a strict placeholder until the data trust policy is validated across more dirty-data patterns and multiple streams. This reduces coupling and keeps the decision gating behavior explainable.
