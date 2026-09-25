"""Compatibility alias for the relocated implementation."""

import sys
from ..modules.agent.domain import action_catalog as implementation

sys.modules[__name__] = implementation
