"""Regression tests for governance intent-merge CI gate."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "ci" / "check_governance_intent_gate.sh"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _base_feature_doc(status: str = "active") -> str:
    return f"""---
change_ids: ["demo-change"]
doc_kind: feature
topics: ["governance", "intent-gate"]
created: 2026-03-05
updated: 2026-03-05
status: {status}
mode: openspec
---

# Feature: demo-change

## Evidence
### Commands
- `pytest -q`

### Results
- pass

### Behavior Verification
- happy path + error path verified

### Risks and Rollback
- risk tracked
- rollback via revert

### Review and Merge Gate Links
- Intent PR: https://github.com/example/repo/pull/101
- Implementation PR: https://github.com/example/repo/pull/110
- Review thread: https://github.com/example/repo/pull/110#discussion_r1
"""


def _base_tree(root: Path) -> None:
    _write(root / "docs" / "features" / "demo-change.md", _base_feature_doc())
    _write(root / "client" / "main.py", "print('demo')\n")
    _write(root / "docs" / "guides" / "Development_Constraints.md", "# placeholder\n")


class GovernanceIntentGateTests(unittest.TestCase):
    def _run_gate(
        self,
        *,
        changed_files: list[str],
        mutate=None,
        pr_state_fixture: str = "",
        include_token: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _base_tree(root)
            if mutate is not None:
                mutate(root)

            env = os.environ.copy()
            env["GOVERNANCE_INTENT_GATE_ROOT_DIR"] = str(root)
            env["GOVERNANCE_INTENT_GATE_CHANGED_FILES"] = "\n".join(changed_files)
            if pr_state_fixture:
                env["GOVERNANCE_INTENT_GATE_PR_STATE_FIXTURE"] = pr_state_fixture
            if include_token:
                env["GITHUB_TOKEN"] = "token-for-tests"

            return subprocess.run(
                [str(GATE_SCRIPT)],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

    def test_docs_only_changes_skip_intent_gate(self) -> None:
        result = self._run_gate(
            changed_files=["docs/guides/Development_Constraints.md", "docs/features/demo-change.md"]
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("No implementation-path changes detected", result.stdout)

    def test_implementation_changes_require_governed_feature_doc_update(self) -> None:
        result = self._run_gate(changed_files=["client/main.py"])

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must update at least one governed feature doc", result.stdout)

    def test_implementation_changes_fail_when_intent_pr_not_merged(self) -> None:
        result = self._run_gate(
            changed_files=["client/main.py", "docs/features/demo-change.md"],
            pr_state_fixture="example/repo#101=open",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is not merged", result.stdout)

    def test_implementation_changes_pass_when_intent_pr_is_merged(self) -> None:
        result = self._run_gate(
            changed_files=["client/main.py", "docs/features/demo-change.md"],
            pr_state_fixture="example/repo#101=merged",
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("passed", result.stdout)

    def test_gate_fails_when_governed_feature_doc_has_no_intent_pr_link(self) -> None:
        def mutate(root: Path) -> None:
            doc = root / "docs" / "features" / "demo-change.md"
            doc.write_text(
                doc.read_text(encoding="utf-8").replace(
                    "- Intent PR: https://github.com/example/repo/pull/101\n",
                    "- Intent PR: TBD\n",
                ),
                encoding="utf-8",
            )

        result = self._run_gate(
            changed_files=["client/main.py", "docs/features/demo-change.md"],
            mutate=mutate,
            pr_state_fixture="example/repo#101=merged",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing Intent PR link", result.stdout)

    def test_gate_requires_canonical_intent_pr_field_not_any_intent_url_line(self) -> None:
        def mutate(root: Path) -> None:
            doc = root / "docs" / "features" / "demo-change.md"
            updated = doc.read_text(encoding="utf-8").replace(
                "- Intent PR: https://github.com/example/repo/pull/101\n",
                "- Intent PR: TBD\n- Historical intent PR note: https://github.com/example/repo/pull/101\n",
            )
            doc.write_text(updated, encoding="utf-8")

        result = self._run_gate(
            changed_files=["client/main.py", "docs/features/demo-change.md"],
            mutate=mutate,
            pr_state_fixture="example/repo#101=merged",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing Intent PR link", result.stdout)

    def test_gate_reports_missing_token_for_pr_lookup_failures(self) -> None:
        result = self._run_gate(
            changed_files=["client/main.py", "docs/features/demo-change.md"],
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing GITHUB_TOKEN for PR state lookup", result.stdout)

    def test_draft_feature_doc_does_not_satisfy_governed_requirement(self) -> None:
        result = self._run_gate(
            changed_files=["client/main.py", "docs/features/demo-change.md"],
            mutate=lambda root: _write(
                root / "docs" / "features" / "demo-change.md",
                _base_feature_doc(status="draft"),
            ),
            pr_state_fixture="example/repo#101=merged",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must update at least one governed feature doc", result.stdout)


if __name__ == "__main__":
    unittest.main()
