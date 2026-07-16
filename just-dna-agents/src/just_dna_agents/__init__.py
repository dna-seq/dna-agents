"""
just-dna-agents: agent definitions and tooling for DNA annotation module creation.

The module spec schema and compiler now live in the shared libraries — import them directly:

    from just_dna_format.spec import ModuleSpecConfig, VariantRow, StudyRow
    from just_dna_compiler.compiler import validate_spec, compile_module, reverse_module
    from just_dna_compiler.models import ValidationResult, CompilationResult

This package provides the agents-specific layer: paper downloading (`papers`), HF module
downloading (`modules`), eval scoring (`eval_scorer`), and Ensembl cache provisioning (`resolver`).
"""
