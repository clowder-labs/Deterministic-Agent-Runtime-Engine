---
name: code-review
description: Code review skill for analyzing and improving code quality. Use when the task involves reviewing code, suggesting improvements, or finding bugs.
---

# Code Review Skill

When performing code reviews:

1. **Structure**: Check for clear separation of concerns and logical organization.
2. **Style**: Verify naming conventions, formatting consistency, and readability.
3. **Safety**: Look for potential bugs, edge cases, and error handling.
4. **Performance**: Identify unnecessary allocations or redundant operations.
5. **Documentation**: Ensure non-obvious logic has explanatory comments.

Provide actionable feedback with specific line references when possible.

When automated checks are needed, use the `run_skill_script` tool with skill_id `code-review` and script_name `run_linter`. Pass the target path as an argument if needed.
