"""Real restricted native private record custody, not accepted knowledge publication."""

import json
from copy import deepcopy
from hashlib import sha256
from importlib.resources import files
from types import SimpleNamespace
from typing import Any

import psycopg
import pytest
import yaml
from docling_core.types.doc import DocItemLabel, DoclingDocument, GroupLabel, TableCell, TableData
from pydantic import BaseModel, create_model
from sqlalchemy import insert, select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import ObservationDraft, SourceViewDraft, UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationKind, ObservationOutcome, TaskUnitType
from corpus_structure.ingest.pdf import PdfConversion, publication_payload
from corpus_structure.ingest.pdf_hierarchy import snapshot
from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.analytical_profile import analytical_inputs
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.domain_operations import domain_rule_inputs
from corpus_structure.semantic.invariant_failures import InvariantViolation
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import bind_result, observation_inputs
from corpus_structure.semantic.operations import (
    BoundReader,
    OperationBinding,
    claim_tasks,
    complete_task,
    complete_unit_result,
    create_run,
    create_task,
    record_method,
    register_document,
)
from corpus_structure.semantic.pdf_contracts import prepare_pdf_product, store_pdf_original
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.publication import (
    EntityRow,
    EvidenceRow,
    MembershipRow,
    MembershipSupportRow,
    PublicationBatch,
    RoleRow,
    ValueRow,
    publish_batch,
)
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)
from corpus_structure.semantic.records import authenticated_coordinate_texts
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.source_views import store_source_view

from .native_record_fixtures import publish_native_record_fixture


class RawReport(BaseModel):
    source_text: str


