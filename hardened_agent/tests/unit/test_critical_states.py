"""
Test Critical States and Protocols

RED TEAM THINKING:
- Does confidence estimation catch hedging language?
- Do protocols return deterministic responses?
- Are overrides actually safer than optimization?
- Can we inject adversarial scenarios?

WHY THIS IS MORE ROBUST:
- Baseline: No tests for failure modes
- Hardened: Every protocol tested against adversarial inputs
"""

import pytest
from src.monitoring.critical_states import (
    CriticalState,
    StateDetection,
    ProtocolResponse,
    ConfidenceEstimator,
    DEADLOCKProtocol,
    PANICProtocol,
    HUBRISProtocol,
    SCARCITYProtocol,
    NOVELTYProtocol
)


class TestConfidenceEstimator:
    """Test confidence estimation from text."""
    
    @pytest.mark.unit
    def test_high_confidence_text(self):
        """Test: High confidence phrases increase score."""
        text = "I am absolutely certain that this is correct. Definitely the right answer."
        confidence = ConfidenceEstimator.estimate_from_text(text)
        
        assert confidence > 0.7, "Should detect high confidence"
    
    @pytest.mark.unit
    def test_low_confidence_text(self):
        """
        RED TEAM: Hedging language should trigger PANIC.
        
        WHY: Baseline agents ignore this and optimize anyway.
        """
        text = "I'm not sure, maybe possibly it could be this? Perhaps that?"
        confidence = ConfidenceEstimator.estimate_from_text(text)
        
        assert confidence < 0.4, "Should detect low confidence from hedging"
    
    @pytest.mark.unit
    def test_neutral_text(self):
        """Test: Neutral text without hedging or confidence markers."""
        text = "Quantum computing uses superposition and entanglement."
        confidence = ConfidenceEstimator.estimate_from_text(text)
        
        assert 0.5 < confidence < 0.9, "Should be neutral confidence"
    
    @pytest.mark.unit
    @pytest.mark.parametrize("hedging_word,expected_low", [
        ("maybe", True),
        ("possibly", True),
        ("perhaps", True),
        ("might", True),
        ("I think", True),
        ("seems like", True),
    ])
    def test_individual_hedging_words(self, hedging_word, expected_low):
        """Test: Each hedging word reduces confidence."""
        text = f"The answer {hedging_word} involves quantum mechanics."
        confidence = ConfidenceEstimator.estimate_from_text(text)
        
        if expected_low:
            assert confidence < 0.7
    
    @pytest.mark.unit
    def test_multiple_hedging_compounds(self):
        """
        RED TEAM: Multiple hedging words should drastically reduce confidence.
        
        WHY: Indicates severe confusion.
        """
        text = "Maybe possibly perhaps it might be this, I think, probably."
        confidence = ConfidenceEstimator.estimate_from_text(text)
        
        assert confidence < 0.3, "Multiple hedging should indicate high confusion"
    
    @pytest.mark.unit
    def test_case_insensitive(self):
        """Test: Hedging detection is case-insensitive."""
        text1 = "maybe this is correct"
        text2 = "MAYBE this is correct"
        
        conf1 = ConfidenceEstimator.estimate_from_text(text1)
        conf2 = ConfidenceEstimator.estimate_from_text(text2)
        
        assert conf1 == conf2


class TestStateDetection:
    """Test StateDetection dataclass."""
    
    @pytest.mark.unit
    def test_bool_conversion(self):
        """Test: StateDetection is truthy when not NONE."""
        detection_active = StateDetection(
            state=CriticalState.PANIC,
            confidence=0.9,
            reason="Test",
            metadata={}
        )
        
        detection_none = StateDetection(
            state=CriticalState.NONE,
            confidence=0.0,
            reason="Normal",
            metadata={}
        )
        
        assert bool(detection_active) is True
        assert bool(detection_none) is False
    
    @pytest.mark.unit
    def test_string_representation(self):
        """Test: StateDetection has readable string format."""
        detection = StateDetection(
            state=CriticalState.DEADLOCK,
            confidence=1.0,
            reason="Loop detected",
            metadata={}
        )
        
        result = str(detection)
        assert "DEADLOCK" in result
        assert "Loop detected" in result
        assert "100" in result and "%" in result  # Format may vary (100% or 100.00%)


