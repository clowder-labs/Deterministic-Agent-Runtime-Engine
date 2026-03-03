"""Regression tests for the governance traceability CI gate."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "ci" / "check_governance_traceability.sh"


FEATURE_DOC = """---
change_ids: ["demo-change"]
doc_kind: feature
topics: ["governance", "traceability"]
todo_ids: ["D2-1", "D2-2"]
created: 2026-03-03
updated: 2026-03-03
status: draft
mode: openspec
---

# Feature: demo-change

## OpenSpec Artifacts
- Proposal: `openspec/changes/demo-change/proposal.md`
- Design: `openspec/changes/demo-change/design.md`
- Tasks: `openspec/changes/demo-change/tasks.md`

## Evidence
### Commands
- `pytest -q`

### Results
- pass

### Behavior Verification
- Happy path recorded.

### Risks and Rollback
- Risk: demo only.
- Rollback: revert demo.

### Review and Merge Gate Links
- Intent PR: https://github.com/example/repo/pull/1
- Implementation PR: https://github.com/example/repo/pull/2
- Review thread: https://github.com/example/repo/pull/2#discussion_r1
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _base_tree(root: Path) -> None:
    _write(
        root / "docs" / "features" / "README.md",
        """# Feature Aggregation Docs

## Template
- `docs/features/templates/feature_aggregation_template.md`

## Active Entries
- `docs/features/demo-change.md`

## Archive Index
- `docs/features/archive/README.md`

## Migration Rules
- Move completed docs to `docs/features/archive/`.
""",
    )
    _write(
        root / "docs" / "features" / "archive" / "README.md",
        """# Feature Aggregation Archive

## Archived Entries
- `docs/features/archive/archived-change.md`

## Archive Migration Rules
- Move docs here only after closeout.
""",
    )
    _write(
        root / "docs" / "features" / "templates" / "feature_aggregation_template.md",
        """# Feature Aggregation Template

```yaml
---
change_ids: ["<change-id>"]
doc_kind: feature
topics: ["..."]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: draft
mode: openspec
---
```
""",
    )
    _write(root / "docs" / "features" / "demo-change.md", FEATURE_DOC)
    _write(
        root / "docs" / "todos" / "demo_master_todo.md",
        """# Demo TODO

## Claim Ledger
| Claim ID | TODO Scope | Owner | Status | Declared At | Expires At | OpenSpec Change | Notes |
|---|---|---|---|---|---|---|---|
| CLM-DEMO | D2-1~D2-2 | demo | active | 2026-03-03 | 2026-03-10 | `demo-change` | demo |
""",
    )
    _write(root / "openspec" / "changes" / "demo-change" / "proposal.md", "# proposal\n")
    _write(root / "openspec" / "changes" / "demo-change" / "design.md", "# design\n")
    _write(root / "openspec" / "changes" / "demo-change" / "tasks.md", "- [ ] demo\n")
    _write(
        root / "docs" / "governance" / "Documentation_Management_Model.md",
        """# Documentation Management Model

## 7. Checkpoint-to-Skill Mapping
- kickoff -> `development-workflow` + `documentation-management`
- verification -> `development-workflow`
- completion-archive -> `documentation-management`
""",
    )
    _write(root / ".codex" / "skills" / "documentation-management" / "SKILL.md", "# doc skill\n")
    _write(root / ".codex" / "skills" / "development-workflow" / "SKILL.md", "# workflow skill\n")


class GovernanceTraceabilityGateTests(unittest.TestCase):
    def _run_gate(self, mutate=None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _base_tree(root)
            if mutate is not None:
                mutate(root)
            env = os.environ.copy()
            env["GOVERNANCE_TRACEABILITY_ROOT_DIR"] = str(root)
            return subprocess.run(
                [str(GATE_SCRIPT)],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

    def test_gate_passes_with_template_index_skill_mapping_and_todo_mapping(self) -> None:
        result = self._run_gate()

        self.assertEqual(result.returncode, 0)
        self.assertIn("passed", result.stdout)

    def test_gate_fails_when_feature_template_is_missing(self) -> None:
        result = self._run_gate(
            lambda root: (root / "docs" / "features" / "templates" / "feature_aggregation_template.md").unlink()
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing feature aggregation template", result.stdout)

    def test_gate_fails_when_active_feature_doc_is_not_indexed(self) -> None:
        def mutate(root: Path) -> None:
            readme = root / "docs" / "features" / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8").replace("- `docs/features/demo-change.md`\n", ""),
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing active feature index entry", result.stdout)

    def test_gate_fails_when_checkpoint_skill_mapping_is_missing(self) -> None:
        def mutate(root: Path) -> None:
            model = root / "docs" / "governance" / "Documentation_Management_Model.md"
            model.write_text("# Documentation Management Model\n", encoding="utf-8")

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing checkpoint-to-skill mapping", result.stdout)

    def test_gate_fails_when_declared_todo_id_has_no_matching_todo_ledger(self) -> None:
        def mutate(root: Path) -> None:
            (root / "docs" / "todos" / "demo_master_todo.md").write_text("# empty\n", encoding="utf-8")

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing TODO mapping for feature doc", result.stdout)


if __name__ == "__main__":
    unittest.main()
