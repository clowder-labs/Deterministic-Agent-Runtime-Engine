---
name: spec-driven-collab-board
description: Use when a claimed spec-driven change needs an execution board, work-package structure, Gate freeze tracking, or historical-reference handling before a docs-only intent PR is merged.
---

# Spec-Driven Collab Board

## Authoritative inputs
- `docs/todos/README.md`
- `docs/todos/templates/change_execution_todo_template.md`
- `docs/guides/Team_Agent_Collab_Playbook.md`
- `docs/todos/project_overall_todos.md`
- `docs/design/TODO_INDEX.md`
- `openspec/changes/<change-id>/tasks.md`
- `docs/features/<change-id>.md` when present

## Core rule

Treat `Claim Ledger` as the outer ownership record and `docs/todos/YYYY-MM-DD_<change-id>_execution_todos.md` as the inner coordination board for an active change.

Do not turn `docs/todos/project_overall_todos.md` into a work-package task board.
Do not claim work directly from `docs/design/TODO_INDEX.md`.

## Workflow

1. Confirm the change state before editing any board.
- Read `openspec/changes/<change-id>/tasks.md`.
- Read `docs/features/<change-id>.md` when it exists.
- Read the matching initiative entry in `docs/todos/project_overall_todos.md` when one exists.
- Read the corresponding `Claim Ledger` entry and confirm the TODO scope is already claimed.
- If tasks are complete and the feature or roadmap status is `done`, do not create a new active board for that change.

2. Decide whether an execution board is needed.
- If the change is single-owner, has no shared-contract risk, and does not need Gate sequencing, report that no execution board is required and stop.
- Otherwise continue and choose exactly one board action.
- `create`: no execution board exists for an active change.
- `refresh`: an execution board exists but its gates, work packages, or evidence links are stale.
- `historical-reference`: the change is completed or superseded and the old board should remain only as reference.

3. Create or refresh the board from the template.
- Use `docs/todos/templates/change_execution_todo_template.md` as the structural baseline.
- Name the file `docs/todos/YYYY-MM-DD_<change-id>_execution_todos.md`.
- Keep the status explicit: `active`, `blocked`, `archived`, or `historical reference`.
- Prepare the board as part of a docs-only intent PR payload; a local-only board is not sufficient coordination.
- Include these sections unless there is a strong reason not to:
  - usage rules
  - context and scope boundary
  - Gate freeze summary
  - work-package coordination board
  - subtask acceptance tables
  - interface compatibility matrix
  - integration and closeout
  - maintenance rules

4. Split work at the work-package level, not at the bullet level.
- Create `2-5` work packages for one change.
- Target `0.5-2` days of work per package.
- Give each package one owner, one main goal, one declared touch scope, and one freeze boundary.
- Keep subtasks small for acceptance and evidence mapping, but do not use them as the default claim unit.

5. Apply Gate rules before allowing parallel work.
- Shared contracts must freeze before downstream packages begin dependent implementation.
- A package should cross at most one Gate.
- If two developers need the same schema, payload, enum, state machine, or audit contract, split into upstream freeze work and downstream implementation work.

6. Keep the board synchronized with the surrounding governance documents.
- `project_overall_todos.md` remains roadmap plus outer `Claim Ledger`; it must not absorb work-package detail.
- `TODO_INDEX.md` remains backlog-only.
- The execution board must link back to the OpenSpec change and reflect the same completion state as `tasks.md`.
- The execution board should be ready before the docs-only intent PR is raised, and that intent PR must merge before implementation starts.
- If a package moves to `review` or `done`, update evidence on the same day.

7. Downgrade completed boards instead of pretending they are still active.
- Change the title and status to make the historical role obvious.
- State why the board is no longer active.
- Point future coordination to the currently active change when one is known.

## Board quality checks

Before claiming the board update is complete, verify:
- the chosen change is still active if the board is marked `active`
- the outer `Claim Ledger` entry exists and names the same TODO scope / change-id
- each work package has `WP`, `Goal`, `Owner`, `Depends On`, `Touch Scope`, `Freeze Gate`, `Status`, `Branch/Worktree`, `PR`, `Evidence`, and `Last Updated`
- subtask tables map back to OpenSpec task IDs, gap IDs, or testable acceptance points
- the board does not duplicate work-package detail into `project_overall_todos.md`
- the board and `openspec/changes/<change-id>/tasks.md` do not contradict each other
- the board is suitable to ship in a docs-only intent PR without implementation code

## Output expectations

Report:
- which action was taken: `create`, `refresh`, or `historical-reference`
- why this change is the correct active or historical board target
- which files were created or updated
- whether an execution board was actually required
- what still needs owner assignment, evidence, Gate freeze, or intent-PR merge

## Examples

Use these boards as references when the structure is unclear:
- `docs/todos/agentscope_domain_execution_todos.md`
- `docs/todos/templates/change_execution_todo_template.md`
