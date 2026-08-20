from __future__ import annotations

from inspect import iscoroutinefunction

from app.orchestrator.modules.base_module import BaseModule


class ModuleRegistry:
    """Dynamic registry for future orchestrator modules."""

    def __init__(self) -> None:
        self._modules: dict[str, BaseModule] = {}

    def register(self, module: BaseModule, name: str | None = None) -> None:
        """Register a module instance by its explicit or intrinsic name."""
        self._validate_module(module)
        module_name = name or module.name
        if not isinstance(module_name, str) or not module_name.strip():
            raise ValueError("Module name is required.")
        module_name = module_name.strip()
        if module_name in self._modules:
            raise ValueError(f"Module already registered: {module_name}")
        self._modules[module_name] = module

    def get(self, name: str) -> BaseModule:
        """Return a registered module by name."""
        try:
            return self._modules[name]
        except KeyError as exc:
            raise KeyError(f"Module is not registered: {name}") from exc

    def exists(self, name: str) -> bool:
        """Return whether a module is registered."""
        return name in self._modules

    def list_modules(self) -> list[str]:
        """Return registered module names in deterministic order."""
        return sorted(self._modules)

    @staticmethod
    def _validate_module(module: BaseModule) -> None:
        if not isinstance(module, BaseModule):
            raise TypeError("Module must implement BaseModule.")
        if not hasattr(module, "name"):
            raise ValueError("Module must define a name.")
        if not callable(getattr(module, "execute", None)):
            raise TypeError("Module must define an execute method.")
        if not iscoroutinefunction(module.execute):
            raise TypeError("Module execute method must be async.")
