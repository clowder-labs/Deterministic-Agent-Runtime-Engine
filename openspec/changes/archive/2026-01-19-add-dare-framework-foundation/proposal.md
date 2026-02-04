# Change: Establish DARE framework foundation (v1.3 runtime + interface layer + example agent)

## Why
The v1.3 architecture and v1.1 interface designs are finalized but not yet captured as executable specs or task breakdowns. We need a clear, validated OpenSpec proposal to implement the five-layer runtime, core interfaces, and a runnable example agent with deterministic (mocked) LLM behavior for flow validation.

## What Changes
- Define new specs for the core runtime loop (five-layer orchestration + state machine + event logging).
- Define new specs for the interface layer (all core interfaces per UML A.1, AgentBuilder composition, and optional MCP integration surface).
- Define new specs for the example coding agent (framework-backed, deterministic/mock mode + optional real model adapter).

## Impact
- Affected specs: new capabilities `core-runtime`, `interface-layer`, `example-agent`.
- Affected code: new modules under `dare_framework/` plus updates in `examples/coding-agent/` (implementation in apply stage).
- References: `docs/design/archive/Architecture_Final_Review_v1.3.md`, `docs/design/archive/Interface_Layer_Design_v1.1_MCP_and_Builtin.md`.
