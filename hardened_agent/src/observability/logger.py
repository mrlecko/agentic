"""
Structured Logging for Hardened Agent

Provides context-aware JSON logging for all critical events:
- State transitions
- Protocol activations
- Circuit breaker trips
- Agent lifecycle events
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class StructuredLogger:
    """
    JSON-formatted logger with context awareness.
    """
    
    def __init__(self, name: str = "hardened_agent", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))
        
        # JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self._create_formatter())
        self.logger.addHandler(handler)
        
        # Context (session_id, agent_id, etc.)
        self.context: Dict[str, Any] = {}
    
    def _create_formatter(self):
        """Create JSON log formatter."""
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                
                # Add extra fields if present
                if hasattr(record, 'context'):
                    log_data.update(record.context)
                
                return json.dumps(log_data)
        
        return JSONFormatter()
    
    def set_context(self, **kwargs):
        """Set context for all subsequent logs."""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear context."""
        self.context = {}
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal log method."""
        context = {**self.context, **kwargs}
        extra = {'context': context}
        getattr(self.logger, level.lower())(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log("CRITICAL", message, **kwargs)
    
    # Domain-specific log methods
    
    def log_state_transition(self, from_state: str, to_state: str, 
                            confidence: float, reasoning: str):
        """Log critical state transition."""
        self.info(
            f"State transition: {from_state} -> {to_state}",
            event_type="state_transition",
            from_state=from_state,
            to_state=to_state,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def log_protocol_activation(self, protocol: str, action: str, 
                                metadata: Dict[str, Any]):
        """Log protocol override."""
        self.warning(
            f"Protocol activated: {protocol}",
            event_type="protocol_activation",
            protocol=protocol,
            action=action,
            metadata=metadata
        )
    
    def log_circuit_breaker_trip(self, reason: str, diagnostics: Dict[str, Any]):
        """Log circuit breaker trip."""
        self.critical(
            f"Circuit breaker tripped: {reason}",
            event_type="circuit_breaker_trip",
            reason=reason,
            diagnostics=diagnostics
        )
    
    def log_agent_start(self, agent_type: str, goal: str):
        """Log agent start."""
        self.info(
            f"Agent started: {agent_type}",
            event_type="agent_start",
            agent_type=agent_type,
            goal=goal
        )
    
    def log_agent_complete(self, result: str, steps: int, tokens: int):
        """Log agent completion."""
        self.info(
            f"Agent completed in {steps} steps",
            event_type="agent_complete",
            result=result,
            steps=steps,
            tokens=tokens
        )

# Global logger instance
_logger: Optional[StructuredLogger] = None

def get_logger(name: str = "hardened_agent", level: str = "INFO") -> StructuredLogger:
    """Get or create global logger instance."""
    global _logger
    if _logger is None:
        _logger = StructuredLogger(name, level)
    return _logger

# Demo
if __name__ == "__main__":
    logger = get_logger(level="DEBUG")
    logger.set_context(session_id="test-123", agent_id="agent-1")
    
    print("=== Structured Logging Demo ===\n")
    
    logger.log_agent_start("HardenedAgent", "Find the answer")
    logger.log_state_transition("NONE", "DEADLOCK", 0.95, "Loop detected")
    logger.log_protocol_activation("DEADLOCK", "force_different_tool", {"loop_count": 3})
    logger.log_circuit_breaker_trip("Too many PANIC states", {"pattern": ["PANIC", "PANIC", "PANIC"]})
    logger.log_agent_complete("Synthesized answer", 10, 500)
