"""v2 entrypoint group names for plugin-extensible component categories.

These group names intentionally do not match the legacy v1 groups. The project does
not require compatibility with v1, and the v2 names prevent accidental mixing of
components that target different contracts.

Note: The framework may ship no-op plugin managers initially; group names still
exist as a stable contract for plugin authors.
"""

ENTRYPOINT_V2_TOOLS = "dare_framework.v2.tools"
ENTRYPOINT_V2_MODEL_ADAPTERS = "dare_framework.v2.model_adapters"
ENTRYPOINT_V2_VALIDATORS = "dare_framework.v2.validators"
ENTRYPOINT_V2_PLANNERS = "dare_framework.v2.planners"
ENTRYPOINT_V2_REMEDIATORS = "dare_framework.v2.remediators"
ENTRYPOINT_V2_PROTOCOL_ADAPTERS = "dare_framework.v2.protocol_adapters"
ENTRYPOINT_V2_HOOKS = "dare_framework.v2.hooks"
ENTRYPOINT_V2_CONFIG_PROVIDERS = "dare_framework.v2.config_providers"

# Optional placeholders (reserved for future expansion).
ENTRYPOINT_V2_MEMORY = "dare_framework.v2.memory"
ENTRYPOINT_V2_PROMPT_STORES = "dare_framework.v2.prompt_stores"
ENTRYPOINT_V2_SKILLS = "dare_framework.v2.skills"
