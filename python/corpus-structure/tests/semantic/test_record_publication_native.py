"""Actual rich publication and selected readers; no legacy run/row projection custody."""

import os
from decimal import Decimal

import pytest
from evaluate.declared_record_native_support import PROJECT, ROOT
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.rich_knowledge_contracts import DdoRichEntity, DdoRichOccurrence
from corpus_structure.semantic.rich_queries import (
    ClaimsQuery,
    EntityQuery,
    RichQueryRefused,
    SourceReadingsQuery,
)
from semantic.record_publication_native_support import (
    authored_propositions,
    publication_recipe,
    publish_authored,
    query_publication,
)
from semantic.record_publication_native_support import (
    authored_publication as authored_publication,
)
from semantic.record_publication_native_support import (
    rich_publication as rich_publication,
)


def number(value):
    return {"kind": "number", "number": Decimal(value)}


def test_publication_prepares_current_rich_contracts_and_authored_semantics(tmp_path):
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.rich_graph_validation import read_rich_graph
    from semantic.data_operation_kernel_support import prepare_kernel

    preparation = prepare_kernel(publication_recipe(tmp_path))
    model = preparation.model
    assert {"rich.consolidate", "rich.admit"} <= {op.semantic_id for op in model.operations}
    assert all(item.complete for item in model.implementation_slices)
    context = SubjectContext(
        PROJECT,
        "knowledge:" + PROJECT,
        None,
        b"{}",
        subject_definition=model.operation("rich.consolidate").subject,
    )
    propositions = authored_propositions(preparation.prepared, model, context, (number("12"),))
    read_rich_graph(
        preparation.prepared, model, context=context, graph=propositions, inputs=(), whole_inputs=()
    )
    assert propositions.standing == "authored-propositions"
    assert any(isinstance(packet.body, DdoRichEntity) for packet in propositions.members)
    assert not any(isinstance(packet.body, DdoRichOccurrence) for packet in propositions.members)
    assert model.operation("rich.consolidate").effects == ()
    assert tuple(effect.name for effect in model.operation("rich.admit").effects) == (
        "native-rich-knowledge-admission",
    )


def test_native_authored_publication_keeps_entity_qualification_and_origin(rich_publication):
    from corpus_structure.semantic.data_operation_identity import decode_semantic_value
    from corpus_structure.semantic.data_operation_service import execute_data_demand

    selected = publish_authored(
        rich_publication,
        (number("12"), number("13")),
        entities=("authored:one", "authored:two"),
        inference="independent-authored-publication",
    )
    assert selected.admission.standing == "accepted"
    assert selected.consolidation.standing == "private-consolidated"
    assert len(selected.admission.selected_fact_ids) == 2
    assert len(selected.admission.selected_occurrence_ids) == 2
    assert selected.admission.selected_reading_ids == ()
    occurrences = [
        packet.body
        for packet in selected.admission.members
        if isinstance(packet.body, DdoRichOccurrence)
    ]
    assert len(occurrences) == 2
    assert all(
        row.establishment == "stated" and row.statement is None and row.evidence_count == 0
        for row in occurrences
    )
    assert all(
        reference.kind == "authored"
        for row in occurrences
        for reference in row.original.support_references
    )
    page = query_publication(selected, ClaimsQuery(name="claims"))
    entities = query_publication(selected, EntityQuery(name="entity"))
    assert len(page["rows"]) == 2 and len(entities["rows"]) == 2
    assert {row["fact"]["subject_entity"] for row in page["rows"]} == {
        "authored:one",
        "authored:two",
    }
    assert {decode_semantic_value(row["object"])["number"] for row in page["rows"]} == {
        Decimal(12),
        Decimal(13),
    }
    assert {
        decode_semantic_value(item["qualification"])["polarity"]
        for row in page["rows"]
        for item in row["occurrences"]
    } == {True}
    assert query_publication(selected, SourceReadingsQuery(name="source_readings"))["rows"] == []
    assert page["scope"]["global_completeness"] == "unknown"
    replay = execute_data_demand(
        rich_publication.kernel.purpose("write"),
        selected.demand_id,
        source_root=ROOT,
        admission_engine=rich_publication.kernel.purpose("admit"),
        project_id=PROJECT,
        database_capacity=6,
    )
    assert replay.receipt_count == 0


