"""Compression utilities for context and memories.

This module provides a single entrypoint, `compress_context`, which agents
and higher-level flows SHOULD use instead of直接操作 STM，以便集中管理上下文压缩策略。
"""

from __future__ import annotations

from .core import compress_context

__all__ = ["compress_context"]

