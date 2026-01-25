## 1. Implementation
- [x] 1.1 Add typed config models in `dare_framework3_4/config/types.py` (LLMConfig, ComponentConfig, Config, ComponentType, proxy support) with defaults and `from_dict`/`to_dict` helpers.
- [x] 1.2 Update ConfigSnapshot to hold the effective Config and adjust config exports accordingly.
- [x] 1.3 Wire managers to respect `components.<type>.disabled` and per-component config (validators, hooks, skills, tools, model adapters, MCP). (Implemented Config helpers; no manager implementations exist in 3_4.)
- [x] 1.4 Ensure the config provider builds a Config from layered sources and returns a new snapshot on reload.
- [x] 1.5 Add/adjust tests for config parsing, component enablement, and snapshot immutability.
- [x] 1.6 Validate with `openspec validate update-runtime-config-model-3-4 --strict`.
- [x] 1.7 Implement a file-backed IConfigProvider that loads user/workspace config JSON and merges layers.
- [x] 1.8 Add a config facade factory that constructs the default IConfigProvider for agent initialization.
