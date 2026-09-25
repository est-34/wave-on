"""Compatibility alias for the relocated implementation."""

import sys
from ..modules.agent.domain import gesture_encoder as implementation

sys.modules[__name__] = implementation
