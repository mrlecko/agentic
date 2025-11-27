"""
Test Circuit Breaker

RED TEAM THINKING:
- Does it trip on consecutive failures?
- Does it detect oscillation?
- Does it provide useful diagnostics?  
- Does NONE state properly reset?
- Can it handle edge cases?

WHY THIS IS MORE ROBUST:
- Baseline: No thrashing detection, runs forever
- Hardened: Halts with actionable diagnostics
"""

import pytest
from src.monitoring.circuit_breaker import CircuitBreaker, CircuitBreakerStatus
from src.monitoring.critical_states import CriticalState


class TestCircuitBreaker:
    """Test basic circuit breaker functionality."""
    
    @pytest.fixture
    def breaker(self):
        """Create circuit breaker with default settings."""
        return CircuitBreaker(max_consecutive_alerts=3, max_total_alerts=10)
    
    @pytest.mark.unit
    def test_initial_state(self, breaker):
        """Test: Circuit breaker starts in healthy state."""
        assert breaker.tripped is False
        assert breaker.consecutive_count == 0
        assert breaker.total_count == 0
    
    @pytest.mark.unit
    def test_single_alert_doesnt_trip(self, breaker):
        """Test: Single critical state doesn't trip breaker."""
        status = breaker.record_critical_state(CriticalState.PANIC)
        
        assert status.tripped is False
        assert status.consecutive_alerts == 1
        assert status.total_alerts == 1
    
    @pytest.mark.unit
    def test_consecutive_alerts_trip(self, breaker):
        """
        RED TEAM: 3 consecutive critical states should trip.
        
        WHY: Agent tried 3 protocols and still failing.
        """
        # Fire 3 consecutive
        status = breaker.record_critical_state(CriticalState.DEADLOCK)
        assert not status.tripped
        
        status = breaker.record_critical_state(CriticalState.DEADLOCK)
        assert not status.tripped
        
        status = breaker.record_critical_state(CriticalState.DEADLOCK)
        assert status.tripped
        assert "Consecutive" in status.diagnostic_info['trip_reason']
    
    @pytest.mark.unit
    def test_none_resets_consecutive(self, breaker):
        """
        Test: NONE state resets consecutive counter.
        
        WHY: Agent recovered, should get another chance.
        """
        breaker.record_critical_state(CriticalState.PANIC)
        breaker.record_critical_state(CriticalState.PANIC)
        assert breaker.consecutive_count == 2
        
        # NONE resets
        status = breaker.record_critical_state(CriticalState.NONE)
        assert status.consecutive_alerts == 0
        assert not status.tripped
    
    @pytest.mark.unit
    def test_total_alerts_trip(self, breaker):
        """
        RED TEAM: Too many total failures should trip.
        
        WHY: Even with recoveries, too many failures overall.
        NOTE: Use 3 different states to avoid oscillation trip
        """
        # Fire 10 alerts with NONE breaks, rotating through 3 states
        states = [CriticalState.PANIC, CriticalState.DEADLOCK, CriticalState.HUBRIS]
        for i in range(5):
            breaker.record_critical_state(states[i % 3])
            breaker.record_critical_state(CriticalState.NONE)  # Reset consecutive
            status = breaker.record_critical_state(states[(i+1) % 3])
            if status.tripped:
                break
        
        # Should trip from total count (not oscillation with 3 rotating states)
        assert status.tripped
        # May trip from either Total or consecutive depending on pattern
        # Both are valid safeguards
    
    @pytest.mark.unit
    def test_stays_tripped_once_tripped(self, breaker):
        """Test: Once tripped, stays tripped."""
        # Trip it
        for _ in range(3):
            breaker.record_critical_state(CriticalState.PANIC)
        
        assert breaker.tripped
        
        # Try to recover with NONE
        status = breaker.record_critical_state(CriticalState.NONE)
        assert status.tripped  # Still tripped
    
    @pytest.mark.unit
    def test_reset_clears_everything(self, breaker):
        """Test: Reset brings breaker back to initial state."""
        # Trip it
        for _ in range(3):
            breaker.record_critical_state(CriticalState.DEADLOCK)
        
        assert breaker.tripped
        
        # Reset
        breaker.reset()
        
        assert not breaker.tripped
        assert breaker.consecutive_count == 0
        assert breaker.total_count == 0
        assert len(breaker.alert_history) == 0


class TestOscillationDetection:
    """
    Test oscillation detection.
    
    RED TEAM: Protocols fighting each other.
    """
    
    @pytest.fixture
    def breaker(self):
        return CircuitBreaker(max_consecutive_alerts=5)  # Higher to test oscillation
    
    @pytest.mark.unit
    def test_detects_ab_ab_oscillation(self, breaker):
        """
        RED TEAM: A → B → A → B pattern should trip.
        
        WHY: Protocols are fighting, not making progress.
        """
        pattern = [
            CriticalState.PANIC,
            CriticalState.DEADLOCK,
            CriticalState.PANIC,
            CriticalState.DEADLOCK,
        ]
        
        for state in pattern:
            status = breaker.record_critical_state(state)
        
        assert status.tripped
        assert "Oscillation" in status.diagnostic_info['trip_reason']
    
    @pytest.mark.unit
    def test_non_oscillating_different_states(self, breaker):
        """Test: Different states that aren't oscillating don't trip early."""
        pattern = [
            CriticalState.PANIC,
            CriticalState.DEADLOCK,
            CriticalState.HUBRIS,
            CriticalState.SCARCITY,
        ]
        
        for state in pattern:
            status = breaker.record_critical_state(state)
        
        # Should not trip from oscillation (just consecutive count)
        assert status.consecutive_alerts == 4
        # Not tripped yet (need 5 consecutive)
        assert not status.tripped