@pytest.mark.skipif(
    os.environ.get("CORPUS_RUN_UDM_T14") != "1",
    reason="private entity qualification requires resolving the captured publication model",
)
def test_minimal_native_authored_entity_publication_and_read(authored_publication):
    """Exercise native rich publication without unrelated PDF extraction setup."""
    selected = publish_authored(
        authored_publication,
        (number("12"), number("13")),
        entities=("authored:one", "authored:two"),
        inference="minimal-authored-entity-publication",
    )

    report = query_publication(selected, EntityQuery(name="entity"))
    rows = {row["entity"]["entity_id"]: row for row in report["rows"]}

    assert set(rows) == {"authored:one", "authored:two"}
    assert all(row["standing"] == "resolved-identity" for row in rows.values())
    assert all(
        row["classes"] == ["urn:record-publication:PublicationSubject"] for row in rows.values()
    )
    assert all(len(row["selected_fact_ids"]) == 1 for row in rows.values())
    assert report["root"]["product_id"] == selected.product["id"]
    assert report["cut"]["read_id"]


@pytest.mark.skipif(
    os.environ.get("CORPUS_RUN_UDM_T14") != "1",
    reason="T14 cross-process acceptance is opt-in until authenticated serving identity closes",
)
def test_minimal_native_entity_query_reuses_across_fresh_cli_processes(
    authored_publication, native_settings, tmp_path
):
    """Run the installed selected-result CLI twice against one retained native admission."""
    import subprocess
    import sys

    from conftest import settings_for_native_clone

    from corpus_structure.semantic.data_operation_json import json_loads
    from semantic.record_publication_native_support import AuthoredPublicationJourney

    assert isinstance(authored_publication, AuthoredPublicationJourney)
    selected = publish_authored(
        authored_publication,
        (number("12"), number("13")),
        entities=("authored:one", "authored:two"),
        inference="fresh-process-authored-entity-publication",
    )
    database_name = authored_publication.kernel.engine.url.database
    assert database_name is not None
    settings = settings_for_native_clone(native_settings, database_name)
    database = settings.database
    cache_root = tmp_path / "served-pages"
    environment = os.environ | {
        "CORPUS_DATABASE__URL": database.url,
        "CORPUS_DATABASE__MAINTENANCE_URL": database.maintenance_url,
        "CORPUS_DATABASE__READER_URL": database.reader_url or "",
        "CORPUS_DATABASE__EVALUATOR_URL": database.evaluator_url or "",
        "CORPUS_DATABASE__ADMISSION_URL": database.admission_url or "",
        "CORPUS_CACHE__ROOT": str(cache_root),
        "CORPUS_CACHE__PROGRAM_STORE_BYTES": "0",
        "CORPUS_CACHE__PAGE_STORE_BYTES": str(8 * 1024**2),
        "CORPUS_RUNTIME__DEFAULT_PROJECT": PROJECT,
    }
    script = """
import os
import sys
from pathlib import Path

derived = 0
def observe(frame, event, arg):
    global derived
    if (
        event == "call"
        and frame.f_globals.get("__name__") == "corpus_structure.serve.rich_knowledge"
        and frame.f_code.co_name == "read_selected_rich_knowledge"
    ):
        derived += 1
    return observe

sys.setprofile(observe)
try:
    from corpus_structure.cli.app import main
    main()
finally:
    sys.setprofile(None)
    Path(os.environ["NATIVE_ENTITY_DERIVATIONS"]).write_text(str(derived))
"""
    command = [
        sys.executable,
        "-c",
        script,
        "query",
        "entity",
        "--demand",
        selected.demand_id,
        "--project",
        PROJECT,
        "--product",
        selected.product["id"],
        "--json",
    ]

    def invoke(ordinal):
        count_path = tmp_path / f"derived-{ordinal}.txt"
        reply = subprocess.run(
            command,
            cwd=ROOT,
            env=environment | {"NATIVE_ENTITY_DERIVATIONS": str(count_path)},
            capture_output=True,
            check=False,
            text=True,
            timeout=180,
        )
        assert reply.returncode == 0, reply.stdout + reply.stderr
        return json_loads(reply.stdout), int(count_path.read_text())

    first, first_derivations = invoke(1)
    second, second_derivations = invoke(2)

    assert first_derivations == 1
    assert second_derivations == 0
    assert first["rows"] == second["rows"]
    assert {row["entity"]["entity_id"] for row in first["rows"]} == {
        "authored:one",
        "authored:two",
    }
    assert first["cut"]["read_id"] != second["cut"]["read_id"]
    assert first["cut_id"] != second["cut_id"]


