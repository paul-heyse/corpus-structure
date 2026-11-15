"""Actual current record families lower completely, with independent evidence refusals."""

from copy import deepcopy
from functools import cache

import pytest

from corpus_structure.semantic import prepare_release
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.rich_knowledge_sources import rich_knowledge_schema_inputs, rich_knowledge_declarations
from corpus_structure.semantic.rich_record_readings import rich_reading_value
from corpus_structure.semantic.types import ResolvedDependencies
from semantic.record_contracts_support import release_inputs
from evaluate.declared_record_grading_support import current_reading


@cache
def current():
    bundle, deps = rich_knowledge_schema_inputs(release_inputs()[0], ResolvedDependencies(),
        qualification_class="StatisticsQualification", statement_class="SourceStatement")
    return prepare_release(bundle, deps), compile_data_operations(bundle, declarations=rich_knowledge_declarations(deps))


def inspected_reading(family):
    from corpus_structure.semantic.record_contracts import anchor_identity, evidence_set_identity, interpretation_identity
    row, coordinates = current_reading(family)
    row = deepcopy(row)
    row["standing"] = "candidate"
    # This controlled producer inspected the actual selected native source scope
    # for every absent role, rather than asserting absence from missing evidence.
    anchors, sets = list(row["anchors"]), list(row["evidence_sets"])
    for field in row["fields"]:
        if field["evidence_status"] == "unavailable" and field["state"] != "present":
            anchor = dict(pin=row["pin"], space="native", pointer=row["pin"]["section_pointer"], precision="item")
            anchor["anchor_id"] = anchor_identity(anchor)
            if anchor not in anchors:
                anchors.append(anchor)
            evidence = dict(role=field["role"], ordering="ordered", usage="context", anchors=(anchor["anchor_id"],))
            evidence["set_id"] = evidence_set_identity(evidence)
            sets.append(evidence)
            field["evidence_sets"] = (evidence["set_id"],)
            field["evidence_status"] = "available"
    row["anchors"], row["evidence_sets"] = tuple(anchors), tuple(sets)
    row["interpretation_id"] = interpretation_identity(row)
    return row, coordinates


@pytest.mark.parametrize("family,class_name",[("definition","DefinitionReading"),("assertion","QualifiedAssertionReading"),("measurement","MeasurementReading"),("table","TableAssertionReading"),("formula_context","FormulaContextReading")])
def test_complete_source_reading_values_keep_every_original_field_without_scientific_fact(family,class_name):
    prepared,model=current()
    row,coordinates=inspected_reading(family)
    value=rich_reading_value(prepared,model,row,coordinate_texts=coordinates)
    assert value.class_name==class_name
    assert set(value.fields)=={field["role"] for field in row["fields"]}
    assert all("role" not in field and "evidence_sets" not in field and "alternatives" not in field for field in value.fields.values())
    assert row["standing"]=="candidate"
    assert not hasattr(value,"fact_id")


def test_incomplete_reading_has_no_partial_lowering_and_no_forged_evidence():
    prepared,model=current()
    row,coordinates=inspected_reading("table")
    original=deepcopy(row)
    for change in ("missing-field","missing-support","forged-coordinate"):
        invalid=deepcopy(row)
        texts=coordinates
        if change=="missing-field":
            invalid["fields"]=invalid["fields"][:-1]
        elif change=="missing-support":
            invalid["fields"][0]["evidence_sets"]=()
        else:
            texts=[{**value,"text":"forged source"} for value in coordinates]
        with pytest.raises(ValueError):
            rich_reading_value(prepared,model,invalid,coordinate_texts=texts)
    assert row==original
