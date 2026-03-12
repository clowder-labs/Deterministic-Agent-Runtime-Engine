from __future__ import annotations

import importlib.util
from pathlib import Path, PureWindowsPath

from scripts.ci.test_ownership_map import is_pytest_discovery_file


def _load_repo_conftest():
    repo_root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "repo_test_conftest",
        repo_root / "tests" / "conftest.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalize_ownership_relpath_uses_forward_slashes() -> None:
    repo_conftest = _load_repo_conftest()

    assert repo_conftest._normalize_ownership_relpath(  # type: ignore[attr-defined]
        PureWindowsPath("tests\\unit\\test_demo.py")
    ) == "tests/unit/test_demo.py"


def test_is_pytest_discovery_file_matches_default_filename_patterns() -> None:
    assert is_pytest_discovery_file("tests/unit/test_demo.py")
    assert is_pytest_discovery_file("tests/unit/demo_test.py")
    assert not is_pytest_discovery_file("tests/unit/demo.py")
