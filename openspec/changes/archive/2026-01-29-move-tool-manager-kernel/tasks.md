## 1. Spec updates
- [x] 1.1 Update interface-layer requirements for ToolManager location and default gateway.

## 2. Code changes
- [x] 2.1 Move `IToolManager` to `tool/kernel.py` and update imports/exports.
- [x] 2.2 Remove `DefaultToolGateway` and update references to `ToolManager`.
- [x] 2.3 Update docs/examples/tests to match new paths and gateway usage.

## 3. Validation
- [x] 3.1 Run `openspec validate move-tool-manager-kernel --strict`.