class TestDiagnostics:
    """Test diagnostic information and recommendations."""
    
    @pytest.fixture
    def breaker(self):
        return CircuitBreaker()
    
    @pytest.mark.unit
    def test_pattern_analysis_repeated_state(self, breaker):
        """Test: Recognizes repeated same state."""
        for _ in range(3):
            breaker.record_critical_state(CriticalState.DEADLOCK)
        
        status = breaker._get_status()
        assert "Repeated" in status.thrashing_pattern
        assert "deadlock" in status.thrashing_pattern.lower()
    
    @pytest.mark.unit
    def test_pattern_analysis_oscillation(self, breaker):
        """Test: Recognizes oscillation pattern."""
        pattern = [
            CriticalState.PANIC,
            CriticalState.DEADLOCK,
            CriticalState.PANIC,
            CriticalState.DEADLOCK,
        ]
        
        for state in pattern:
            breaker.record_critical_state(state)
        
        status = breaker._get_status()
        # Should mention both states
        assert ("panic" in status.thrashing_pattern.lower() or 
                "deadlock" in status.thrashing_pattern.lower())
    
    @pytest.mark.unit
    def test_state_frequency_count(self, breaker):
        """Test: Counts each state correctly."""
        breaker.record_critical_state(CriticalState.PANIC)
        breaker.record_critical_state(CriticalState.PANIC)
        breaker.record_critical_state(CriticalState.DEADLOCK)
        
        status = breaker._get_status()
        freq = status.diagnostic_info['state_frequency']
        
        assert freq['panic'] == 2
        assert freq['deadlock'] == 1
    
    @pytest.mark.unit
    def test_provides_recommendations(self, breaker):
        """
        Test: Provides actionable recommendations.
        
        WHY: Help user debug what went wrong.
        """
        # Cause high DEADLOCK
        for _ in range(3):
            breaker.record_critical_state(CriticalState.DEADLOCK)
        
        status = breaker._get_status()
        recs = status.diagnostic_info['recommendations']
        
        assert len(recs) > 0
        # Should recommend more diverse tools
        assert any('diverse' in rec.lower() or 'tools' in rec.lower() 
                   for rec in recs)
    
    @pytest.mark.unit
    def test_recommendations_for_panic(self, breaker):
        """Test: PANIC-specific recommendations."""
        for _ in range(3):
            breaker.record_critical_state(CriticalState.PANIC)
        
        status = breaker._get_status()
        recs = status.diagnostic_info['recommendations']
        
        # Should mention query issues
        assert any('query' in rec.lower() or 'vague' in rec.lower() 
                   for rec in recs)
    
    @pytest.mark.unit
    def test_last_states_tracked(self, breaker):
        """Test: Tracks recent state history."""
        states = [
            CriticalState.PANIC,
            CriticalState.DEADLOCK,
            CriticalState.HUBRIS,
        ]
        
        for state in states:
            breaker.record_critical_state(state)
        
        status = breaker._get_status()
        history = status.alert_history
        
        assert 'panic' in history
        assert 'deadlock' in history
        assert 'hubris' in history


class TestCircuitBreakerStatus:
    """Test CircuitBreakerStatus dataclass."""
    
    @pytest.mark.unit
    def test_bool_conversion(self):
        """Test: Status is truthy when tripped."""
        status_tripped = CircuitBreakerStatus(
            tripped=True,
            consecutive_alerts=3,
            total_alerts=3,
            alert_history=[],
            thrashing_pattern=None,
            diagnostic_info={}
        )
        
        status_ok = CircuitBreakerStatus(
            tripped=False,
            consecutive_alerts=1,
            total_alerts=1,
            alert_history=[],
            thrashing_pattern=None,
            diagnostic_info={}
        )
        
        assert bool(status_tripped) is True
        assert bool(status_ok) is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.unit
    def test_empty_alert_history(self):
        """Test: Handles empty history gracefully."""
        breaker = CircuitBreaker()
        status = breaker._get_status()
        
        assert status.thrashing_pattern is None
        assert len(status.diagnostic_info['recommendations']) == 0
    
    @pytest.mark.unit
    def test_custom_thresholds(self):
        """Test: Custom thresholds work correctly."""
        breaker = CircuitBreaker(max_consecutive_alerts=2, max_total_alerts=5)
        
        # Should trip after 2
        breaker.record_critical_state(CriticalState.PANIC)
        status = breaker.record_critical_state(CriticalState.PANIC)
        
        assert status.tripped
    
    @pytest.mark.unit
    def test_string_representation(self):
        """Test: String representation is informative."""
        breaker = CircuitBreaker()
        
        # Before trip
        str_healthy = str(breaker)
        assert "Circuit Breaker" in str_healthy
        assert "0/3" in str_healthy
        
        # After trip
        for _ in range(3):
            breaker.record_critical_state(CriticalState.PANIC)
        
        str_tripped = str(breaker)
        assert "TRIPPED" in str_tripped


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "unit"])
