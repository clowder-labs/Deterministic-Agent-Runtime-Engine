## MODIFIED Requirements
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
