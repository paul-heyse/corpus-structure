"""Shared controlled inputs and builders for record consumers support."""

from copy import deepcopy
from types import MappingProxyType

import pytest

from corpus_structure.semantic import PreparationProfile, prepare_release
from corpus_structure.semantic.analytical_profile import analytical_inputs
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.record_contracts import interpretation_identity, record_identity
from corpus_structure.semantic.record_projection import ARTIFACT, project_record_reports
from corpus_structure.semantic.record_queries import CompletedRecordProjection
from semantic.record_contracts_support import (
    formula_record,
    measurement_record,
    record_from_fields,
    release_inputs,
    table_record,
)


@pytest.fixture(scope="module")
def prepared():
    bundle, _, _ = release_inputs()
    bundle, dependencies = analytical_inputs(bundle)
    return prepare_release(
        bundle, composed_dependencies(dependencies), PreparationProfile(version="semantic-2")
    )


def other_records():
    definition, _ = record_from_fields(
        "DefinitionRecordFields",
        "definition",
        (
            (
                "term",
                "literal",
                "#/texts/1",
                "native",
                "variable",
                {"kind": "text", "text": "variable"},
            ),
            (
                "defining_text",
                "literal",
                "#/texts/2",
                "native",
                "map",
                {"kind": "text", "text": "map"},
            ),
            (
                "scope",
                "native",
                "#/groups/1",
                "native",
                None,
                {"kind": "native_location", "pointer": "#/groups/1"},
            ),
        ),
        (("alias", "literal", False), ("relation_type", "classified", False)),
    )
    assertion, _ = record_from_fields(
        "AssertionRecordFields",
        "assertion",
        (
            ("subject", "literal", "#/texts/1", "native", "X", {"kind": "text", "text": "X"}),
            (
                "predicate",
                "literal",
                "#/texts/2",
                "native",
                "may grow",
                {"kind": "text", "text": "may grow"},
            ),
            (
                "object",
                "literal",
                "#/texts/3",
                "native",
                "12",
                {"kind": "decimal", "lexical": "12"},
            ),
        ),
        tuple(
            (role, "classified" if role in {"polarity", "modality"} else "literal", True)
            for role in (
                "polarity",
                "modality",
                "attribution",
                "condition",
                "quantification",
                "scope",
            )
        ),
    )
    return definition, assertion


@pytest.fixture
def projection(prepared):
    table, _ = table_record()
    # A rejected alternative and its computation dependency remain separately visible.
    fields = [dict(field) for field in table["fields"]]
    fields[4]["alternatives"] = (
        dict(
            alternative_id="other-cell-value",
            reason="competing source reading",
            value={"kind": "decimal", "lexical": "12.000"},
            evidence_sets=fields[4]["evidence_sets"],
        ),
    )
    table["fields"] = tuple(fields)
    originals = (table, measurement_record()[0], formula_record()[0], *other_records())
    records = []
    for original in originals:
        record = deepcopy(original)
        record["standing"] = "candidate"
        record["record_id"] = record_identity(prepared.release_id, record)
        record["interpretation_id"] = interpretation_identity(record)
        records.append(record)
    reports = [
        dict(
            selected_task_id=71,
            origin_task_id=23,
            cut_id=9,
            source="source:table",
            outcome="complete",
            records=records,
        ),
        dict(
            selected_task_id=72,
            origin_task_id=24,
            cut_id=9,
            source="source:empty",
            outcome="empty",
            records=(),
        ),
        dict(
            selected_task_id=73,
            origin_task_id=25,
            cut_id=9,
            source="source:absent",
            outcome="complete",
            records=None,
        ),
    ]
    return CompletedRecordProjection(
        run_id=41,
        release_id=prepared.release_id,
        realization_id="z",
        data_revision=0,
        cut_id=9,
        projection_digest=next(
            artifact.digest for artifact in prepared.artifacts if artifact.kind == ARTIFACT
        ),
        prepared=prepared,
        rows=project_record_reports(prepared, reports),
        source_view_ids=None,
        report_source_view_ids=MappingProxyType({71: 7, 72: 8, 73: 9}),
    )