class TestDEADLOCKProtocol:
    """
    Test DEADLOCK protocol - the most critical one.
    
    RED TEAM: This prevents infinite loops.
    """
    
    @pytest.fixture
    def protocol(self):
        return DEADLOCKProtocol()
    
    @pytest.mark.unit
    def test_first_loop_tries_different_action(self, protocol):
        """
        Test: First loop should try different action.
        
        WHY: Maybe the agent just needs a nudge.
        """
        detection = StateDetection(
            state=CriticalState.DEADLOCK,
            confidence=1.0,
            reason="Loop detected",
            metadata={'pattern': 'search → search'}
        )
        
        response = protocol.handle(detection)
        
        assert response.override_action == "force_different_tool"
        assert "Breaking loop" in response.reasoning
        assert response.metadata['loop_count'] == 1
    
    @pytest.mark.unit
    def test_third_loop_forces_synthesis(self, protocol):
        """
        RED TEAM: After 3 loops, stop trying and synthesize.
        
        WHY: Baseline agents loop forever. We force synthesis.
        """
        detection = StateDetection(
            state=CriticalState.DEADLOCK,
            confidence=1.0,
            reason="Loop detected",
            metadata={'pattern': 'search → search'}
        )
        
        # Trigger 3 times
        protocol.handle(detection)
        protocol.handle(detection)
        response = protocol.handle(detection)
        
        assert response.override_action == "force_synthesis"
        assert "Synthesizing with current knowledge" in response.reasoning
        assert response.metadata['loop_count'] == 3
    
    @pytest.mark.unit
    def test_reset_clears_count(self, protocol):
        """Test: Reset clears loop counter."""
        detection = StateDetection(
            state=CriticalState.DEADLOCK,
            confidence=1.0,
            reason="Loop",
            metadata={}
        )
        
        protocol.handle(detection)
        protocol.handle(detection)
        assert protocol.loop_count == 2
        
        protocol.reset()
        assert protocol.loop_count == 0


class TestPANICProtocol:
    """
    Test PANIC protocol.
    
    RED TEAM: Handles confusion when baseline would optimize blindly.
    """
    
    @pytest.fixture
    def protocol(self):
        return PANICProtocol()
    
    @pytest.mark.unit
    def test_switches_to_tank_mode(self, protocol):
        """
        Test: PANIC switches to conservative tank mode.
        
        WHY: When confused, be safe not clever.
        """
        detection = StateDetection(
            state=CriticalState.PANIC,
            confidence=0.9,  # 90% sure we're confused
            reason="High hedging detected",
            metadata={}
        )
        
        response = protocol.handle(detection)
        
        assert response.override_action == "tank_mode"
        assert "conservative" in response.reasoning.lower()
        assert response.metadata['require_consensus'] is True
    
    @pytest.mark.unit
    def test_uses_whitelisted_sources(self, protocol):
        """Test: Tank mode restricts to safe sources."""
        detection = StateDetection(
            state=CriticalState.PANIC,
            confidence=0.85,
            reason="Confusion",
            metadata={}
        )
        
        response = protocol.handle(detection)
        
        assert 'allowed_sources' in response.metadata
        assert 'wikipedia' in response.metadata['allowed_sources']


class TestHUBRISProtocol:
    """
    Test HUBRIS protocol.
    
    RED TEAM: Prevents accepting first answer (could be misinformation).
    """
    
    @pytest.fixture
    def protocol(self):
        return HUBRISProtocol(min_sources=3)
    
    @pytest.mark.unit
    def test_forces_deeper_research(self, protocol):
        """
        RED TEAM: Early confidence triggers deeper research.
        
        WHY: Baseline accepts first answer, could be wrong.
        """
        detection = StateDetection(
            state=CriticalState.HUBRIS,
            confidence=0.95,
            reason="Too confident too early",
            metadata={'steps_taken': 1}
        )
        
        response = protocol.handle(detection)
        
        assert response.override_action == "force_deeper_research"
        assert response.metadata['require_additional_sources'] == 3
        assert response.metadata['seek_contrary_opinions'] is True
    
    @pytest.mark.unit
    def test_includes_step_count_in_reasoning(self, protocol):
        """Test: Explains how few steps were taken."""
        detection = StateDetection(
            state=CriticalState.HUBRIS,
            confidence=0.9,
            reason="Hubris",
            metadata={'steps_taken': 2}
        )
        
        response = protocol.handle(detection)
        
        assert "2 steps" in response.reasoning


