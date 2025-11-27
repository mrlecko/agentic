# The Hardened Agent: Production-Ready LangChain Demo

> **"Most LangChain agents loop forever, hallucinate confidently, and crash ungracefully. This one knows when to panic, when to stop, and when to admit it's wrong. That's not smarter. That's wiser. That's survival."**

## 🛡️ What Is This?

A **battle-hardened** LangChain research agent that demonstrates **CONSIDERABLE ROBUSTNESS** through:

- **Meta-Cognitive Monitoring** - The agent watches itself
- **Critical State Protocols** - Five hard-coded survival instincts
- **Circuit Breakers** - Graceful failure when thrashing
- **Transparent Decisions** - Explainable geometry, not opaque scores

## 🎯 Why Is This Different?

**Normal LangChain Agent:**
- ❌ Loops forever when confused
- ❌ Hallucinates with perfect confidence
- ❌ Crashes when out of tokens
- ❌ No self-awareness

**Hardened Agent:**
- ✅ Detects loops and breaks them
- ✅ Admits uncertainty explicitly
- ✅ Degrades gracefully under resource limits
- ✅ Has meta-cognitive monitoring

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│   Layer 3: Circuit Breaker          │
│   "If thrashing, HALT"              │
└─────────────────────────────────────┘
              ↑
┌─────────────────────────────────────┐
│   Layer 2: Brainstem (5 Protocols)  │
│   PANIC | DEADLOCK | HUBRIS         │
│   SCARCITY | NOVELTY                │
└─────────────────────────────────────┘
              ↑
┌─────────────────────────────────────┐
│   Layer 1: Cortex (LangChain)       │
│   ReAct Agent + Tools               │
└─────────────────────────────────────┘
```

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Run tests (uses mocked LLM)
pytest tests/ -v

# 4. Run adversarial scenarios (Red Team battery)
pytest tests/adversarial/ -v -m adversarial

# 5. Try it yourself
python examples/demo.py
```

## 🧪 Test-Driven Development

This project is built with **TDD + RED TEAM** mindset:

```bash
# Run all tests
pytest

# Run only unit tests (fast, mocked)
pytest -m unit

# Run integration tests (may use real API)
pytest -m integration

# Run adversarial scenarios (Red Team)
pytest -m adversarial

# Run with coverage
pytest --cov=src --cov-report=html
```

## 🎪 The Five Critical States

| State | Trigger | Response | Philosophy |
|-------|---------|----------|------------|
| **PANIC** | High confusion | Conservative actions | "When confused, be safe not clever" |
| **DEADLOCK** | Action loops | Force different action | "Insanity is doing the same thing over and over" |
| **HUBRIS** | Over-confidence | Force skepticism | "Success breeds complacency" |
| **SCARCITY** | Low resources | Immediate synthesis | "Perfect is the enemy of done" |
| **NOVELTY** | Contradictions | Pause and integrate | "Surprise is data" |

## 📊 Red Team Battery

Five adversarial scenarios that **prove** robustness:

1. **Infinite Research Loop** - Baseline loops forever ❌ → Hardened breaks loop ✅
2. **Honey Pot** - Baseline accepts misinformation ❌ → Hardened seeks balance ✅
3. **Confusion Pit** - Baseline hallucinates ❌ → Hardened admits uncertainty ✅
4. **Token Death Spiral** - Baseline crashes ❌ → Hardened degrades gracefully ✅
5. **Contradiction Bomb** - Baseline ignores ❌ → Hardened acknowledges both ✅

## 📁 Project Structure

```
hardened_agent/
├── src/
│   ├── agents/
│   │   ├── baseline.py       # Standard agent (Smart Fool)
│   │   └── hardened.py       # Meta-cognitive agent (Wise Survivor)
│   ├── monitoring/
│   │   ├── critical_states.py
│   │   ├── circuit_breaker.py
│   │   └── silver_gauge.py
│   ├── memory/
│   │   └── action_history.py
│   └── utils/
│       └── mock_llm.py       # Mocked LLM for testing
├── tests/
│   ├── unit/                 # Fast, mocked tests
│   ├── integration/          # Real API tests
│   └── adversarial/          # Red Team scenarios
├── scenarios/                # Adversarial test scenarios
└── examples/                 # Demo scripts
```

## 🔬 Philosophy

This implementation embodies hard-won wisdom from battle scars:

- **Aphorism #7**: "Insanity is doing the same thing over and over" → DEADLOCK protocol
- **Aphorism #13**: "Entropy is an API" → PANIC detection
- **Aphorism #25**: "Be your own assassin" → Red Team battery
- **Aphorism #37**: "History vetoes feelings" → Memory-based overrides
- **Aphorism #64**: "Legendary standard" → This implementation


## 📝 License

MIT - Share the wisdom

---

**Built with:** Test-Driven Development + Red Team thinking
