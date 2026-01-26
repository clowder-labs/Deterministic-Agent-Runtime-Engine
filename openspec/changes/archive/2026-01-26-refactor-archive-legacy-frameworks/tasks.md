## 1. Implementation
- [x] 1.1 Create the legacy archive root (`archive/frameworks/`) with a short README describing the archived framework status and non-supported intent.
- [x] 1.2 Move legacy framework directories into the archive root: `dare_framework`, `dare_framework2`, `dare_framework3`, `dare_framework3_2`, `dare_framework3_3`.
- [x] 1.3 Rename `dare_framework3_4/` to `dare_framework/` and update any intra-package references that rely on the old package name.
- [x] 1.4 Update imports and references across the repo (examples, tests, docs) to use `dare_framework` instead of versioned package names.
- [x] 1.5 Port legacy basic-chat examples to the canonical package where feasible; for blocked examples, add explicit TODO notes describing missing APIs required to run.
- [x] 1.6 Update tests that referenced `dare_framework3_4` to the new package path and either migrate legacy-version tests to the canonical API or mark them with explicit skip reasons when missing capabilities prevent execution.

## 2. Validation
- [x] 2.1 Run focused import sanity checks (e.g., `python -c "import dare_framework"`).
- [x] 2.2 Run relevant pytest targets (unit + integration) and record any expected skips tied to missing framework capabilities.
