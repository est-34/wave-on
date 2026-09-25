"""Compatibility alias for the relocated implementation."""

import sys
from ..adapters import input_observer as implementation

sys.modules[__name__] = implementation
