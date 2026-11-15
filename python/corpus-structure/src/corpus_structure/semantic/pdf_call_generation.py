"""Generate PDF native helper projections from the captured current DDO asset."""

from pathlib import Path

from corpus_structure.schema.generate import _format

from .metadata import metadata
from .native_call_generation import render_call_bindings, render_call_identifiers
from .pdf_domain import pdf_call_bindings


def generated_source() -> str:
    return _format(
        "semantic/_pdf_native_calls.py",
        render_call_bindings(
            pdf_call_bindings(),
            metadata,
            canonical_identifiers=True,
            identifiers_module="._pdf_native_ids",
            context_validator=(".pdf_domain", "require_pdf_call_context"),
        ),
    )


def generated_enums() -> str:
    return _format(
        "semantic/_pdf_native_ids.py",
        render_call_identifiers(pdf_call_bindings(), canonical_identifiers=True),
    )


if __name__ == "__main__":
    Path(__file__).with_name("_pdf_native_calls.py").write_text(generated_source())
    Path(__file__).with_name("_pdf_native_ids.py").write_text(generated_enums())
