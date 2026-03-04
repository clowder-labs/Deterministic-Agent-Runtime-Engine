from __future__ import annotations

from scripts.ci.check_test_failure_ownership import validate_category_specs
from scripts.ci.p0_gate import CategorySpec


def _spec(
    label: str,
    *,
    tests: list[str] | None = None,
    modules: list[str] | None = None,
    owner: str = "@zts212653",
) -> CategorySpec:
    return CategorySpec(
        label=label,
        tests=tests or ["tests/example.py::test_case"],
        modules=modules or ["dare_framework/example.py"],
        owner=owner,
        action="inspect category",
    )


def test_validate_category_specs_accepts_valid_mapping() -> None:
    issues = validate_category_specs(
        [
            _spec("SECURITY_REGRESSION", tests=["tests/a.py::test_x"]),
            _spec("STEP_EXEC_REGRESSION", tests=["tests/b.py::test_y"]),
        ]
    )

    assert issues == []


def test_validate_category_specs_rejects_duplicate_test_mapping() -> None:
    issues = validate_category_specs(
        [
            _spec("SECURITY_REGRESSION", tests=["tests/a.py::test_x"]),
            _spec("STEP_EXEC_REGRESSION", tests=["tests/a.py::test_x"]),
        ]
    )

    assert any("duplicate test selector mapping" in issue for issue in issues)


def test_validate_category_specs_rejects_missing_owner() -> None:
    issues = validate_category_specs(
        [
            _spec("SECURITY_REGRESSION", owner=""),
        ]
    )

    assert any("missing owner" in issue for issue in issues)

