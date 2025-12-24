# Change: Add core runtime main flow

## Why
The project currently has design documentation but no executable runtime flow. We need a production-ready core orchestration loop that follows the design so the framework can execute sessions, milestones, and tools deterministically.

## What Changes
- Add the core runtime main flow (Session/Milestone/Plan/Execute/Tool loops) per the architecture design.
- Define the minimal data models and error types required to run the flow.
- Provide interface stubs for pluggable components (model adapter, tool runtime, policy engine, event log, checkpoint, validator, remediator, context assembler).

## Impact
- Affected specs: runtime-core
- Affected code: new `dare_framework/` core and component modules
