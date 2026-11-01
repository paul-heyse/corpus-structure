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
    return _format(
        "semantic/_typed_columns.py",
        render_typed_columns(metadata, TYPED_RELATIONS, PHYSICAL_MODEL_ID),
    )


if __name__ == "__main__":
    Path(__file__).with_name("_typed_columns.py").write_text(generated_source())
