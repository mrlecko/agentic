"""
Prometheus Metrics for Hardened Agent

Provides metrics for monitoring:
- Agent execution (steps, completions)
- Critical states (activations by type)
- Protocol overrides (by protocol)
- Circuit breaker trips
- LLM performance (latency, tokens)
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from typing import Optional
import time

class AgentMetrics:
    """
    Prometheus metrics for the Hardened Agent.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        
        # Agent execution metrics
        self.steps_total = Counter(
            'agent_steps_total',
            'Total steps executed by agent',
            ['agent_type', 'session_id'],
            registry=self.registry
        )
        
        self.completions_total = Counter(
            'agent_completions_total',
            'Total agent completions',
            ['agent_type', 'outcome'],
            registry=self.registry
        )
        
        # Critical state metrics
        self.critical_states_total = Counter(
            'agent_critical_states_total',
            'Critical state activations',
            ['state', 'session_id'],
            registry=self.registry
        )
        
        # Protocol override metrics
        self.protocol_overrides_total = Counter(
            'agent_protocol_overrides_total',
            'Protocol override activations',
            ['protocol', 'session_id'],
            registry=self.registry
        )
        
        # Circuit breaker metrics
        self.circuit_breaker_trips_total = Counter(
            'circuit_breaker_trips_total',
            'Circuit breaker trip events',
            ['reason'],
            registry=self.registry
        )
        
        # LLM performance metrics
        self.llm_latency_seconds = Histogram(
            'agent_llm_latency_seconds',
            'LLM call latency in seconds',
            ['agent_type'],
            registry=self.registry
        )
        
        self.token_usage_total = Counter(
            'agent_token_usage_total',
            'Total tokens consumed',
            ['agent_type', 'session_id'],
            registry=self.registry
        )
        
        # Current state gauge
        self.current_state = Gauge(
            'agent_current_state',
            'Current agent state (0=NONE, 1=DEADLOCK, 2=PANIC, 3=HUBRIS, 4=SCARCITY, 5=NOVELTY)',
            ['session_id'],
            registry=self.registry
        )
    
    def record_step(self, agent_type: str, session_id: str):
        """Record a step execution."""
        self.steps_total.labels(agent_type=agent_type, session_id=session_id).inc()
    
    def record_completion(self, agent_type: str, outcome: str):
        """Record agent completion."""
        self.completions_total.labels(agent_type=agent_type, outcome=outcome).inc()
    
    def record_critical_state(self, state: str, session_id: str):
        """Record critical state activation."""
        self.critical_states_total.labels(state=state, session_id=session_id).inc()
        
        # Update current state gauge
        state_map = {
            "NONE": 0,
            "DEADLOCK": 1,
            "PANIC": 2,
            "HUBRIS": 3,
            "SCARCITY": 4,
            "NOVELTY": 5
        }
        self.current_state.labels(session_id=session_id).set(state_map.get(state, 0))
    
    def record_protocol_override(self, protocol: str, session_id: str):
        """Record protocol override."""
        self.protocol_overrides_total.labels(protocol=protocol, session_id=session_id).inc()
    
    def record_circuit_breaker_trip(self, reason: str):
        """Record circuit breaker trip."""
        self.circuit_breaker_trips_total.labels(reason=reason).inc()
    
    def record_llm_latency(self, agent_type: str, latency_seconds: float):
        """Record LLM call latency."""
        self.llm_latency_seconds.labels(agent_type=agent_type).observe(latency_seconds)
    
    def record_token_usage(self, agent_type: str, session_id: str, tokens: int):
        """Record token usage."""
        self.token_usage_total.labels(agent_type=agent_type, session_id=session_id).inc(tokens)
    
    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry)

# Global metrics instance
_metrics: Optional[AgentMetrics] = None

def get_metrics() -> AgentMetrics:
    """Get or create global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = AgentMetrics()
    return _metrics

# Context manager for timing LLM calls
class llm_timer:
    """Context manager to time LLM calls."""
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, *args):
        if self.start_time:
            latency = time.time() - self.start_time
            get_metrics().record_llm_latency(self.agent_type, latency)

# Demo
if __name__ == "__main__":
    print("=== Prometheus Metrics Demo ===\n")
    
    metrics = get_metrics()
    
    # Simulate agent execution
    metrics.record_step("HardenedAgent", "session-123")
    metrics.record_critical_state("DEADLOCK", "session-123")
    metrics.record_protocol_override("DEADLOCK", "session-123")
    
    # Simulate LLM call
    with llm_timer("HardenedAgent"):
        time.sleep(0.1)  # Simulate LLM call
    
    metrics.record_token_usage("HardenedAgent", "session-123", 150)
    metrics.record_completion("HardenedAgent", "success")
    
    # Print metrics
    print(metrics.get_metrics().decode('utf-8'))
