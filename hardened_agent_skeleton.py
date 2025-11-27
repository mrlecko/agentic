"""
The Hardened Agent: Core Architecture Skeleton

This is a starter template showing the three-layer architecture.
Implement each TODO to build out the full system.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import sqlite3


# ============================================================================
# CRITICAL STATES (Layer 2: Brainstem)
# ============================================================================

class CriticalState(Enum):
    """The five critical states that override LLM decision-making."""
    NONE = "none"
    PANIC = "panic"          # High confusion
    DEADLOCK = "deadlock"    # Action loops
    HUBRIS = "hubris"        # Over-confidence
    SCARCITY = "scarcity"    # Resource limits
    NOVELTY = "novelty"      # Contradictions


@dataclass
class StateDetection:
    """Result of critical state monitoring."""
    state: CriticalState
    confidence: float
    reason: str
    metadata: Dict


# ============================================================================
# ACTION HISTORY (Memory for Loop Detection)
# ============================================================================

class ActionHistory:
    """Tracks all agent actions for loop detection and analysis."""
    
    def __init__(self, db_path: str = "action_history.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_table()
    
    def _create_table(self):
        """Create action history table if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tool TEXT NOT NULL,
                args TEXT NOT NULL,
                result TEXT,
                tokens_used INTEGER,
                session_id TEXT
            )
        """)
        self.conn.commit()
    
    def record_action(self, tool: str, args: str, result: str, tokens: int, session_id: str):
        """Record an action to history."""
        self.conn.execute("""
            INSERT INTO actions (timestamp, tool, args, result, tokens_used, session_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), tool, args, result, tokens, session_id))
        self.conn.commit()
    
    def get_recent_actions(self, session_id: str, n: int = 10) -> List[Dict]:
        """Get the last N actions for this session."""
        cursor = self.conn.execute("""
            SELECT * FROM actions 
            WHERE session_id = ? 
            ORDER BY id DESC 
            LIMIT ?
        """, (session_id, n))
        
        return [
            {
                'id': row[0],
                'timestamp': row[1],
                'tool': row[2],
                'args': row[3],
                'result': row[4],
                'tokens_used': row[5]
            }
            for row in cursor.fetchall()
        ]
    
    def detect_loop(self, session_id: str, window: int = 5) -> Optional[str]:
        """
        Detect if the agent is in a loop.
        Returns loop pattern if found, None otherwise.
        """
        actions = self.get_recent_actions(session_id, window)
        
        # TODO: Implement sophisticated loop detection
        # Current: Simple exact repetition check
        if len(actions) >= 3:
            last_three = [(a['tool'], a['args']) for a in actions[:3]]
            if last_three[0] == last_three[1] == last_three[2]:
                return f"EXACT_REPEAT: {last_three[0]}"
        
        return None


# ============================================================================
# META-COGNITIVE MONITOR (Layer 2: Watchful Eye)
# ============================================================================

