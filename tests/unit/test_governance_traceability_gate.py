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

TODO_DOC_FRONTMATTER = """---
change_ids: []
doc_kind: todo
topics: ["governance", "todo"]
created: 2026-03-03
updated: 2026-03-03
status: active
---
"""

STANDARD_DOC_FRONTMATTER = """---
change_ids: ["demo-change"]
doc_kind: standard
topics: ["governance", "traceability"]
created: 2026-03-03
updated: 2026-03-03
status: active
---
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
    _write(root / "docs" / "features" / "archive" / "archived-change.md", "# archived\n")
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
        """---
change_ids: []
doc_kind: todo
topics: ["governance", "todo"]
created: 2026-03-03
updated: 2026-03-03
status: active
---

# Demo TODO

## Claim Ledger
| Claim ID | TODO Scope | Owner | Status | Declared At | Expires At | OpenSpec Change | Notes |
|---|---|---|---|---|---|---|---|
| CLM-DEMO | D2-1~D2-2 | demo | active | 2026-03-03 | 2026-03-10 | `demo-change` | demo |

## 切片规划
| Slice | 目标 | 建议 OpenSpec Change | 主要覆盖 TODO |
|---|---|---|---|
| Slice A | demo | `demo-change` | D2-1, D2-2 |
""",
    )
    _write(root / "openspec" / "changes" / "demo-change" / "proposal.md", "# proposal\n")
    _write(root / "openspec" / "changes" / "demo-change" / "design.md", "# design\n")
    _write(
        root / "openspec" / "changes" / "demo-change" / "tasks.md",
        """## TODO Coverage
- D2-1~D2-2

- [ ] demo
""",
    )
    _write(
        root / "docs" / "governance" / "Documentation_Management_Model.md",
        """---
change_ids: ["demo-change"]
doc_kind: standard
topics: ["governance", "traceability"]
created: 2026-03-03
updated: 2026-03-03
status: active
---

# Documentation Management Model

## 7. Checkpoint-to-Skill Mapping
- kickoff -> `development-workflow` + `documentation-management`
- execution-sync -> `development-workflow` + `documentation-management`
- verification -> `development-workflow`
- review-merge-gate -> `development-workflow` + `documentation-management`
- completion-archive -> `development-workflow` + `documentation-management`
""",
    )
    _write(
        root / "docs" / "guides" / "Documentation_First_Development_SOP.md",
        """---
change_ids: ["demo-change"]
doc_kind: standard
topics: ["governance", "sop"]
created: 2026-03-03
updated: 2026-03-03
status: active
---

# Demo SOP
""",
    )
    _write(
        root / "docs" / "guides" / "Development_Constraints.md",
        """---
change_ids: ["demo-change"]
doc_kind: standard
topics: ["governance", "constraints"]
created: 2026-03-03
updated: 2026-03-03
status: active
---

# Demo Constraints
""",
    )
    _write(
        root / "docs" / "guides" / "Evidence_Truth_Implementation_Strategy.md",
        """---
change_ids: ["demo-change"]
doc_kind: standard
topics: ["governance", "evidence"]
created: 2026-03-03
updated: 2026-03-03
status: active
---

# Demo Evidence Truth
""",
    )
    _write(
        root / "docs" / "design" / "Design_Reconstructability_Traceability_Matrix.md",
        """---
change_ids: ["demo-change"]
doc_kind: design
topics: ["governance", "traceability"]
created: 2026-03-03
updated: 2026-03-03
status: active
---

