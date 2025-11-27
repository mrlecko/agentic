"""
Hardened Agent: The Wise Survivor

WHY THIS IS MORE ROBUST:
- Baseline: Optimizes blindly, loops forever, crashes.
- Hardened: 
    1. Monitors state (Meta-Cognition)
    2. Overrides LLM when necessary (Critical Protocols)
    3. Halts if thrashing (Circuit Breaker)
    4. Remembers past actions (History)

ARCHITECTURE:
   [Circuit Breaker] -> HALT
          ^
   [Meta-Monitor] -> [Critical Protocols] -> [Action]
          ^                   ^
   [Action History]           |
          ^                   |
   [Cortex (LLM)] -> [Standard Action]
"""

from typing import Dict, Any, Optional
import time

from src.utils.mock_llm import MockLLM
from src.memory.action_history import ActionHistory
from src.monitoring.circuit_breaker import CircuitBreaker
from src.monitoring.monitor import MetaCognitiveMonitor
from src.monitoring.critical_states import (
    CriticalState, DEADLOCKProtocol, PANICProtocol, 
    HUBRISProtocol, SCARCITYProtocol, NOVELTYProtocol
)

class HardenedAgent:
    """
    A battle-hardened agent that survives where others fail.
    """
    
    def __init__(self, 
                 llm: MockLLM, 
                 tools: Dict[str, Any], 
                 max_steps: int = 10,
                 token_budget: int = 1000):
        
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.token_budget = token_budget
        self.session_id = f"session_{int(time.time())}"
        
        # 1. Initialize Memory
        self.history = ActionHistory(":memory:")
        
        # 2. Initialize Safety Systems
        self.circuit_breaker = CircuitBreaker()
        self.monitor = MetaCognitiveMonitor(self.history, self.circuit_breaker)
        
        # 3. Initialize Protocols
        self.protocols = {
            CriticalState.DEADLOCK: DEADLOCKProtocol(),
            CriticalState.PANIC: PANICProtocol(),
            CriticalState.HUBRIS: HUBRISProtocol(),
            CriticalState.SCARCITY: SCARCITYProtocol(),
            CriticalState.NOVELTY: NOVELTYProtocol()
        }
        
    def run(self, goal: str) -> str:
        """
        Run the hardened agent loop.
        """
        print(f"--- Hardened Agent Starting: {goal} ---")
        current_context = f"Goal: {goal}\n"
        tokens_used_total = 0
        
        for i in range(self.max_steps):
            print(f"\nStep {i+1}/{self.max_steps}")
            
            # 1. Check Circuit Breaker (Layer 3)
            if self.circuit_breaker.tripped:
                return f"HALTED: {self.circuit_breaker.trip_reason}"
            
            # 2. Get LLM Response (Cortex)
            # We get the response first to analyze it, but don't execute yet
            prompt = self._build_prompt(current_context)
            llm_response = self.llm.invoke(prompt)
            tokens_used_total += llm_response.tokens_used
            
            # 3. Meta-Cognitive Check (Brainstem)
            state_detection = self.monitor.check_state(
                llm_response=llm_response.content,
                current_step=i+1,
                max_steps=self.max_steps,
                tokens_used=tokens_used_total,
                budget=self.token_budget,
                session_id=self.session_id
            )
            
            print(f"State: {state_detection.state.value.upper()} (Conf: {state_detection.confidence:.2f})")
            
            # 4. Decide Action
            if state_detection.state == CriticalState.NONE:
                # Normal Operation: Use Cortex
                if not llm_response.tool_calls:
                    print(f"Final Answer: {llm_response.content}")
                    return llm_response.content
                
                tool_call = llm_response.tool_calls[0]
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                reasoning = "Normal optimization"
                
            else:
                # Critical State: Use Protocol
                protocol = self.protocols[state_detection.state]
                response = protocol.handle(state_detection)
                
                tool_name = response.override_action
                tool_args = response.metadata
                reasoning = response.reasoning
                print(f"⚠️ PROTOCOL OVERRIDE: {reasoning}")
            
            # 5. Execute Action
            print(f"Action: {tool_name}({tool_args})")
            
            # Handle special protocol actions or normal tools
            if tool_name in self.tools:
                observation = self._execute_tool(tool_name, tool_args)
            elif tool_name == "force_different_tool":
                observation = "Protocol forced different tool. (Simulated)"
                # In real impl, we'd pick a different tool from list
            elif tool_name == "force_synthesis":
                return f"Synthesized Answer (Forced by DEADLOCK): {current_context[-100:]}"
            elif tool_name == "tank_mode":
                observation = "Switching to conservative sources... (Simulated)"
            elif tool_name == "immediate_synthesis":
                return f"Synthesized Answer (Forced by SCARCITY): {current_context[-100:]}"
            else:
                observation = f"Executed protocol action: {tool_name}"
            
            print(f"Observation: {observation}")
            
            # 6. Record to History
            self.history.record_action(
                tool=tool_name,
                args=str(tool_args),
                result=str(observation),
                tokens=llm_response.tokens_used,
                session_id=self.session_id
            )
            
            # Update context
            current_context += f"\nThought: {llm_response.content}\nState: {state_detection.state.value}\nAction: {tool_name}\nObservation: {observation}\n"
            
        return "Max steps reached"

    def _build_prompt(self, context: str) -> str:
        return f"Goal: {context}" # Simplified for mock
    
    def _execute_tool(self, name: str, args: Dict) -> str:
        try:
            return self.tools[name](**args)
        except Exception as e:
            return f"Error: {e}"

# Demo
if __name__ == "__main__":
    tools = {"search": lambda query: "Results"}
    
    print("=== HARDENED AGENT vs INFINITE LOOP ===")
    from src.utils.mock_llm import MockBehavior
    
    # Same loop behavior that killed the Baseline Agent
    loop_llm = MockLLM(behavior=MockBehavior.LOOP_FOREVER)
    
    agent = HardenedAgent(loop_llm, tools, max_steps=10)
    result = agent.run("Find the answer")
    
    print(f"\nResult: {result}")
    
    if "Synthesized Answer" in result:
        print("\n✅ SUCCESS: Agent broke the loop and synthesized an answer!")
    else:
        print("\n❌ FAILURE: Agent did not break the loop.")
