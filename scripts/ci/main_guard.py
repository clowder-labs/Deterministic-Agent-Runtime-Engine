#!/usr/bin/env python3
"""Detect and classify direct pushes to main by PR association metadata."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

HEX40_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(slots=True)
class GuardDecision:
    is_direct_push: bool
    reason: str
    commit_shas: list[str]
    associated_pr_numbers: list[int]
    unlinked_commits: list[str]


def load_event(event_path: Path) -> dict:
    with event_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def parse_allow_actors(raw: str) -> set[str]:
    actors = {item.strip() for item in raw.split(",") if item.strip()}
    return actors


def _is_valid_sha(value: str) -> bool:
    return bool(HEX40_RE.fullmatch(value.lower()))


def collect_commit_shas(event: dict) -> list[str]:
    # Push payload commits may be truncated; still include "after" SHA for latest commit.
    shas: list[str] = []
    seen: set[str] = set()

    for commit in event.get("commits", []):
        sha = str(commit.get("id", "")).strip().lower()
        if sha and _is_valid_sha(sha) and sha not in seen:
            seen.add(sha)
            shas.append(sha)

    after = str(event.get("after", "")).strip().lower()
    if after and _is_valid_sha(after) and after not in seen:
        shas.append(after)

    return shas


def has_allow_marker(event: dict, allow_marker: str) -> bool:
    if not allow_marker:
        return False

    head_commit = event.get("head_commit") or {}
    head_msg = str(head_commit.get("message", ""))
    if allow_marker in head_msg:
        return True

    for commit in event.get("commits", []):
        if allow_marker in str(commit.get("message", "")):
            return True
    return False


def fetch_associated_pr_numbers(repository: str, commit_sha: str, token: str) -> list[int] | None:
    url = f"https://api.github.com/repos/{repository}/commits/{commit_sha}/pulls"
    request = urllib.request.Request(
        url=url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "main-guard",
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

    numbers: list[int] = []
    for item in payload:
        number = item.get("number")
        if isinstance(number, int):
            numbers.append(number)
    return numbers


def evaluate_push_event(
    *,
    event: dict,
    repository: str,
    token: str,
    allow_actors: set[str],
    allow_marker: str,
    fetch_pr_numbers: Callable[[str, str, str], list[int] | None],
) -> GuardDecision:
    ref = str(event.get("ref", ""))
    if ref != "refs/heads/main":
        return GuardDecision(
            is_direct_push=False,
            reason="Ignoring non-main push ref.",
            commit_shas=[],
            associated_pr_numbers=[],
            unlinked_commits=[],
        )

    if bool(event.get("deleted")):
        return GuardDecision(
            is_direct_push=False,
            reason="Ignoring deleted ref event.",
            commit_shas=[],
            associated_pr_numbers=[],
            unlinked_commits=[],
        )

    actor = str((event.get("pusher") or {}).get("name", "")).strip()
    if actor and actor in allow_actors:
        return GuardDecision(
            is_direct_push=False,
            reason=f"Ignoring allowlisted actor: {actor}.",
            commit_shas=[],
            associated_pr_numbers=[],
            unlinked_commits=[],
        )

    if has_allow_marker(event, allow_marker):
        return GuardDecision(
            is_direct_push=False,
            reason=f"Ignoring push due to allow marker: {allow_marker}.",
            commit_shas=[],
            associated_pr_numbers=[],
            unlinked_commits=[],
        )

    commit_shas = collect_commit_shas(event)
    if not commit_shas:
        return GuardDecision(
            is_direct_push=False,
            reason="No commit SHAs found in push payload.",
            commit_shas=[],
            associated_pr_numbers=[],
            unlinked_commits=[],
        )

    associated_pr_numbers: set[int] = set()
    unlinked_commits: list[str] = []
    lookup_failed_commits: list[str] = []
    for sha in commit_shas:
        pr_numbers = fetch_pr_numbers(repository, sha, token)
        if pr_numbers is None:
            lookup_failed_commits.append(sha)
        elif pr_numbers:
            associated_pr_numbers.update(pr_numbers)
        else:
            unlinked_commits.append(sha)

    if lookup_failed_commits:
        return GuardDecision(
            is_direct_push=False,
            reason=(
                "Skipping enforcement because commit->PR lookup failed for at least one commit: "
                + ",".join(lookup_failed_commits)
            ),
            commit_shas=commit_shas,
            associated_pr_numbers=sorted(associated_pr_numbers),
            unlinked_commits=[],
        )

    if unlinked_commits:
        return GuardDecision(
            is_direct_push=True,
            reason=(
                f"Detected {len(unlinked_commits)} commit(s) on main without associated PR metadata."
            ),
            commit_shas=commit_shas,
            associated_pr_numbers=sorted(associated_pr_numbers),
            unlinked_commits=unlinked_commits,
        )

    return GuardDecision(
        is_direct_push=False,
        reason="All pushed commits are associated with at least one PR.",
        commit_shas=commit_shas,
        associated_pr_numbers=sorted(associated_pr_numbers),
        unlinked_commits=[],
    )


def _write_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return

    with open(output_path, "a", encoding="utf-8") as fh:
        fh.write(f"{name}={value}\n")


def _comma_join(values: list[str]) -> str:
    return ",".join(values)


def _int_join(values: list[int]) -> str:
    return ",".join(str(item) for item in values)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True, type=Path, help="Path to GitHub event payload JSON.")
    parser.add_argument("--repository", required=True, help="owner/repo")
    parser.add_argument("--token", default="", help="GitHub token for commit->PR lookup.")
    parser.add_argument(
        "--allow-actors",
        default="",
        help="Comma-separated allowlist of pusher actor names, e.g. release-bot,admin-user",
    )
    parser.add_argument(
        "--allow-marker",
        default="[main-guard:allow-direct-push]",
        help="Commit message marker that bypasses direct-push incident handling.",
    )
    args = parser.parse_args()

    event = load_event(args.event)
    decision = evaluate_push_event(
        event=event,
        repository=args.repository,
        token=args.token,
        allow_actors=parse_allow_actors(args.allow_actors),
        allow_marker=args.allow_marker,
        fetch_pr_numbers=fetch_associated_pr_numbers,
    )

    _write_output("is_direct_push", "true" if decision.is_direct_push else "false")
    _write_output("reason", decision.reason)
    _write_output("commit_shas", _comma_join(decision.commit_shas))
    _write_output("unlinked_commits", _comma_join(decision.unlinked_commits))
    _write_output("associated_pr_numbers", _int_join(decision.associated_pr_numbers))

    print(json.dumps(asdict(decision), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
