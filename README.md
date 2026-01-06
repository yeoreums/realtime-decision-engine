# Realtime Decision Engine for Unreliable Market Data

This repository explores the design of a decision gating system for real-time market data under unreliable and imperfect conditions.

Rather than predicting prices or executing trades, the system focuses on determining **when a decision should be allowed, restricted, or halted**, based on data reliability and market stability.

The core question this project addresses is:

Can a decision structure validated on imperfect historical data remain reliable in a real-time WebSocket environment?

---

## 1. Design Philosophy

This system is built around three principles.

First, dirty data is inevitable in real markets.  
Second, not making a decision is also a valid decision.  
Third, data reliability and market validity must be evaluated independently.

The goal is operational safety and explainability, not prediction accuracy.

---

## 2. System Overview

The system processes four concurrent data streams.

- Trades
- Orderbook updates
- Liquidation events
- Market tickers

Each stream may arrive with delays, duplication, missing events, or inconsistent timestamps.  
The system does not assume a unified time axis across streams.

---

## 3. Data Sanitization

Incoming events are classified into three categories.

- **ACCEPT**  
  Valid data that can be used directly.

- **REPAIR**  
  Recoverable anomalies that can be corrected or normalized.

- **QUARANTINE**  
  Unreliable data that must not influence decisions directly.

The following signals trigger quarantine or trust degradation.

### Fat Finger Events
A price jump exceeding **3 percent within 2 seconds**.  
Structural anomalies are confirmed only when such events occur consecutively.

### Crossed Market
Persistent bid greater than or equal to ask conditions.  
Single occurrences are tolerated, consecutive occurrences indicate structural issues.

### Stream Stall
No incoming events for a sustained period.

- 3 seconds without data leads to trust degradation.
- 5 seconds without data leads to an untrusted state.

---

## 4. Data Trust State

The system maintains a data trust state that summarizes overall data reliability.

- **TRUSTED**  
  No recent structural anomalies.

- **DEGRADED**  
  Early warning signals detected. Decisions should be treated cautiously.

- **UNTRUSTED**  
  Structural issues or prolonged data absence detected. Decisions must be halted.

Trust state transitions are driven by the frequency and severity of quarantine signals and stream stalls.

---

## 5. Market Hypothesis

The system evaluates a single hypothesis.

After a large liquidation event, the orderbook requires time to stabilize before allowing reliable decisions.

Hypothesis validity is classified as:

- **VALID**
- **WEAKENING**
- **INVALID**

Following a liquidation event, the system enforces a minimum **5 second no-decision window**.  
During this period, the system continues to observe orderbook depth, spread behavior, and subsequent liquidation activity.

---

## 6. Decision Permission Engine

Final decision permissions are derived from the combination of data trust and hypothesis validity.

| Data Trust | Hypothesis | Decision |
|----------|-----------|----------|
| TRUSTED | VALID | ALLOWED |
| TRUSTED | WEAKENING | RESTRICTED |
| TRUSTED | INVALID | HALTED |
| DEGRADED | VALID | RESTRICTED |
| DEGRADED | WEAKENING | RESTRICTED |
| DEGRADED | INVALID | HALTED |
| UNTRUSTED | ANY | HALTED |

This separation ensures that decisions are never made when either the data or the market context is unreliable.

---

## 7. Observability

All state transitions and decisions are logged explicitly.

Logs allow post-hoc analysis of:

- Why a decision was halted
- Which data anomalies influenced trust
- How hypothesis validity evolved over time

The system prioritizes explainability over silent automation.

---

## 8. Scope and Limitations

This project does not attempt to optimize trading performance or generate alpha.  
Its purpose is to explore robust decision control under real-world data uncertainty.

The architecture is intentionally generic and applicable to any real-time event-driven system facing unreliable inputs.