@pytest.fixture
def private_source(semantic_db_engine, semantic_writer_engine, tmp_path):
    schema = dict(
        id="https://example/private-records",
        name="private_records",
        imports=["core"],
        prefixes={"ex": "https://example/"},
        default_prefix="ex",
        classes={
            "FixtureConditionalField": dict(
                is_a="RequiredLiteralRecordField",
                rules=[
                    dict(
                        preconditions=dict(
                            slot_conditions=dict(state=dict(equals_string="present"))
                        ),
                        postconditions=dict(
                            slot_conditions=dict(
                                reason=dict(required=True, equals_string="source-read")
                            )
                        ),
                    )
                ],
            ),
            "FixtureRecordFields": dict(
                is_a="SemanticRecordFields",
                attributes={
                    "family": dict(equals_string="table"),
                    "occurrence_recipe": dict(equals_string="source-anchor-membership-1"),
                    "value": dict(range="FixtureConditionalField", required=True, inlined=True),
                    "location": dict(
                        range="RequiredNativeRecordField", required=True, inlined=True
                    ),
                },
            ),
        },
    )
    bundle = observation_inputs(
        SourceBundle(
            "domain",
            (
                SourceArtifact(
                    "core",
                    files("corpus_structure").joinpath("model/semantic/core.yaml").read_bytes(),
                ),
                SourceArtifact("domain", yaml.safe_dump(schema).encode()),
            ),
        )
    )
    dependencies = domain_rule_inputs(ResolvedDependencies(), b"rules: []\n")
    bundle, dependencies = analytical_inputs(bundle, dependencies)
    from .method_dimensions_support import fixture_execution_inputs

    dependencies = composed_dependencies(dependencies, fixture_execution_inputs('private.source', 'private.records'))
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="private-records"))
        conn.execute(
            insert(table("data.realization")).values(
                project_id="private-records",
                realization_id="private-input",
                release_id=prepared.release_id,
            )
        )
    original, recipe = b"%PDF-1.7\nprivate source record fixture", b'{"recipe":"private-records-1"}'
    doc = DoclingDocument(name="Two independent native cells")
    section = doc.add_group(label=GroupLabel.SECTION, name="Measurements")
    native_table = doc.add_table(
        parent=section,
        data=TableData(
            num_rows=1,
            num_cols=2,
            table_cells=[
                TableCell(
                    text="12",
                    start_row_offset_idx=0,
                    end_row_offset_idx=1,
                    start_col_offset_idx=column,
                    end_col_offset_idx=column + 1,
                )
                for column in range(2)
            ],
        ),
    )
    sibling = doc.add_group(label=GroupLabel.SECTION, name="Other source")
    sibling_text = doc.add_text(label=DocItemLabel.TEXT, text="12", orig="12", parent=sibling)
    native_schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    payload = publication_payload(
        PdfConversion(
            sha256(original).hexdigest(), recipe, snapshot(doc), "success", (), (), (), None
        ),
        product_key="native",
        schema_digest=sha256(native_schema).hexdigest(),
        section_refs=frozenset((section.self_ref, sibling.self_ref)),
    )
    product = prepare_pdf_product(payload, original, native_schema, recipe)
    writer = semantic_writer_engine
    with writer.begin() as conn:
        run = create_run(
            conn,
            project_id="private-records",
            binding=OperationBinding(prepared.release_id, "private-input", 0, b"{}"),
            kind="full",
            options={},
            code_commit="private-records-test",
        )
        method = SimpleNamespace(
            name="private.source",
            version="1",
            family="ingest",
            tier="deterministic",
            confidence_source=None,
            unit_type="document",
            Config=create_model("PrivateSourceConfig"),
        )
        config = record_method(conn, method, "default", {}, "private-source-config", prepared=prepared)
        path = tmp_path / "source.pdf"
        path.write_bytes(original)
        document = register_document(
            conn,
            project_id="private-records",
            source_uri="source.pdf",
            original_path=str(path),
            original=original,
            mime="application/pdf",
        )
        source_task = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="ingest",
            unit_type="document",
            unit_id=document,
            unit_key="source.pdf",
            input_hash=sha256(original).hexdigest(),
        )
        claim = claim_tasks(conn, run_id=run, config_id=config, holder="private-source")[0]
        store_pdf_original(
            conn,
            task_id=source_task,
            attempt=claim.attempt,
            holder="private-source",
            original=original,
            recipe_bytes=recipe,
        )
    published = publish_native_record_fixture(
        writer,
        tmp_path / "native",
        task_id=source_task,
        attempt=claim.attempt,
        holder="private-source",
        product=product,
        document=doc,
    )
    reference = ProductReference(source_task, "native", published.logical_digest)
    with writer.begin() as conn:
        draft = SourceViewDraft(
            "private-view",
            document,
            reference,
            section.self_ref,
            "direct",
            "12\n12",
            (
                dict(
                    kind="native_text",
                    item_ref=native_table.self_ref,
                    source_field="cell_text",
                    cell_index=0,
                    start=0,
                    end=2,
                ),
                dict(kind="synthetic_separator", start=2, end=3),
                dict(
                    kind="native_text",
                    item_ref=native_table.self_ref,
                    source_field="cell_text",
                    cell_index=1,
                    start=3,
                    end=5,
                ),
            ),
            (section.self_ref, native_table.self_ref),
            (),
            dict(payload["health"], formula_outcomes=[]),
            b'{"view":"cells"}',
        )
        view = store_source_view(
            conn,
            run_id=run,
            task_id=source_task,
            attempt=claim.attempt,
            holder="private-source",
            draft=draft,
            position=0,
        )
        other = SourceViewDraft(
            "other-view",
            document,
            reference,
            sibling.self_ref,
            "direct",
            "12",
            (
                dict(
                    kind="native_text",
                    item_ref=sibling_text.self_ref,
                    source_field="text",
                    start=0,
                    end=2,
                ),
            ),
            (sibling.self_ref, sibling_text.self_ref),
            (),
            dict(payload["health"], formula_outcomes=[]),
            b'{"view":"other"}',
        )
        other_view = store_source_view(
            conn,
            run_id=run,
            task_id=source_task,
            attempt=claim.attempt,
            holder="private-source",
            draft=other,
            position=1,
        )
        complete_task(
            conn,
            task_id=source_task,
            attempt=claim.attempt,
            holder="private-source",
            prepared=prepared,
            observations=[],
            outcome="empty",
        )
        record_method_ = SimpleNamespace(
            name="private.records",
            version="1",
            family="record",
            tier="deterministic",
            confidence_source=None,
            unit_type=TaskUnitType.SOURCE_VIEW,
            Config=create_model("PrivateRecordConfig"),
        )
        record_config = record_method(conn, record_method_, "default", {}, "private-config", prepared=prepared)
        task = create_task(
            conn,
            run_id=run,
            config_id=record_config,
            stage="record",
            unit_type="source_view",
            unit_id=view,
            unit_key="private-unit",
            input_hash="private-input-hash",
        )
        held = claim_tasks(conn, run_id=run, config_id=record_config, holder="records")[0]
        view_row = dict(
            conn.execute(
                select(table("kb.source_view")).where(table("kb.source_view").c.id == view)
            )
            .mappings()
            .one()
        )
        task_row = dict(
            conn.execute(select(table("ops.task")).where(table("ops.task").c.id == task))
            .mappings()
            .one()
        )
    return SimpleNamespace(
        prepared=prepared,
        writer=writer,
        run=run,
        task=task,
        held=held,
        view=view,
        other_view=other_view,
        source_task=source_task,
        view_row=view_row,
        task_row=task_row,
        method=record_method_,
        table=native_table.self_ref,
        sibling=sibling_text.self_ref,
    )


