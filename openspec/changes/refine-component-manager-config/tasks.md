## 1. Design + interfaces
- [x] 1.1 Document config-aware component filtering and lifecycle ownership for ComponentManager derivatives.
- [x] 1.2 Define composite tool recipe shape and minimal validation rules.

## 2. Implementation
- [x] 2.1 Update ComponentManager to honor config enable/disable lists for all managed component types.
- [x] 2.2 Implement composite tool assembly in ToolManager based on config recipes.
- [x] 2.3 Ensure lifecycle hooks (init/register/close) are applied only to components created by managers; caller-injected components remain unmanaged.

## 3. Validation
- [x] 3.1 Add unit tests for config filtering, composite tool registration, and lifecycle boundaries.
- [x] 3.2 Validate config-driven behaviors with minimal fixtures (no external entry points).
