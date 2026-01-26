## 1. Builder API Restructure
- [x] 1.1 Add an internal base builder that implements shared config+manager resolution rules.
- [x] 1.2 Add `SimpleChatAgentBuilder` and wire it to build `SimpleChatAgent`.
- [x] 1.3 Add `FiveLayerAgentBuilder` and wire it to build `FiveLayerAgent`.
- [x] 1.4 Add a `Builder` facade (factory) for selecting builder variants.

## 2. Config + Manager Resolution
- [x] 2.1 Add a `with_managers(...)` injection surface that accepts per-domain manager instances (model/tools/planner/validator/remediator/hooks/etc).
- [x] 2.2 Define deterministic precedence rules in code: explicit builder injection wins; missing components are resolved via managers.
- [x] 2.3 Implement multi-load merge semantics for tools/hooks/validators: explicit list + manager list (extend).
- [x] 2.4 Enforce boundary: config enable/disable filtering applies only to manager-loaded components, not explicitly injected ones.

## 3. Five-Layer Enablement Fixes
- [x] 3.1 Align `FiveLayerAgent` tool invocation with `IToolGateway.invoke(..., envelope=...)` so the default gateway can be used safely.
- [x] 3.2 Update mocks/tests that assume the old invoke signature.

## 4. Config Interface Simplification
- [x] 4.1 Remove `ConfigSnapshot` and update `IConfigProvider` to return `Config` directly.
- [x] 4.2 Update `FileConfigProvider` and config exports accordingly.
- [x] 4.3 Update unit tests that reference `ConfigSnapshot`.

## 5. Tests + Examples
- [x] 5.1 Add unit tests for: model resolved via manager; explicit model override; multi-load extend + config filtering boundary.
- [x] 5.2 Update existing builder tests to cover the new builder variants/factory (keep minimal surface).
- [x] 5.3 Update call sites (examples/tests) to the `add_*` multi-load APIs (no `with_tools` compatibility layer).

## 6. Validation
- [x] 6.1 Run `openspec validate refactor-agent-builder-config-managers --strict` and fix all issues.
- [x] 6.2 Run `pytest` (and `ruff`/`black`/`mypy` when available) and fix any regressions.
