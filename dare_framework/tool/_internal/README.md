Tool Internal Layout (dare_framework)

This directory contains non-public implementations for the tool domain.
Imports should prefer `dare_framework.tool` or `dare_framework.tool._internal`
aggregates; the subpackages below organize internal responsibilities.

Subpackages
- adapters: protocol adapters (example: MCP adapter + no-op client).
- control: execution control plane (pause/resume/checkpoints).
- gateway: tool gateway implementations (capability registry + invoke).
- providers: capability providers / manager-style adapters.
- toolkits: tool aggregation helpers (example: MCP toolkit).
- tools: built-in tools shipped with the framework.
- utils: shared utilities for tool implementations.

Manager vs built-in tools
- Manager-style components live in `gateway/`, `providers/`, and `toolkits/`.
- System/built-in tools live in `tools/` (file/command helpers, noop/echo).

Naming
- Use snake_case for file and function names.
- Keep new internal modules in the appropriate subpackage and re-export
  through `dare_framework.tool._internal.__init__` when needed.