class TestSCARCITYProtocol:
    """
    Test SCARCITY protocol.
    
    RED TEAM: Graceful degradation vs. crashing.
    """
    
    @pytest.fixture
    def protocol(self):
        return SCARCITYProtocol()
    
    @pytest.mark.unit
    def test_immediate_synthesis(self, protocol):
        """
        RED TEAM: Low resources triggers immediate synthesis.
        
        WHY: Baseline crashes or times out. We degrade gracefully.
        """
        detection = StateDetection(
            state=CriticalState.SCARCITY,
            confidence=0.95,
            reason="Low resources",
            metadata={'token_budget': 0.1, 'step_budget': 0.15}
        )
        
        response = protocol.handle(detection)
        
        assert response.override_action == "immediate_synthesis"
        assert "Synthesizing now" in response.reasoning
        assert response.metadata['add_caveat'] is True
    
    @pytest.mark.unit
    def test_includes_caveat_text(self, protocol):
        """Test: Adds caveat about limited resources."""
        detection = StateDetection(
            state=CriticalState.SCARCITY,
            confidence=1.0,
            reason="Scarcity",
            metadata={'token_budget': 0.05, 'step_budget': 0.1}
        )
        
        response = protocol.handle(detection)
        
        assert 'caveat_text' in response.metadata
        assert "Limited resources" in response.metadata['caveat_text']


class TestNOVELTYProtocol:
    """
    Test NOVELTY protocol.
    
    RED TEAM: Handles contradictions vs. ignoring them.
    """
    
    @pytest.fixture
    def protocol(self):
        return NOVELTYProtocol()
    
    @pytest.mark.unit
    def test_integrates_contradiction(self, protocol):
        """
        RED TEAM: Contradiction triggers re-evaluation.
        
        WHY: Baseline ignores or picks randomly. We acknowledge both.
        """
        detection = StateDetection(
            state=CriticalState.NOVELTY,
            confidence=0.8,
            reason="Contradictory info",
            metadata={}
        )
        
        response = protocol.handle(detection)
        
        assert response.override_action == "integrate_contradiction"
        assert response.metadata['rerank_sources'] is True
        assert response.metadata['flag_contradiction'] is True
        assert response.metadata['update_confidence'] is True


class TestProtocolResponse:
    """Test ProtocolResponse dataclass."""
    
    @pytest.mark.unit
    def test_protocol_response_structure(self):
        """Test: ProtocolResponse has required fields."""
        response = ProtocolResponse(
            override_action="test_action",
            reasoning="test reasoning",
            metadata={'key': 'value'}
        )
        
        assert response.override_action == "test_action"
        assert response.reasoning == "test reasoning"
        assert response.metadata['key'] == 'value'


class TestIntegration:
    """
    Integration tests for protocol interactions.
    
    RED TEAM: What if multiple protocols fire at once?
    """
    
    @pytest.mark.unit
    def test_deadlock_protocol_is_stateful(self):
        """
        Test: DEADLOCK protocol maintains state across calls.
        
        WHY: Needs to count loops to escalate response.
        """
        protocol = DEADLOCKProtocol()
        detection = StateDetection(
            state=CriticalState.DEADLOCK,
            confidence=1.0,
            reason="Loop",
            metadata={}
        )
        
        # First call
        response1 = protocol.handle(detection)
        assert "attempt 1" in response1.reasoning
        
        # Second call - state persists
        response2 = protocol.handle(detection)
        assert "attempt 2" in response2.reasoning
    
    @pytest.mark.unit
    def test_other_protocols_are_stateless(self):
        """
        Test: Other protocols don't maintain state.
        
        WHY: They should respond the same way each time.
        """
        panic = PANICProtocol()
        detection = StateDetection(
            state=CriticalState.PANIC,
            confidence=0.9,
            reason="Confusion",
            metadata={}
        )
        
        response1 = panic.handle(detection)
        response2 = panic.handle(detection)
        
        # Should be identical
        assert response1.override_action == response2.override_action
        assert response1.reasoning == response2.reasoning


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "unit"])
