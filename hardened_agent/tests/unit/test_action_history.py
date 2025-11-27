"""
Test Action History and Loop Detection

RED TEAM THINKING:
- Can the agent detect exact loops? (A → A → A)
- Can it detect cycle loops? (A → B → A → B)
- Does it handle edge cases? (empty history, single action)
- Is it fast enough for real-time monitoring?

WHY THIS IS MORE ROBUST:
- Baseline agents have no loop detection at all
- They repeat failing actions forever
- We detect and break loops deterministically
"""

import pytest
import os
import tempfile
from src.memory.action_history import ActionHistory, LoopPattern


class TestActionHistory:
    """Unit tests for action history tracking."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for each test."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)
    
    @pytest.fixture
    def history(self, temp_db):
        """Create action history instance."""
        return ActionHistory(temp_db)
    
    @pytest.mark.unit
    def test_create_table(self, history):
        """Test: Database table is created successfully."""
        # Should not raise
        assert history.conn is not None
    
    @pytest.mark.unit
    def test_record_action(self, history):
        """Test: Can record an action."""
        history.record_action(
            tool="search",
            args="quantum computing",
            result="Found 10 results",
            tokens=100,
            session_id="test-session"
        )
        
        actions = history.get_recent_actions("test-session", n=10)
        assert len(actions) == 1
        assert actions[0]['tool'] == 'search'
        assert actions[0]['args'] == 'quantum computing'
    
    @pytest.mark.unit
    def test_get_recent_actions(self, history):
        """Test: Can retrieve recent actions in reverse order."""
        session = "test-session"
        
        # Record 5 actions
        for i in range(5):
            history.record_action(
                tool=f"tool_{i}",
                args=f"args_{i}",
                result=f"result_{i}",
                tokens=100,
                session_id=session
            )
        
        # Get last 3
        recent = history.get_recent_actions(session, n=3)
        assert len(recent) == 3
        
        # Should be in reverse order (most recent first)
        assert recent[0]['tool'] == 'tool_4'
        assert recent[1]['tool'] == 'tool_3'
        assert recent[2]['tool'] == 'tool_2'
    
    @pytest.mark.unit
    def test_detect_exact_loop(self, history):
        """
        RED TEAM: Exact repetition loop (A → A → A)
        
        WHY: Baseline agents do this constantly when stuck.
        """
        session = "loop-test"
        
        # Record same action 3 times
        for _ in range(3):
            history.record_action(
                tool="search",
                args="same query",
                result="same result",
                tokens=100,
                session_id=session
            )
        
        loop = history.detect_loop(session, window=5)
        
        assert loop is not None
        assert loop.pattern_type == LoopPattern.EXACT_REPEAT
        assert loop.confidence == 1.0
        assert "search" in loop.description
    
    @pytest.mark.unit
    def test_detect_cycle_loop(self, history):
        """
        RED TEAM: Cycle loop (A → B → A → B → A)
        
        WHY: Slightly smarter agents oscillate between two actions.
        """
        session = "cycle-test"
        
        # Record A → B → A → B → A
        actions = ["search", "synthesize", "search", "synthesize", "search"]
        for action in actions:
            history.record_action(
                tool=action,
                args="args",
                result="result",
                tokens=100,
                session_id=session
            )
        
        loop = history.detect_loop(session, window=5)
        
        assert loop is not None
        assert loop.pattern_type == LoopPattern.CYCLE
        assert "search" in loop.description or "cycle" in loop.description.lower()
    
    @pytest.mark.unit
    def test_no_loop_on_varied_actions(self, history):
        """Test: Different actions should NOT trigger loop detection."""
        session = "varied-test"
        
        # Record different actions
        actions = ["search", "synthesize", "calculate", "verify"]
        for action in actions:
            history.record_action(
                tool=action,
                args=f"{action}_args",
                result="result",
                tokens=100,
                session_id=session
            )
        
        loop = history.detect_loop(session, window=5)
        
        assert loop is None, "Should NOT detect loop with varied actions"
    
    @pytest.mark.unit
    def test_loop_detection_edge_case_empty(self, history):
        """Test: Empty history should not crash."""
        loop = history.detect_loop("empty-session", window=5)
        assert loop is None
    
    @pytest.mark.unit
    def test_loop_detection_edge_case_single_action(self, history):
        """Test: Single action should not trigger loop."""
        session = "single-test"
        history.record_action(
            tool="search",
            args="query",
            result="result",
            tokens=100,
            session_id=session
        )
        
        loop = history.detect_loop(session, window=5)
        assert loop is None
    
    @pytest.mark.unit
    def test_session_isolation(self, history):
        """Test: Different sessions don't interfere."""
        # Record in session 1
        history.record_action("search", "q1", "r1", 100, "session-1")
        history.record_action("search", "q1", "r1", 100, "session-1")
        history.record_action("search", "q1", "r1", 100, "session-1")
        
        # Record different action in session 2
        history.record_action("synthesize", "q2", "r2", 100, "session-2")
        
        # Session 1 should have loop
        loop1 = history.detect_loop("session-1")
        assert loop1 is not None
        
        # Session 2 should NOT have loop
        loop2 = history.detect_loop("session-2")
        assert loop2 is None
    
    @pytest.mark.unit
    @pytest.mark.parametrize("repeat_count,should_detect", [
        (2, False),  # 2 repeats: Not enough
        (3, True),   # 3 repeats: Should detect
        (5, True),   # 5 repeats: Definitely detect
    ])
    def test_loop_threshold(self, history, repeat_count, should_detect):
        """
        Test: Loop detection threshold (need 3+ repeats).
        
        WHY: Prevents false positives from occasional repeated actions.
        """
        session = f"threshold-test-{repeat_count}"
        
        for _ in range(repeat_count):
            history.record_action("search", "same", "same", 100, session)
        
        loop = history.detect_loop(session)
        
        if should_detect:
            assert loop is not None, f"Should detect loop with {repeat_count} repeats"
        else:
            assert loop is None, f"Should NOT detect loop with {repeat_count} repeats"


