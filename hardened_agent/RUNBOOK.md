# Hardened Agent - Operations Runbook

**Version:** 1.0  
**Last Updated:** 2024-11-27  
**On-Call Contact:** [Insert PagerDuty/Slack channel]

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Monitoring](#monitoring)
3. [Common Incidents](#common-incidents)
4. [Troubleshooting](#troubleshooting)
5. [Configuration](#configuration)
6. [Escalation](#escalation)

---

## 1. System Overview

### Architecture

```
┌─────────────────────────────────────┐
│   Circuit Breaker                   │
│   "If thrashing, HALT"              │
└─────────────────────────────────────┘
              ↑
┌─────────────────────────────────────┐
│   Meta-Cognitive Monitor             │
│   PANIC | DEADLOCK | HUBRIS         │
│   SCARCITY | NOVELTY                │
└─────────────────────────────────────┘
              ↑
┌─────────────────────────────────────┐
│   LLM Agent (Cortex)                │
│   ReAct Agent + Tools               │
└─────────────────────────────────────┘
```

### Key Components

- **Monitor** (`src/monitoring/monitor.py`): Evaluates critical states
- **Circuit Breaker** (`src/monitoring/circuit_breaker.py`): Prevents thrashing
- **Action History** (`src/memory/action_history.py`): Loop detection
- **Protocols** (`src/monitoring/critical_states.py`): Deterministic interventions

---

## 2. Monitoring

### 2.1 Metrics Endpoint

**URL:** `http://localhost:8000/metrics`  
**Format:** Prometheus

### 2.2 Key Metrics

| Metric | Type | Description | Alert Threshold |
|--------|------|-------------|-----------------|
| `agent_critical_states_total` | Counter | Critical state activations | >10/hour per state |
| `circuit_breaker_trips_total` | Counter | Circuit breaker trips | >1/hour |
| `agent_llm_latency_seconds` | Histogram | LLM call latency | p99 >5s |
| `agent_completions_total{outcome="timeout"}` | Counter | Timeout failures | >5% of completions |

### 2.3 Logs

**Format:** JSON structured logs  
**Location:** `stdout` (capture with Fluentd/Logstash)

**Key Log Events:**
```json
{
  "event_type": "circuit_breaker_trip",
  "level": "CRITICAL",
  "reason": "Too many PANIC states",
  "diagnostics": {...}
}
```

### 2.4 Sample Grafana Queries

```promql
# Circuit Breaker Trip Rate
rate(circuit_breaker_trips_total[5m])

# Critical State Activations by Type
sum by (state) (rate(agent_critical_states_total[5m]))

# LLM Latency p99
histogram_quantile(0.99, agent_llm_latency_seconds_bucket)

# Agent Success Rate
rate(agent_completions_total{outcome="success"}[5m]) 
/ 
rate(agent_completions_total[5m])
```

---

## 3. Common Incidents

### 3.1 Circuit Breaker Tripped

**Symptoms:**
- Log: `"Circuit breaker tripped: <reason>"`
- Metric: `circuit_breaker_trips_total` incremented
- Agent stops executing

**Root Causes:**
1. Repeated DEADLOCK (loop detected multiple times)
2. Repeated PANIC (LLM confused)
3. Oscillation between states (A→B→A→B)

**Resolution:**

1. **Check logs** for the trip reason:
   ```bash
   grep "circuit_breaker_trip" logs.json | jq .
   ```

2. **Identify pattern**:
   - DEADLOCK: Check if tools are stuck/broken
   - PANIC: Check LLM config (temperature, prompt)
   - Oscillation: Check for conflicting tool responses

3. **Short-term fix**:
   - Restart agent (circuit breaker resets)
   - Adjust thresholds in `config.yaml` if too sensitive

4. **Long-term fix**:
   - Fix broken tools
   - Improve prompts
   - Add better tools for the task

**Prevention:**
- Set alerts on `circuit_breaker_trips_total`
- Review circuit breaker diagnostics weekly

---

### 3.2 DEADLOCK Loop Detected

**Symptoms:**
- Log: `"State transition: NONE -> DEADLOCK"`
- Metric: `agent_critical_states_total{state="DEADLOCK"}` incremented
- Agent activates DEADLOCK protocol

**Root Causes:**
1. Tool returns same result repeatedly
2. LLM stuck in repetitive pattern
3. Argument values don't match expected schema

**Resolution:**

1. **Check action history**:
   ```bash
   grep "event_type.*state_transition" logs.json | grep DEADLOCK | jq .
   ```

2. **Identify loop**:
   - Exact loop: `search → search → search`
   - Cycle loop: `search → click → search → click`

3. **Fix:**
   - If tool broken: Fix tool logic
   - If LLM stuck: Adjust temperature or prompt
   - If semantic loop: Enable similarity detection (Phase 2)

**Auto-Recovery:**
- DEADLOCK protocol forces different action (1st attempt)
- Forces synthesis (3rd attempt)

---

### 3.3 SCARCITY Resource Exhaustion

**Symptoms:**
- Log: `"State transition: NONE -> SCARCITY"`
- Agent reaches 80% of token/step budget
- Agent forces immediate synthesis

**Root Causes:**
1. Task complexity exceeds budget
2. `max_steps` or `token_budget` too low
3. Inefficient tool usage

**Resolution:**

1. **Check resource usage**:
   ```promql
   agent_token_usage_total
   agent_steps_total
   ```

2. **Adjust budget**:
   ```yaml
   # config.yaml
   agent:
     max_steps: 20  # Increase if needed
     token_budget: 2000
   ```

3. **Optimize**:
   - Review if tools are efficient
   - Check if task can be simplified

**Trade-off:**
- Higher budget = More cost
- Lower budget = More SCARCITY triggers

---

### 3.4 PANIC Low Confidence

**Symptoms:**
- Log: `"State transition: NONE -> PANIC"`
- LLM output has low confidence (hedging words: "maybe", "perhaps")
- Agent switches to "tank mode"

**Root Causes:**
1. LLM truly uncertain (ambiguous task)
2. Insufficient context
3. Temperature too high (randomness)

**Resolution:**

1. **Review LLM response**:
   ```bash
   grep "event_type.*protocol_activation.*PANIC" logs.json | jq .
   ```

2. **Check confidence**:
   - If <0.4: LLM is guessing
   - Review prompt quality
   - Provide more context to tools

3. **Fix:**
   - Improve prompt clarity
   - Lower temperature (0.0 for deterministic)
   - Add better tools for info gathering

**Auto-Recovery:**
- PANIC protocol uses whitelisted reliable sources

---

### 3.5 HUBRIS Over-Confidence

**Symptoms:**
- Log: `"State transition: NONE -> HUBRIS"`
- LLM output very confident (>0.9) with minimal steps
- Agent forces deeper research

**Root Causes:**
1. LLM "hallucinating" with high confidence
2. Task too simple (actual success, not hubris)
3. Temperature too low (LLM overconfident)

**Resolution:**

1. **Check steps taken**:
   ```bash
   grep "event_type.*agent_complete" logs.json | jq '.steps'
   ```

2. **If <3 steps**: Likely true hubris
   - Review LLM output for hallucinations
   - Force research protocol activated correctly

3. **Adjust threshold**:
   ```yaml
   # config.yaml
   critical_states:
     hubris_threshold: 0.95  # Increase to reduce false positives
   ```

---

## 4. Troubleshooting

### 4.1 Agent Not Starting

**Check:**
1. `.env` file exists with `OPENAI_API_KEY`
2. Dependencies installed: `pip install -r requirements.txt`
3. Config file valid: `python src/config/loader.py`

### 4.2 Metrics Not Available

**Check:**
1. `config.yaml` has `observability.metrics_enabled: true`
2. Port 8000 not in use: `lsof -i :8000`
3. Prometheus client installed: `pip install prometheus-client`

### 4.3 Logs Not Structured

**Check:**
1. Logger initialized: `from src.observability.logger import get_logger`
2. Log level correct in config: `observability.log_level`

### 4.4 High Latency

**Check:**
1. LLM latency metric: `agent_llm_latency_seconds`
2. If p99 >5s: OpenAI API may be slow
3. Consider switching model or adding caching

---

## 5. Configuration

### 5.1 Tuning Thresholds

**Conservative (Less false positives):**
```yaml
critical_states:
  panic_threshold: 0.3  # Lower = stricter
  hubris_threshold: 0.95  # Higher = less sensitive
  deadlock_window: 5  # More repeats before trigger

circuit_breaker:
  consecutive_limit: 5  # Allow more failures
```

**Aggressive (More protection):**
```yaml
critical_states:
  panic_threshold: 0.5  # Higher = more sensitive
  hubris_threshold: 0.85  # Lower = catch more overconf
  deadlock_window: 2  # Fewer repeats trigger

circuit_breaker:
  consecutive_limit: 2  # Faster halt
```

### 5.2 Reloading Config

**Note:** Config is loaded on agent initialization. Restart required for changes.

```bash
# Restart agent process
kill -HUP <pid>
```

---

## 6. Escalation

### 6.1 When to Escalate

**Page Immediately If:**
- Circuit breaker trips >5 times/hour
- Agent success rate <50%
- LLM API errors >10%

**Escalate to Engineering If:**
- Repeated pattern of same failure
- New failure mode discovered
- Config tuning doesn't resolve

### 6.2 Escalation Contacts

- **On-Call Engineer:** [PagerDuty rotation]
- **Team Slack:** #hardened-agent-oncall
- **Runbook Issues:** [GitHub repo]

---

## 7. Appendix

### 7.1 Log Event Types

| Event Type | Level | Description |
|------------|-------|-------------|
| `agent_start` | INFO | Agent initialized |
| `state_transition` | INFO | Critical state changed |
| `protocol_activation` | WARNING | Protocol override |
| `circuit_breaker_trip` | CRITICAL | Circuit breaker tripped |
| `agent_complete` | INFO | Agent finished |

### 7.2 Useful Commands

```bash
# Tail logs in JSON format
tail -f logs.json | jq .

# Count critical states by type
cat logs.json | jq -r 'select(.event_type=="state_transition") | .to_state' | sort | uniq -c

# Find circuit breaker trips
cat logs.json | jq 'select(.event_type=="circuit_breaker_trip")'

# Check current config
python src/config/loader.py
```

---

**End of Runbook**
