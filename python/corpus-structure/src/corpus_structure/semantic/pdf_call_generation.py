"""Generate PDF native helper projections from the captured current DDO asset."""

from pathlib import Path

from corpus_structure.schema.code_generation import _format

from .metadata import get_metadata
from .native_call_generation import render_call_bindings, render_call_identifiers
from .pdf_domain import pdf_call_bindings


def generated_source(*, target_metadata=None, domain=None) -> str:
    target_metadata = get_metadata() if target_metadata is None else target_metadata
    return _format(
        "semantic/_pdf_native_calls.py",
        render_call_bindings(
            pdf_call_bindings(domain),
            target_metadata,
            canonical_identifiers=True,
            identifiers_module="._pdf_native_ids",
            context_validator=(".pdf_domain", "require_pdf_call_context"),
        ),
    )


def generated_enums(*, domain=None) -> str:
    return _format(
        "semantic/_pdf_native_ids.py",
        render_call_identifiers(pdf_call_bindings(domain), canonical_identifiers=True),
    )


def generated_producer_profiles(staging: bytes) -> str:
    """Realize the captured producer profile fields as lightweight worker code."""
    import yaml
    from linkml_runtime.utils.schemaview import SchemaView

    view = SchemaView(staging.decode())
    classes = yaml.safe_load(staging)["classes"]
    generic_name = "PdfNativePreparationIdentity"
    standard_name = "PdfStandardNativePreparationIdentity"
    generic = classes[generic_name]["annotations"]
    standard = classes[standard_name]["annotations"]
    generic_slots = view.class_induced_slots(generic_name)
    standard_slots = view.class_induced_slots(standard_name)
    generic_fields = tuple(str(slot.name) for slot in generic_slots)
    standard_fields = tuple(str(slot.name) for slot in standard_slots)
    (contract,) = tuple(name for name in standard_fields if name not in generic_fields)
    generic_id = generic["pds:preparation_profile"]
    standard_id = standard["pds:preparation_profile"]
    values = {
        "DEMAND_PREPARATION": generic_id,
        "STANDARD_PREPARATION": standard_id,
        "DEMAND_LOWERING": generic["pds:lowering_profile"],
        "STANDARD_LOWERING": standard["pds:lowering_profile"],
        "STANDARD_SCOPE": standard["pds:lowering_scope"],
        "STANDARD_CONTRACT_FIELD": contract,
        "PREPARATION_FIELDS": {generic_id: generic_fields, standard_id: standard_fields},
    }
    records = []
    for name, profile, slots in (
        ("DemandPreparationIdentity", generic_id, generic_slots),
        ("StandardPreparationIdentity", standard_id, standard_slots),
    ):
        fields = [f"class {name}(TypedDict):"]
        for slot in slots:
            annotation = (
                f"Literal[{profile!r}]"
                if slot.name == "profile"
                else "dict[str, Any] | None"
                if slot.range == "PdfRecordJson"
                else "str"
            )
            fields.append(f"    {slot.name}: {annotation}")
        records.append("\n".join(fields))
    return _format(
        "ingest/_pdf_producer_profiles.py",
        '"""Generated from the PDF staging producer declarations."""\n\n'
        + "from typing import Any, Literal, TypedDict\n\n"
        + "\n".join(f"{name} = {value!r}" for name, value in values.items())
        + "\n\n"
        + "\n\n".join(records)
        + "\n",
    )


if __name__ == "__main__":
    source, enums = generated_source(), generated_enums()
    Path(__file__).with_name("_pdf_native_calls.py").write_text(source)
    Path(__file__).with_name("_pdf_native_ids.py").write_text(enums)
