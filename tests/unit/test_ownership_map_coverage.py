"""Verify OWNERSHIP_MAP stays in sync with actual test files."""
from pathlib import Path

from scripts.ci.test_ownership_map import OWNERSHIP_MAP, is_pytest_discovery_file

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_all_test_files_have_ownership_entry():
    """Every pytest-discoverable test module must be present in OWNERSHIP_MAP."""
    actual = sorted(
        p.relative_to(REPO_ROOT).as_posix()
        for p in REPO_ROOT.joinpath("tests").rglob("*.py")
        if is_pytest_discovery_file(p)
    )
    mapped = set(OWNERSHIP_MAP.keys())
    missing = [f for f in actual if f not in mapped]
    assert not missing, f"Test files missing from OWNERSHIP_MAP: {missing}"


def test_no_stale_ownership_entries():
    """Every OWNERSHIP_MAP entry must correspond to an existing test file."""
    actual = set(
        p.relative_to(REPO_ROOT).as_posix()
        for p in REPO_ROOT.joinpath("tests").rglob("*.py")
        if is_pytest_discovery_file(p)
    )
    stale = sorted(k for k in OWNERSHIP_MAP if k not in actual)
    assert not stale, f"Stale OWNERSHIP_MAP entries (files no longer exist): {stale}"


def test_all_owners_are_nonempty():
    """Every entry must have a non-empty owner assigned."""
    unassigned = sorted(k for k, v in OWNERSHIP_MAP.items() if not v.get("owner"))
    assert not unassigned, f"Entries with no owner assigned: {unassigned[:10]}..."
