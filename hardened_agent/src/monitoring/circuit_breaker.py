"""
Circuit Breaker: Escalation Protocol

WHY THIS IS MORE ROBUST:
- Baseline agents: Thrash between failure modes forever
- Hardened agent: Detects thrashing, HALTS with diagnostics

RED TEAM DESIGN:
- If critical states fire 3+ times in a row → TRIP
- If oscillating between different states → TRIP
- When tripped: Stop everything, return diagnostics

Aphorism #20: "Oscillation is Death"
Aphorism #23: "A dead agent is better than a thrashing agent"
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import Counter
from src.monitoring.critical_states import CriticalState


@dataclass
class CircuitBreakerStatus:
    """Status of the circuit breaker."""
    tripped: bool
    consecutive_alerts: int
    total_alerts: int
    alert_history: List[str]
    thrashing_pattern: Optional[str]
    diagnostic_info: Dict
    
    def __bool__(self):
        """Allow: if status: ... (True if tripped)"""
        return self.tripped


class CircuitBreaker:
    """
    Circuit Breaker: Layer 3 of the defensive architecture.
    
    Prevents thrashing by halting when critical states fire repeatedly.
    
    WHY THIS IS MORE ROBUST:
    - Baseline: Thrashes forever (PANIC → try something → DEADLOCK → PANIC → ...)
    - Hardened: Detects thrashing after 3 attempts, HALTS cleanly
    
    Design Decision: "A halted agent reveals the problem. A thrashing agent masks it."
    """
    
    def __init__(self, max_consecutive_alerts: int = 3, max_total_alerts: int = 10):
        """
        Initialize circuit breaker.
        
        Args:
            max_consecutive_alerts: Consecutive critical states before trip (default: 3)
            max_total_alerts: Total critical states in session before trip (default: 10)
        
        WHY THESE THRESHOLDS:
        - 3 consecutive: Agent tried 3 different protocols and still failing
        - 10 total: Even with breaks, too many failures overall
        """
        self.max_consecutive = max_consecutive_alerts
        self.max_total = max_total_alerts
        
        self.consecutive_count = 0
        self.total_count = 0
        self.alert_history: List[CriticalState] = []
        self.tripped = False
        self.trip_reason: Optional[str] = None
    
    def record_critical_state(self, state: CriticalState) -> CircuitBreakerStatus:
        """
        Record a critical state activation.
        
        Returns:
            CircuitBreakerStatus indicating if breaker tripped
        
        RED TEAM SCENARIOS:
        - Exact repeats: PANIC → PANIC → PANIC
        - Oscillation: PANIC → DEADLOCK → PANIC → DEADLOCK
        - Many small failures: 10+ different states
        """
        # If already tripped, stay tripped
        if self.tripped:
            return self._get_status()
        
        # NONE state resets consecutive counter (agent is healthy again)
        if state == CriticalState.NONE:
            self.consecutive_count = 0
            return self._get_status()
        
        # Record the alert
        self.alert_history.append(state)
        self.consecutive_count += 1
        self.total_count += 1
        
        # Check trip conditions
        tripped = False
        reason = None
        
        # Condition 1: Too many consecutive alerts
        if self.consecutive_count >= self.max_consecutive:
            tripped = True
            reason = f"Consecutive critical states: {self.consecutive_count}"
            
        # Condition 2: Too many total alerts
        elif self.total_count >= self.max_total:
            tripped = True
            reason = f"Total critical states exceeded: {self.total_count}"
        
        # Condition 3: Rapid oscillation (same 2 states back-and-forth)
        elif self._detect_oscillation():
            tripped = True
            reason = "Oscillation detected between critical states"
        
        if tripped:
            self.tripped = True
            self.trip_reason = reason
        
        return self._get_status()
    
    def _detect_oscillation(self) -> bool:
        """
        Detect if agent is oscillating between states.
        
        Pattern: A → B → A → B (even if interrupted by NONE)
        
        WHY: This indicates protocols are fighting each other.
        """
        if len(self.alert_history) < 4:
            return False
        
        # Look at last 4 non-NONE states
        recent = [s for s in self.alert_history[-6:] if s != CriticalState.NONE]
        
        if len(recent) >= 4:
            # Check for A-B-A-B pattern
            if (recent[-4] == recent[-2] and 
                recent[-3] == recent[-1] and 
                recent[-4] != recent[-3]):
                return True
        
        return False
    
    def _get_status(self) -> CircuitBreakerStatus:
        """Get current status of circuit breaker."""
        # Analyze thrashing pattern
        pattern = self._analyze_pattern()
        
        # Get diagnostic info
        diagnostics = {
            'trip_reason': self.trip_reason,
            'state_frequency': self._get_state_frequency(),
            'last_5_states': [s.value for s in self.alert_history[-5:]],
            'recommendations': self._get_recommendations()
        }
        
        return CircuitBreakerStatus(
            tripped=self.tripped,
            consecutive_alerts=self.consecutive_count,
            total_alerts=self.total_count,
            alert_history=[s.value for s in self.alert_history[-10:]],
            thrashing_pattern=pattern,
            diagnostic_info=diagnostics
        )
    
    def _analyze_pattern(self) -> Optional[str]:
        """
        Analyze the pattern of critical states.
        
        Returns human-readable description of the problem.
        """
        if not self.alert_history:
            return None
        
        # Count occurrences
        counter = Counter(self.alert_history)
        most_common = counter.most_common(2)
        
        if len(most_common) == 1:
            # Single repeated state
            state, count = most_common[0]
            return f"Repeated {state.value} ({count} times)"
        
        elif len(most_common) >= 2:
            # Multiple states
            state1, count1 = most_common[0]
            state2, count2 = most_common[1]
            
            if count1 == count2:
                return f"Oscillating between {state1.value} and {state2.value}"
            else:
                return f"Primarily {state1.value} ({count1}x) with some {state2.value} ({count2}x)"
        
        return "Multiple different states"
    
    def _get_state_frequency(self) -> Dict[str, int]:
        """Get frequency count of each state."""
        counter = Counter(self.alert_history)
        return {state.value: count for state, count in counter.items()}
    
    def _get_recommendations(self) -> List[str]:
        """
        Generate recommendations based on thrashing pattern.
        
        WHY: Help user debug what went wrong.
        """
        if not self.tripped:
            return []
        
        recommendations = []
        counter = Counter(self.alert_history)
        
        # Specific recommendations by state
        if counter[CriticalState.DEADLOCK] >= 3:
            recommendations.append(
                "High DEADLOCK count: Consider adding more diverse tools/actions"
            )
        
        if counter[CriticalState.PANIC] >= 3:
            recommendations.append(
                "High PANIC count: Query may be too vague or contradictory"
            )
        
        if counter[CriticalState.HUBRIS] >= 2:
            recommendations.append(
                "Multiple HUBRIS triggers: Agent may need lower confidence threshold"
            )
        
        if counter[CriticalState.SCARCITY] >= 2:
            recommendations.append(
                "Multiple SCARCITY triggers: Increase token/step budget"
            )
        
        # Oscillation recommendation
        if self._detect_oscillation():
            recommendations.append(
                "Oscillation detected: Protocols may have conflicting priorities"
            )
        
        if not recommendations:
            recommendations.append(
                "General thrashing: Consider simplifying the query or adding more context"
            )
        
        return recommendations
    
    def reset(self):
        """
        Reset the circuit breaker.
        
        WHY: For new sessions or after fixing the issue.
        """
        self.consecutive_count = 0
        self.total_count = 0
        self.alert_history = []
        self.tripped = False
        self.trip_reason = None
    
    def __str__(self):
        """Human-readable status."""
        if self.tripped:
            return f"CIRCUIT BREAKER TRIPPED: {self.trip_reason}"
        else:
            return f"Circuit Breaker: {self.consecutive_count}/{self.max_consecutive} consecutive, {self.total_count}/{self.max_total} total"


# Demo
if __name__ == "__main__":
    print("=== CIRCUIT BREAKER DEMO ===\n")
    
    breaker = CircuitBreaker(max_consecutive_alerts=3)
    
    # Scenario 1: Consecutive failures
    print("1. Consecutive Failures (RED TEAM):")
    for i in range(4):
        status = breaker.record_critical_state(CriticalState.DEADLOCK)
        print(f"   Alert {i+1}: {breaker}")
        
        if status.tripped:
            print(f"\n   🚨 TRIPPED: {status.diagnostic_info['trip_reason']}")
            print(f"   Pattern: {status.thrashing_pattern}")
            print(f"   Recommendations:")
            for rec in status.diagnostic_info['recommendations']:
                print(f"     - {rec}")
            break
    
    # Scenario 2: Oscillation
    print("\n2. Oscillation Pattern (RED TEAM):")
    breaker.reset()
    
    pattern = [
        CriticalState.PANIC,
        CriticalState.DEADLOCK,
        CriticalState.PANIC,
        CriticalState.DEADLOCK,
    ]
    
    for state in pattern:
        status = breaker.record_critical_state(state)
        print(f"   State: {state.value}, Consecutive: {status.consecutive_alerts}")
    
    if status.tripped:
        print(f"\n   🚨 TRIPPED: {status.diagnostic_info['trip_reason']}")
        print(f"   Pattern: {status.thrashing_pattern}")
    
    # Scenario 3: Healthy operation with NONE resets
    print("\n3. Healthy Operation (resets work):")
    breaker.reset()
    
    healthy_pattern = [
        CriticalState.PANIC,
        CriticalState.NONE,  # Recovery
        CriticalState.NONE,
        CriticalState.DEADLOCK,
        CriticalState.NONE,  # Recovery
    ]
    
    for state in healthy_pattern:
        status = breaker.record_critical_state(state)
        if state == CriticalState.NONE:
            print(f"   ✓ Recovery: consecutive reset to {status.consecutive_alerts}")
    
    print(f"\n   Final state: {breaker}")
    print(f"   Tripped: {status.tripped}")
    
    print("\n=== WHY THIS MATTERS ===")
    print("✓ Baseline agents thrash forever")
    print("✓ Masks the real problem with activity")
    print("✓ Circuit breaker HALTS and provides diagnostics")
    print("✓ Aphorism #23: 'A dead agent is better than a thrashing agent'")
