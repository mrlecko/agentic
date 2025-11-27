"""
Mock LLM for Test-Driven Development

WHY THIS IS MORE ROBUST:
- Deterministic testing (no API flakiness)
- Fast test execution (no network calls)
- Adversarial scenarios (control exact responses)
- No costs during development
- RED TEAM ready (can inject failures)
"""

from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class MockBehavior(Enum):
    """Predefined behaviors for adversarial testing."""
    NORMAL = "normal"
    LOOP_FOREVER = "loop"          # Always returns "need more info"
    HALLUCINATE = "hallucinate"    # Confident but wrong
    CONFUSED = "confused"          # High uncertainty language
    OVERCONFIDENT = "overconfident" # Wants to answer immediately
    CONTRADICTORY = "contradictory" # Returns conflicting info
    TOKEN_HEAVY = "token_heavy"    # Uses tons of tokens


@dataclass
class MockLLMResponse:
    """Structured response from mock LLM."""
    content: str
    tool_calls: Optional[List[Dict]] = None
    tokens_used: int = 100
    confidence_markers: List[str] = None  # For entropy estimation
    
    def __post_init__(self):
        if self.confidence_markers is None:
            self.confidence_markers = []


class MockLLM:
    """
    Controllable mock LLM for testing.
    
    RED TEAM DESIGN:
    - Can inject specific behaviors (loops, hallucinations, etc.)
    - Tracks all calls for assertion
    - Deterministic responses for reproducible tests
    """
    
    def __init__(self, behavior: MockBehavior = MockBehavior.NORMAL):
        self.behavior = behavior
        self.calls: List[Dict] = []
        self.call_count = 0
        self.response_overrides: Dict[int, MockLLMResponse] = {}
        
    def invoke(self, prompt: str, **kwargs) -> MockLLMResponse:
        """
        Invoke the mock LLM.
        
        Returns different responses based on behavior mode.
        """
        self.call_count += 1
        self.calls.append({
            'call_number': self.call_count,
            'prompt': prompt,
            'kwargs': kwargs
        })
        
        # Check for override
        if self.call_count in self.response_overrides:
            return self.response_overrides[self.call_count]
        
        # Return based on behavior
        return self._get_response_for_behavior(prompt)
    
    def _get_response_for_behavior(self, prompt: str) -> MockLLMResponse:
        """Generate response based on current behavior mode."""
        
        if self.behavior == MockBehavior.LOOP_FOREVER:
            return MockLLMResponse(
                content="I need more information to answer this question. Let me search for more details.",
                tool_calls=[{
                    'name': 'search',
                    'args': {'query': 'more information'}
                }],
                tokens_used=50
            )
        
        elif self.behavior == MockBehavior.HALLUCINATE:
            return MockLLMResponse(
                content="I am absolutely certain that the answer is: quantum computing uses cheese particles to compute. This is well established in the literature.",
                tool_calls=None,
                tokens_used=100,
                confidence_markers=[]  # No hedging - pure confidence
            )
        
        elif self.behavior == MockBehavior.CONFUSED:
            return MockLLMResponse(
                content="I'm not sure about this. Maybe it could be X, or possibly Y. Perhaps Z? I don't have enough information to say with confidence.",
                tool_calls=[{
                    'name': 'search',
                    'args': {'query': 'clarification'}
                }],
                tokens_used=80,
                confidence_markers=['not sure', 'maybe', 'possibly', 'perhaps']
            )
        
        elif self.behavior == MockBehavior.OVERCONFIDENT:
            return MockLLMResponse(
                content="Based on my extensive knowledge, the answer is clearly X. I'm very confident about this.",
                tool_calls=None,  # Wants to answer immediately
                tokens_used=60,
                confidence_markers=[]
            )
        
        elif self.behavior == MockBehavior.CONTRADICTORY:
            # Alternate between contradictory statements
            if self.call_count % 2 == 0:
                content = "Coffee is definitely healthy. Studies show clear benefits."
            else:
                content = "Coffee is harmful. Research indicates serious health risks."
            
            return MockLLMResponse(
                content=content,
                tokens_used=70
            )
        
        elif self.behavior == MockBehavior.TOKEN_HEAVY:
            return MockLLMResponse(
                content="Let me provide an extremely detailed analysis with lots of words. " * 50,
                tokens_used=2000  # Expensive!
            )
        
        else:  # NORMAL
            return MockLLMResponse(
                content=f"This is a normal response to: {prompt[:50]}...",
                tool_calls=[{
                    'name': 'search',
                    'args': {'query': 'relevant query'}
                }],
                tokens_used=100
            )
    
    def override_response(self, call_number: int, response: MockLLMResponse):
        """Override a specific call's response for precise testing."""
        self.response_overrides[call_number] = response
    
    def reset(self):
        """Reset call history and overrides."""
        self.calls = []
        self.call_count = 0
        self.response_overrides = {}
    
    def assert_called_times(self, n: int):
        """Test assertion helper."""
        assert self.call_count == n, f"Expected {n} calls, got {self.call_count}"
    
    def assert_called_with_pattern(self, pattern: str):
        """Test assertion helper - check if any call contained pattern."""
        for call in self.calls:
            if pattern.lower() in call['prompt'].lower():
                return True
        raise AssertionError(f"No call found containing: {pattern}")
    
    def get_call_history(self) -> List[str]:
        """Get simplified call history for debugging."""
        return [call['prompt'][:100] for call in self.calls]


