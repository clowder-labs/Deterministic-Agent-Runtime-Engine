# Change: Move builder API into agent domain and expose builders via BaseAgent

## Why
The builder API currently lives in a separate `builder` domain even though it is part of the agent developer surface. This proposal consolidates composition under the agent domain, removes the standalone builder module, and exposes builder factories directly on `BaseAgent` to simplify usage.

## What Changes
- **BREAKING**: Remove `dare_framework.builder` package and the `Builder` facade.
- Move builder implementation into the `dare_framework.agent` domain while preserving existing builder logic.
- Promote `BaseAgent` to a public agent-domain module and expose `BaseAgent.simple_chat_agent_builder(...)` and `BaseAgent.five_layer_agent_builder(...)` as the new entry points.
- Update examples, tests, and docs to use the new `BaseAgent` builder API.

## Impact
- Affected specs: `interface-layer`, `example-agent`.
- Affected code: `dare_framework/builder/`, `dare_framework/agent/`, examples, unit tests, and documentation referencing the builder facade.
