"""
The Silver Gauge: Geometry of Decision Making

WHY THIS IS MORE ROBUST:
- Baseline: Opaque float scores (0.87).
- Hardened: Geometric relationship between Goal Value (G) and Info Gain (I).
- Reveals WHY an action was chosen (Specialist vs Generalist).

FORMULA:
k_explore = HarmonicMean(G, I) / ArithmeticMean(G, I)

INTERPRETATION:
- k ≈ 1.0: GENERALIST (Balanced G and I)
- k << 1.0: SPECIALIST (Imbalanced, e.g. high G low I)

Aphorism #53: "First Principles First"
"""

import math
from dataclasses import dataclass
from enum import Enum

class ActionType(Enum):
    GENERALIST = "generalist"   # Balanced approach
    SPECIALIST = "specialist"   # Focused approach (or imbalanced)
    UNKNOWN = "unknown"

@dataclass
class GaugeReading:
    g_val: float
    i_val: float
    hm: float
    am: float
    k_explore: float
    action_type: ActionType
    description: str

class SilverGauge:
    """
    Diagnostic tool to measure the 'geometry' of an action.
    """
    
    @staticmethod
    def calculate(g_val: float, i_val: float) -> GaugeReading:
        """
        Calculate the Silver Gauge reading.
        
        Args:
            g_val: Goal Value (0.0 to 1.0)
            i_val: Information Gain (0.0 to 1.0)
        """
        # Clamp inputs
        g = max(0.001, min(1.0, g_val))
        i = max(0.001, min(1.0, i_val))
        
        # Pythagorean Means
        am = (g + i) / 2.0
        hm = (2 * g * i) / (g + i)
        
        # k_explore ratio
        # If AM is 0, k is defined as 0 (though clamped inputs prevent this)
        k = hm / am if am > 0 else 0.0
        
        # Classification
        # k=1.0 means G=I (Perfect balance)
        # k decreases as G and I diverge
        # Threshold: 0.8 is a reasonable cut-off for "balanced"
        action_type = ActionType.GENERALIST if k >= 0.8 else ActionType.SPECIALIST
        
        # Description
        if action_type == ActionType.GENERALIST:
            desc = "Balanced action (Generalist)"
        else:
            if g > i:
                desc = "Goal-focused action (Specialist)"
            else:
                desc = "Exploration-focused action (Specialist)"
                
        return GaugeReading(
            g_val=g,
            i_val=i,
            hm=hm,
            am=am,
            k_explore=k,
            action_type=action_type,
            description=desc
        )

# Demo
if __name__ == "__main__":
    print("=== SILVER GAUGE DEMO ===\n")
    
    scenarios = [
        (0.9, 0.9), # Perfectly balanced
        (0.9, 0.1), # High Goal, Low Info (Specialist)
        (0.1, 0.9), # Low Goal, High Info (Specialist)
        (0.5, 0.5), # Balanced but mediocre
        (0.7, 0.6), # Roughly balanced
    ]
    
    print(f"{'G':<5} {'I':<5} {'k':<6} {'Type':<12} {'Description'}")
    print("-" * 50)
    
    for g, i in scenarios:
        reading = SilverGauge.calculate(g, i)
        print(f"{g:<5.1f} {i:<5.1f} {reading.k_explore:<6.3f} {reading.action_type.value:<12} {reading.description}")
