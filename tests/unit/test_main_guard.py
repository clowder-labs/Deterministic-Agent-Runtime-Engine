import json
import tempfile
from pathlib import Path

import pytest

from scripts.ci.main_guard import evaluate_push_event, load_event


def _base_event() -> dict:
    return {
        "ref": "refs/heads/main",
        "after": "a" * 40,
        "pusher": {"name": "dev-user"},
        "commits": [
            {"id": "a" * 40, "message": "normal commit"},
        ],
        "head_commit": {"id": "a" * 40, "message": "normal commit"},
    }


def test_load_event_reads_json_payload() -> None:
    payload = _base_event()
    with tempfile.TemporaryDirectory() as tmp_dir:
        event_path = Path(tmp_dir) / "event.json"
        event_path.write_text(json.dumps(payload), encoding="utf-8")
        assert load_event(event_path) == payload


def test_evaluate_returns_non_direct_for_non_main_ref() -> None:
    event = _base_event()
    event["ref"] = "refs/heads/feature/a"

    result = evaluate_push_event(
        event=event,
        repository="owner/repo",
        token="token",
        allow_actors=set(),
        allow_marker="[main-guard:allow-direct-push]",
        fetch_pr_numbers=lambda *_args, **_kwargs: [12],
    )

    assert result.is_direct_push is False
    assert "non-main" in result.reason


def test_evaluate_returns_non_direct_for_allowlisted_actor() -> None:
    event = _base_event()

    result = evaluate_push_event(
        event=event,
        repository="owner/repo",
        token="token",
        allow_actors={"dev-user"},
        allow_marker="[main-guard:allow-direct-push]",
        fetch_pr_numbers=lambda *_args, **_kwargs: pytest.fail(
            "fetch_pr_numbers should not run for allowlisted actor"
        ),
    )

    assert result.is_direct_push is False
    assert "allowlisted actor" in result.reason


def test_evaluate_returns_non_direct_for_allow_marker() -> None:
    event = _base_event()
    event["head_commit"]["message"] = "hotfix [main-guard:allow-direct-push]"

    result = evaluate_push_event(
        event=event,
        repository="owner/repo",
        token="token",
        allow_actors=set(),
        allow_marker="[main-guard:allow-direct-push]",
        fetch_pr_numbers=lambda *_args, **_kwargs: pytest.fail(
            "fetch_pr_numbers should not run for allow marker"
        ),
    )

    assert result.is_direct_push is False
    assert "allow marker" in result.reason


def test_evaluate_returns_non_direct_when_all_commits_have_pr() -> None:
    event = _base_event()
    event["commits"] = [
        {"id": "a" * 40, "message": "commit A"},
        {"id": "b" * 40, "message": "commit B"},
    ]
    event["after"] = "b" * 40
    fetched = []

    def _fetch(_repo: str, sha: str, _token: str) -> list[int]:
        fetched.append(sha)
        return [42]

    result = evaluate_push_event(
        event=event,
        repository="owner/repo",
        token="token",
        allow_actors=set(),
        allow_marker="[main-guard:allow-direct-push]",
        fetch_pr_numbers=_fetch,
    )

    assert fetched == ["a" * 40, "b" * 40]
    assert result.is_direct_push is False
    assert result.unlinked_commits == []


def test_evaluate_returns_direct_push_when_unlinked_commit_found() -> None:
    event = _base_event()
    event["commits"] = [
        {"id": "a" * 40, "message": "commit A"},
        {"id": "b" * 40, "message": "commit B"},
    ]
    event["after"] = "b" * 40

    def _fetch(_repo: str, sha: str, _token: str) -> list[int]:
        return [] if sha == "b" * 40 else [9]

    result = evaluate_push_event(
        event=event,
        repository="owner/repo",
        token="token",
        allow_actors=set(),
        allow_marker="[main-guard:allow-direct-push]",
        fetch_pr_numbers=_fetch,
    )

    assert result.is_direct_push is True
    assert result.unlinked_commits == ["b" * 40]
    assert "without associated PR" in result.reason


def test_evaluate_skips_enforcement_when_lookup_fails() -> None:
    event = _base_event()

    result = evaluate_push_event(
        event=event,
        repository="owner/repo",
        token="token",
        allow_actors=set(),
        allow_marker="[main-guard:allow-direct-push]",
        fetch_pr_numbers=lambda *_args, **_kwargs: None,
    )

    assert result.is_direct_push is False
    assert "lookup failed" in result.reason
