"""Compression utilities for context and memories.

- MovingCompressor: 移动窗口式 STM 压缩（LLM 摘要），见 moving_compression。
"""

from __future__ import annotations

from dare_framework.compression.moving_compression import MovingCompressor

__all__ = ["MovingCompressor"]

