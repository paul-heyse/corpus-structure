"""S4 · LinkML compilation: the pack loader, the core shapes and the compilers (spike code).

Modules: ``paths`` (inputs and outputs), ``pack`` (SchemaView facts and the rules file),
``core_shapes`` (hand-written core Pydantic shapes, D2 §6), ``batch_models`` (per-predicate batch
models and JSON Schemas, D2 §7.3), ``sidetable`` (the entity-type side-table check), ``rules``
(rule language helper, view builder, rule compiler, D2 §7.4), ``reference`` (annotator reference,
D2 §7.5), ``tables`` (schema tables, D2 §7.1), ``gliner`` (GLiNER2 dicts, D2 §7.2).
"""
