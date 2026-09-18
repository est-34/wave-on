from dataclasses import dataclass


@dataclass
class AgentPolicy:
    suggestion_threshold: int = 3
    auto_execution_threshold: float = 0.60
    recency_half_life_days: float = 10.0
    confirm_feedback_window_seconds: int = 60
