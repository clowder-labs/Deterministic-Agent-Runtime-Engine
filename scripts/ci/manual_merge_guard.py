#!/usr/bin/env python3
"""Enforce manual review policy for PR merges into main (free-tier fallback)."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class ManualMergeDecision:
    is_eligible_event: bool
    is_compliant: bool
    reason: str
    pr_number: int | None
    author: str
    merger: str
    merge_commit_sha: str
    approved_reviewers: list[str]


def load_event(event_path: Path) -> dict:
    with event_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def parse_allow_mergers(raw: str) -> set[str]:
    return {item.strip() for item in raw.split(",") if item.strip()}


def _extract_latest_review_states(reviews: list[dict]) -> dict[str, str]:
    latest_state: dict[str, str] = {}
    for review in reviews:
        user = review.get("user") or {}
        login = str(user.get("login", "")).strip()
        state = str(review.get("state", "")).strip().upper()
        if not login:
            continue
        latest_state[login] = state
    return latest_state


def find_approved_reviewers(*, reviews: list[dict], author: str) -> list[str]:
    latest_states = _extract_latest_review_states(reviews)
    return sorted(
        reviewer
        for reviewer, state in latest_states.items()
        if state == "APPROVED" and reviewer != author
    )


def evaluate_merged_pr_event(
    *,
    event: dict,
    reviews: list[dict],
    allow_mergers: set[str],
) -> ManualMergeDecision:
    action = str(event.get("action", ""))
    pr = event.get("pull_request") or {}
    merged = bool(pr.get("merged"))
    base_ref = str((pr.get("base") or {}).get("ref", ""))

    pr_number = pr.get("number")
    if not isinstance(pr_number, int):
        pr_number = None

    author = str((pr.get("user") or {}).get("login", "")).strip()
    merger = str((pr.get("merged_by") or {}).get("login", "")).strip()
    merge_commit_sha = str(pr.get("merge_commit_sha", "")).strip()

    if action != "closed" or not merged or base_ref != "main":
        return ManualMergeDecision(
            is_eligible_event=False,
            is_compliant=True,
            reason="Ignoring non-merged-main pull_request close event.",
            pr_number=pr_number,
            author=author,
            merger=merger,
            merge_commit_sha=merge_commit_sha,
            approved_reviewers=[],
        )

    if merger and merger in allow_mergers:
        return ManualMergeDecision(
            is_eligible_event=True,
            is_compliant=True,
            reason=f"Ignoring enforcement for allowlisted merger: {merger}.",
            pr_number=pr_number,
            author=author,
            merger=merger,
            merge_commit_sha=merge_commit_sha,
            approved_reviewers=[],
        )

    approved_reviewers = find_approved_reviewers(reviews=reviews, author=author)
    has_independent_approval = bool(approved_reviewers)
    is_self_merge = bool(author and merger and author == merger)

    violations: list[str] = []
    if is_self_merge:
        violations.append("self-merge detected")
    if not has_independent_approval:
        violations.append("missing independent approval review")

    if violations:
        return ManualMergeDecision(
            is_eligible_event=True,
            is_compliant=False,
            reason="; ".join(violations),
            pr_number=pr_number,
            author=author,
            merger=merger,
            merge_commit_sha=merge_commit_sha,
            approved_reviewers=approved_reviewers,
        )

    return ManualMergeDecision(
        is_eligible_event=True,
        is_compliant=True,
        reason="Manual merge policy satisfied.",
        pr_number=pr_number,
        author=author,
        merger=merger,
        merge_commit_sha=merge_commit_sha,
        approved_reviewers=approved_reviewers,
    )


def fetch_pr_reviews(repository: str, pr_number: int, token: str) -> list[dict] | None:
    url = f"https://api.github.com/repos/{repository}/pulls/{pr_number}/reviews?per_page=100"
    request = urllib.request.Request(
        url=url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "manual-merge-guard",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError:
        return None
    except urllib.error.URLError:
        return None

    if isinstance(payload, list):
        return payload
    return None


def _write_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as fh:
        fh.write(f"{name}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True, type=Path, help="Path to GitHub event payload JSON.")
    parser.add_argument("--repository", required=True, help="owner/repo")
    parser.add_argument("--token", default="", help="GitHub token for PR review lookup.")
    parser.add_argument(
        "--allow-mergers",
        default="",
        help="Comma-separated merger allowlist for emergency bypass.",
    )
    args = parser.parse_args()

    event = load_event(args.event)
    pr = event.get("pull_request") or {}
    pr_number = pr.get("number")

    reviews: list[dict] = []
    lookup_failed = False
    if isinstance(pr_number, int):
        fetched = fetch_pr_reviews(args.repository, pr_number, args.token)
        if fetched is None:
            lookup_failed = True
        else:
            reviews = fetched

    decision = evaluate_merged_pr_event(
        event=event,
        reviews=reviews,
        allow_mergers=parse_allow_mergers(args.allow_mergers),
    )

    # Fail-open on API lookup failures to avoid accidental rollback on GitHub outage.
    if decision.is_eligible_event and lookup_failed:
        decision = ManualMergeDecision(
            is_eligible_event=True,
            is_compliant=True,
            reason="Skipping enforcement because PR review lookup failed.",
            pr_number=decision.pr_number,
            author=decision.author,
            merger=decision.merger,
            merge_commit_sha=decision.merge_commit_sha,
            approved_reviewers=[],
        )

    _write_output("is_eligible_event", "true" if decision.is_eligible_event else "false")
    _write_output("is_compliant", "true" if decision.is_compliant else "false")
    _write_output("needs_rollback", "true" if decision.is_eligible_event and not decision.is_compliant else "false")
    _write_output("reason", decision.reason)
    _write_output("pr_number", "" if decision.pr_number is None else str(decision.pr_number))
    _write_output("author", decision.author)
    _write_output("merger", decision.merger)
    _write_output("merge_commit_sha", decision.merge_commit_sha)
    _write_output("approved_reviewers", ",".join(decision.approved_reviewers))

    print(json.dumps(asdict(decision), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
