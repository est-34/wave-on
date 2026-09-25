"""Legacy Session-based entry points. New callers use modules.agent.api."""

from ..bootstrap import build_agent_dependencies
from ..modules.agent.application import confirmation as implementation


def apply_confirmation(db, *args, **kwargs):
    return implementation.apply_confirmation(build_agent_dependencies(db), *args, **kwargs)


is_confirm_gesture = implementation.is_confirm_gesture
CONFIRM_GESTURES = implementation.CONFIRM_GESTURES
