"""
Meta-Cognitive Monitor: The Orchestrator

WHY THIS IS MORE ROBUST:
- Baseline agents: React to single signals or ignore them.
- Hardened agent: Centralizes all signals (history, confidence, resources).
- Implements PRIORITY ORDERING for critical states.

RED TEAM DESIGN:
- Must handle conflicting signals (e.g. Confused AND Looping).
- Must always record to Circuit Breaker.
- Must be fast (runs every step).

Aphorism #3: "The ultimate sophistication is the wisdom of the reflexes"
"""

from typing import Optional, Dict, Any
from src.monitoring.critical_states import (
    CriticalState, StateDetection, ConfidenceEstimator
)
from src.memory.action_history import ActionHistory
from src.monitoring.circuit_breaker import CircuitBreaker

class MetaCognitiveMonitor:
    """
    The "Brainstem" of the agent.
    
    Monitors all inputs and determines the current Critical State.
    """
    
    def __init__(self, action_history: ActionHistory, circuit_breaker: CircuitBreaker):
        self.history = action_history
        self.circuit_breaker = circuit_breaker
        
        # Configuration
        self.panic_threshold = 0.4      # Below this confidence = PANIC
        self.hubris_threshold = 0.9     # Above this confidence = HUBRIS (if early)
        self.hubris_max_steps = 2       # Steps considered "early"
        self.scarcity_threshold = 0.9   # >90% resource usage = SCARCITY
        
    def check_state(self, 
                   llm_response: str, 
                   current_step: int, 
                   max_steps: int,
                   tokens_used: int = 0,
                   budget: int = 0,
                   session_id: str = "default") -> StateDetection:
        """
        Evaluate current context and determine Critical State.
        
        Priority Order:
        1. SCARCITY (Physical reality overrides everything)
        2. DEADLOCK (Stuck is stuck)
        3. PANIC (Confusion is dangerous)
        4. HUBRIS (Overconfidence is a trap)
        5. NOVELTY (Contradiction - TODO: Implement with source tracking)
        6. NONE (Normal)
        """
        
        # 1. Check SCARCITY
        # -----------------
        step_usage = current_step / max_steps if max_steps > 0 else 0
        token_usage = tokens_used / budget if budget > 0 else 0
        
        if step_usage > self.scarcity_threshold or token_usage > self.scarcity_threshold:
            state = CriticalState.SCARCITY
            reason = []
            if step_usage > self.scarcity_threshold:
                reason.append(f"Steps exhausted ({step_usage:.0%})")
            if token_usage > self.scarcity_threshold:
                reason.append(f"Tokens exhausted ({token_usage:.0%})")
            
            detection = StateDetection(
                state=state,
                confidence=1.0,
                reason=f"SCARCITY: {', '.join(reason)}",
                metadata={'step_budget': step_usage, 'token_budget': token_usage}
            )
            self.circuit_breaker.record_critical_state(state)
            return detection

        # 2. Check DEADLOCK
        # -----------------
        loop = self.history.detect_loop(session_id)
        if loop:
            state = CriticalState.DEADLOCK
            detection = StateDetection(
                state=state,
                confidence=loop.confidence,
                reason=f"DEADLOCK: {loop.description}",
                metadata={'pattern': loop.detected_sequence}
            )
            self.circuit_breaker.record_critical_state(state)
            return detection

        # 3. Check PANIC & HUBRIS (Confidence-based)
        # ------------------------------------------
        confidence = ConfidenceEstimator.estimate_from_text(llm_response)
        
        if confidence < self.panic_threshold:
            state = CriticalState.PANIC
            detection = StateDetection(
                state=state,
                confidence=1.0 - confidence, # Confidence in the panic state
                reason=f"PANIC: Low confidence detected ({confidence:.0%})",
                metadata={'text_confidence': confidence}
            )
            self.circuit_breaker.record_critical_state(state)
            return detection
            
        if confidence > self.hubris_threshold and current_step <= self.hubris_max_steps:
            state = CriticalState.HUBRIS
            detection = StateDetection(
                state=state,
                confidence=confidence,
                reason=f"HUBRIS: High confidence ({confidence:.0%}) too early (step {current_step})",
                metadata={'steps_taken': current_step}
            )
            self.circuit_breaker.record_critical_state(state)
            return detection

        # 4. Normal Operation
        # -------------------
        self.circuit_breaker.record_critical_state(CriticalState.NONE)
        return StateDetection(
            state=CriticalState.NONE,
            confidence=0.0,
            reason="Normal operation",
            metadata={}
        )

