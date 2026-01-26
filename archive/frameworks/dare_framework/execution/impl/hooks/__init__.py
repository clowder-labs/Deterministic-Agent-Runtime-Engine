"""Hook components (Layer 2)."""

from .protocols import IHook
from .noop import NoOpHook
from .stdout import StdoutHook

__all__ = ["IHook", "NoOpHook", "StdoutHook"]