class MetaCognitiveMonitor:
    """
    Watches the agent and detects critical states.
    This is the "reptilian brain" that overrides optimization.
    """
    
    def __init__(self, 
                 max_tokens: int = 4000,
                 max_steps: int = 20,
                 panic_threshold: float = 0.7,
                 hubris_threshold: int = 2):
        self.max_tokens = max_tokens
        self.max_steps = max_steps
        self.panic_threshold = panic_threshold
        self.hubris_threshold = hubris_threshold
        
        self.history = ActionHistory()
        self.tokens_used = 0
        self.steps_taken = 0
    
    def check_critical_state(self, 
                            session_id: str,
                            llm_response: str,
                            confidence: float) -> StateDetection:
        """
        Check if we're in a critical state.
        Returns the highest-priority state detected.
        """
        
        # Priority order: DEADLOCK > SCARCITY > PANIC > HUBRIS > NOVELTY
        
        # 1. DEADLOCK (loops are death)
        loop = self.history.detect_loop(session_id)
        if loop:
            return StateDetection(
                state=CriticalState.DEADLOCK,
                confidence=1.0,
                reason=f"Loop detected: {loop}",
                metadata={'pattern': loop}
            )
        
        # 2. SCARCITY (resource limits)
        token_budget = (self.max_tokens - self.tokens_used) / self.max_tokens
        step_budget = (self.max_steps - self.steps_taken) / self.max_steps
        
        if token_budget < 0.2 or step_budget < 0.2:
            return StateDetection(
                state=CriticalState.SCARCITY,
                confidence=1.0 - min(token_budget, step_budget),
                reason=f"Low resources: {token_budget:.0%} tokens, {step_budget:.0%} steps",
                metadata={'token_budget': token_budget, 'step_budget': step_budget}
            )
        
        # 3. PANIC (confusion)
        if confidence < (1 - self.panic_threshold):  # Low confidence
            confusion_score = 1 - confidence
            if confusion_score > self.panic_threshold:
                return StateDetection(
                    state=CriticalState.PANIC,
                    confidence=confusion_score,
                    reason=f"High confusion: {confusion_score:.0%}",
                    metadata={'confidence': confidence}
                )
        
        # 4. HUBRIS (over-confidence with shallow research)
        if self.steps_taken <= self.hubris_threshold and confidence > 0.9:
            return StateDetection(
                state=CriticalState.HUBRIS,
                confidence=confidence,
                reason=f"Too confident too early: {self.steps_taken} steps",
                metadata={'steps': self.steps_taken, 'confidence': confidence}
            )
        
        # 5. NOVELTY (TODO: detect contradictions)
        # Requires comparing new information with previous beliefs
        
        # No critical state
        return StateDetection(
            state=CriticalState.NONE,
            confidence=0.0,
            reason="All systems nominal",
            metadata={}
        )


# ============================================================================
# SILVER GAUGE (Transparent Geometry)
# ============================================================================

class SilverGauge:
    """Calculate the decision geometry for transparency."""
    
    @staticmethod
    def calculate_k_explore(goal_value: float, info_gain: float) -> float:
        """
        Calculate k_explore: ratio of Harmonic to Arithmetic mean.
        
        k ≈ 1.0: GENERALIST (balanced goal and info)
        k ≈ 0.0: SPECIALIST (high in one, low in other)
        """
        if goal_value <= 0 or info_gain <= 0:
            return 0.0
        
        hm = 2 * goal_value * info_gain / (goal_value + info_gain)
        am = (goal_value + info_gain) / 2
        
        return hm / am if am > 0 else 0.0
    
    @staticmethod
    def score_action(action: str, 
                     goal_relevance: float, 
                     information_novelty: float) -> Dict:
        """
        Score an action and return its geometry.
        
        Args:
            action: The action being considered
            goal_relevance: How much it helps answer the question (0-1)
            information_novelty: How much new info it provides (0-1)
        
        Returns:
            Dictionary with scores and geometry label
        """
        k = SilverGauge.calculate_k_explore(goal_relevance, information_novelty)
        
        return {
            'action': action,
            'goal_value': goal_relevance,
            'info_gain': information_novelty,
            'k_explore': k,
            'geometry': 'GENERALIST' if k > 0.5 else 'SPECIALIST',
            'reasoning': SilverGauge._explain_geometry(k, goal_relevance, information_novelty)
        }
    
    @staticmethod
    def _explain_geometry(k: float, g: float, i: float) -> str:
        """Generate human-readable explanation of the geometry."""
        if k > 0.7:
            return f"Balanced action: high goal value ({g:.2f}) AND high info gain ({i:.2f})"
        elif g > i * 2:
            return f"Goal-focused: strong relevance ({g:.2f}) but limited new information ({i:.2f})"
        elif i > g * 2:
            return f"Exploration-focused: high novelty ({i:.2f}) but unclear goal contribution ({g:.2f})"
        else:
            return f"Moderate: goal={g:.2f}, info={i:.2f}, balance={k:.2f}"


# ============================================================================
# CIRCUIT BREAKER (Layer 3: Escalation)
# ============================================================================

