"""Evidence items emitted by tools and validators (v2)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Evidence:
    """A single evidence record suitable for auditing and verification."""

    evidence_id: str
    kind: str
    payload: Any
    created_at: float = field(default_factory=time.time)

