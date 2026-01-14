# Change: Refine ComponentManager with config-driven selection and minimal lifecycle

## Why
ComponentManager currently discovers components via entry points and orders them, but it lacks a clear contract for config-driven enable/disable, composite tool assembly, and lifecycle boundaries. We need a minimal, predictable design so component selection can be driven by configuration without surprising side effects.

## What Changes
- Define a config-aware component manager design (filters, composite tool recipes) and clarify lifecycle ownership (init/register/close) for managed vs injected components.
- Specify minimal behaviors for ToolManager to assemble composite tools from config recipes and to apply enable/disable lists consistently.
- Document the interface boundaries and event/logging expectations for component loading.

## Impact
- Affected specs: component-management
- Affected code: `dare_framework/component_manager.py`, composite tool wiring, related tests
