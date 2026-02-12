from scripts.ci.manual_merge_guard import evaluate_merged_pr_event


def _event(
    *,
    merged: bool = True,
    base_ref: str = "main",
    author: str = "alice",
    merger: str = "bob",
    pr_number: int = 71,
    merge_sha: str = "a" * 40,
) -> dict:
    return {
        "action": "closed",
        "pull_request": {
            "number": pr_number,
            "merged": merged,
            "base": {"ref": base_ref},
            "user": {"login": author},
            "merged_by": {"login": merger},
            "merge_commit_sha": merge_sha,
        },
    }


def test_non_main_close_event_is_ignored() -> None:
    decision = evaluate_merged_pr_event(
        event=_event(base_ref="feature/x"),
        reviews=[],
        allow_mergers=set(),
    )
    assert decision.is_eligible_event is False
    assert decision.is_compliant is True


def test_self_merge_is_non_compliant_even_with_approval() -> None:
    decision = evaluate_merged_pr_event(
        event=_event(author="alice", merger="alice"),
        reviews=[{"user": {"login": "bob"}, "state": "APPROVED"}],
        allow_mergers=set(),
    )
    assert decision.is_eligible_event is True
    assert decision.is_compliant is False
    assert "self-merge" in decision.reason


def test_missing_independent_approval_is_non_compliant() -> None:
    decision = evaluate_merged_pr_event(
        event=_event(author="alice", merger="bob"),
        reviews=[],
        allow_mergers=set(),
    )
    assert decision.is_compliant is False
    assert "approval" in decision.reason


def test_independent_approval_allows_merge() -> None:
    decision = evaluate_merged_pr_event(
        event=_event(author="alice", merger="bob"),
        reviews=[{"user": {"login": "charlie"}, "state": "APPROVED"}],
        allow_mergers=set(),
    )
    assert decision.is_compliant is True
    assert decision.approved_reviewers == ["charlie"]


def test_allowlisted_merger_can_bypass_gate() -> None:
    decision = evaluate_merged_pr_event(
        event=_event(author="alice", merger="alice"),
        reviews=[],
        allow_mergers={"alice"},
    )
    assert decision.is_compliant is True
    assert "allowlisted merger" in decision.reason
