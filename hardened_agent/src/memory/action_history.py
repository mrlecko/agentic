"""
Action History: Track agent actions and detect loops

WHY THIS IS MORE ROBUST THAN BASELINE:
- Baseline agents: No action tracking, repeat mistakes forever
- Hardened agent: Full history + pattern detection + deterministic loop breaking

RED TEAM DESIGN:
- Detects exact loops (A → A → A)
- Detects cycle loops (A → B → A → B)
- Configurable threshold (prevents false positives)
- Session isolation (multiple conversations don't interfere)
- Fast queries (indexed by session_id and timestamp)
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class LoopPattern(Enum):
    """Types of loops we can detect."""
    EXACT_REPEAT = "exact_repeat"  # A → A → A
    CYCLE = "cycle"                # A → B → A → B
    SIMILARITY = "similarity"       # Similar but not identical


@dataclass
class LoopDetection:
    """Result of loop detection."""
    pattern_type: LoopPattern
    confidence: float  # 0.0 to 1.0
    description: str
    detected_sequence: List[str]
    
    def __bool__(self):
        """Allow simple if loop: check."""
        return True


class ActionHistory:
    """
    Tracks all agent actions for loop detection and analysis.
    
    This is the MEMORY that prevents the agent from repeating mistakes.
    Aphorism #37: "History vetoes feelings"
    """
    
    def __init__(self, db_path: str = "action_history.db"):
        """
        Initialize action history with SQLite backend.
        
        Args:
            db_path: Path to database file, or ":memory:" for testing
        """
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self._create_table()
    
    def _create_table(self):
        """Create action history table with indexes."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tool TEXT NOT NULL,
                args TEXT NOT NULL,
                result TEXT,
                tokens_used INTEGER,
                session_id TEXT NOT NULL
            )
        """)
        
        # Index for fast session queries
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_timestamp 
            ON actions(session_id, timestamp DESC)
        """)
        
        self.conn.commit()
    
    def record_action(self, 
                     tool: str, 
                     args: str, 
                     result: str, 
                     tokens: int, 
                     session_id: str):
        """
        Record an action to history.
        
        WHY: Every action is logged for loop detection and debugging.
        """
        self.conn.execute("""
            INSERT INTO actions (timestamp, tool, args, result, tokens_used, session_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            tool,
            args,
            result,
            tokens,
            session_id
        ))
        self.conn.commit()
    
    def get_recent_actions(self, session_id: str, n: int = 10) -> List[Dict]:
        """
        Get the last N actions for this session.
        
        Returns:
            List of actions (most recent first)
        """
        cursor = self.conn.execute("""
            SELECT * FROM actions 
            WHERE session_id = ? 
            ORDER BY id DESC 
            LIMIT ?
        """, (session_id, n))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def detect_loop(self, 
                   session_id: str, 
                   window: int = 5,
                   threshold: int = 3) -> Optional[LoopDetection]:
        """
        Detect if the agent is in a loop.
        
        Args:
            session_id: Session to check
            window: How many recent actions to examine
            threshold: Minimum repeats to call it a loop (default: 3)
        
        Returns:
            LoopDetection if loop found, None otherwise
        
        WHY THIS DETECTION STRATEGY:
        1. Exact repeats: Most common failure mode
        2. Cycle detection: Second most common
        3. Threshold of 3: Prevents false positives from occasional repeats
        """
        actions = self.get_recent_actions(session_id, window)
        
        if len(actions) < threshold:
            return None  # Not enough history
        
        # Extract tool+args pairs (most recent first)
        signatures = [
            (action['tool'], action['args'])
            for action in actions
        ]
        
        # Check for exact repetition (highest priority)
        loop = self._detect_exact_loop(signatures, threshold)
        if loop:
            return loop
        
        # Check for cycle pattern
        loop = self._detect_cycle_loop(signatures, threshold)
        if loop:
            return loop
        
        return None
    
    def _detect_exact_loop(self, 
                          signatures: List[tuple], 
                          threshold: int) -> Optional[LoopDetection]:
        """
        Detect exact repetition: A → A → A
        
        RED TEAM: This is the most common failure mode.
        Baseline agents get stuck saying "let me search..." forever.
        """
        if len(signatures) < threshold:
            return None
        
        # Check if first N are all the same
        first = signatures[0]
        repeat_count = 1
        
        for sig in signatures[1:]:
            if sig == first:
                repeat_count += 1
                if repeat_count >= threshold:
                    # LOOP DETECTED
                    return LoopDetection(
                        pattern_type=LoopPattern.EXACT_REPEAT,
                        confidence=1.0,
                        description=f"Exact repetition: {first[0]}('{first[1]}') × {repeat_count}",
                        detected_sequence=[f"{s[0]}({s[1]})" for s in signatures[:repeat_count]]
                    )
            else:
                break  # Not a continuous run
        
        return None
    
    def _detect_cycle_loop(self, 
                          signatures: List[tuple], 
                          threshold: int) -> Optional[LoopDetection]:
        """
        Detect cycle pattern: A → B → A → B
        
        RED TEAM: Smarter agents oscillate between two actions.
        Example: search → synthesize → search → synthesize → ...
        """
        if len(signatures) < 4:
            return None  # Need at least 4 for a 2-cycle
        
        # Check for 2-cycle (most common)
        if len(signatures) >= 4:
            # Pattern should be: A, B, A, B, ...
            if (signatures[0] == signatures[2] and 
                signatures[1] == signatures[3] and
                signatures[0] != signatures[1]):
                
                # Check if it continues
                cycle_length = 0
                for i in range(0, min(len(signatures) - 1, 6), 2):
                    if i + 1 < len(signatures):
                        if (signatures[i] == signatures[0] and 
                            signatures[i + 1] == signatures[1]):
                            cycle_length += 1
                        else:
                            break
                
                if cycle_length >= 2:  # At least 2 full cycles
                    return LoopDetection(
                        pattern_type=LoopPattern.CYCLE,
                        confidence=0.9,
                        description=f"2-cycle: {signatures[0][0]} ↔ {signatures[1][0]} ({cycle_length} cycles)",
                        detected_sequence=[f"{s[0]}({s[1]})" for s in signatures[:cycle_length * 2]]
                    )
        
        # Check for 3-cycle (less common): A → B → C → A → B → C
        if len(signatures) >= 6:
            # Check if pattern repeats: positions 0,1,2 match 3,4,5
            if (signatures[0] == signatures[3] and
                signatures[1] == signatures[4] and
                signatures[2] == signatures[5]):
                
                # Ensure they're actually different from each other
                if not (signatures[0] == signatures[1] == signatures[2]):
                    return LoopDetection(
                        pattern_type=LoopPattern.CYCLE,
                        confidence=0.85,
                        description=f"3-cycle: {signatures[0][0]} → {signatures[1][0]} → {signatures[2][0]}",
                        detected_sequence=[f"{s[0]}({s[1]})" for s in signatures[:6]]
                    )
        
        return None
    
    def get_token_usage(self, session_id: str) -> int:
        """Get total tokens used in this session."""
        cursor = self.conn.execute("""
            SELECT SUM(tokens_used) as total
            FROM actions
            WHERE session_id = ?
        """, (session_id,))
        
        result = cursor.fetchone()
        return result['total'] if result['total'] is not None else 0
    
    def get_action_count(self, session_id: str) -> int:
        """Get total number of actions in this session."""
        cursor = self.conn.execute("""
            SELECT COUNT(*) as count
            FROM actions
            WHERE session_id = ?
        """, (session_id,))
        
        result = cursor.fetchone()
        return result['count']
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        """Context manager support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support."""
        self.close()


# Demo
if __name__ == "__main__":
    print("=== ACTION HISTORY DEMO ===\n")
    
    with ActionHistory(":memory:") as history:
        session = "demo-session"
        
        # Simulate normal exploration
        print("1. Normal exploration (no loop):")
        for action in ["search", "synthesize", "verify"]:
            history.record_action(action, "args", "result", 100, session)
        
        loop = history.detect_loop(session)
        print(f"   Loop detected: {loop}\n")
        
        # Simulate exact loop
        print("2. Exact repetition loop (RED TEAM):")
        session2 = "loop-session"
        for _ in range(4):
            history.record_action("search", "same query", "result", 100, session2)
        
        loop = history.detect_loop(session2)
        if loop:
            print(f"   ✓ DETECTED: {loop.description}")
            print(f"   Pattern type: {loop.pattern_type.value}")
            print(f"   Confidence: {loop.confidence}\n")
        
        # Simulate cycle loop
        print("3. Cycle loop (RED TEAM):")
        session3 = "cycle-session"
        for _ in range(3):
            history.record_action("search", "q", "r", 100, session3)
            history.record_action("synthesize", "s", "r", 100, session3)
        
        loop = history.detect_loop(session3)
        if loop:
            print(f"   ✓ DETECTED: {loop.description}")
            print(f"   Pattern type: {loop.pattern_type.value}\n")
        
        print("=== WHY THIS MATTERS ===")
        print("✓ Baseline agents have NO loop detection")
        print("✓ They repeat the same mistake forever")
        print("✓ This gives us deterministic loop breaking")
        print("✓ Aphorism #7: 'Insanity is doing the same thing over and over'")
