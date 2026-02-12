"""Decision arbitration for governed hook results."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from dare_framework.hook.types import HookResult

_PRECEDENCE = {"allow": 0, "ask": 1, "block": 2}


def _to_payload(result: dict[str, Any] | HookResult) -> dict[str, Any]:
    if isinstance(result, HookResult):
        payload = asdict(result)
        payload["decision"] = result.decision.value
        return payload
    if is_dataclass(result):
        return asdict(result)
    return dict(result)


def arbitrate(results: list[dict[str, Any] | HookResult]) -> dict[str, Any]:
    """Choose one decision using precedence: block > ask > allow."""

    if not results:
        return {"decision": "allow"}

    winner = _to_payload(results[0])
    winner_rank = _PRECEDENCE.get(str(winner.get("decision", "allow")).lower(), 0)
    for candidate in results[1:]:
        payload = _to_payload(candidate)
        rank = _PRECEDENCE.get(str(payload.get("decision", "allow")).lower(), 0)
        if rank > winner_rank:
            winner = payload
            winner_rank = rank
    winner["decision"] = str(winner.get("decision", "allow")).lower()
    return winner


__all__ = ["arbitrate"]
