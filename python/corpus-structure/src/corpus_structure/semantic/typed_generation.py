"""Generate the static surfaces consumed by fixed relational operations."""

from pathlib import Path

from corpus_structure.schema.generate import _format
from corpus_structure.schema.relational import render_typed_columns

from .metadata import metadata

# Operation selection only; every field, type and optionality comes from the model.
TYPED_RELATIONS = (
    "sem.runtime_binding",
    "ops.pdf_stage_document",
    "ops.pdf_stage_native",
    "ops.pdf_stage_membership",
    "ops.pdf_stage_reference",
    "ops.pdf_stage_artifact_stream",
    "ops.pdf_stage_artifact_part",
)


def generated_identifiers(model=metadata) -> str:
    """One current nominal owner, projected from explicit physical declarations."""
    from keyword import iskeyword

    declarations = {}
    for relation in model.tables.values():
        for column in relation.columns:
            if qualified := column.info.get("python_type"):
                module, name = qualified.rsplit(".", 1)
                base = column.type.python_type
                if (
                    module != "corpus_structure.semantic.identifiers"
                    or base not in {str, int}
                    or iskeyword(name)
                ):
                    raise ValueError("unsupported canonical physical nominal " + qualified)
                if name in declarations and declarations[name] != base.__name__:
                    raise ValueError("inconsistent canonical physical nominal " + qualified)
                declarations[name] = base.__name__
    return _format(
        "semantic/identifiers.py",
        "\n".join(
            [
                '"""Current semantic identifiers generated from explicit physical declarations."""',
                "from typing import NewType",
                "",
                *(
                    f"{name} = NewType({name!r}, {base})"
                    for name, base in sorted(declarations.items())
                ),
                "",
            ]
        ),
    )


def generated_source(model=metadata) -> str:
    from hashlib import sha256

    from corpus_structure.schema.relational import column_type_annotation

    from .identity import canonical_bytes

    bindings, imports, facts = {}, set(), {}
    for relation in TYPED_RELATIONS:
        target = model.tables[relation]
        fields = bindings[relation] = {}
        for column in target.columns:
            fields[column.name] = column_type_annotation(column)
            if qualified := column.info.get("python_type"):
                module, name = qualified.rsplit(".", 1)
                if module != "corpus_structure.semantic.identifiers":
                    raise ValueError("typed columns require the canonical physical nominal owner")
                imports.add(name)
            facts[f"{relation}.{column.name}"] = {
                "type": fields[column.name],
                "nominal": column.info.get("python_type"),
                "enum": column.info.get("enum", ()),
            }
    physical_id = model.info["physical_model_id"]
    identity = sha256(
        canonical_bytes(
            {"renderer": "semantic-typed-columns/3", "physical": physical_id, "bindings": facts}
        )
    ).hexdigest()
    return _format(
        "semantic/_typed_columns.py",
        render_typed_columns(
            model,
            TYPED_RELATIONS,
            physical_id,
            bindings=bindings,
            imports=imports,
            identifiers_module=".identifiers",
            type_model_id=identity,
        ),
    )


def generated_fates() -> str:
    from .data_operation_protocol import generated_fate_source
    from .metadata import PHYSICAL_MODEL

    return _format(
        "semantic/_data_operation_fates.py",
        generated_fate_source(PHYSICAL_MODEL.with_name("data-operation-native.yaml").read_bytes()),
    )


if __name__ == "__main__":
    Path(__file__).with_name("identifiers.py").write_text(generated_identifiers())
    Path(__file__).with_name("_typed_columns.py").write_text(generated_source())
    Path(__file__).with_name("_data_operation_fates.py").write_text(generated_fates())
