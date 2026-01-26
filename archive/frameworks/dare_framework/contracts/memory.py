"""Memory capability contract (v2).

Compatibility note:
- `IMemory` is defined in `dare_framework.context.components` to align with the
  domain architecture. This module re-exports it for legacy imports.
"""

from __future__ import annotations

from dare_framework.context.components import IMemory

__all__ = ["IMemory"]
