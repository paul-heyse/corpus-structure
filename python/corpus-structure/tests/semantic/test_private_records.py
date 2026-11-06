"""Real restricted native private record custody, not accepted knowledge publication."""

from copy import deepcopy
from importlib.resources import files

import psycopg
import pytest
import yaml
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.invariant_failures import InvariantViolation
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.operations import (
    BoundReader,
)
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
from corpus_structure.semantic.records import authenticated_coordinate_texts
from corpus_structure.semantic.releases import persist_release

from .native_record_fixtures import (
    bypass,
    candidate,
    complete,
    complete_absent_and_empty_reports,
    refresh_record_identities,
)
from .native_record_fixtures import (
    private_preparation as private_preparation,
)
from .native_record_fixtures import (
    private_source as private_source,
)
from .native_record_fixtures import (
    private_source_options as private_source_options,
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
    "change, expected_message",
    [
        (
            lambda c, r: r["pin"].update(product_digest="d" * 64),
            "private record pin differs from persisted selected source view",
        ),
        (
            lambda c, r: r["pin"].update(product_digest="not-a-digest"),
            "private record report differs from released shape",
        ),
        (
            lambda c, r: r["pin"].update(recipe_digest="d" * 64),
            "private record pin differs from persisted selected source view",
        ),
        (
            lambda c, r: r["pin"].update(native_product_task_id=c.source_task + 10000),
            "private record pin differs from persisted selected source view",
        ),
        (
            lambda c, r: r["pin"].update(source_view_id=c.other_view),
            "private record pin differs from persisted selected source view",
        ),
        (
            lambda c, r: r["pin"].update(source="forged-source"),
            "private record pin differs from persisted selected source view",
        ),
        (
            lambda c, r: r["anchors"][0].update(source_piece="99"),
            "private record anchor does not reconstruct actual persisted source text",
        ),
        (
            lambda c, r: r["anchors"][0].update(pointer=c.sibling),
            "private record anchor is outside selected source view",
        ),
        (
            lambda c, r: r["anchors"][0].update(pointer=c.table + "/data/table_cells/99"),
            "private record cell is outside native table",
        ),
        (
            lambda c, r: r.update(standing="accepted"),
            "private record custody does not admit accepted whole records",
        ),
        (
            lambda c, r: r["fields"][0]["value"].update(lexical="NaN"),
            "private record report differs from released shape",
        ),
        (
            lambda c, r: r["fields"][0].update(reason="forged-conditional-branch"),
            "private record fields differ from released family shape",
        ),
    ],
)
def test_native_completion_independently_refuses_forged_private_source_custody(
    private_source, change, expected_message
):
    case = private_source
    record = deepcopy(candidate(case))
    change(case, record)
    refresh_record_identities(case, record)
    with case.writer.begin() as conn:
        with conn.begin_nested() as positive:
            bypass(case, conn, (candidate(case),))
            assert (
                conn.scalar(
                    select(table("ops.task_result").c.task_id).where(
                        table("ops.task_result").c.task_id == case.task
                    )
                )
                == case.task
            )
            positive.rollback()
        with pytest.raises((DBAPIError, InvariantViolation)) as caught, conn.begin_nested():
            bypass(case, conn, (record,))
        native = (
            caught.value.__cause__ if isinstance(caught.value, InvariantViolation) else caught.value
        )
        assert isinstance(native, DBAPIError)
        assert isinstance(native.orig, psycopg.Error)
        assert (native.orig.sqlstate, native.orig.diag.message_primary) == (
            "23514",
            expected_message,
        )
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
    refresh_record_identities(case, record)
    with case.writer.begin() as conn:
        with pytest.raises(ValueError, match="synthetic"):
            authenticated_coordinate_texts(
                conn, case.prepared, case.task_row, "private-unit", (record,)
            )
        with pytest.raises((DBAPIError, InvariantViolation)) as caught, conn.begin_nested():
            bypass(case, conn, (record,))
        native = (
            caught.value.__cause__ if isinstance(caught.value, InvariantViolation) else caught.value
        )
        assert isinstance(native, DBAPIError)
        assert isinstance(native.orig, psycopg.Error)
        assert (native.orig.sqlstate, native.orig.diag.message_primary) == (
            "23514",
            "private projection anchor crosses synthetic or different source pieces",
        )


def test_predecessor_absence_and_explicit_empty_private_report_remain_distinct(private_source):
    case = private_source
    task = complete_absent_and_empty_reports(case)
    with case.writer.connect() as conn:
        reader = BoundReader(conn, case.run, case.prepared, analysis=False)
        assert reader.source_record_report(case.task).records is None
        assert reader.source_record_report(task).records == ()


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
@pytest.mark.parametrize("datatype_name", ["RecordSourcePin", "SourceContribution"])
def test_private_product_types_are_independently_refused_by_protected_knowledge_graph(
    private_source, form, datatype_name
):
    case = private_source
    datatype = case.prepared.index.definitions[datatype_name].iri
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


def test_private_placement_preserves_schemas_and_excludes_graph_applicability(private_preparation):
    from corpus_structure.semantic.record_contracts import record_product_classes
    from corpus_structure.semantic.releases import _projection_rows

    prepared = private_preparation.prepared
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


@pytest.mark.parametrize(
    "field, message",
    [
        ("anchor", "record anchor identity differs from content"),
        ("evidence", "record evidence set identity differs from content"),
        ("record", "record occurrence identity differs from released source membership"),
        (
            "interpretation",
            "record interpretation identity differs from private fields or dependencies",
        ),
    ],
)
def test_native_structure_rejects_deliberately_corrupt_derived_identity(
    private_source, semantic_db_engine, field, message
):
    from sqlalchemy import bindparam
    from sqlalchemy.dialects.postgresql import JSONB

    case = private_source
    valid = candidate(case)
    invalid = deepcopy(valid)
    if field == "anchor":
        invalid["anchors"][0]["anchor_id"] = "record-anchor:" + "0" * 64
    elif field == "evidence":
        invalid["evidence_sets"][0]["set_id"] = "record-evidence:" + "0" * 64
    else:
        invalid["record_id" if field == "record" else "interpretation_id"] = "0" * 64
    statement = text("SELECT data.validate_source_record_structure(:r,:record)").bindparams(
        bindparam("record", type_=JSONB)
    )
    with semantic_db_engine.begin() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        conn.execute(statement, dict(r=case.prepared.release_id, record=valid))
        with pytest.raises(DBAPIError) as caught, conn.begin_nested():
            conn.execute(statement, dict(r=case.prepared.release_id, record=invalid))
        assert isinstance(caught.value.orig, psycopg.Error)
        assert (caught.value.orig.sqlstate, caught.value.orig.diag.message_primary) == (
            "23514",
            message,
        )
