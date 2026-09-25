"""Legacy Session-based entry points. New callers use modules.agent.api."""

from ..bootstrap import build_agent_dependencies
from ..modules.agent.application import pattern_learning as implementation


def record_user_action(db, *args, **kwargs):
    return implementation.record_user_action(build_agent_dependencies(db), *args, **kwargs)


def respond_to_suggestion(db, *args, **kwargs):
    return implementation.respond_to_suggestion(build_agent_dependencies(db), *args, **kwargs)


def check_intent_change(db, *args, **kwargs):
    return implementation.check_intent_change(build_agent_dependencies(db), *args, **kwargs)
