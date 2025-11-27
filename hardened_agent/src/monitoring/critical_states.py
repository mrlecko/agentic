"""
Critical States: The Five Survival Protocols

WHY THIS IS MORE ROBUST:
- Baseline agents: No self-monitoring, optimize blindly until they crash
- Hardened agent: Detects 5 critical states and overrides LLM with rules

RED TEAM DESIGN:
Each state has a specific trigger and deterministic response.
These are HARD-CODED instincts, not learned behaviors.

Aphorism #13: "Entropy is an API"
Aphorism #15: "The Panic Protocol"  
Aphorism #17: "Doubt buys Time"
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional

class CriticalState(Enum):
    """
    The five critical states that override optimization.
    
    NONE: Normal operation
    PANIC: High confusion/uncertainty
    DEADLOCK: Stuck in action loop  
    HUBRIS: Over-confident with shallow research
    SCARCITY: Running low on resources
    NOVELTY: Contradictory information detected
    """
    NONE = "none"
    PANIC = "panic"
    DEADLOCK = "deadlock"
    HUBRIS = "hubris"
    SCARCITY = "scarcity"
    NOVELTY = "novelty"


@dataclass
class StateDetection:
    """
    Result of critical state monitoring.
    
    WHY: Makes state transitions transparent and debuggable.
    """
    state: CriticalState
    confidence: float  # 0.0 to 1.0 (how sure are we?)
    reason: str       # Human-readable explanation
    metadata: Dict    # Additional diagnostic data
    recommended_action: Optional[str] = None
    
    def __bool__(self):
        """Allow: if detection: ... """
        return self.state != CriticalState.NONE
    
    def __str__(self):
        return f"{self.state.value.upper()}: {self.reason} (confidence: {self.confidence:.2%})"


@dataclass
class ProtocolResponse:
    """
    Deterministic response from a critical state protocol.
    
    WHY: Protocols are RULES, not suggestions. They override the LLM.
    """
    override_action: str  # What action to take instead
    reasoning: str        # Why this override
    metadata: Dict        # For logging/debugging


class ConfidenceEstimator:
    """
    Estimate confidence/entropy from LLM responses.
    
    WHY THIS IS MORE ROBUST:
    - Baseline: Trusts LLM blindly
    - Hardened: Parses hedging language, measures uncertainty
    
    RED TEAM: Can inject known-confused responses for testing.
    """
    
    # Words that indicate uncertainty
    HEDGING_WORDS = [
        'maybe', 'possibly', 'perhaps', 'might', 'could', 
        'probably', 'likely', 'uncertain', 'not sure',
        'i think', 'i believe', 'seems like', 'appears to'
    ]
    
    # Phrases that indicate high confidence
    CONFIDENCE_PHRASES = [
        'definitely', 'certainly', 'absolutely', 'clearly',
        'obviously', 'without doubt', 'for sure', 'guaranteed'
    ]
    
    @staticmethod
    def estimate_from_text(text: str) -> float:
        """
        Estimate confidence from text content.
        
        Returns:
            Confidence score 0.0 (confused) to 1.0 (certain)
        
        WHY: Baseline agents don't monitor their own confidence.
        We parse the actual words for uncertainty markers.
        """
        text_lower = text.lower()
        
        # Count hedging words
        hedging_count = sum(
            1 for word in ConfidenceEstimator.HEDGING_WORDS 
            if word in text_lower
        )
        
        # Count confidence phrases  
        confidence_count = sum(
            1 for phrase in ConfidenceEstimator.CONFIDENCE_PHRASES
            if phrase in text_lower
        )
        
        # Base confidence
        confidence = 0.7  # Neutral baseline
        
        # Reduce confidence for each hedging word (max -0.6)
        confidence -= min(0.6, hedging_count * 0.15)
        
        # Increase confidence for confidence phrases (max +0.3)
        confidence += min(0.3, confidence_count * 0.1)
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, confidence))
    
    @staticmethod
    def estimate_from_logprobs(logprobs: Dict) -> float:
        """
        Estimate confidence from log probabilities (if available).
        
        This is more accurate than text parsing but requires API support.
        """
        # TODO: Implement when using real OpenAI API with logprobs
        raise NotImplementedError("Logprob-based confidence not implemented yet")


class DEADLOCKProtocol:
    """
    DEADLOCK Protocol: Break infinite loops.
    
    Trigger: Agent is repeating the same actions (detected by ActionHistory)
    Response: Force a different action or force synthesis
    
    WHY THIS IS MORE ROBUST:
    - Baseline: Loops forever saying "let me search..."
    - Hardened: Detects loop after 3 iterations, forces break
    
    Aphorism #7: "Insanity is doing the same thing over and over"
    """
    
    def __init__(self, force_synthesis_after: int = 3):
        self.force_synthesis_after = force_synthesis_after
        self.loop_count = 0
        
    def handle(self, detection: StateDetection) -> ProtocolResponse:
        """
        Handle DEADLOCK state.
        
        Strategy:
        1. First loop: Try a different action
        2. Second loop: Force synthesis with current knowledge
        3. Third+ loop: Should never happen (circuit breaker)
        """
        self.loop_count += 1
        
        if self.loop_count >= self.force_synthesis_after:
            return ProtocolResponse(
                override_action="force_synthesis",
                reasoning=f"DEADLOCK: Repeated loop {self.loop_count} times. Synthesizing with current knowledge.",
                metadata={
                    'loop_count': self.loop_count,
                    'loop_pattern': detection.metadata.get('pattern', 'unknown')
                }
            )
        else:
            return ProtocolResponse(
                override_action="force_different_tool",
                reasoning=f"DEADLOCK: Breaking loop (attempt {self.loop_count}). Trying different approach.",
                metadata={
                    'loop_count': self.loop_count,
                    'previous_action': detection.metadata.get('pattern', 'unknown')
                }
            )
    
    def reset(self):
        """Reset loop counter (called when loop successfully broken)."""
        self.loop_count = 0


class PANICProtocol:
    """
    PANIC Protocol: Handle high confusion.
    
    Trigger: Low confidence in responses, high hedging language
    Response: Switch to conservative "tank mode" actions
    
    WHY THIS IS MORE ROBUST:
    - Baseline: Optimizes confidently even when confused → walks into traps
    - Hardened: Detects confusion, switches to safe reliable actions
    
    Aphorism #24: "Fear is Functional"
    Aphorism #99: "When confused, be safe not clever"
    """
    
    def __init__(self, conservative_sources: List[str] = None):
        self.conservative_sources = conservative_sources or [
            'wikipedia', 'arxiv', 'official_docs'
        ]
    
    def handle(self, detection: StateDetection) -> ProtocolResponse:
        """
        Handle PANIC state.
        
        Strategy: Switch to "tank mode"
        - Use only whitelisted reliable sources
        - Require consensus from multiple sources
        - Acknowledge uncertainty explicitly in response
        """
        return ProtocolResponse(
            override_action="tank_mode",
            reasoning=f"PANIC: High confusion detected ({detection.confidence:.0%}). Switching to conservative sources.",
            metadata={
                'confusion_level': 1 - detection.confidence,
                'allowed_sources': self.conservative_sources,
                'require_consensus': True
            }
        )


class HUBRISProtocol:
    """
    HUBRIS Protocol: Force skepticism when over-confident too early.
    
    Trigger: Wants to answer after minimal research with high confidence
    Response: Force additional research, seek contrary opinions
    
    WHY THIS IS MORE ROBUST:
    - Baseline: Accepts first answer, could be misinformation/hallucination
    - Hardened: Forces deeper research, seeks balance
    
    Aphorism #28: "Success is a Mask"
    Aphorism #55: "If your AI is too smart to be skeptical..."
    """
    
    def __init__(self, min_sources: int = 3):
        self.min_sources = min_sources
    
    def handle(self, detection: StateDetection) -> ProtocolResponse:
        """
        Handle HUBRIS state.
        
        Strategy:
        - Require N more sources before answering
        - Explicitly search for contrary opinions
        - Add "Confidence: X%" caveat to final answer
        """
        steps = detection.metadata.get('steps_taken', 0)
        
        return ProtocolResponse(
            override_action="force_deeper_research",
            reasoning=f"HUBRIS: Too confident after only {steps} steps. Seeking more sources and contrary views.",
            metadata={
                'require_additional_sources': self.min_sources,
                'seek_contrary_opinions': True,
                'steps_so_far': steps
            }
        )


class SCARCITYProtocol:
    """
    SCARCITY Protocol: Graceful degradation under resource limits.
    
    Trigger: Running low on tokens/steps/time
    Response: Synthesize immediately with current information
    
    WHY THIS IS MORE ROBUST:
    - Baseline: Keeps researching until crash/timeout
    - Hardened: Detects scarcity, provides best answer with caveat
    
    Aphorism #6: "Perfect is the enemy of done"
    Aphorism #64: "When time is short, ship it"
    """
    
    def handle(self, detection: StateDetection) -> ProtocolResponse:
        """
        Handle SCARCITY state.
        
        Strategy: "Spartan Mode"
        - Stop all research immediately
        - Synthesize with available information
        - Add caveat about resource limitations
        """
        token_budget = detection.metadata.get('token_budget', 0)
        step_budget = detection.metadata.get('step_budget', 0)
        
        return ProtocolResponse(
            override_action="immediate_synthesis",
            reasoning=f"SCARCITY: Low resources ({token_budget:.0%} tokens, {step_budget:.0%} steps). Synthesizing now.",
            metadata={
                'add_caveat': True,
                'caveat_text': f"Note: Limited resources prevented exhaustive research."
            }
        )


class NOVELTYProtocol:
    """
    NOVELTY Protocol: Handle contradictions and surprising information.
    
    Trigger: New information contradicts previous findings
    Response: Pause, update beliefs, flag contradiction
    
    WHY THIS IS MORE ROBUST:
    - Baseline: Ignores contradictions or picks one side randomly
    - Hardened: Acknowledges both sides, provides nuanced answer
    
    Aphorism #11: "Surprise is data"
    Aphorism #34: "The Outlier is the Teacher"
    """
    
    def handle(self, detection: StateDetection) -> ProtocolResponse:
        """
        Handle NOVELTY state.
        
        Strategy:
        - Pause and re-rank all sources by reliability
        - Update confidence estimates
        - Explicitly flag contradiction in response
        """
        return ProtocolResponse(
            override_action="integrate_contradiction",
            reasoning="NOVELTY: Contradictory information detected. Re-evaluating all sources.",
            metadata={
                'rerank_sources': True,
                'flag_contradiction': True,
                'update_confidence': True
            }
        )


# Demo
if __name__ == "__main__":
    print("=== CRITICAL STATES DEMO ===\n")
    
    # Test 1: Confidence estimation
    print("1. Confidence Estimation:")
    examples = [
        "I'm absolutely certain that quantum computing uses superposition.",
        "Maybe it could be related to quantum entanglement? I'm not sure.",
        "The answer is probably related to wave functions, perhaps.",
    ]
    
    for text in examples:
        conf = ConfidenceEstimator.estimate_from_text(text)
        print(f"   Text: '{text[:50]}...'")
        print(f"   Confidence: {conf:.0%}\n")
    
    # Test 2: DEADLOCK Protocol
    print("2. DEADLOCK Protocol:")
    protocol = DEADLOCKProtocol()
    detection = StateDetection(
        state=CriticalState.DEADLOCK,
        confidence=1.0,
        reason="Repeated search action 3 times",
        metadata={'pattern': 'search → search → search'}
    )
    
    response = protocol.handle(detection)
    print(f"   {response.reasoning}")
    print(f"   Action: {response.override_action}\n")
    
    # Test 3: PANIC Protocol  
    print("3. PANIC Protocol:")
    protocol = PANICProtocol()
    detection = StateDetection(
        state=CriticalState.PANIC,
        confidence=0.95,  # 95% sure we're confused
        reason="High hedging language detected",
        metadata={}
    )
    response = protocol.handle(detection)
    print(f"   {response.reasoning}")
    print(f"   Action: {response.override_action}\n")
    
    print("=== WHY THIS MATTERS ===")
    print("✓ Baseline agents optimize blindly")
    print("✓ They don't monitor their own state")
    print(print("✓ These protocols are DETERMINISTIC overrides"))
    print("✓ Like a reptilian brain that says 'STOP'")
    print("✓ Aphorism #3: 'The ultimate sophistication is the wisdom of the reflexes'")
