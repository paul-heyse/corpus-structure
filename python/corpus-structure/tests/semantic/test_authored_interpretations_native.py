"""Real authored admission/grouped-read custody over controlled native cell readings.

The source conversion and candidate producer are controlled. Their CPU execution,
completion, source selection and AuthoredFactRef admissions are actual native work;
this supplies no provider-accuracy or accepted-scientific-knowledge evidence.
"""

from copy import deepcopy
from typing import cast

import pytest
from evaluate.declared_record_native_support import PROJECT, authored, request, run_readings
from evaluate.declared_record_native_support import current_record_policy as current_record_policy
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.demand_results import read_demand_result
from corpus_structure.semantic.grouped_record_interpretations import (
    AuthoredJudgmentRead,
    GroupedInterpretationRequest,
    InterpretationRoot,
)
from corpus_structure.semantic.interpretations import metadata_binding
from corpus_structure.serve.interpretation_authoring import author_interpretations
from corpus_structure.serve.interpretations import group_selected_interpretations


def _read(journey, selection):
    with journey.kernel.purpose("read").begin() as connection:
        return group_selected_interpretations(connection, selection).model_dump(mode="python")[
            "body"
        ]


def _authored_read(journey, report):
    products = tuple(row["product_id"] for row in report["authored_admissions"])
    scope = {"product_ids": list(products)}
    with journey.kernel.purpose("read").begin() as connection:
        page = read_demand_result(
            connection,
            report["demand_id"],
            project_id=PROJECT,
            scope=scope,
            limit=1000,
        )
    return AuthoredJudgmentRead(
        demand_id=report["demand_id"],
        read_id=page.cut.record["read_id"],
        expected_cut=page.cut.identity,
        scope=scope,
        product_ids=products,
    ), page


