"""config domain facade."""

from dare_framework3_4.config.interfaces import (
    IHookManager,
    IModelAdapterManager,
    IPlannerManager,
    IProtocolAdapterManager,
    IRemediatorManager,
    IToolManager,
    IValidatorManager,
)
from dare_framework3_4.config.kernel import IConfigProvider
from dare_framework3_4.config.types import ConfigSnapshot

__all__ = [
    "ConfigSnapshot",
    "IConfigProvider",
    "IHookManager",
    "IModelAdapterManager",
    "IPlannerManager",
    "IProtocolAdapterManager",
    "IRemediatorManager",
    "IToolManager",
    "IValidatorManager",
]
