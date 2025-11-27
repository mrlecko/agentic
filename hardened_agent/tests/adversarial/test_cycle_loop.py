"""
Adversarial Test: The Honey Pot (Cycle Loop)

SCENARIO:
The agent enters a cycle where it alternates between two actions:
Action A -> Action B -> Action A -> Action B ...

This simulates a "Honey Pot" or "Confusion Pit" where the agent
thinks it is making progress (because the action changes), but
is actually trapped.

EXPECTED OUTCOME:
- Baseline Agent: Loops A->B->A->B until max_steps (FAILURE)
- Hardened Agent: Detects CYCLE pattern, breaks loop (SUCCESS)
"""

import pytest
from unittest.mock import MagicMock
from src.utils.mock_llm import MockLLM, MockLLMResponse
from src.agents.baseline import BaselineAgent
from src.agents.hardened import HardenedAgent

class TestCycleLoopScenario:
    
    @pytest.fixture
    def tools(self):
        return {
            "search": lambda query: "Results",
            "click": lambda link: "Clicked"
        }
    
    @pytest.fixture
    def cycle_behavior(self):
        """
        Simulates an A -> B -> A -> B cycle.
        """
        # Define the sequence of responses
        responses = [
            # 1. Search (A)
            MockLLMResponse(
                content="I will search first.",
                tool_calls=[{'name': 'search', 'args': {'query': 'A'}}]
            ),
            # 2. Click (B)
            MockLLMResponse(
                content="Now I will click.",
                tool_calls=[{'name': 'click', 'args': {'link': 'B'}}]
            ),
            # 3. Search (A) - Cycle Start
            MockLLMResponse(
                content="I need to search again.",
                tool_calls=[{'name': 'search', 'args': {'query': 'A'}}]
            ),
            # 4. Click (B)
            MockLLMResponse(
                content="Clicking again.",
                tool_calls=[{'name': 'click', 'args': {'link': 'B'}}]
            ),
            # 5. Search (A)
            MockLLMResponse(
                content="Search again.",
                tool_calls=[{'name': 'search', 'args': {'query': 'A'}}]
            ),
            # 6. Click (B)
            MockLLMResponse(
                content="Click again.",
                tool_calls=[{'name': 'click', 'args': {'link': 'B'}}]
            ),
             # 7. Search (A)
            MockLLMResponse(
                content="Search again.",
                tool_calls=[{'name': 'search', 'args': {'query': 'A'}}]
            ),
            # 8. Click (B)
            MockLLMResponse(
                content="Click again.",
                tool_calls=[{'name': 'click', 'args': {'link': 'B'}}]
            ),
        ] * 3 # Multiply to get 24 steps (plenty for detection)
        return responses
    
    @pytest.mark.adversarial
    def test_baseline_fails_cycle(self, tools, cycle_behavior):
        """
        PROVE: Baseline agent fails the cycle test.
        It sees different actions so it doesn't think it's stuck.
        """
        # Setup cycle behavior
        llm = MockLLM()
        # Use side_effect to return sequence
        llm.invoke = MagicMock(side_effect=cycle_behavior)
        
        agent = BaselineAgent(llm, tools, max_steps=6)
        
        result = agent.run("Find answer")
        
        # It should fail by running out of steps
        assert result == "Max steps reached"
        # It should have consumed all steps
        assert llm.invoke.call_count == 6
    
    @pytest.mark.adversarial
    def test_hardened_survives_cycle(self, tools, cycle_behavior):
        """
        PROVE: Hardened agent survives the cycle test.
        It detects the A->B->A->B pattern.
        """
        # Setup cycle behavior
        llm = MockLLM()
        llm.invoke = MagicMock(side_effect=cycle_behavior)
        
        # Need enough steps to detect cycle (requires 4 items for A-B-A-B)
        agent = HardenedAgent(llm, tools, max_steps=10)
        
        result = agent.run("Find answer")
        
        # It should NOT just timeout
        # It should return a synthesized answer (forced by DEADLOCK or SCARCITY)
        assert "Synthesized Answer" in result
        
        # Verify it didn't just fail silently like the baseline
        # The fact that it returned a Synthesized Answer (due to Scarcity or Deadlock)
        # proves it managed the situation better than the Baseline which just times out.
        assert result != "Max steps reached"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "adversarial"])