def test_native_empty_admission_is_explicit_and_does_not_assert_global_absence(rich_publication):
    selected = publish_authored(
        rich_publication, (), inference="explicit-empty-authored-publication"
    )
    assert selected.admission.selected_fact_ids == selected.admission.selected_occurrence_ids == ()
    assert selected.admission.members == ()
    page = query_publication(selected, ClaimsQuery(name="claims"))
    assert page["rows"] == []
    assert page["root"]["product_id"] == selected.product["id"]
    assert page["scope"]["examined"] == "one-selected-whole-admission"
    assert page["scope"]["global_completeness"] == "unknown"


def test_native_selected_reader_pages_and_pins_actual_product_and_support(rich_publication):
    from corpus_structure.semantic.refusals import InvalidContinuation
    from corpus_structure.serve.rich_queries import RichQueryRequest, serve_rich_query

    selected = publish_authored(
        rich_publication,
        (number("12"), number("13")),
        entities=("authored:one", "authored:two"),
        inference="pinned-rich-publication",
    )
    first = query_publication(selected, ClaimsQuery(name="claims"), limit=1)
    assert len(first["rows"]) == 1 and first["cursor"] is not None
    other = publish_authored(
        rich_publication, (number("14"),), inference="another-explicit-publication"
    )
    second = query_publication(
        selected, ClaimsQuery(name="claims"), limit=1, cursor=first["cursor"]
    )
    assert len(second["rows"]) == 1 and second["cursor"] is None
    assert first["rows"][0]["fact"]["fact_id"] != second["rows"][0]["fact"]["fact_id"]
    assert first["cut_id"] == second["cut_id"]
    assert first["root"] == second["root"]
    with rich_publication.kernel.purpose("read").begin() as connection:
        with pytest.raises(InvalidContinuation):
            serve_rich_query(
                connection,
                RichQueryRequest(
                    project_id=PROJECT,
                    demand_id=other.demand_id,
                    product_id=other.product["id"],
                    query=ClaimsQuery(name="claims"),
                    cursor=first["cursor"],
                ),
            )
        with pytest.raises(ValueError):
            serve_rich_query(
                connection,
                RichQueryRequest(
                    project_id=PROJECT,
                    demand_id=selected.demand_id,
                    product_id=selected.consolidation_product["id"],
                    query=ClaimsQuery(name="claims"),
                ),
            )


def test_native_public_reader_rejects_wrong_scope_and_capacity_without_partial_graph(
    rich_publication,
):
    from corpus_structure.serve.rich_queries import RichQueryRequest, serve_rich_query

    selected = publish_authored(
        rich_publication, (number("12"),), inference="bounded-rich-publication"
    )
    with rich_publication.kernel.purpose("read").begin() as connection:
        for project, product in (
            ("another-project", selected.product["id"]),
            (PROJECT, "unselected:product"),
        ):
            with pytest.raises(ValueError), connection.begin_nested():
                serve_rich_query(
                    connection,
                    RichQueryRequest(
                        project_id=project,
                        demand_id=selected.demand_id,
                        product_id=product,
                        query=ClaimsQuery(name="claims"),
                    ),
                )
        for limits in ({"max_graph_members": 1}, {"max_bytes": 1024}):
            with pytest.raises(RichQueryRefused), connection.begin_nested():
                serve_rich_query(
                    connection,
                    RichQueryRequest.model_validate(
                        dict(
                            project_id=PROJECT,
                            demand_id=selected.demand_id,
                            product_id=selected.product["id"],
                            query={"name": "claims"},
                            **limits,
                        )
                    ),
                )
    assert len(query_publication(selected, ClaimsQuery(name="claims"))["rows"]) == 1


