"""Cross-domain shared contracts (infra).

This package contains small, dependency-free interfaces and types used across
multiple domains (config, builder, and pluggable components).
"""

from dare_framework.infra.component import ComponentType, IComponent

__all__ = ["ComponentType", "IComponent"]

