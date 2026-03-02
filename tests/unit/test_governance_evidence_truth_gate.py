"""Regression tests for governance evidence-truth CI gate."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "ci" / "check_governance_evidence_truth.sh"


def _base_doc(
    *,
    status: str = "active",
    contract_heading: str = "### Contract Delta",
    golden_heading: str = "### Golden Cases",
    regression_heading: str = "### Regression Summary",
    observability_heading: str = "### Observability and Failure Localization",
    structured_review_heading: str = "### Structured Review Report",
    behavior_heading: str = "### Behavior Verification",
    risk_heading: str = "### Risks and Rollback",
    review_heading: str = "### Review and Merge Gate Links",
    intent_pr: int = 120,
    implementation_pr: int = 121,
    observability_body: str | None = None,
) -> str:
    if observability_body is None:
        observability_body = (
            "- Markers: start, tool_call, end, fail.\n"
            "- Fields: run_id, tool_call_id, capability_id, attempt, trace_id.\n"
            "- Error locator: error_code."
        )

    return f"""---
change_ids: ["fixture-change"]
doc_kind: feature
status: {status}
mode: openspec
---

# Feature: fixture-change

## Evidence
### Commands
- `pytest -q tests/unit/test_governance_evidence_truth_gate.py`

### Results
- pass

{contract_heading}
- schema: none, reason: docs-only governance check.
- error semantics: error_type (framework-native marker).
- retry semantics: none, reason: deterministic docs gate.

{golden_heading}
- `golden_case`

{regression_heading}
- Runner: `pytest -q tests/unit/test_governance_evidence_truth_gate.py`
- Summary: pass 1, fail 0, skip 0.

{observability_heading}
{observability_body}

{structured_review_heading}
- Changed Module Boundaries / Public API: docs/ci governance only.
- New State: none.
- Concurrency / Timeout / Retry: none.
- Side Effects and Idempotency: deterministic checks only.
- Coverage and Residual Risk: covered by unit + script checks.

{behavior_heading}
- Happy path + error path validated.

{risk_heading}
- Risk: regex false positive edge cases.
- Rollback: revert gate script and spec changes.

{review_heading}
- Intent PR: https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/{intent_pr}
- Implementation PR: https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/{implementation_pr}
- Review thread: https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/{intent_pr}#issuecomment-3983984020
"""


class GovernanceEvidenceTruthGateTests(unittest.TestCase):
    def _run_gate_with_doc(self, doc_content: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            feature_dir = temp_path / "docs" / "features"
            feature_dir.mkdir(parents=True, exist_ok=True)
            (feature_dir / "fixture-feature.md").write_text(doc_content, encoding="utf-8")

            env = os.environ.copy()
            env["GOVERNANCE_EVIDENCE_ROOT_DIR"] = str(temp_path)
            return subprocess.run(
                [str(GATE_SCRIPT)],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

    def test_status_in_review_variant_is_governed(self) -> None:
        result = self._run_gate_with_doc(_base_doc(status="in-review"))

        self.assertEqual(result.returncode, 0)
        self.assertIn("passed", result.stdout)

    def test_gate_fails_when_no_governed_docs_present(self) -> None:
        result = self._run_gate_with_doc(_base_doc(status="draft"))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no governed docs in status active/in_review", result.stdout)

    def test_observability_na_with_reason_and_fallback_passes(self) -> None:
        observability_body = (
            "- N/A for runtime event chain in docs-only governance change.\n"
            "- Reason: this change only touches documentation + gate script behavior.\n"
            "- Fallback evidence: regression commands and runner output listed above."
        )
        result = self._run_gate_with_doc(
            _base_doc(status="in_review", observability_body=observability_body)
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Observability N/A accepted with reason + fallback evidence", result.stdout)

    def test_intent_and_implementation_must_reference_different_prs(self) -> None:
        result = self._run_gate_with_doc(
            _base_doc(status="in_review", intent_pr=130, implementation_pr=130)
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must reference different pull requests", result.stdout)

    def test_heading_variants_are_accepted(self) -> None:
        result = self._run_gate_with_doc(
            _base_doc(
                status="in_review",
                contract_heading="### Contract Changes",
                golden_heading="### Golden Case",
                regression_heading="### Regression Results",
                observability_heading="### Observability",
                structured_review_heading="### Structured Review",
                behavior_heading="### Behavior Checks",
                risk_heading="### Risk and Rollback",
                review_heading="### Review / Merge Gate Links",
            )
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("passed", result.stdout)

    def test_active_baseline_without_acceptance_pack_sections_passes(self) -> None:
        active_doc = """---
change_ids: ["fixture-change"]
doc_kind: feature
status: active
mode: openspec
---

# Feature: fixture-change

## Evidence
### Commands
- `pytest -q`

### Results
- pass

### Behavior Verification
- Happy path and known error branch are tracked at intent level.

### Risks and Rollback
- Risk: implementation evidence pending until in_review phase.
- Rollback: keep active scope as docs-only until implementation starts.

### Review and Merge Gate Links
- Slice intent PR: https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/141
- Slice implementation PR: https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/145
- Review thread: https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/145#discussion_r2872038646
"""
        result = self._run_gate_with_doc(active_doc)

        self.assertEqual(result.returncode, 0)
        self.assertIn("passed", result.stdout)

    def test_in_review_requires_contract_delta_section(self) -> None:
        doc = _base_doc(status="in_review")
        doc = doc.replace(
            "### Contract Delta\n- schema: none, reason: docs-only governance check.\n- error semantics: error_type (framework-native marker).\n- retry semantics: none, reason: deterministic docs gate.\n\n",
            "",
        )
        result = self._run_gate_with_doc(doc)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Contract Delta missing schema semantics", result.stdout)

    def test_intent_marker_without_pr_url_fails_even_with_other_links(self) -> None:
        doc = _base_doc(status="in_review").replace(
            "- Intent PR: https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/120",
            "- Intent PR: TBD",
        )
        result = self._run_gate_with_doc(doc)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Intent PR marker must include a valid GitHub PR link", result.stdout)

    def test_error_message_only_is_not_accepted_as_error_locator(self) -> None:
        observability_body = (
            "- Markers: start, tool_call, end, fail.\n"
            "- Fields: run_id, tool_call_id, capability_id, attempt, trace_id.\n"
            "- Error locator: error_message only."
        )
        result = self._run_gate_with_doc(
            _base_doc(status="in_review", observability_body=observability_body)
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing error locator semantics", result.stdout)


if __name__ == "__main__":
    unittest.main()