def test_native_reader_purpose_cannot_publish_products(rich_publication):
    selected = publish_authored(
        rich_publication, (number("12"),), inference="purpose-rich-publication"
    )
    with rich_publication.kernel.purpose("read").begin() as connection:
        with pytest.raises(DBAPIError) as refused, connection.begin_nested():
            connection.execute(text("INSERT INTO kb.data_product DEFAULT VALUES"))
        assert getattr(refused.value.orig, "sqlstate", None) == "42501"
    assert len(query_publication(selected, ClaimsQuery(name="claims"))["rows"]) == 1


def test_actual_current_record_structure_and_literal_evidence_refuse_semantic_tampering(
    rich_publication,
):
    from copy import deepcopy

    from evaluate.declared_record_native_support import run_readings

    from corpus_structure.semantic.record_contracts import (
        evidence_set_identity,
        interpretation_identity,
    )
    from corpus_structure.semantic.rich_record_readings import rich_reading_value

    journey = rich_publication
    source = journey.sources[0]
    readings = run_readings(journey, (source,), policy=None, inference="current-record-structure")
    ((_, raw),) = readings.raw
    complete = []
    for member in raw["members"]:
        row = dict(member["body"])
        if row.pop("candidate_type") == "record" and all(
            field["state"] == "present" for field in row["fields"]
        ):
            complete.append(row)
    assert len(complete) == 2
    order = {entry["pointer"]: index for index, entry in enumerate(raw["coordinate_texts"])}
    complete.sort(
        key=lambda row: min(
            order[anchor["pointer"]] for anchor in row["anchors"] if "source_piece" in anchor
        )
    )
    baseline = complete[0]
    checked = rich_reading_value(
        journey.kernel.prepared,
        journey.kernel.model,
        baseline,
        coordinate_texts=raw["coordinate_texts"],
    )
    assert checked.class_name == "TableAssertionReading"
    assert set(checked.fields) == {"value", "location"}
    changes = []
    missing = deepcopy(baseline)
    missing["fields"] = missing["fields"][:-1]
    changes.append(missing)
    repeated = deepcopy(baseline)
    repeated["fields"] = (*repeated["fields"], repeated["fields"][0])
    changes.append(repeated)
    cyclic = deepcopy(baseline)
    cyclic["fields"][0]["premises"] = (cyclic["fields"][1]["role"],)
    cyclic["fields"][1]["premises"] = (cyclic["fields"][0]["role"],)
    changes.append(cyclic)
    for premise in ("missing-role", "family"):
        forged = deepcopy(baseline)
        forged["fields"][0]["premises"] = (premise,)
        changes.append(forged)
    unavailable = deepcopy(baseline)
    unavailable["fields"][0]["evidence_sets"] = ("missing-set",)
    changes.append(unavailable)
    altered = deepcopy(baseline)
    field = next(field for field in altered["fields"] if field["role"] == "value")
    field["value"] = {"kind": "decimal", "lexical": "999"}
    changes.append(altered)
    alternative = deepcopy(baseline)
    alternative["fields"][0]["alternatives"] = (
        dict(
            alternative_id="unavailable-alternative",
            value={"kind": "decimal", "lexical": "999"},
            evidence_sets=("missing-set",),
            reason="counterreading",
        ),
    )
    changes.append(alternative)
    for changed in changes:
        changed["interpretation_id"] = interpretation_identity(changed)
        with pytest.raises(ValueError):
            rich_reading_value(
                journey.kernel.prepared,
                journey.kernel.model,
                changed,
                coordinate_texts=raw["coordinate_texts"],
            )

    # One actual ordered literal set spans the two independently captured native cells.
    ordered = deepcopy(baseline)
    field = next(field for field in ordered["fields"] if field["role"] == "value")
    second_field = next(field for field in complete[1]["fields"] if field["role"] == "value")
    first_set = next(
        item for item in ordered["evidence_sets"] if item["set_id"] == field["evidence_sets"][0]
    )
    second_set = next(
        item
        for item in complete[1]["evidence_sets"]
        if item["set_id"] == second_field["evidence_sets"][0]
    )
    second_anchor = next(
        item for item in complete[1]["anchors"] if item["anchor_id"] == second_set["anchors"][0]
    )
    ordered["anchors"] = (*ordered["anchors"], second_anchor)
    literal = {**first_set, "anchors": (*first_set["anchors"], *second_set["anchors"])}
    literal["set_id"] = evidence_set_identity(literal)
    ordered["evidence_sets"] = tuple(
        literal if item["set_id"] == first_set["set_id"] else item
        for item in ordered["evidence_sets"]
    )
    pieces = (field.pop("original"), second_field["original"])
    assert pieces == ("12", "12")
    field.update(
        original_pieces=pieces,
        value={"kind": "text_sequence", "items": pieces},
        evidence_sets=(literal["set_id"],),
    )
    ordered["interpretation_id"] = interpretation_identity(ordered)
    rich_reading_value(
        journey.kernel.prepared,
        journey.kernel.model,
        ordered,
        coordinate_texts=raw["coordinate_texts"],
    )
    for ordering, anchors in (
        ("unordered", literal["anchors"]),
        ("ordered", tuple(reversed(literal["anchors"]))),
    ):
        changed = deepcopy(ordered)
        replacement = {**literal, "ordering": ordering, "anchors": anchors}
        replacement["set_id"] = evidence_set_identity(replacement)
        changed["evidence_sets"] = tuple(
            replacement if item["set_id"] == literal["set_id"] else item
            for item in changed["evidence_sets"]
        )
        next(field for field in changed["fields"] if field["role"] == "value")["evidence_sets"] = (
            replacement["set_id"],
        )
        changed["interpretation_id"] = interpretation_identity(changed)
        with pytest.raises(ValueError):
            rich_reading_value(
                journey.kernel.prepared,
                journey.kernel.model,
                changed,
                coordinate_texts=raw["coordinate_texts"],
            )