def test_actual_authored_measurement_terminology_admission_and_grouped_private_read(
    current_record_policy,
):
    journey = current_record_policy
    source = journey.sources[0]
    population = run_readings(
        journey,
        (source,),
        policy=None,
        inference="authored-source-judgment-candidates",
        family="measurement",
    )
    product, _ = population.raw[0]
    primary = GroupedInterpretationRequest(
        project_id=PROJECT,
        demand_id=population.demand_id,
        roots=(InterpretationRoot(product_id=product["id"]),),
    )
    initial = _read(journey, primary)
    assert len(initial["items"]) == 2
    group = initial["items"][0]
    assert len(group["readings"]) == 2 and group["family"] == "measurement"
    reading = next(
        item
        for item in group["readings"]
        if next(field for field in item["body"]["fields"] if field["role"] == "original_value")[
            "state"
        ]
        == "present"
    )
    row = reading["body"]
    field = next(field for field in row["fields"] if field["role"] == "original_value")
    evidence = next(
        item for item in row["evidence_sets"] if item["set_id"] == field["evidence_sets"][0]
    )
    anchor = next(item for item in row["anchors"] if item["anchor_id"] == evidence["anchors"][0])
    assert anchor["source_piece"] == "12"
    cut = initial["cut"]
    source_record = {
        **{
            name: cut[name]
            for name in ("project_id", "demand_id", "read_id", "release_id", "runtime_id")
        },
        "cut_id": initial["cut_id"],
        "read_scope_json": json_bytes(cut["scope"]).decode(),
        "product_id": product["id"],
        "member_id": reading["reference"]["member_id"],
        "kind_contract": reading["reference"]["kind_contract"],
        "family_contract": group["family_contract"],
        "record_id": group["record_id"],
        "interpretation_id": reading["interpretation_id"],
        "source_pin": row["pin"],
    }
    focus = {
        "role": "original_value",
        **{key: anchor[key] for key in ("anchor_id", "start", "end", "source_piece")},
    }
    digest, _metadata = metadata_binding(journey.kernel.prepared)
    common = dict(
        source_record=source_record,
        standing="private_authored_judgment",
        vocabulary_release=journey.kernel.prepared.release_id,
        metadata_digest=digest,
    )
    measurement = dict(
        **common,
        judgment_type="measurement.interpretation",
        focus=focus,
        outcome="unresolved",
        basis_status="unknown",
        numerical_equivalence="unassessed",
        assessment="This native numeric cell does not identify a unit or measurement basis.",
        reviewer="controlled actual source reviewer",
    )
    terminology = dict(
        **common,
        judgment_type="terminology.interpretation",
        lookup_policy="released-lexical-1",
        decisions=[
            dict(
                field="distribution_family",
                focus=focus,
                candidates=[],
                outcome="no_match",
                assessment="This numeric cell states no statistical distribution family.",
                reviewer="controlled actual source reviewer",
            )
        ],
    )
    kinds = {item.name: item.iri for item in journey.kernel.prepared.definitions}

    def admit(values, suffix):
        selections = tuple(
            authored(
                journey,
                suffix + ":" + name,
                value,
                kind=kind,
                context=source.context,
                author="actual operator assertion",
                selection_id=suffix + ":" + name,
            )
            for name, kind, value in values
        )
        pending = request(
            journey,
            ("fixture.record_candidates",),
            (source.context,),
            originals=selections,
            source_sets=(FrozenSourceSet.from_selected("fixture-record-sources", (source.entry(),)),),
            inference=suffix,
        )
        return author_interpretations(
            journey.kernel.purpose("write"),
            journey.kernel.prepared,
            request=pending,
        )

    for mutation in ("member", "cut", "source", "context"):
        forged = deepcopy(measurement)
        if mutation in {"member", "cut"}:
            forged["source_record"][mutation + "_id"] = "foreign:" + mutation
        else:
            source_pin = forged["source_record"]["source_pin"]
            assert isinstance(source_pin, dict)
            source_pin["document" if mutation == "source" else "subject"] = "foreign:" + mutation
        with pytest.raises((ValueError, DBAPIError)):
            admit(
                ((mutation, kinds["DdoAuthoredMeasurementJudgment"], forged),), "refuse:" + mutation
            )

    with journey.kernel.engine.connect() as connection:
        before = connection.scalar(text("SELECT count(*) FROM ops.data_derivation"))
    retained = admit(
        (
            ("measurement", kinds["DdoAuthoredMeasurementJudgment"], measurement),
            ("terminology", kinds["DdoAuthoredTerminologyJudgment"], terminology),
        ),
        "actual-authored-judgments",
    )
    assert retained["standing"] == "authored" and retained["selected"] is False
    with journey.kernel.engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == before
    selected_authored, _ = _authored_read(journey, retained)
    selected = primary.model_copy(
        update={
            "read_id": cut["read_id"],
            "expected_cut": initial["cut_id"],
            "authored_reads": (selected_authored,),
        }
    )
    answer = _read(journey, selected)
    actual = next(item for item in answer["items"] if item["record_id"] == group["record_id"])
    assert actual["readings"] == group["readings"]
    assert actual["standing"] == "private_uncalibrated_candidates"
    assert len(actual["authored_judgments"]) == 2
    assert {item["body"]["judgment_type"] for item in actual["authored_judgments"]} == {
        "measurement.interpretation",
        "terminology.interpretation",
    }
    assert all(
        item["reference"]["support_references"][0]["kind"] == "authored"
        for item in actual["authored_judgments"]
    )
    assert all(
        item["standing"] == "private_authored_judgment" for item in actual["authored_judgments"]
    )
    assert all(
        item["author"] == "actual operator assertion" for item in actual["authored_judgments"]
    )
    assert (
        next(
            item["body"]
            for item in actual["authored_judgments"]
            if item["body"]["judgment_type"] == "measurement.interpretation"
        )["numerical_equivalence"]
        == "unassessed"
    )

    generic = admit((("generic", "primitive:integer", 41),), "generic-authored-fact")
    generic_read, _ = _authored_read(journey, generic)
    with pytest.raises(ValueError, match="captured judgment kind"):
        _read(journey, selected.model_copy(update={"authored_reads": (generic_read,)}))

    revoked = retained["authored_admissions"][0]
    with journey.kernel.purpose("write").begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": PROJECT,
                    "original_source": source.context.original_source,
                    "selector_kind": "original-admission",
                    "selector": revoked["admission_id"],
                    "reason": "controlled authored judgment validity refusal",
                },
            )
        )
    refreshed, page = _authored_read(journey, retained)
    assert revoked["admission_id"] not in {
        item["admission_id"] for item in page.record["original_source_admissions"]
    }
    with pytest.raises((ValueError, DBAPIError)):
        _read(journey, selected.model_copy(update={"authored_reads": (refreshed,)}))
