# 🛡️ Hardened Agent: Demo Walkthrough

> **"The agent that cannot panic is the agent that will die calmly."**

This document guides you through the **Legendary-Tier Hardened LangChain Demo**. We have built a robust research agent that survives adversarial scenarios where standard agents fail.

## 🚀 Quick Start

### 1. Run the Adversarial Tests (The Proof)

We have two key scenarios proving robustness:

**A. The Infinite Loop (A -> A -> A)**
```bash
pytest tests/adversarial/test_infinite_loop.py -v
```

**B. The Honey Pot / Cycle Loop (A -> B -> A -> B)**
*This addresses the "triviality" concern by testing complex patterns.*
```bash
pytest tests/adversarial/test_cycle_loop.py -v
```

**Expected Output for Both:**
- `test_baseline_fails...`: **PASSED** (Confirms baseline fails)
- `test_hardened_survives...`: **PASSED** (Confirms hardened agent survives)

### 2. Run the Interactive Demo

See the Hardened Agent fight a loop in real-time:

```bash
python src/agents/hardened.py
```

You will see:
1.  Agent starts looping ("search", "search"...)
2.  **DEADLOCK** detected by the Brainstem.
3.  **PROTOCOL OVERRIDE** forces a different tool.
4.  Agent tries to loop again.
5.  **DEADLOCK** detected again.
6.  **SCARCITY** detected (max steps).
7.  **PROTOCOL OVERRIDE** forces immediate synthesis.
8.  Agent returns a result instead of crashing.

### 3. Run the Real LangChain Integration

See the hardening layer wrapping a **Real LangChain Agent**:

```bash
PYTHONPATH=. python src/agents/langchain_hardened.py
```

This demonstrates:
-   **LangChain Primitives**: Uses `ChatPromptTemplate`, `BaseChatModel`, `@tool`.
-   **Custom Agent Loop**: Wraps the standard chain with the "Brainstem" safety layer.
-   **Same Robustness**: Survives the infinite loop just like the pure Python version.

### 4. Run with Real OpenAI API

To test with a real LLM:

1.  Edit `hardened_agent/.env` and add your key:
    ```bash
    OPENAI_API_KEY=sk-...
    USE_MOCK_LLM=False
    ```
2.  Run the LangChain demo:
    ```bash
    PYTHONPATH=. python src/agents/langchain_hardened.py
    ```
    It will detect the key and use `ChatOpenAI` (GPT-4o).

### 5. Run the Baseline Demo (The Failure)

See the "Smart Fool" get stuck:

```bash
python src/agents/baseline.py
```

You will see it loop blindly until "Max steps reached".

---

## 🏗️ Architecture: The Bicameral Mind

We implemented a **3-Layer Defensive Architecture**:

### Layer 1: Cortex (The LLM)
- **Component**: `src/agents/hardened.py`
- **Role**: Optimizes for the goal. Smart but naive.
- **Behavior**: Standard ReAct loop.

### Layer 2: Brainstem (Meta-Cognitive Monitor)
- **Component**: `src/monitoring/monitor.py`
- **Role**: Watches the Cortex. Detects 5 Critical States.
- **Protocols**:
    - **DEADLOCK**: Breaks loops (`src/memory/action_history.py`)
    - **PANIC**: Handles confusion (low confidence)
    - **HUBRIS**: Checks over-confidence
    - **SCARCITY**: Manages resources
    - **NOVELTY**: Handles contradictions

### Layer 3: Circuit Breaker (The Kill Switch)
- **Component**: `src/monitoring/circuit_breaker.py`
- **Role**: Prevents thrashing.
- **Behavior**: If the Brainstem fires 3+ times in a row, the Circuit Breaker HALTS the agent to prevent damage/waste.

---

## 🧪 The "Silver Gauge"

We also implemented the **Silver Gauge** (`src/monitoring/silver_gauge.py`) to make decisions transparent.

It calculates `k_explore` based on **Goal Value (G)** and **Information Gain (I)**:
- `k ≈ 1.0`: **Generalist** (Balanced)
- `k << 1.0`: **Specialist** (Imbalanced)

Run the gauge demo:
```bash
python src/monitoring/silver_gauge.py
```

---

## 📜 Philosophy

This project is an implementation of the **72 Aphorisms** for Robust AI.

- **Aphorism #7**: "Insanity is doing the same thing over and over" → **DEADLOCK Protocol**
- **Aphorism #13**: "Entropy is an API" → **PANIC Protocol**
- **Aphorism #23**: "A dead agent is better than a thrashing agent" → **Circuit Breaker**
- **Aphorism #37**: "History vetoes feelings" → **Action History**

## 📂 Project Structure

```
hardened_agent/
├── src/
│   ├── agents/          # Baseline and Hardened agents
│   ├── memory/          # ActionHistory (SQLite)
│   ├── monitoring/      # Critical States, Monitor, Circuit Breaker
│   └── utils/           # MockLLM for deterministic testing
├── tests/
│   ├── adversarial/     # The "Red Team" scenarios
│   └── unit/            # Unit tests for all components
└── README.md
```

## 🏆 Conclusion

We have successfully transformed a "Smart Fool" (Baseline) into a "Wise Survivor" (Hardened). 

The Hardened Agent:
1.  **Knows when it is stuck.**
2.  **Knows when it is confused.**
3.  **Knows when to stop.**

This is the difference between a demo and a production system.