def candidate(case, cell=0, *, projected=False, coarse=False):
    row = case.view_row
    pin = dict(
        source="private-unit",
        native_product_task_id=row["native_task_id"],
        product_key=row["native_product_key"],
        product_digest=row["native_content_digest"],
        projection_digest=row["projection_digest"],
        recipe_digest=row["recipe_digest"],
        source_view_id=row["id"],
    )
    pointer = f"{case.table}/data/table_cells/{cell}"
    literal: dict[str, Any] = dict(
        pin=pin,
        space="selected_projection" if projected else "native",
        pointer=pointer,
        precision="coarse" if coarse else "exact",
        source_piece="12",
    )
    if not coarse:
        literal.update(start=cell * 3 if projected else 0, end=cell * 3 + 2 if projected else 2)
    location = dict(pin=pin, space="native", pointer=pointer, precision="item")
    anchors, evidence, fields = [], [], []
    for role, anchor, usage in (("value", literal, "literal"), ("location", location, "native")):
        anchor["anchor_id"] = anchor_identity(anchor)
        anchors.append(anchor)
        support = dict(role=role, ordering="ordered", usage=usage, anchors=(anchor["anchor_id"],))
        support["set_id"] = evidence_set_identity(support)
        evidence.append(support)
        field = dict(
            role=role,
            kind="literal" if role == "value" else "native",
            state="present",
            meaning_changing=True,
            evidence_status="available",
            evidence_sets=(support["set_id"],),
            value=dict(kind="decimal", lexical="12")
            if role == "value"
            else dict(kind="native_location", pointer=pointer),
        )
        if role == "value":
            field["original"] = "12"
            field["reason"] = "source-read"
        fields.append(field)
    record = dict(
        contract="FixtureRecordFields",
        family="table",
        occurrence_recipe="source-anchor-membership-1",
        pin=pin,
        occurrence_anchors=(location["anchor_id"],),
        standing="candidate",
        policy_version="private-1",
        anchors=tuple(anchors),
        evidence_sets=tuple(evidence),
        fields=tuple(fields),
    )
    return identities(case, record)


def identities(case, record):
    record["record_id"] = record_identity(case.prepared.release_id, record)
    record["interpretation_id"] = interpretation_identity(record)
    return record


def unit(case):
    payload = RawReport(source_text="12\n12")
    return UnitResult(
        ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
        outcome=ObservationOutcome.PRODUCED,
        observations=(
            ObservationDraft(
                kind=ObservationKind.RECORD,
                payload=payload,
                payload_class=RawReport,
                payload_version="1",
                source_view_id=case.view,
            ),
        ),
    )


def complete(case, conn, records):
    return complete_unit_result(
        conn,
        task_id=case.task,
        attempt=case.held.attempt,
        holder="records",
        prepared=case.prepared,
        method=case.method,
        configuration_hash="private-config",
        source="private-unit",
        result=unit(case),
        records=records,
    )


