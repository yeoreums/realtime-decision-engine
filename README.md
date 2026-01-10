# Realtime Decision Engine for Unreliable Market Data

This repository implements a decision gating system for unreliable market data.

The goal is not prediction or alpha generation.
The system answers a simpler operational question:

> When should the system allow, restrict, or halt decisions,
> and can that logic remain consistent across historical CSV
> and realtime WebSocket environments?

---

## What this submission demonstrates

This submission implements a **Single Decision Engine** that operates
without logic divergence across two environments:

* Phase 1: Historical validation using CSV
* Phase 2: Realtime validation using Binance Futures WebSocket

The system focuses on **decision safety and explainability**, not prediction.

---

## System Architecture

```
Ingest → Sanitize → Trust → Hypothesis → Decision → Logs
```

Each stage is explicitly separated to keep failure modes observable and explainable.

---

## Implemented Features

### Execution Environments

* Historical CSV execution (Docker + mounted `/data`)
* Realtime WebSocket execution (Binance Futures)

The same decision logic is used in both environments.

---

### Multi-Stream Ingestion

The system processes the following streams:

* Trades
* Orderbook
* Liquidations
* Ticker

Historical CSV streams are inferred from file names.
Realtime streams are consumed via Binance Futures multiplex WebSocket.

---

### Time Alignment Policy

The system distinguishes between:

* event-time (`ts`)
* processing-time (`receive_ts`)

Out-of-order and late events are evaluated using an `allowed_lateness_sec` threshold.
Events exceeding this threshold are treated as unreliable.

---

### Sanitization Policy

Events are classified as:

* ACCEPT
* REPAIR
* QUARANTINE

Implemented dirty-data signals:

* Out-of-order timestamps

  * REPAIR if lateness is within the threshold
  * QUARANTINE if lateness exceeds the threshold
* Fat-finger price jumps

  * QUARANTINE if price changes by at least 3 percent within 2 seconds

---

### Trust Management

* Initial state: TRUSTED
* TRUSTED → DEGRADED on QUARANTINE
* DEGRADED → UNTRUSTED on stream stall detection

All trust transitions are logged to `state_transitions.jsonl`.

---

### Hypothesis Evaluation

* Liquidation events trigger a no-decision window
* During this window, the hypothesis state is downgraded to WEAKENING
* After the window expires, the hypothesis recovers automatically

This models the assumption that market conditions immediately after liquidation
are unstable for decision-making.

---

### Decision Policy

Decision permission is derived from `(data_trust, hypothesis_state)`:

* DEGRADED or WEAKENING → RESTRICTED
* UNTRUSTED or INVALID → HALTED
* TRUSTED and VALID → ALLOWED

Decision changes are recorded in `decisions.jsonl` with explicit reasons.

---

### Realtime Robustness

The realtime system is designed to remain operational under:

* Network disconnects and reconnects
* Out-of-order or duplicate messages
* Burst traffic
* Stream stalls

The system does not terminate on these conditions and continues
updating internal state and logs.

---

## Outputs

For each execution mode, outputs are written under:

```
output/
├── historical/
│   ├── decisions.jsonl
│   ├── state_transitions.jsonl
│   └── summary.json
└── realtime/
    ├── decisions.jsonl
    ├── state_transitions.jsonl
    └── summary.json
```

---

## Example Logs

### decisions.jsonl

```json
{
  "ts": 1699999999.0,
  "stream": "trade",
  "data_trust": "DEGRADED",
  "hypothesis": "WEAKENING",
  "decision": "RESTRICTED",
  "action": "RESTRICTED",
  "reason": "hypothesis_weakening"
}
```

### state_transitions.jsonl

```json
{
  "ts": 1699999999.0,
  "trigger": "out_of_order_timestamp",
  "previous_trust": "TRUSTED",
  "current_trust": "DEGRADED"
}
```

---

## How to Run (Docker)

### Build

```bash
docker build -t decision-engine .
```

### Run (Historical CSV)

```bash
docker run --rm \
  -e DATA_DIR=/data \
  -e OUTPUT_DIR=/output \
  -v /path/to/challenge_data/validation:/data \
  -v "$(pwd)/output:/output" \
  decision-engine historical
```

### Run (Realtime)

```bash
docker run --rm \
  -e OUTPUT_DIR=/output \
  -v "$(pwd)/output:/output" \
  decision-engine realtime
```

---

## Most Dangerous Uncertainty

The most dangerous uncertainty is **time inconsistency across streams**.

Even when timestamps appear identical, they may not represent the same
market moment. The system therefore avoids assuming a unified timeline
and instead enforces decision gating through trust degradation and
hypothesis weakening.

---

## If Simplifying Further

If simplified further, crossed-market detection and deeper orderbook
analysis would be deferred until the data trust policy is validated
across more dirty-data patterns and longer realtime runs.
