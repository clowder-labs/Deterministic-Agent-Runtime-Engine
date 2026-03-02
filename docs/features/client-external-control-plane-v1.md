---
change_ids: ["client-external-control-plane-v1"]
doc_kind: feature
topics: ["client-cli", "host-orchestration", "control-plane", "issue-135"]
todo_ids: ["CCLI-005", "CCLI-006"]
created: 2026-03-02
updated: 2026-03-02
status: active
mode: openspec
---

# Feature: client-external-control-plane-v1

## Scope

落实 Issue #135 的 Slice C：为 `client/` 增加外部结构化 control plane v1，优先采用 `--control-stdin` 作为本地宿主入口，并覆盖审批、MCP、skills 与 session status 的最小控制面。

## OpenSpec Artifacts

- Proposal: `openspec/changes/client-external-control-plane-v1/proposal.md`
- Design: `openspec/changes/client-external-control-plane-v1/design.md`
- Specs:
  - `openspec/changes/client-external-control-plane-v1/specs/client-host-orchestration/spec.md`
- Tasks: `openspec/changes/client-external-control-plane-v1/tasks.md`

## TODO Coverage

- `CCLI-005`
- `CCLI-006`

## Evidence

### Commands

- `git fetch origin`
- `git worktree add .worktrees/client-external-control-plane-v1 -b codex/client-external-control-plane-v1 origin/main`
- `openspec list`
- `openspec validate client-external-control-plane-v1 --type change --strict --json --no-interactive`
- `./scripts/ci/check_governance_evidence_truth.sh`

### Results

- `git fetch origin`: confirmed `origin/main` includes merged Slice B via PR `#145`.
- `git worktree add .worktrees/client-external-control-plane-v1 -b codex/client-external-control-plane-v1 origin/main`: created an isolated Slice C workspace from `origin/main` commit `bc39bc0`.
- `openspec list`: confirms Slice A / Slice B have been archived out of the active change list, and the new Slice C kickoff change is recognized as `0/7 tasks`.
- `openspec validate client-external-control-plane-v1 --type change --strict --json --no-interactive`: passed (`1/1` change valid, `0` issues).
- `./scripts/ci/check_governance_evidence_truth.sh`: passed after the Slice C feature evidence block and prior-slice archive moves were synchronized.

### Behavior Verification

- Happy path: the planned Slice C contract narrows v1 external control to `--control-stdin`, preserving the landed headless event envelope from Slice B as the read-only observation channel.
- Error branch: Slice C keeps unknown action ids and unsupported MCP operations on the structured error path; it does not permit fallback to prompt text or undocumented CLI-only verbs such as `mcp:unload`.

### Risks and Rollback

- Risk: adding a second stdin consumer beside `chat` / `script` can create framing ambiguity if control and prompt input are not cleanly separated.
- Rollback: drop the Slice C kickoff change and keep the repository at the merged Slice B baseline where headless remains read-only.

### Review and Merge Gate Links

- Slice A intent gate (merged): `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/141`
- Slice B implementation gate (merged): `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/145`
