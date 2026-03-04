from __future__ import annotations

from scripts.ci.p0_gate import CategoryResult, CategorySpec, extract_failed_tests, format_summary


def _spec(
    label: str,
    *,
    modules: list[str] | None = None,
    owner: str = "@zts212653",
    action: str = "inspect category",
) -> CategorySpec:
    return CategorySpec(
        label=label,
        tests=["tests/example.py::test_case"],
        modules=modules or ["module.one", "module.two"],
        owner=owner,
        action=action,
    )


def test_extract_failed_tests_returns_node_ids_in_order() -> None:
    output = """
=========================== short test summary info ============================
FAILED tests/integration/test_p0_conformance_gate.py::test_step_driven_session_stops_after_first_failed_step
FAILED tests/unit/test_event_sqlite_event_log.py::test_verify_chain_detects_tampered_row - assert False
"""

    assert extract_failed_tests(output) == [
        "tests/integration/test_p0_conformance_gate.py::test_step_driven_session_stops_after_first_failed_step",
        "tests/unit/test_event_sqlite_event_log.py::test_verify_chain_detects_tampered_row",
    ]


def test_extract_failed_tests_includes_error_node_ids() -> None:
    output = """
=========================== short test summary info ============================
ERROR tests/unit/test_p0_gate_ci.py::test_extract_failed_tests_includes_error_node_ids
ERROR tests/integration/test_p0_conformance_gate.py::test_default_event_log_replay_and_hash_chain_hold_for_runtime_session - RuntimeError: boom
"""

    assert extract_failed_tests(output) == [
        "tests/unit/test_p0_gate_ci.py::test_extract_failed_tests_includes_error_node_ids",
        "tests/integration/test_p0_conformance_gate.py::test_default_event_log_replay_and_hash_chain_hold_for_runtime_session",
    ]


def test_format_summary_reports_pass_for_all_categories() -> None:
    summary = format_summary(
        [
            CategoryResult(spec=_spec("SECURITY_REGRESSION"), passed=True, failed_tests=[], raw_output=""),
            CategoryResult(spec=_spec("STEP_EXEC_REGRESSION"), passed=True, failed_tests=[], raw_output=""),
            CategoryResult(spec=_spec("AUDIT_CHAIN_REGRESSION"), passed=True, failed_tests=[], raw_output=""),
        ]
    )

    assert summary == "\n".join(
        [
            "p0-gate: PASS",
            "- SECURITY_REGRESSION: 0 failures",
            "- STEP_EXEC_REGRESSION: 0 failures",
            "- AUDIT_CHAIN_REGRESSION: 0 failures",
        ]
    )


def test_format_summary_reports_failures_with_modules_and_action() -> None:
    summary = format_summary(
        [
            CategoryResult(
                spec=_spec(
                    "STEP_EXEC_REGRESSION",
                    modules=[
                        "dare_framework/agent/dare_agent.py",
                        "dare_framework/agent/_internal/execute_engine.py",
                    ],
                    action="inspect step execution order and fail-fast handling",
                ),
                passed=False,
                failed_tests=[
                    "tests/integration/test_p0_conformance_gate.py::test_step_driven_session_stops_after_first_failed_step"
                ],
                raw_output="FAILED ...",
            )
        ]
    )

    assert summary == "\n".join(
        [
            "p0-gate: FAIL",
            "- STEP_EXEC_REGRESSION",
            "  tests: tests/integration/test_p0_conformance_gate.py::test_step_driven_session_stops_after_first_failed_step",
            "  modules: dare_framework/agent/dare_agent.py, dare_framework/agent/_internal/execute_engine.py",
            "  owner: @zts212653",
            "  action: inspect step execution order and fail-fast handling",
        ]
    )
