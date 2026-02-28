# workspace-file-tools Specification

## Purpose
TBD - created by archiving change add-v4-tooling. Update Purpose after archive.
## Requirements
### Requirement: Built-in workspace file tools
The system SHALL provide built-in tool capabilities named `read_file`, `search_code`, `write_file`, and `edit_line` that implement the v4.0 `ITool` contract and are exposed through the tool gateway as `CapabilityDescriptor` entries of type `TOOL`.

#### Scenario: Tool gateway lists the minimal file toolset
- **WHEN** the tool gateway lists capabilities
- **THEN** the capability catalog includes `tool:read_file`, `tool:search_code`, `tool:write_file`, and `tool:edit_line`

### Requirement: Workspace-root enforcement for file tools
All workspace file tools SHALL resolve input paths against `workspace_roots` from the effective config and MUST reject paths that resolve outside those roots.

#### Scenario: Path outside workspace roots is rejected
- **GIVEN** `workspace_roots` includes `/workspace`
- **WHEN** `read_file` is invoked with a path that resolves outside `/workspace`
- **THEN** the tool returns a failure result indicating the path is not allowed

### Requirement: File tool guardrail configuration
Workspace file tools SHALL read guardrail settings from `Config.tools.<tool_name>` and apply safe defaults when unspecified.

Guardrail keys and defaults:
- `read_file.max_bytes`: 1_000_000
- `write_file.max_bytes`: 1_000_000
- `edit_line.max_bytes`: 1_000_000
- `search_code.max_results`: 50
- `search_code.max_file_bytes`: 1_000_000
- `search_code.ignore_dirs`: [".git", "node_modules", "__pycache__", ".venv", "venv"]

#### Scenario: Default guardrails apply when config is missing
- **GIVEN** no `Config.tools.read_file` entry exists
- **WHEN** `read_file` is invoked
- **THEN** the tool enforces a `max_bytes` limit of 1_000_000

#### Scenario: Guardrails honor configuration overrides
- **GIVEN** `Config.tools.search_code.max_results` is set to 10
- **WHEN** `search_code` is invoked
- **THEN** the tool returns at most 10 matches and reports truncation when more exist

### Requirement: File tool evidence emission
Each workspace file tool SHALL include at least one evidence record describing the operation (tool name and target path) when it completes successfully.

#### Scenario: Evidence is recorded for a write
- **WHEN** `write_file` completes successfully
- **THEN** the tool result includes an evidence record identifying the written path

### Requirement: Read file tool behavior
The `read_file` tool SHALL read text content from a file, support optional 1-indexed `start_line` and `end_line` bounds, and return content with metadata including total line count, file size, and a `truncated` flag.

#### Scenario: Read succeeds within limits
- **GIVEN** a text file under `workspace_roots` and within `read_file.max_bytes`
- **WHEN** `read_file` is invoked
- **THEN** the tool returns file content, `size_bytes`, `line_count`, and `truncated: false`

#### Scenario: Read fails when file exceeds max bytes
- **GIVEN** a file larger than `read_file.max_bytes`
- **WHEN** `read_file` is invoked
- **THEN** the tool returns a failure result indicating the size limit was exceeded

### Requirement: Search code tool behavior
The `search_code` tool SHALL perform regex search across files under a workspace root, skip ignored directories, cap results with `search_code.max_results`, and return matches in deterministic order (path then line).

#### Scenario: Search returns deterministic, bounded matches
- **GIVEN** multiple matching files under the workspace root
- **WHEN** `search_code` is invoked
- **THEN** results are ordered by path then line number and capped at `search_code.max_results`

### Requirement: Write file tool behavior
The `write_file` tool SHALL overwrite or create a text file under the workspace root, create parent directories when requested, enforce `write_file.max_bytes`, and use an atomic replace strategy.

#### Scenario: Write creates a new file
- **WHEN** `write_file` writes to a new path under the workspace root
- **THEN** the file is created and the tool returns the number of bytes written

### Requirement: Edit line tool behavior
The `edit_line` tool SHALL insert or delete a line in a text file using a 1-indexed `line_number`, enforce `edit_line.max_bytes`, preserve newline style, and default `strict_match` to true for deletions.

When `line_number` is omitted, the tool MUST default it to `1`.

#### Scenario: Insert adds a line at the target index
- **WHEN** `edit_line` is invoked with `mode: insert`
- **THEN** the line is inserted at the requested position and the tool returns the affected line number

#### Scenario: Insert defaults to first line when line_number is omitted
- **GIVEN** an existing text file under workspace roots
- **WHEN** `edit_line` is invoked with `mode: insert` and no `line_number`
- **THEN** the line is inserted at line 1
- **AND** the tool returns `line_number: 1`

#### Scenario: Delete fails on strict mismatch
- **GIVEN** `strict_match` is true and the target line differs from the provided text
- **WHEN** `edit_line` is invoked with `mode: delete`
- **THEN** the tool returns a failure result indicating a mismatch