def test_native_qualification_keeps_distinct_propositions_in_one_entity(rich_publication):
    from corpus_structure.semantic.data_operation_identity import decode_semantic_value

    selected = publish_authored(
        rich_publication,
        (number("12"), number("12")),
        qualifications=(
            {"modality": "asserted", "polarity": True},
            {"modality": "asserted", "polarity": False},
        ),
        inference="distinct-authored-qualification",
    )
    page = query_publication(selected, ClaimsQuery(name="claims", population="retained"))
    assert len(page["rows"]) == 2
    assert len({row["fact"]["qualification_meaning"] for row in page["rows"]}) == 2
    assert {
        decode_semantic_value(occurrence["qualification"])["polarity"]
        for row in page["rows"]
        for occurrence in row["occurrences"]
    } == {True, False}
    assert {row["fact"]["subject_entity"] for row in page["rows"]} == {"authored:subject"}


def test_native_empty_inspection_and_missing_resolution_do_not_fall_back_to_raw_acceptance(
    rich_publication,
):
    from evaluate.declared_record_native_support import run_readings

    from semantic.record_publication_native_support import publish_readings

    journey = rich_publication
    source = journey.sources[0]
    empty = run_readings(
        journey,
        (source,),
        policy=None,
        empty_sources=(source.pin.source,),
        inference="explicit-native-empty-record-inspection",
    )
    ((raw_product, raw),) = empty.raw
    assert raw["inspection_outcome"] == "empty" and raw["members"] == []
    selected = publish_readings(
        journey, empty, source=source, inference="explicit-empty-reading-publication"
    )
    assert raw_product["id"] in {
        item.product_id for item in selected.consolidation.input_population
    }
    assert selected.admission.reading_decisions == selected.admission.selected_reading_ids == ()
    assert query_publication(selected, SourceReadingsQuery(name="source_readings"))["rows"] == []
    produced = run_readings(
        journey, (source,), policy=None, inference="raw-without-selected-resolution"
    )
    missing = publish_readings(
        journey,
        produced,
        source=source,
        include_resolution=False,
        inference="missing-resolution-publication",
    )
    assert len(missing.admission.reading_decisions) == 4
    assert {row.reason_code for row in missing.admission.reading_decisions} == {
        "resolution-unavailable"
    }
    assert missing.admission.selected_reading_ids == ()
    assert query_publication(missing, SourceReadingsQuery(name="source_readings"))["rows"] == []
