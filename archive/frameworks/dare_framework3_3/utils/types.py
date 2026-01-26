"""[Types] Common utility types used across the framework."""

from __future__ import annotations


class BaseComponent:
    """Base class for pluggable components.

    Provides common functionality for components that can be
    discovered and loaded via the plugin system.
    """

    order = 100

    @property
    def component_name(self) -> str:
        """Return the component name."""
        name = getattr(self, "name", None)
        if isinstance(name, str):
            return name
        return self.__class__.__name__

    async def init(
        self,
        config: object | None = None,
        prompts: object | None = None,
    ) -> None:
        """Initialize the component with configuration."""
        pass

    async def close(self) -> None:
        """Clean up component resources."""
        pass


__all__ = ["BaseComponent"]