def bypass(case, conn, records):
    bound = bind_result(
        case.prepared,
        source="private-unit",
        method=case.method.name,
        operation_version="1",
        configuration_hash="private-config",
        input_hash="private-input-hash",
        invocation_key=case.task_row["invocation_key"],
        result=unit(case),
    )
    envelope = bound.model_dump(mode="json", exclude={"observations"})
    envelope["records"] = json.loads(json.dumps(records))
    item = bound.model_dump(mode="python")["observations"][0]
    return complete_task(
        conn,
        task_id=case.task,
        attempt=case.held.attempt,
        holder="records",
        prepared=case.prepared,
        observations=(
            dict(
                payload_definition="SourceObservation",
                item_key=item["item_key"],
                observation_key=item["observation_key"],
                payload=item,
                kind=item["family"],
                source_view_id=case.view,
                outcome=item["outcome"],
            ),
        ),
        envelope=envelope,
    )


def test_private_record_round_trip_repeated_cells_coarse_precision_and_replay(private_source):
    case = private_source
    records = (candidate(case), candidate(case, 1, projected=True), candidate(case, coarse=True))
    with case.writer.begin() as conn:
        receipt = complete(case, conn, records)
        assert complete(case, conn, records).receipt == receipt.receipt
    with case.writer.connect() as conn:
        report = BoundReader(conn, case.run, case.prepared, analysis=False).source_record_report(
            case.task
        )
        assert report.origin_task_id == case.task
        assert report.records is not None
        assert len(report.records) == 3
        records = tuple(record.model_dump(mode="python") for record in report.records)
        assert records[0]["record_id"] != records[1]["record_id"]
        assert records[1]["anchors"][0]["pointer"] == "#/tables/0/data/table_cells/1"
        assert records[1]["anchors"][0]["start"] == 3
        assert records[2]["anchors"][0]["precision"] == "coarse"
        assert "start" not in records[2]["anchors"][0]


@pytest.mark.parametrize(
    "change",
    [
        lambda c, r: r["pin"].update(product_digest="d" * 64),
        lambda c, r: r["pin"].update(product_digest="not-a-digest"),
        lambda c, r: r["pin"].update(recipe_digest="d" * 64),
        lambda c, r: r["pin"].update(native_product_task_id=c.source_task + 10000),
        lambda c, r: r["pin"].update(source_view_id=c.other_view),
        lambda c, r: r["pin"].update(source="forged-source"),
        lambda c, r: r["anchors"][0].update(source_piece="99"),
        lambda c, r: r["anchors"][0].update(pointer=c.sibling),
        lambda c, r: r["anchors"][0].update(pointer=c.table + "/data/table_cells/99"),
        lambda c, r: r.update(standing="accepted"),
        lambda c, r: r["fields"][0]["value"].update(lexical="NaN"),
        lambda c, r: r["fields"][0].update(reason="forged-conditional-branch"),
    ],
)
def test_native_completion_independently_refuses_forged_private_source_custody(
    private_source, change
):
    case = private_source
    record = deepcopy(candidate(case))
    change(case, record)
    with case.writer.begin() as conn:
        with pytest.raises((DBAPIError, InvariantViolation)), conn.begin_nested():
            bypass(case, conn, (record,))
        assert (
            conn.execute(
                select(table("ops.task_result")).where(
                    table("ops.task_result").c.task_id == case.task
                )
            ).first()
            is None
        )
        assert (
            conn.execute(
                select(table("kb.observation")).where(
                    table("kb.observation").c.task_id == case.task
                )
            ).first()
            is None
        )


def test_native_projection_refuses_synthetic_separator_even_with_caller_forged_text(private_source):
    case = private_source
    record = candidate(case, projected=True)
    record["anchors"][0].update(start=1, end=4, source_piece="2\n1")
    with case.writer.begin() as conn:
        with pytest.raises(ValueError, match="synthetic"):
            authenticated_coordinate_texts(
                conn, case.prepared, case.task_row, "private-unit", (record,)
            )
        with pytest.raises((DBAPIError, InvariantViolation)), conn.begin_nested():
            bypass(case, conn, (record,))


