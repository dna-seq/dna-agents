"""
dna-agents: Module compiler and agent definitions for DNA annotation.

Public API:
    CompilationResult   — result of spec compilation
    ValidationResult    — result of spec validation
    ModuleSpecConfig    — top-level model for module_spec.yaml
    validate_spec       — validate a module spec directory
    compile_module      — compile a spec to parquet
"""

from dna_agents.compiler import compile_module, validate_spec
from dna_agents.models import CompilationResult, ModuleSpecConfig, ValidationResult

__all__ = [
    "CompilationResult",
    "ValidationResult",
    "ModuleSpecConfig",
    "validate_spec",
    "compile_module",
]
