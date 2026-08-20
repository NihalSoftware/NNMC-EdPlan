"""Module contracts and registry for the EdPlan orchestrator."""

from app.orchestrator.modules.base_module import BaseModule
from app.orchestrator.modules.example_module import EXAMPLE_MODULE, ExampleModule
from app.orchestrator.modules.module_registry import ModuleRegistry

__all__ = ["BaseModule", "EXAMPLE_MODULE", "ExampleModule", "ModuleRegistry"]
