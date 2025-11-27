"""
Hardened LangChain Agent

This module implements the Hardened Agent using ACTUAL LangChain primitives.
It demonstrates how to wrap the "Brainstem" (Safety Layer) around a 
standard LangChain "Cortex" (LLM Chain).

ARCHITECTURE:
    [User Input] -> [Hardened Loop]
                          |
            +-------------+-------------+
            |                           |
      [Brainstem Check]           [LangChain Chain]
      (Monitor/History)           (Prompt|LLM|Parser)
            |                           |
      [Critical State?] --NO--> [Invoke Chain]
            |                           |
           YES                          v
            |                    [Tool Execution]
            v                           |
    [Protocol Action] <-----------------+
            |
            v
     [Action History]
"""

from typing import List, Dict, Any, Union, Sequence
import json
import time

# LangChain Imports
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool, tool
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration

# Hardening Imports
from src.memory.action_history import ActionHistory
from src.monitoring.monitor import MetaCognitiveMonitor
from src.monitoring.circuit_breaker import CircuitBreaker
from src.monitoring.critical_states import (
    CriticalState, DEADLOCKProtocol, PANICProtocol, 
    HUBRISProtocol, SCARCITYProtocol, NOVELTYProtocol
)

# ==========================================
# 1. Adapter for Mocking (TDD Support)
# ==========================================
class MockLangChainChatModel(BaseChatModel):
    """
    A LangChain-compatible ChatModel that uses our MockLLM backend.
    Allows us to run LangChain tests deterministically.
    """
    mock_backend: Any
    
    def __init__(self, mock_backend: Any):
        super().__init__(mock_backend=mock_backend)
        
    @property
    def _llm_type(self) -> str:
        return "mock-hardened"
        
    def _generate(self, messages: List[BaseMessage], stop: List[str] = None, **kwargs) -> ChatResult:
        # Convert LangChain messages to string prompt for our simple mock
        prompt = "\n".join([m.content for m in messages])
        
        # Get response from our deterministic mock
        response = self.mock_backend.invoke(prompt)
        
        # Convert back to LangChain format
        content = response.content
        
        # If tool calls exist, format them for ReAct parsing
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            # Append ReAct-style action text so our parser sees it
            # In a real agent, we'd use tool_calling features, but this ensures
            # the text-based parser works for the demo.
            content += f"\nAction: {tool_call['name']}({tool_call['args']})"
            
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