class TestLoopPatternDetection:
    """Test different types of loop patterns."""
    
    @pytest.fixture
    def history(self):
        """In-memory database for tests."""
        return ActionHistory(":memory:")
    
    @pytest.mark.unit
    def test_alternating_loop_ab_ab(self, history):
        """RED TEAM: A → B → A → B pattern."""
        session = "ab-test"
        pattern = ["search", "synthesize"] * 3  # A, B, A, B, A, B
        
        for action in pattern:
            history.record_action(action, "args", "result", 100, session)
        
        loop = history.detect_loop(session)
        assert loop is not None
        assert loop.pattern_type == LoopPattern.CYCLE
    
    @pytest.mark.unit
    def test_triple_loop_abc_abc(self, history):
        """
        RED TEAM: A → B → C → A → B → C pattern.
        
        WHY: Need at least 3 cycles for high-confidence 3-cycle detection.
        """
        session = "abc-test"
        pattern = ["search", "synthesize", "verify"] * 3  # 3 full cycles for confidence
        
        for action in pattern:
            history.record_action(action, "args", "result", 100, session)
        
        loop = history.detect_loop(session, window=10)  # Need larger window for 9 actions
        assert loop is not None
        assert loop.pattern_type == LoopPattern.CYCLE
    
    @pytest.mark.unit
    def test_similar_but_not_identical_args(self, history):
        """
        Test: Same tool with different args should NOT always be a loop.
        
        WHY: "search(query1), search(query2), search(query3)" might be valid exploration.
        """
        session = "similar-test"
        
        for i in range(5):
            history.record_action(
                tool="search",
                args=f"different_query_{i}",  # Different args
                result="result",
                tokens=100,
                session_id=session
            )
        
        loop = history.detect_loop(session)
        
        # Current implementation might detect this as a loop
        # This is a design decision: Should "search, search, search" with different
        # args be considered a loop?
        # 
        # OPTION A: Yes, same tool = potential loop (more conservative)
        # OPTION B: No, different args = different actions (more permissive)
        #
        # For now, we'll document this behavior and can refine later
        # based on real-world testing
        pass  # TODO: Decide on policy


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "unit"])