# Demo Matrix
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

    def test_gate_requires_active_membership_inside_active_entries_section(self) -> None:
        def mutate(root: Path) -> None:
            readme = root / "docs" / "features" / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8").replace(
                    "## Migration Rules\n- Move completed docs to `docs/features/archive/`.\n",
                    "## Migration Rules\n"
                    "- Move completed docs to `docs/features/archive/`.\n"
                    "- Migration note keeps `docs/features/demo-change.md` as an example path.\n",
                ).replace("- `docs/features/demo-change.md`\n", ""),
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing active feature index entry", result.stdout)

    def test_gate_fails_when_active_index_contains_stale_feature_path(self) -> None:
        def mutate(root: Path) -> None:
            readme = root / "docs" / "features" / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8").replace(
                    "## Archive Index\n",
                    "- `docs/features/missing-change.md`\n\n## Archive Index\n",
                ),
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale active feature index entry", result.stdout)

    def test_gate_rejects_archive_paths_inside_active_entries(self) -> None:
        def mutate(root: Path) -> None:
            readme = root / "docs" / "features" / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8").replace(
                    "## Archive Index\n",
                    "- `docs/features/archive/README.md`\n\n## Archive Index\n",
                ),
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid active feature index entry path", result.stdout)

    def test_gate_rejects_active_index_readme_entry(self) -> None:
        def mutate(root: Path) -> None:
            readme = root / "docs" / "features" / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8").replace(
                    "## Archive Index\n",
                    "- `docs/features/README.md`\n\n## Archive Index\n",
                ),
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid active feature index entry path", result.stdout)

    def test_gate_rejects_archive_index_readme_entry(self) -> None:
        def mutate(root: Path) -> None:
            readme = root / "docs" / "features" / "archive" / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8").replace(
                    "## Archive Migration Rules\n",
                    "- `docs/features/archive/README.md`\n\n## Archive Migration Rules\n",
                ),
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid archived feature index entry path", result.stdout)

    def test_gate_requires_frontmatter_for_governance_standard_and_todo_docs(self) -> None:
        def mutate(root: Path) -> None:
            todo_doc = root / "docs" / "todos" / "demo_master_todo.md"
            todo_doc.write_text(todo_doc.read_text(encoding="utf-8").split("---\n", 2)[2], encoding="utf-8")
            sop_doc = root / "docs" / "guides" / "Documentation_First_Development_SOP.md"
            sop_doc.write_text(sop_doc.read_text(encoding="utf-8").split("---\n", 2)[2], encoding="utf-8")

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing frontmatter in docs/todos/demo_master_todo.md", result.stdout)
        self.assertIn("missing frontmatter in docs/guides/Documentation_First_Development_SOP.md", result.stdout)

    def test_gate_fails_when_checkpoint_skill_mapping_is_missing(self) -> None:
        def mutate(root: Path) -> None:
            model = root / "docs" / "governance" / "Documentation_Management_Model.md"
            model.write_text(f"{STANDARD_DOC_FRONTMATTER}\n# Documentation Management Model\n", encoding="utf-8")

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing checkpoint-to-skill mapping", result.stdout)

    def test_gate_requires_all_declared_lifecycle_checkpoints(self) -> None:
        def mutate(root: Path) -> None:
            model = root / "docs" / "governance" / "Documentation_Management_Model.md"
            model.write_text(
                f"""{STANDARD_DOC_FRONTMATTER}
# Documentation Management Model

## 7. Checkpoint-to-Skill Mapping
- kickoff -> `development-workflow` + `documentation-management`
- verification -> `development-workflow`
- completion-archive -> `documentation-management`
""",
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing execution-sync checkpoint", result.stdout)
        self.assertIn("missing review-merge-gate checkpoint", result.stdout)

    def test_gate_requires_explicit_checkpoint_to_skill_pairs(self) -> None:
        def mutate(root: Path) -> None:
            model = root / "docs" / "governance" / "Documentation_Management_Model.md"
            model.write_text(
                f"""{STANDARD_DOC_FRONTMATTER}
# Documentation Management Model

## 7. Checkpoint-to-Skill Mapping

Required lifecycle checkpoints MUST be skillized:
- kickoff
- execution-sync
- verification
- review-merge-gate
- completion-archive

Skill contract (minimum two skills):
- management skill: `.codex/skills/documentation-management/SKILL.md`
- workflow skill: `.codex/skills/development-workflow/SKILL.md`
""",
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing checkpoint-to-skill pair", result.stdout)

    def test_gate_fails_when_declared_todo_id_has_no_matching_todo_ledger(self) -> None:
        def mutate(root: Path) -> None:
            (root / "docs" / "todos" / "demo_master_todo.md").write_text(
                f"{TODO_DOC_FRONTMATTER}\n# empty\n",
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing TODO mapping for feature doc", result.stdout)

    def test_gate_matches_todo_ids_as_discrete_tokens(self) -> None:
        def mutate(root: Path) -> None:
            feature_doc = root / "docs" / "features" / "demo-change.md"
            feature_doc.write_text(
                feature_doc.read_text(encoding="utf-8").replace('todo_ids: ["D2-1", "D2-2"]', 'todo_ids: ["D2-1"]'),
                encoding="utf-8",
            )
            todo_doc = root / "docs" / "todos" / "demo_master_todo.md"
            todo_doc.write_text(
                f"""{TODO_DOC_FRONTMATTER}
# Demo TODO

## Claim Ledger
| Claim ID | TODO Scope | Owner | Status | Declared At | Expires At | OpenSpec Change | Notes |
|---|---|---|---|---|---|---|---|
| CLM-DEMO | D2-10 | demo | active | 2026-03-03 | 2026-03-10 | `demo-change` | demo |
""",
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing TODO mapping for feature doc", result.stdout)

    def test_gate_requires_todo_and_change_in_same_ledger_record(self) -> None:
        def mutate(root: Path) -> None:
            feature_doc = root / "docs" / "features" / "demo-change.md"
            feature_doc.write_text(
                feature_doc.read_text(encoding="utf-8").replace('todo_ids: ["D2-1", "D2-2"]', 'todo_ids: ["D2-1"]'),
                encoding="utf-8",
            )
            todo_doc = root / "docs" / "todos" / "demo_master_todo.md"
            todo_doc.write_text(
                f"""{TODO_DOC_FRONTMATTER}
# Demo TODO

## Claim Ledger
| Claim ID | TODO Scope | Owner | Status | Declared At | Expires At | OpenSpec Change | Notes |
|---|---|---|---|---|---|---|---|
| CLM-TODO | D2-1 | demo | active | 2026-03-03 | 2026-03-10 | `other-change` | wrong change |
| CLM-CHANGE | D9-9 | demo | active | 2026-03-03 | 2026-03-10 | `demo-change` | wrong todo |
""",
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing TODO mapping for feature doc", result.stdout)

    def test_gate_requires_claim_ledger_record_for_todo_change_mapping(self) -> None:
        def mutate(root: Path) -> None:
            feature_doc = root / "docs" / "features" / "demo-change.md"
            feature_doc.write_text(
                feature_doc.read_text(encoding="utf-8").replace('todo_ids: ["D2-1", "D2-2"]', 'todo_ids: ["D2-1"]'),
                encoding="utf-8",
            )
            todo_doc = root / "docs" / "todos" / "demo_master_todo.md"
            todo_doc.write_text(
                f"""{TODO_DOC_FRONTMATTER}
# Demo TODO

## Claim Ledger
| Claim ID | TODO Scope | Owner | Status | Declared At | Expires At | OpenSpec Change | Notes |
|---|---|---|---|---|---|---|---|
| CLM-DEMO | D9-9 | demo | active | 2026-03-03 | 2026-03-10 | `other-change` | wrong claim |

## Detail Board
| ID | OpenSpec Change | Status |
|---|---|---|
| D2-1 | `demo-change` | done |
""",
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing TODO mapping for feature doc", result.stdout)

    def test_gate_accepts_date_prefixed_archived_change_tasks(self) -> None:
        def mutate(root: Path) -> None:
            feature_doc = root / "docs" / "features" / "demo-change.md"
            feature_doc.write_text(
                feature_doc.read_text(encoding="utf-8").replace('change_ids: ["demo-change"]', 'change_ids: ["archived-change"]'),
                encoding="utf-8",
            )
            todo_doc = root / "docs" / "todos" / "demo_master_todo.md"
            todo_doc.write_text(
                todo_doc.read_text(encoding="utf-8").replace("`demo-change`", "`archived-change`"),
                encoding="utf-8",
            )
            active_change_dir = root / "openspec" / "changes" / "demo-change"
            for path in active_change_dir.iterdir():
                path.unlink()
            active_change_dir.rmdir()
            _write(
                root / "openspec" / "changes" / "archive" / "2026-03-03-archived-change" / "tasks.md",
                "## TODO Coverage\n- D2-1~D2-2\n\n- [x] archived\n",
            )

        result = self._run_gate(mutate)

        self.assertEqual(result.returncode, 0)
        self.assertIn("passed", result.stdout)

    def test_gate_accepts_todo_ids_covered_by_claim_scope_for_same_change(self) -> None:
        def mutate(root: Path) -> None:
            todo_doc = root / "docs" / "todos" / "demo_master_todo.md"
            todo_doc.write_text(
                f"""{TODO_DOC_FRONTMATTER}
# Demo TODO

## Claim Ledger
| Claim ID | TODO Scope | Owner | Status | Declared At | Expires At | OpenSpec Change | Notes |
|---|---|---|---|---|---|---|---|
| CLM-DEMO | D2-1~D2-4, D4-1~D4-4 | demo | active | 2026-03-03 | 2026-03-10 | `demo-change` | demo |

## Detail Board
| ID | Task | Status |
|---|---|---|
| D2-1 | task 1 | done |
| D2-2 | task 2 | done |
| D4-3 | task 3 | done |
""",
                encoding="utf-8",
            )
            tasks_doc = root / "openspec" / "changes" / "demo-change" / "tasks.md"
            tasks_doc.write_text(
                "## TODO Coverage\n- D2-1~D2-4\n- D4-1~D4-4\n\n- [ ] demo\n",
                encoding="utf-8",
            )
            feature_doc = root / "docs" / "features" / "demo-change.md"
            feature_doc.write_text(
                feature_doc.read_text(encoding="utf-8").replace(
                    'todo_ids: ["D2-1", "D2-2"]',
                    'todo_ids: ["D2-2", "D4-3"]',
                ),
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertEqual(result.returncode, 0)
        self.assertIn("passed", result.stdout)

    def test_gate_accepts_claim_scope_range_without_explicit_todo_token(self) -> None:
        def mutate(root: Path) -> None:
            todo_doc = root / "docs" / "todos" / "demo_master_todo.md"
            todo_doc.write_text(
                f"""{TODO_DOC_FRONTMATTER}
# Demo TODO

## Claim Ledger
| Claim ID | TODO Scope | Owner | Status | Declared At | Expires At | OpenSpec Change | Notes |
|---|---|---|---|---|---|---|---|
| CLM-DEMO | D2-1~D2-4, D4-1~D4-4 | demo | active | 2026-03-03 | 2026-03-10 | `demo-change` | demo |

## Detail Board
| ID | Task | Status |
|---|---|---|
| D2-1 | task 1 | done |
| D2-2 | task 2 | done |
""",
                encoding="utf-8",
            )
            tasks_doc = root / "openspec" / "changes" / "demo-change" / "tasks.md"
            tasks_doc.write_text(
                "## TODO Coverage\n- D2-1~D2-4\n- D4-1~D4-4\n\n- [ ] demo\n",
                encoding="utf-8",
            )
            feature_doc = root / "docs" / "features" / "demo-change.md"
            feature_doc.write_text(
                feature_doc.read_text(encoding="utf-8").replace(
                    'todo_ids: ["D2-1", "D2-2"]',
                    'todo_ids: ["D4-3"]',
                ),
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertEqual(result.returncode, 0)
        self.assertIn("passed", result.stdout)

    def test_gate_requires_tasks_todo_coverage_for_active_feature_todo_ids(self) -> None:
        def mutate(root: Path) -> None:
            tasks_doc = root / "openspec" / "changes" / "demo-change" / "tasks.md"
            tasks_doc.write_text("- [ ] demo\n", encoding="utf-8")

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing TODO coverage in tasks artifact", result.stdout)

    def test_gate_requires_master_todo_slice_mapping_targets_to_exist(self) -> None:
        def mutate(root: Path) -> None:
            todo_doc = root / "docs" / "todos" / "demo_master_todo.md"
            todo_doc.write_text(
                todo_doc.read_text(encoding="utf-8").replace(
                    "| Slice A | demo | `demo-change` | D2-1, D2-2 |\n",
                    "| Slice A | demo | `demo-change` | D2-1, D2-2 |\n"
                    "| Slice B | drift | `missing-change` | D9-9 |\n",
                ),
                encoding="utf-8",
            )

        result = self._run_gate(mutate)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing feature aggregation doc for TODO change mapping", result.stdout)


if __name__ == "__main__":
    unittest.main()
