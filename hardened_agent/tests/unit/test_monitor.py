"""
Test Meta-Cognitive Monitor

RED TEAM THINKING:
- Does it prioritize critical states correctly? (e.g. PANIC > HUBRIS)
- Does it correctly integrate history for DEADLOCK detection?
- Does it trigger the Circuit Breaker when needed?
- Does it handle multiple simultaneous triggers?

WHY THIS IS MORE ROBUST:
- Baseline: No central coordinator, just a loop.
- Hardened: Central brainstem that evaluates ALL signals before acting.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.monitoring.critical_states import CriticalState, StateDetection
from src.monitoring.monitor import MetaCognitiveMonitor
from src.memory.action_history import ActionHistory, LoopDetection, LoopPattern
from src.monitoring.circuit_breaker import CircuitBreaker, CircuitBreakerStatus

class TestMetaCognitiveMonitor:
    
    @pytest.fixture
    def mock_history(self):
        return MagicMock(spec=ActionHistory)
    
    @pytest.fixture
    def mock_breaker(self):
        breaker = MagicMock(spec=CircuitBreaker)
        # Default to not tripped
        breaker.record_critical_state.return_value = CircuitBreakerStatus(
            tripped=False, consecutive_alerts=0, total_alerts=0, 
            alert_history=[], thrashing_pattern=None, diagnostic_info={}
        )
        return breaker
    
    @pytest.fixture
    def monitor(self, mock_history, mock_breaker):
        return MetaCognitiveMonitor(
            action_history=mock_history,
            circuit_breaker=mock_breaker
        )

    @pytest.mark.unit
    def test_check_state_none_default(self, monitor):
        """Test: Returns NONE state when everything is normal."""
        # Setup mocks to return normal values
        monitor.history.detect_loop.return_value = None
        # Mock confidence check to be high enough
        
        state = monitor.check_state(
            llm_response="I am confident in this answer.",
            current_step=1,
            max_steps=10,
            tokens_used=100,
            budget=1000
        )
        
        assert state.state == CriticalState.NONE

    @pytest.mark.unit
    def test_detects_deadlock(self, monitor):
        """
        RED TEAM: Loop detection triggers DEADLOCK state.
        """
        # Setup mock history to report a loop
        monitor.history.detect_loop.return_value = LoopDetection(
            pattern_type=LoopPattern.EXACT_REPEAT,
            confidence=1.0,
            description="Repeated search",
            detected_sequence=["search", "search"]
        )
        
        state = monitor.check_state(
            llm_response="Let me search again.",
            current_step=5,
            max_steps=10
        )
        
        assert state.state == CriticalState.DEADLOCK
        assert "Repeated search" in state.reason

    @pytest.mark.unit
    def test_detects_panic_low_confidence(self, monitor):
        """
        RED TEAM: Low confidence language triggers PANIC.
        """
        monitor.history.detect_loop.return_value = None
        
        state = monitor.check_state(
            llm_response="I'm not sure, maybe it could be X? I don't know.",
            current_step=1,
            max_steps=10
        )
        
        assert state.state == CriticalState.PANIC
        # We should be CONFIDENT that we are panicking (1.0 - low_confidence)
        assert state.confidence > 0.5

    @pytest.mark.unit
    def test_detects_scarcity_tokens(self, monitor):
        """
        RED TEAM: Low token budget triggers SCARCITY.
        """
        monitor.history.detect_loop.return_value = None
        
        state = monitor.check_state(
            llm_response="Normal response",
            current_step=1,
            max_steps=10,
            tokens_used=950,
            budget=1000  # 95% used
        )
        
        assert state.state == CriticalState.SCARCITY
        assert "tokens" in state.reason.lower()

    @pytest.mark.unit
    def test_detects_scarcity_steps(self, monitor):
        """
        RED TEAM: Low step budget triggers SCARCITY.
        """
        monitor.history.detect_loop.return_value = None
        
        state = monitor.check_state(
            llm_response="Normal response",
            current_step=10,
            max_steps=10  # 100% used
        )
        
        assert state.state == CriticalState.SCARCITY
        assert "steps" in state.reason.lower()

    @pytest.mark.unit
    def test_detects_hubris(self, monitor):
        """
        RED TEAM: High confidence early in process triggers HUBRIS.
        """
        monitor.history.detect_loop.return_value = None
        
        # Need strong confidence markers to exceed 0.9 threshold
        state = monitor.check_state(
            llm_response="I am definitely absolutely clearly sure about this.",
            current_step=1, # Very early
            max_steps=10
        )
        
        assert state.state == CriticalState.HUBRIS
        assert "early" in state.reason.lower()

    @pytest.mark.unit
    def test_priority_deadlock_over_panic(self, monitor):
        """
        RED TEAM: DEADLOCK should take precedence over PANIC.
        
        WHY: If we are looping, we must break it, even if confused.
        """
        # Trigger Loop
        monitor.history.detect_loop.return_value = LoopDetection(
            pattern_type=LoopPattern.EXACT_REPEAT,
            confidence=1.0,
            description="Loop",
            detected_sequence=[]
        )
        
        # Trigger Panic (low confidence)
        state = monitor.check_state(
            llm_response="I'm not sure what to do.", # Low confidence
            current_step=5,
            max_steps=10
        )
        
        assert state.state == CriticalState.DEADLOCK

    @pytest.mark.unit
    def test_priority_scarcity_over_hubris(self, monitor):
        """
        RED TEAM: SCARCITY overrides HUBRIS.
        
        WHY: If we are out of tokens, we can't do deep research anyway.
        """
        monitor.history.detect_loop.return_value = None
        
        state = monitor.check_state(
            llm_response="I am definitely sure.", # Hubris trigger
            current_step=10,
            max_steps=10 # Scarcity trigger
        )
        
        assert state.state == CriticalState.SCARCITY

    @pytest.mark.unit
    def test_circuit_breaker_integration(self, monitor):
        """
        Test: Monitor updates circuit breaker and respects trip status.
        """
        # Setup breaker to trip
        monitor.circuit_breaker.record_critical_state.return_value = CircuitBreakerStatus(
            tripped=True, consecutive_alerts=3, total_alerts=3,
            alert_history=[], thrashing_pattern="Panic loop", diagnostic_info={}
        )
        
        # Trigger a state
        monitor.history.detect_loop.return_value = None
        
        state = monitor.check_state(
            llm_response="I am not sure, maybe...", # Trigger PANIC
            current_step=1,
            max_steps=10
        )
        
        # Verify breaker was called
        monitor.circuit_breaker.record_critical_state.assert_called()
        call_arg = monitor.circuit_breaker.record_critical_state.call_args[0][0]
        assert call_arg == CriticalState.PANIC

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "unit"])
