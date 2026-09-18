"""Compatibility alias for the relocated implementation."""

import sys
from ..adapters import action_executor as implementation

sys.modules[__name__] = implementation