def test_predecessor_absence_and_explicit_empty_private_report_remain_distinct(private_source):
    case = private_source
    with case.writer.begin() as conn:
        complete_unit_result(
            conn,
            task_id=case.task,
            attempt=case.held.attempt,
            holder="records",
            prepared=case.prepared,
            method=case.method,
            configuration_hash="private-config",
            source="private-unit",
            result=unit(case),
        )
        report = BoundReader(conn, case.run, case.prepared, analysis=False).source_record_report(
            case.task
        )
        assert report.records is None
        task = create_task(
            conn,
            run_id=case.run,
            config_id=case.task_row["method_config_id"],
            stage="record",
            unit_type="source_view",
            unit_id=case.view,
            unit_key="private-unit-empty",
            input_hash="empty",
        )
        held = claim_tasks(
            conn, run_id=case.run, config_id=case.task_row["method_config_id"], holder="empty"
        )[0]
        complete_unit_result(
            conn,
            task_id=task,
            attempt=held.attempt,
            holder="empty",
            prepared=case.prepared,
            method=case.method,
            configuration_hash="private-config",
            source="private-unit-empty",
            result=UnitResult(
                ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit-empty"),
                outcome=ObservationOutcome.EMPTY,
            ),
            records=(),
        )
        report = BoundReader(conn, case.run, case.prepared, analysis=False).source_record_report(
            task
        )
        assert report.records == ()


def test_untrusted_private_candidate_grouping_is_not_promoted_and_reader_refuses_it(private_source):
    case = private_source
    record = candidate(case)
    record["fields"][0]["evidence_sets"] = ("missing-set",)
    with case.writer.begin() as conn:
        bypass(case, conn, (record,))
        with pytest.raises(ValueError, match="field evidence set membership"):
            BoundReader(conn, case.run, case.prepared, analysis=False).source_record_report(
                case.task
            )


@pytest.mark.parametrize("form", ["empty", "disconnected", "nested", "membership"])
def test_private_product_types_are_independently_refused_by_protected_knowledge_graph(
    private_source, form
):
    case = private_source
    datatype = case.prepared.index.definitions["RecordSourcePin"].iri
    values = (ValueRow("private-product", "record", datatype=datatype),)
    roles = ()
    entities, memberships, evidence, support = (), (), (), ()
    if form == "disconnected":
        values = (*values, ValueRow("ordinary-text", "string", text_value="visible ordinary value"))
    elif form == "nested":
        values = (*values, ValueRow("outer-sequence", "sequence"))
        roles = (RoleRow("outer-sequence", "item", 0, "private-product"),)
    elif form == "membership":
        values = ()
        entities = (EntityRow("product-entity"),)
        memberships = (MembershipRow("product-entity", datatype, "stated"),)
        evidence = (EvidenceRow("evidence", "source.pdf", "native", "fixture", "1"),)
        support = (MembershipSupportRow("product-entity", datatype, "evidence"),)
    batch = PublicationBatch(
        case.prepared.release_id,
        "private-input",
        "forbidden-" + form,
        typed_value=values,
        value_role=roles,
        entity=entities,
        membership=memberships,
        evidence=evidence,
        membership_support=support,
    )
    with pytest.raises(DBAPIError, match="private record product cannot be a knowledge graph"):
        publish_batch(case.writer, batch)
    with case.writer.connect() as conn:
        assert (
            conn.execute(
                select(table("data.batch")).where(table("data.batch").c.batch_id == batch.batch_id)
            ).first()
            is None
        )


