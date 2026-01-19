"""Entrypoint-based plugin loading utilities (v2).

This package implements the *mechanism* for discovering and selecting pluggable
components via Python entrypoints.

Layering note:
- Kernel (Layer 0) MUST NOT import this package.
- Builder/composition code MAY use it to assemble Layer 2 components deterministically.
"""