class CircuitBreaker:
    """
    Prevents thrashing by halting if critical states fire repeatedly.
    "A dead agent is better than a thrashing agent."
    """
    
    def __init__(self, max_consecutive_alerts: int = 3):
        self.max_consecutive_alerts = max_consecutive_alerts
        self.consecutive_alerts = 0
        self.alert_history: List[CriticalState] = []
    
    def record_critical_state(self, state: CriticalState) -> bool:
        """
        Record a critical state activation.
        Returns True if circuit breaker should trip (HALT).
        """
        if state == CriticalState.NONE:
            self.consecutive_alerts = 0
            return False
        
        self.consecutive_alerts += 1
        self.alert_history.append(state)
        
        if self.consecutive_alerts >= self.max_consecutive_alerts:
            return True  # TRIP THE BREAKER
        
        return False
    
    def get_diagnostic_info(self) -> Dict:
        """Return information about the thrashing pattern."""
        return {
            'consecutive_alerts': self.consecutive_alerts,
            'alert_history': [s.value for s in self.alert_history[-10:]],
            'thrashing': self.consecutive_alerts >= self.max_consecutive_alerts
        }


# ============================================================================
# HARDENED AGENT (Layer 1-3 Integration)
# ============================================================================

class HardenedAgent:
    """
    The main agent wrapper that integrates all three layers.
    
    Layer 1: LangChain agent (cortex)
    Layer 2: Meta-cognitive monitor + Critical states (brainstem)
    Layer 3: Circuit breaker (safety net)
    """
    
    def __init__(self, 
                 langchain_agent,  # Your LangChain agent
                 max_tokens: int = 4000,
                 max_steps: int = 20):
        
        # Layer 1: The smart but potentially foolish optimizer
        self.cortex = langchain_agent
        
        # Layer 2: The watchful brainstem
        self.monitor = MetaCognitiveMonitor(max_tokens, max_steps)
        
        # Layer 3: The circuit breaker
        self.breaker = CircuitBreaker()
        
        self.session_id = datetime.now().isoformat()
    
    def run(self, query: str) -> Dict:
        """
        Execute the agent with meta-cognitive monitoring.
        
        Returns:
            {
                'answer': str,
                'critical_states_encountered': List[str],
                'circuit_breaker_tripped': bool,
                'diagnostic_info': Dict
            }
        """
        states_encountered = []
        
        while self.monitor.steps_taken < self.monitor.max_steps:
            self.monitor.steps_taken += 1
            
            # TODO: Get LLM suggestion from Layer 1 (cortex)
            llm_action = self._get_cortex_action(query)
            
            # TODO: Estimate confidence (parse response for hedging, etc.)
            confidence = self._estimate_confidence(llm_action)
            
            # Check for critical state (Layer 2)
            state_detection = self.monitor.check_critical_state(
                self.session_id,
                llm_action['response'],
                confidence
            )
            
            # Record action
            self.monitor.history.record_action(
                tool=llm_action.get('tool', 'llm'),
                args=str(llm_action.get('args', '')),
                result=llm_action.get('response', ''),
                tokens=llm_action.get('tokens', 0),
                session_id=self.session_id
            )
            
            # Check circuit breaker (Layer 3)
            if self.breaker.record_critical_state(state_detection.state):
                # THRASHING DETECTED - HALT
                return {
                    'answer': self._emergency_synthesis(),
                    'critical_states_encountered': states_encountered,
                    'circuit_breaker_tripped': True,
                    'diagnostic_info': self.breaker.get_diagnostic_info()
                }
            
            # Handle critical state or proceed normally
            if state_detection.state != CriticalState.NONE:
                states_encountered.append(state_detection.state.value)
                action = self._handle_critical_state(state_detection)
            else:
                action = llm_action
            
            # Execute action
            result = self._execute_action(action)
            
            # Check if we're done
            if result.get('done', False):
                return {
                    'answer': result['answer'],
                    'critical_states_encountered': states_encountered,
                    'circuit_breaker_tripped': False,
                    'diagnostic_info': {}
                }
        
        # Max steps reached
        return {
            'answer': self._emergency_synthesis(),
            'critical_states_encountered': states_encountered,
            'circuit_breaker_tripped': False,
            'diagnostic_info': {'reason': 'max_steps_reached'}
        }
    
    def _get_cortex_action(self, query: str) -> Dict:
        """Get action suggestion from the LangChain agent."""
        # TODO: Implement LangChain agent invocation
        raise NotImplementedError("Integrate with your LangChain agent")
    
    def _estimate_confidence(self, llm_action: Dict) -> float:
        """Estimate confidence from LLM response."""
        # TODO: Parse for hedging words, measure variance, use logprobs if available
        response = llm_action.get('response', '')
        hedging_words = ['maybe', 'possibly', 'perhaps', 'might', 'could', "i'm not sure"]
        
        hedging_count = sum(1 for word in hedging_words if word in response.lower())
        confidence = max(0.0, 1.0 - (hedging_count * 0.15))
        
        return confidence
    
    def _handle_critical_state(self, detection: StateDetection) -> Dict:
        """Override LLM with protocol-based action."""
        protocols = {
            CriticalState.PANIC: self._panic_protocol,
            CriticalState.DEADLOCK: self._deadlock_protocol,
            CriticalState.HUBRIS: self._hubris_protocol,
            CriticalState.SCARCITY: self._scarcity_protocol,
            CriticalState.NOVELTY: self._novelty_protocol,
        }
        
        handler = protocols.get(detection.state)
        if handler:
            return handler(detection)
        
        return {}
    
    def _panic_protocol(self, detection: StateDetection) -> Dict:
        """PANIC: Switch to conservative, safe actions."""
        # TODO: Implement tank mode (whitelist sources, require consensus)
        return {'protocol': 'PANIC', 'action': 'conservative_search'}
    
    def _deadlock_protocol(self, detection: StateDetection) -> Dict:
        """DEADLOCK: Force different action to break loop."""
        # TODO: Force different tool or force synthesis
        return {'protocol': 'DEADLOCK', 'action': 'force_synthesis'}
    
    def _hubris_protocol(self, detection: StateDetection) -> Dict:
        """HUBRIS: Force skepticism and deeper research."""
        # TODO: Require N more sources, search for contrary opinions
        return {'protocol': 'HUBRIS', 'action': 'seek_contrary_views'}
    
    def _scarcity_protocol(self, detection: StateDetection) -> Dict:
        """SCARCITY: Immediate synthesis with current info."""
        # TODO: Synthesize immediately, no more research
        return {'protocol': 'SCARCITY', 'action': 'immediate_synthesis'}
    
    def _novelty_protocol(self, detection: StateDetection) -> Dict:
        """NOVELTY: Pause and integrate contradictory information."""
        # TODO: Re-rank sources, update beliefs, flag contradiction
        return {'protocol': 'NOVELTY', 'action': 'integrate_contradiction'}
    
    def _execute_action(self, action: Dict) -> Dict:
        """Execute an action (either LLM or protocol-driven)."""
        # TODO: Implement action execution
        raise NotImplementedError("Implement action execution")
    
    def _emergency_synthesis(self) -> str:
        """Emergency synthesis when halting."""
        return (
            "I've reached my operational limits. "
            "Based on the information gathered so far, here's my current understanding... "
            "[TODO: Synthesize from action history]"
        )


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # TODO: Replace with actual LangChain agent
    mock_langchain_agent = None
    
    agent = HardenedAgent(
        langchain_agent=mock_langchain_agent,
        max_tokens=4000,
        max_steps=20
    )
    
    # Demo: Silver Gauge
    gauge = SilverGauge()
    
    actions = [
        ("search_arxiv", 0.9, 0.8),   # High goal, high info
        ("search_wikipedia", 0.3, 0.9),  # Low goal, high info
        ("synthesize", 0.9, 0.1),     # High goal, low info
    ]
    
    print("\\n=== SILVER GAUGE DEMO ===")
    for action, goal, info in actions:
        score = gauge.score_action(action, goal, info)
        print(f"\\n{score['action']}:")
        print(f"  k_explore: {score['k_explore']:.3f} ({score['geometry']})")
        print(f"  {score['reasoning']}")
    
    # Demo: Loop Detection
    print("\\n=== LOOP DETECTION DEMO ===")
    history = ActionHistory(":memory:")  # In-memory for demo
    session = "demo-session"
    
    for i in range(4):
        history.record_action(
            tool="search",
            args="quantum computing",
            result="...",
            tokens=100,
            session_id=session
        )
    
    loop = history.detect_loop(session)
    print(f"Loop detected: {loop}")
    
    print("\\n=== READY TO BUILD ===")
    print("Next steps:")
    print("1. Implement LangChain integration (_get_cortex_action)")
    print("2. Implement protocol actions (PANIC, DEADLOCK, etc.)")
    print("3. Add confidence estimation (entropy proxy)")
    print("4. Build adversarial test scenarios")
    print("5. Create visualization dashboard")
