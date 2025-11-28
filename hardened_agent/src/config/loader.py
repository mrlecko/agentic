"""
Configuration Loader

Loads and validates configuration from YAML file.
Provides defaults if config is missing or invalid.
"""

import yaml
import os
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

@dataclass
class AgentConfig:
    max_steps: int = 10
    token_budget: int = 1000

@dataclass
class CriticalStatesConfig:
    panic_threshold: float = 0.4
    hubris_threshold: float = 0.9
    deadlock_window: int = 3
    scarcity_token_threshold: float = 0.8
    scarcity_step_threshold: float = 0.8

@dataclass
class CircuitBreakerConfig:
    consecutive_limit: int = 3
    total_limit: int = 10
    oscillation_window: int = 4

@dataclass
class ObservabilityConfig:
    log_level: str = "INFO"
    metrics_enabled: bool = True
    metrics_port: int = 8000

@dataclass
class HardenedAgentConfig:
    """Complete configuration for Hardened Agent."""
    agent: AgentConfig = field(default_factory=AgentConfig)
    critical_states: CriticalStatesConfig = field(default_factory=CriticalStatesConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    
    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "HardenedAgentConfig":
        """Load config from YAML file."""
        if not os.path.exists(path):
            print(f"Warning: Config file {path} not found, using defaults")
            return cls()
        
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f) or {}
            
            return cls(
                agent=AgentConfig(**data.get('agent', {})),
                critical_states=CriticalStatesConfig(**data.get('critical_states', {})),
                circuit_breaker=CircuitBreakerConfig(**data.get('circuit_breaker', {})),
                observability=ObservabilityConfig(**data.get('observability', {}))
            )
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")
            return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'agent': self.agent.__dict__,
            'critical_states': self.critical_states.__dict__,
            'circuit_breaker': self.circuit_breaker.__dict__,
            'observability': self.observability.__dict__
        }

# Global config instance
_config: Optional[HardenedAgentConfig] = None

def load_config(path: str = "config.yaml") -> HardenedAgentConfig:
    """Load or reload configuration."""
    global _config
    _config = HardenedAgentConfig.from_yaml(path)
    return _config

def get_config() -> HardenedAgentConfig:
    """Get current configuration."""
    global _config
    if _config is None:
        _config = load_config()
    return _config

# Demo
if __name__ == "__main__":
    print("=== Configuration Loader Demo ===\n")
    
    # Load config
    config = load_config()
    
    # Print config
    import json
    print(json.dumps(config.to_dict(), indent=2))
    
    # Access config values
    print(f"\nMax Steps: {config.agent.max_steps}")
    print(f"PANIC Threshold: {config.critical_states.panic_threshold}")
    print(f"Circuit Breaker Limit: {config.circuit_breaker.consecutive_limit}")
    print(f"Log Level: {config.observability.log_level}")
