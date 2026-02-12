# Change: Add Hierarchical Configuration Management

## Why
The current static configuration system only supports flat configuration dictionaries and cannot handle multi-level configurations (system/user/project) or runtime configuration composition. This limits the framework's flexibility for different deployment scenarios and user contexts.

## What Changes
- Add a hierarchical configuration model with system/user/project levels and a deterministic override order
- Define a typed Config model for llm/mcp/allow_tools/allow_mcps and related metadata
- Specify a ConfigProvider interface that returns an effective Config and supports reload
- Define component enable/disable configuration for entry point components
- Clarify JSON file locations and composition rules (framework/user/project)
- Keep implementation out of scope for this proposal (interfaces and model design only)

## Impact
- Affected specs: configuration-management
- Affected code:
  - dare_framework/core/models/config.py (add Config model)
  - dare_framework/core/config.py (update IConfigProvider)
  - dare_framework/core/models/context.py (update SessionContext)
  - dare_framework/composition/component_manager.py (update load method)
