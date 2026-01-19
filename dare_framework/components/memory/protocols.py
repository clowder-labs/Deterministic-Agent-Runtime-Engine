"""Component-facing memory protocol re-export (v2).

The Kernel depends on the shared `contracts/` definition of `IMemory`. This module
re-exports the contract so memory component code can keep a stable import path.
"""

from __future__ import annotations

from dare_framework.contracts.memory import IMemory

__all__ = ["IMemory"]