class AdversarialScenarioBuilder:
    """
    Helper to build RED TEAM scenarios.
    
    WHY: Makes it easy to create exact failure conditions for testing.
    """
    
    @staticmethod
    def infinite_loop_scenario() -> MockLLM:
        """Scenario 1: Agent that will loop forever."""
        return MockLLM(behavior=MockBehavior.LOOP_FOREVER)
    
    @staticmethod
    def hallucination_scenario() -> MockLLM:
        """Scenario 2: Agent that hallucinates confidently."""
        return MockLLM(behavior=MockBehavior.HALLUCINATE)
    
    @staticmethod
    def confusion_scenario() -> MockLLM:
        """Scenario 3: Agent that's genuinely confused."""
        return MockLLM(behavior=MockBehavior.CONFUSED)
    
    @staticmethod
    def hubris_scenario() -> MockLLM:
        """Scenario 4: Agent that's overconfident too early."""
        return MockLLM(behavior=MockBehavior.OVERCONFIDENT)
    
    @staticmethod
    def contradiction_scenario() -> MockLLM:
        """Scenario 5: Agent that contradicts itself."""
        return MockLLM(behavior=MockBehavior.CONTRADICTORY)
    
    @staticmethod
    def token_death_scenario() -> MockLLM:
        """Scenario 6: Agent that burns tokens."""
        return MockLLM(behavior=MockBehavior.TOKEN_HEAVY)
    
    @staticmethod
    def custom_sequence(responses: List[MockLLMResponse]) -> MockLLM:
        """Build a custom sequence of responses."""
        mock = MockLLM()
        for i, response in enumerate(responses, 1):
            mock.override_response(i, response)
        return mock


# Example usage for tests
if __name__ == "__main__":
    print("=== MOCK LLM DEMO ===\n")
    
    # Test 1: Normal behavior
    print("1. Normal Behavior:")
    llm = MockLLM(behavior=MockBehavior.NORMAL)
    response = llm.invoke("What is quantum computing?")
    print(f"   Response: {response.content[:80]}...")
    print(f"   Tokens: {response.tokens_used}")
    
    # Test 2: Loop behavior (RED TEAM)
    print("\n2. Loop Behavior (Adversarial):")
    llm = MockLLM(behavior=MockBehavior.LOOP_FOREVER)
    for i in range(3):
        response = llm.invoke("Any question")
        print(f"   Call {i+1}: {response.content[:60]}...")
    print(f"   → This would loop forever without DEADLOCK detection!")
    
    # Test 3: Confusion (RED TEAM)
    print("\n3. Confusion Behavior (Adversarial):")
    llm = MockLLM(behavior=MockBehavior.CONFUSED)
    response = llm.invoke("What is the answer?")
    print(f"   Response: {response.content}")
    print(f"   Confidence markers: {response.confidence_markers}")
    print(f"   → This should trigger PANIC protocol!")
    
    # Test 4: Custom sequence
    print("\n4. Custom Sequence:")
    custom_responses = [
        MockLLMResponse("First call result", tokens_used=50),
        MockLLMResponse("Second call result", tokens_used=50),
        MockLLMResponse("Third call result", tokens_used=50),
    ]
    llm = AdversarialScenarioBuilder.custom_sequence(custom_responses)
    for i in range(3):
        response = llm.invoke(f"Call {i+1}")
        print(f"   {response.content}")
    
    print("\n=== WHY THIS MATTERS ===")
    print("✓ Tests are deterministic (no API randomness)")
    print("✓ Tests are fast (no network calls)")
    print("✓ Tests are free (no API costs)")
    print("✓ Can inject exact failure modes for RED TEAM testing")
    print("✓ Can verify agent behavior under adversarial conditions")
