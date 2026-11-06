"""Native candidate alternative custody; no acceptance or model-quality claim."""

from copy import deepcopy

from sqlalchemy import select

from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import seal_cut
from corpus_structure.semantic.record_contracts import (
    evidence_set_identity,
    interpretation_identity,
)
from corpus_structure.semantic.record_projection import RECORD_ROW_TYPES, reconstruct_record
from semantic.native_record_fixtures import private_source_options as private_source_options

from .native_record_fixtures import candidate, complete
from .native_record_fixtures import private_source as private_source


def test_unresolved_value_alternative_keeps_own_evidence_through_publication(private_source):
    case = private_source
    original = deepcopy(candidate(case))
    field = next(item for item in original["fields"] if item["role"] == "value")
    literal_set = next(
        item for item in original["evidence_sets"] if item["set_id"] == field["evidence_sets"][0]
    )
    inspected_set = dict(literal_set, usage="context")
    inspected_set["set_id"] = evidence_set_identity(inspected_set)
    original["evidence_sets"] = (*original["evidence_sets"], inspected_set)
    actual_value = field.pop("value")
    field.pop("original", None)
    field.pop("original_pieces", None)
    field.update(
        state="unresolved",
        reason="independent inspection leaves this reading unresolved",
        evidence_sets=(inspected_set["set_id"],),
        alternatives=(
            dict(
                alternative_id="controlled-actual-value-alternative",
                value=actual_value,
                evidence_sets=(literal_set["set_id"],),
                reason="actual located value retained as a candidate alternative",
            ),
        ),
    )
    original["interpretation_id"] = interpretation_identity(original)
    with case.writer.begin() as conn:
        complete(case, conn, (original,))
        cut = seal_cut(conn, case.run, "candidate-alternative-final", final=True)
    result = consolidate_cut(case.writer, cut, "candidate-alternative-publication")
    with case.writer.connect() as conn:
        rows = {
            name: conn.execute(
                select(table("data." + name)).where(
                    table("data." + name).c.release_id == case.prepared.release_id,
                    table("data." + name).c.realization_id == result.realization_id,
                )
            )
            .mappings()
            .all()
            for name in RECORD_ROW_TYPES
        }
    restored = reconstruct_record(rows, original["record_id"], original["interpretation_id"])
    assert restored == original
    restored_field = next(item for item in restored["fields"] if item["role"] == "value")
    assert restored_field["state"] == "unresolved" and "value" not in restored_field
    assert restored_field["evidence_sets"] == (inspected_set["set_id"],)
    assert restored_field["alternatives"][0]["evidence_sets"] == (literal_set["set_id"],)
    assert rows["record_admission"][0]["decision"] == "candidate"
    assert rows["record_assertion"] == []