# ==========================================
# 2. The Hardened Agent
# ==========================================
class HardenedLangChainAgent:
    """
    The 'Wise Survivor' implementation using LangChain.
    """
    
    def __init__(self, llm: BaseChatModel, tools: Sequence[BaseTool]):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.max_steps = 10
        self.token_budget = 1000
        self.session_id = f"session_{int(time.time())}"
        
        # --- THE BRAINSTEM (Safety Layer) ---
        self.history = ActionHistory(":memory:")
        self.circuit_breaker = CircuitBreaker()
        self.monitor = MetaCognitiveMonitor(self.history, self.circuit_breaker)
        self.protocols = {
            CriticalState.DEADLOCK: DEADLOCKProtocol(),
            CriticalState.PANIC: PANICProtocol(),
            CriticalState.HUBRIS: HUBRISProtocol(),
            CriticalState.SCARCITY: SCARCITYProtocol(),
            CriticalState.NOVELTY: NOVELTYProtocol()
        }
        
        # --- THE CORTEX (LangChain Layer) ---
        # Standard ReAct prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful research assistant. Answer the user's request."),
            ("user", "{input}"),
            ("assistant", "{agent_scratchpad}"),
        ])
        
    def run(self, input_text: str):
        """
        Custom Agent Loop that injects Hardening checks.
        """
        print(f"--- Hardened LangChain Agent Starting: {input_text} ---")
        
        agent_scratchpad = ""
        tokens_used_total = 0
        
        for step in range(self.max_steps):
            print(f"\nStep {step+1}/{self.max_steps}")
            
            # 1. CIRCUIT BREAKER CHECK
            if self.circuit_breaker.tripped:
                return f"HALTED: {self.circuit_breaker.trip_reason}"
            
            # 2. CORTEX: Generate Thought (Probabilistic)
            # We invoke the chain to get the *proposed* thought/action
            chain = self.prompt | self.llm
            response_msg = chain.invoke({
                "input": input_text,
                "agent_scratchpad": agent_scratchpad
            })
            response_text = response_msg.content
            
            # Track tokens (approximate)
            tokens_used_total += len(response_text.split()) 
            
            # 3. BRAINSTEM: Meta-Cognitive Check (Deterministic)
            # "Wait, before I act... am I crazy?"
            state_detection = self.monitor.check_state(
                llm_response=response_text,
                current_step=step+1,
                max_steps=self.max_steps,
                tokens_used=tokens_used_total,
                budget=self.token_budget,
                session_id=self.session_id
            )
            
            print(f"State: {state_detection.state.value.upper()} (Conf: {state_detection.confidence:.2f})")
            
            # 4. DECISION: Cortex vs Brainstem
            final_action = None
            final_tool_input = None
            
            if state_detection.state == CriticalState.NONE:
                # --- NORMAL MODE (Cortex) ---
                # Parse the LLM response to find action
                # (Simple ReAct parsing for demo)
                if "Action:" in response_text:
                    parts = response_text.split("Action:")
                    thought = parts[0].strip()
                    action_part = parts[1].strip()
                    
                    # Very naive parser for demo purposes
                    # In production use LangChain's ReActSingleInputOutputParser
                    if "(" in action_part:
                        action_name = action_part.split("(")[0].strip()
                        action_input = action_part.split("(")[1].rstrip(")").strip()
                    else:
                        action_name = action_part
                        action_input = "{}"
                        
                    final_action = action_name
                    final_tool_input = action_input
                    print(f"Thought (Cortex): {thought}")
                else:
                    # Final Answer
                    print(f"Final Answer: {response_text}")
                    return response_text
            else:
                # --- CRITICAL MODE (Brainstem) ---
                # Protocol VETOES the Cortex
                protocol = self.protocols[state_detection.state]
                protocol_resp = protocol.handle(state_detection)
                
                final_action = protocol_resp.override_action
                final_tool_input = str(protocol_resp.metadata)
                print(f"⚠️ PROTOCOL OVERRIDE: {protocol_resp.reasoning}")
            
            # 5. EXECUTION
            print(f"Executing: {final_action}({final_tool_input})")
            
            observation = self._execute_tool(final_action, final_tool_input)
            print(f"Observation: {observation}")
            
            # 6. MEMORY: Record to History
            self.history.record_action(
                tool=final_action,
                args=str(final_tool_input),
                result=str(observation),
                tokens=10, # Dummy
                session_id=self.session_id
            )
            
            # Update Scratchpad for next turn
            agent_scratchpad += f"\nAI: {response_text}\nSystem: Observation: {observation}\n"
            
        return "Max steps reached"

    def _execute_tool(self, name: str, input_str: str) -> str:
        """Execute tool or protocol action."""
        # Protocol Actions
        if name == "force_different_tool":
            return "Protocol forced a different approach."
        if name == "immediate_synthesis":
            return "Synthesized answer due to scarcity."
        
        # Real Tools
        if name in self.tools:
            try:
                # In real LangChain, we'd parse the input_str to dict
                # Here we just pass the string for the demo tools
                return self.tools[name].invoke(input_str)
            except Exception as e:
                return f"Error: {e}"
        
        return f"Tool {name} not found"

# ==========================================
# 3. DEMO
# ==========================================
if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    from langchain_openai import ChatOpenAI
    
    load_dotenv()
    
    # Define a LangChain tool
    @tool
    def search(query: str) -> str:
        """Search for information."""
        return f"Results for {query}"
        
    print("=== REAL LANGCHAIN INTEGRATION DEMO ===\n")
    
    # Check configuration
    api_key = os.getenv("OPENAI_API_KEY")
    use_mock = os.getenv("USE_MOCK_LLM", "True").lower() == "true"
    
    if api_key and not use_mock:
        print(f">>> USING REAL OPENAI API (Key found: {api_key[:4]}...) <<<")
        # Use real Cortex
        lc_llm = ChatOpenAI(model="gpt-4o", temperature=0)
        query = "What is the capital of France? Answer in one sentence."
    else:
        print(">>> USING MOCK LLM (No key or USE_MOCK_LLM=True) <<<")
        # Use Mock Cortex (Infinite Loop Scenario)
        from src.utils.mock_llm import MockLLM, MockBehavior
        mock_backend = MockLLM(behavior=MockBehavior.LOOP_FOREVER)
        lc_llm = MockLangChainChatModel(mock_backend)
        query = "Find the answer"
    
    # Create Hardened Agent
    agent = HardenedLangChainAgent(llm=lc_llm, tools=[search])
    
    # Run
    result = agent.run(query)
    print(f"\nFinal Result: {result}")
