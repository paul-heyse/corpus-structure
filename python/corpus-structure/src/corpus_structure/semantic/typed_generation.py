"""Generate the static surfaces consumed by fixed relational operations."""

from pathlib import Path

from corpus_structure.schema.generate import _format
from corpus_structure.schema.relational import render_typed_columns

from .metadata import PHYSICAL_MODEL_ID, metadata

# Operation selection only; every field, type and optionality comes from the model.
TYPED_RELATIONS = (
    "data.occurrence",
    "ops.pdf_stage_document",
    "ops.pdf_stage_native",
    "ops.pdf_stage_membership",
    "ops.pdf_stage_reference",
    "ops.pdf_stage_artifact_stream",
    "ops.pdf_stage_artifact_part",
)


def generated_source() -> str:
    from dataclasses import asdict
    from hashlib import sha256

    from .contracts import OperationFieldBinding, compile_execution_model, trusted_execution_inputs
    from .identity import canonical_bytes
    from .operation_call_generation import _PRIMITIVES, source_bindings

    inputs = trusted_execution_inputs()
    model = compile_execution_model(inputs)
    _, nominal, _, resolve = source_bindings(model, inputs)
    bindings, imports, facts = {}, set(), {}
    for relation in TYPED_RELATIONS:
        target = metadata.tables[relation]
        fields = bindings[relation] = {}
        for column in target.columns:
            reference = f"physical:{target.schema}.{target.info['model_class']}.{column.name}"
            binding = OperationFieldBinding(column.name, reference, bool(column.nullable))
            resolved, source = resolve(binding, {})
            name = nominal(reference)
            kind = name or (
                "Literal[" + ", ".join(repr(v) for v in resolved.enum_values) + "]"
                if resolved.enum_values
                else _PRIMITIVES[resolved.kind]
            )
            if name:
                imports.add(name)
            if resolved.multivalued:
                kind = f"list[{kind}]"
            if column.nullable:
                kind += " | None"
            fields[column.name] = kind
            facts[reference] = {"source": source, "nominal": name, "type": asdict(resolved)}
    identity = sha256(
        canonical_bytes(
            {
                "renderer": "semantic-typed-columns/2",
                "physical": PHYSICAL_MODEL_ID,
                "bindings": facts,
            }
        )
    ).hexdigest()
    return _format(
        "semantic/_typed_columns.py",
        render_typed_columns(
            metadata,
            TYPED_RELATIONS,
            PHYSICAL_MODEL_ID,
            bindings=bindings,
            imports=imports,
            type_model_id=identity,
        ),
    )


if __name__ == "__main__":
    Path(__file__).with_name("_typed_columns.py").write_text(generated_source())
