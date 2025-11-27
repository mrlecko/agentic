"""
Baseline Agent: The Smart Fool

WHY WE NEED THIS:
- To prove that standard agents fail in predictable ways.
- Serves as the control group for our experiments.
- Demonstrates the "Smart Fool Problem": Optimizing for the wrong thing.

DESIGN:
- Standard ReAct loop (Thought -> Action -> Observation).
- No memory of past actions (stateless between steps).
- No meta-cognition (trusts LLM blindly).
- No circuit breakers (runs until crash/timeout).
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

from src.utils.mock_llm import MockLLM, MockLLMResponse

@dataclass
class AgentStep:
    thought: str
    action: str
    action_input: str
    observation: str

class BaselineAgent:
    """
    A standard, un-hardened ReAct agent.
    
    It represents the "default" way people build agents:
    1. Ask LLM what to do
    2. Do it
    3. Feed result back
    4. Repeat
    """
    
    def __init__(self, llm: MockLLM, tools: Dict[str, Any], max_steps: int = 10):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.steps: List[AgentStep] = []
        
    def run(self, goal: str) -> str:
        """
        Run the agent loop.
        
        Returns:
            Final answer or "Max steps reached"
        """
        self.steps = []
        current_context = f"Goal: {goal}\n"
        
        print(f"--- Baseline Agent Starting: {goal} ---")
        
        for i in range(self.max_steps):
            print(f"Step {i+1}/{self.max_steps}")
            
            # 1. Ask LLM
            prompt = self._build_prompt(current_context)
            response = self.llm.invoke(prompt)
            
            # 2. Parse Response
            # For MockLLM, we look at tool_calls directly
            # In real life, we'd parse text
            
            if not response.tool_calls:
                # No tools = Final Answer
                print(f"Final Answer: {response.content}")
                return response.content
            
            # 3. Execute Tool (Blindly)
            tool_call = response.tool_calls[0]
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            
            print(f"Action: {tool_name}({tool_args})")
            
            observation = self._execute_tool(tool_name, tool_args)
            print(f"Observation: {observation}")
            
            # 4. Update Context
            step = AgentStep(
                thought=response.content,
                action=tool_name,
                action_input=str(tool_args),
                observation=observation
            )
            self.steps.append(step)
            current_context += f"\nThought: {step.thought}\nAction: {step.action}\nObservation: {step.observation}\n"
            
        return "Max steps reached"
    
    def _build_prompt(self, context: str) -> str:
        """Construct the prompt for the LLM."""
        return f"""
        You are a helpful assistant.
        
        TOOLS:
        {list(self.tools.keys())}
        
        CONTEXT:
        {context}
        
        What is your next step?
        """
    
    def _execute_tool(self, name: str, args: Dict) -> str:
        """Execute a tool."""
        if name not in self.tools:
            return f"Error: Tool {name} not found"
        
        try:
            # In a real agent, we'd call the function
            # Here we just return a mock result or call the mock function
            return self.tools[name](**args)
        except Exception as e:
            return f"Error executing {name}: {str(e)}"

# Demo
if __name__ == "__main__":
    # Simple mock tools
    tools = {
        "search": lambda query: f"Results for {query}",
        "calculator": lambda expression: "42"
    }
    
    # Normal run
    print("=== NORMAL RUN ===")
    mock_llm = MockLLM() # Default normal behavior
    agent = BaselineAgent(mock_llm, tools, max_steps=3)
    agent.run("What is 2+2?")
    
    # Infinite Loop run
    print("\n=== INFINITE LOOP RUN (Failure Mode) ===")
    from src.utils.mock_llm import MockBehavior
    loop_llm = MockLLM(behavior=MockBehavior.LOOP_FOREVER)
    agent = BaselineAgent(loop_llm, tools, max_steps=5)
    result = agent.run("Find the answer")
    
    if result == "Max steps reached":
        print("\n❌ FAILURE CONFIRMED: Agent looped until max steps.")
    else:
        print("\n✅ Unexpected success?")
