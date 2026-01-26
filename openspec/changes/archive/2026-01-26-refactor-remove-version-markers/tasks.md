## 1. Implementation
- [x] 1.1 Inventory version markers in non-archived code/docs/tests/examples.
- [x] 1.2 Rename versioned example/test files to neutral names (resolve collisions explicitly).
- [x] 1.3 Update imports/references to renamed files across docs, examples, and tests.
- [x] 1.4 Remove version labels from docstrings/logs/comments in canonical code and docs (non-archive).
- [x] 1.5 Update skip reasons and README notes to reference "archived" or "legacy" without version numbers.

## 2. Validation
- [x] 2.1 Run targeted tests affected by renamed files and updated references.
- [x] 2.2 Run `python -c "import dare_framework"` to confirm imports still work.
