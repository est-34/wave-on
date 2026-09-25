"""Legacy Session-based entry points. New callers use modules.agent.api."""

from ..bootstrap import build_agent_dependencies
from ..modules.agent.application import intent_reasoner as implementation


def infer_intent(db, *args, **kwargs):
    return implementation.infer_intent(build_agent_dependencies(db), *args, **kwargs)
