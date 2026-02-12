## 1. Implementation
- [x] 1.1 Add approval domain models and deterministic matcher strategies in tool control internals.
- [x] 1.2 Add workspace/user persistent rule stores and session/one-shot in-memory stores.
- [x] 1.3 Add `ToolApprovalManager` APIs for evaluate/pending/grant/deny/revoke.
- [x] 1.4 Integrate approval gating into `DareAgent` tool loop for `requires_approval` capabilities.
- [x] 1.5 Wire approval manager creation/injection in agent builder.
- [x] 1.6 Add transport actions and action handler support for listing/granting/denying/revoking approvals.
- [x] 1.7 Ensure action payloads are deterministic and include sufficient request/rule metadata.

## 2. Tests
- [x] 2.1 Add unit tests for matcher behavior (`capability`, `exact_params`, `command_prefix`).
- [x] 2.2 Add unit tests for persistent rule store read/write semantics.
- [x] 2.3 Add unit tests for pending approval lifecycle (request -> grant/deny -> unblock).
- [x] 2.4 Add integration-oriented unit tests for tool-loop auto-pass after prior approval.
- [x] 2.5 Add unit tests for approval action handler operations and error cases.

## 3. Validation
- [x] 3.1 Run `openspec validate add-tool-approval-memory --strict`.
- [x] 3.2 Run targeted pytest suites for approval manager, interaction handlers, and agent tool loop.
