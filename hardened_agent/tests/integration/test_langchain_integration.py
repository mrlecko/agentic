"""
Integration Test: Real LangChain Agent

Verifies that the HardenedLangChainAgent works with the real OpenAI API.
Requires OPENAI_API_KEY to be set.
"""

import pytest
import os
from src.agents.langchain_hardened import HardenedLangChainAgent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

class TestLangChainIntegration:
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_openai_connection(self):
        """
        Test that we can connect to OpenAI and get a response
        through the Hardened Agent wrapper.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not found")
            
        # Setup Real Agent
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        
        @tool
        def search(query: str) -> str:
            """Search for information."""
            return "Paris is the capital of France."
            
        agent = HardenedLangChainAgent(llm=llm, tools=[search])
        
        # Simple query that shouldn't trigger critical states
        result = agent.run("What is the capital of France?")
        
        # Verify we got a valid response
        assert "Paris" in result
        assert "Max steps reached" != result

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
