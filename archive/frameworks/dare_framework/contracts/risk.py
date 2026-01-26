"""Risk level taxonomy used by security/policy and tool envelopes (v2)."""

from __future__ import annotations

from enum import Enum


class RiskLevel(Enum):
    """Risk level classification for capabilities that may have side effects."""

    READ_ONLY = "read_only"
    IDEMPOTENT_WRITE = "idempotent_write"
    NON_IDEMPOTENT_EFFECT = "non_idempotent_effect"
    COMPENSATABLE = "compensatable"

