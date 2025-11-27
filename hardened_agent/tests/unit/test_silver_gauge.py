"""
Test Silver Gauge

RED TEAM THINKING:
- Does it handle edge cases (0.0, 1.0)?
- Does it correctly classify balanced vs imbalanced?
- Is the math correct?

WHY THIS IS MORE ROBUST:
- Provides mathematical transparency into "black box" decisions.
"""

import pytest
from src.monitoring.silver_gauge import SilverGauge, ActionType

class TestSilverGauge:
    
    @pytest.mark.unit
    def test_perfect_balance(self):
        """Test: G=I should yield k=1.0 (Generalist)."""
        reading = SilverGauge.calculate(0.8, 0.8)
        assert reading.k_explore == pytest.approx(1.0)
        assert reading.action_type == ActionType.GENERALIST
        
    @pytest.mark.unit
    def test_extreme_imbalance(self):
        """Test: High G, Low I should yield low k (Specialist)."""
        reading = SilverGauge.calculate(0.9, 0.1)
        # AM = 0.5, HM = 0.18. k = 0.36
        assert reading.k_explore < 0.5
        assert reading.action_type == ActionType.SPECIALIST
        assert "Goal-focused" in reading.description
        
    @pytest.mark.unit
    def test_exploration_specialist(self):
        """Test: Low G, High I should yield low k (Specialist)."""
        reading = SilverGauge.calculate(0.1, 0.9)
        assert reading.k_explore < 0.5
        assert reading.action_type == ActionType.SPECIALIST
        assert "Exploration-focused" in reading.description

    @pytest.mark.unit
    def test_near_balance(self):
        """Test: G and I close to each other should be Generalist."""
        reading = SilverGauge.calculate(0.7, 0.6)
        # AM = 0.65, HM = 0.84/1.3 = 0.646. k = 0.99
        assert reading.k_explore > 0.8
        assert reading.action_type == ActionType.GENERALIST
        
    @pytest.mark.unit
    def test_zero_handling(self):
        """Test: Handles 0.0 input by clamping."""
        reading = SilverGauge.calculate(0.0, 0.5)
        assert reading.g_val == 0.001 # Clamped
        assert reading.k_explore > 0.0

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "unit"])