def test_private_placement_preserves_schemas_and_excludes_graph_applicability(private_source):
    from corpus_structure.semantic.record_contracts import record_product_classes
    from corpus_structure.semantic.releases import _projection_rows

    prepared = private_source.prepared
    products = record_product_classes(prepared.definitions)
    private_iris = {prepared.index.definitions[name].iri for name in products}
    rows = _projection_rows(prepared)
    assert private_iris <= {row["class_id"] for row in rows["class_definition"]}
    assert not private_iris & {row["class_id"] for row in rows["property_applicability"]}
    assert not private_iris & {row["class_id"] for row in rows["identity_slot"]}
    assert not private_iris & {row["class_id"] for row in rows["operation_property_role"]}
    assert not private_iris & {row["class_id"] for row in rows["conditional_rule"]}
    assert any(
        row["class_id"] == prepared.index.definitions["Entity"].iri
        for row in rows["property_applicability"]
    )
    assert any(
        row["class_id"] == prepared.index.definitions["Entity"].iri and row["role"] == "identity"
        for row in rows["operation_property_role"]
    )
    assert prepared.json_schema("RecordSourcePin")["properties"]["product_digest"]["allOf"] == [
        {"pattern": "^[0-9a-f]{64}$"},
    ]


@pytest.mark.parametrize("inlined", [True, False])
def test_graph_properties_cannot_range_into_private_products(inlined):
    from corpus_structure.semantic import PreparationError

    schema = dict(
        id="https://example/graph-range",
        name="graph_range",
        imports=["core"],
        classes={
            "GraphRecord": dict(attributes={"pin": dict(range="RecordSourcePin", inlined=inlined)})
        },
    )
    bundle = observation_inputs(
        SourceBundle(
            "domain",
            (
                SourceArtifact(
                    "core",
                    files("corpus_structure").joinpath("model/semantic/core.yaml").read_bytes(),
                ),
                SourceArtifact("domain", yaml.safe_dump(schema).encode()),
            ),
        )
    )
    with pytest.raises(PreparationError, match="cannot range into a private record product"):
        prepare_release(bundle)


def test_ordinary_graph_regex_admission_remains_refused(semantic_db_engine):
    schema = dict(
        id="https://example/graph-regex",
        name="graph_regex",
        default_range="string",
        types={"string": dict(base="str", uri="http://www.w3.org/2001/XMLSchema#string")},
        classes={"GraphRecord": dict(attributes={"label": dict(pattern="^x$", required=True)})},
    )
    bundle = SourceBundle("domain", (SourceArtifact("domain", yaml.safe_dump(schema).encode()),))
    dependencies = composed_dependencies(ResolvedDependencies())
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    with (
        pytest.raises(DBAPIError, match="unsupported required native constraint scope or pattern"),
        semantic_db_engine.begin() as conn,
    ):
        persist_release(conn, bundle, dependencies, profile, prepared)
        conn.execute(text("SELECT data.require_execution_release(:r)"), {"r": prepared.release_id})


def test_native_projection_still_refuses_missing_ordinary_graph_roles(
    semantic_db_engine, monkeypatch
):
    from corpus_structure.semantic import releases

    schema = dict(
        id="https://example/graph-roles",
        name="graph_roles",
        default_range="string",
        types={"string": dict(base="str", uri="http://www.w3.org/2001/XMLSchema#string")},
        classes={
            "GraphRecord": dict(
                attributes={"id": dict(identifier=True), "label": dict(required=True)}
            )
        },
    )
    bundle = SourceBundle("domain", (SourceArtifact("domain", yaml.safe_dump(schema).encode()),))
    dependencies = composed_dependencies(ResolvedDependencies())
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    original = releases._projection_rows

    def omitted_role(product):
        rows = original(product)
        rows["operation_property_role"] = [
            row for row in rows["operation_property_role"] if row["role"] != "identity"
        ]
        return rows

    monkeypatch.setattr(releases, "_projection_rows", omitted_role)
    with (
        pytest.raises(
            releases.ReleaseConflict, match="archived operation_property_role projection differs"
        ) as refused,
        semantic_db_engine.begin() as conn,
    ):
        persist_release(conn, bundle, dependencies, profile, prepared)
        conn.execute(
            text("SELECT sem.require_execution_projection(:r)"), {"r": prepared.release_id}
        )
    assert isinstance(refused.value.__cause__, DBAPIError)
    assert isinstance(refused.value.__cause__.orig, psycopg.Error)
    assert refused.value.__cause__.orig.sqlstate == "23514"
