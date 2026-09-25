"""Legacy Session-based entry points. New callers use modules.agent.api."""

from ..bootstrap import build_agent_dependencies
from ..modules.agent.application import feedback_service as implementation


def record_feedback(db, *args, **kwargs):
    return implementation.record_feedback(build_agent_dependencies(db), *args, **kwargs)
