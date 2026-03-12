import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Marker registration & automatic injection from canonical ownership map
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Register ``module`` and ``owner`` markers so they pass ``--strict-markers``."""
    config.addinivalue_line("markers", "module(name): responsible dare_framework module")
    config.addinivalue_line("markers", "owner(name): responsible owner/team handle")


def _normalize_ownership_relpath(path: Path) -> str:
    """Normalize repo-relative test paths into OWNERSHIP_MAP key format."""
    return path.as_posix()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Inject ``@pytest.mark.module`` / ``@pytest.mark.owner`` from the ownership map."""
    import warnings

    from scripts.ci.test_ownership_map import OWNERSHIP_MAP, is_pytest_discovery_file

    for item in items:
        rel = _normalize_ownership_relpath(Path(item.fspath).relative_to(ROOT))
        entry = OWNERSHIP_MAP.get(rel)
        if entry:
            item.add_marker(pytest.mark.module(entry["module"]))
            if entry.get("owner"):
                item.add_marker(pytest.mark.owner(entry["owner"]))

    # Warn about test files missing from OWNERSHIP_MAP (soft guard)
    collected_files = {_normalize_ownership_relpath(Path(item.fspath).relative_to(ROOT)) for item in items}
    test_files = {f for f in collected_files if is_pytest_discovery_file(f)}
    unmapped = test_files - set(OWNERSHIP_MAP.keys())
    if unmapped:
        warnings.warn(
            f"Test files missing from OWNERSHIP_MAP ({len(unmapped)}): "
            + ", ".join(sorted(unmapped)[:5]),
            stacklevel=1,
        )
