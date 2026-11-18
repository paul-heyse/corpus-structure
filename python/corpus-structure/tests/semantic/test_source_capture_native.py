"""Native source capture decisions with explicit controlled proof dependencies."""

import json
from hashlib import sha256

import pytest
from sqlalchemy import Column, MetaData, Table, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.data_operation_source_native import (
    source_native_sources,
    source_native_sql,
)
from corpus_structure.semantic.metadata import get_metadata, table
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.source_capture_native import source_capture_native_sql


@pytest.fixture
def source_capture_control(infrastructure_rollback):
    connection = infrastructure_rollback
    for schema in ("ops", "kb", "sem", "data"):
        connection.exec_driver_sql("CREATE SCHEMA " + schema)
    # Reuse every real named column/type. These controls isolate capture
    # decisions; unrelated issuance/row-admission constraints are not exercised.
    relations = (
        "kb.document",
        "kb.source_artifact",
        "ops.data_request",
        "ops.data_demand_read",
        "ops.data_derivation",
        "ops.data_derivation_output",
        "ops.data_completion_intent",
        "kb.data_product",
        "sem.data_operation_definition",
    )
    for name in relations:
        original = table(name)
        relation = Table(
            original.name,
            MetaData(),
            *(Column(item.name, item.type) for item in original.c),
            schema=original.schema,
        )
        connection.execute(CreateTable(relation))
    controls = (
        "CREATE FUNCTION ops.ddo_fields(value jsonb,required text[]) RETURNS void LANGUAGE plpgsql IMMUTABLE AS $$BEGIN IF EXISTS(SELECT FROM unnest(required) field WHERE NOT value ? field) THEN RAISE EXCEPTION 'missing control field'; END IF; END$$",
        "CREATE FUNCTION data.record_json_meaning(value jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$SELECT value$$",
        "CREATE FUNCTION data.ddo_normalize(value jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$SELECT value$$",
        "CREATE FUNCTION data.ddo_json(value jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$SELECT value$$",
        "CREATE FUNCTION ops.ddo_digest(value jsonb) RETURNS text LANGUAGE sql IMMUTABLE AS $$SELECT 'coordinate-hash-control'::text$$",
        "CREATE FUNCTION ops.ddo_node_valid(kind text,identity text,boundary ops.data_demand_read) RETURNS boolean LANGUAGE sql STABLE AS $$SELECT identity<>'rejected'$$",
        "CREATE FUNCTION ops.ddo_pdf_producing_request(identity text) RETURNS ops.data_request LANGUAGE sql STABLE AS $$SELECT r FROM ops.data_request r WHERE id='producer'$$",
        "CREATE FUNCTION ops.ddo_authorize_request(request ops.data_request) RETURNS void LANGUAGE plpgsql STABLE AS $$BEGIN IF request.binding->>'authorize'='false' THEN RAISE EXCEPTION 'request authority refused' USING ERRCODE='42501'; END IF; END$$",
        "CREATE FUNCTION ops.require_pdf_operation(release text,operation text) RETURNS void LANGUAGE plpgsql STABLE AS $$BEGIN IF release<>'release:one' OR operation<>'read_native_source' THEN RAISE EXCEPTION 'PDF operation refused' USING ERRCODE='23514'; END IF; END$$",
        "CREATE FUNCTION ops.pdf_publication_projection(receipt jsonb,task bigint,attempt bigint,holder text) RETURNS jsonb LANGUAGE sql STABLE AS $$SELECT jsonb_build_object('document',receipt->>'document','task',task,'attempt',attempt,'holder',holder)$$",
        "CREATE FUNCTION ops.ddo_single_input_support_episode(value jsonb) RETURNS text LANGUAGE plpgsql IMMUTABLE AS $$BEGIN IF value ? 'must_not_evaluate' THEN RAISE EXCEPTION 'unselected proof evaluated'; END IF; RETURN value->>'derivation_id'; END$$",
    )
    for statement in controls:
        connection.exec_driver_sql(statement)
    prepared = prepare_sql(source_capture_native_sql(get_metadata()), source="capture-control")
    for index, _ in enumerate(prepared.statements):
        connection.exec_driver_sql(
            prepared.excerpt(index), execution_options={"no_parameters": True}
        )
    original = b"original document bytes"
    digest = sha256(original).hexdigest()
    reference = dict(
        kind="original-document",
        project_id="project",
        document_key="document",
        content_hash=digest,
        mime="application/pdf",
    )
    connection.execute(
        table("kb.document").insert(),
        dict(
            id=1,
            project_id="project",
            key="document",
            content_hash=digest,
            mime="application/pdf",
            source_uri="file:source",
            original_path="retained.pdf",
        ),
    )
    connection.execute(
        table("kb.source_artifact").insert(), dict(artifact_digest=digest, content=original)
    )
    receipt = dict(document="document", publication="sealed:one")
    expected = dict(document="document", task=17, attempt=3, holder="producer-holder")
    binding = dict(
        inputs=[
            dict(product_id="ignored", must_not_evaluate=True),
            dict(product_id="product", derivation_id="derivation"),
        ],
        support=[dict(derivation_id="derivation")],
    )
    connection.execute(
        table("ops.data_request").insert(),
        [
            dict(
                id="producer",
                project_id="project",
                original_source="document",
                release_id="release:one",
                operation_id="pdf.capture",
                binding={},
            ),
            dict(
                id="consumer",
                project_id="project",
                original_source="document",
                release_id="release:one",
                operation_id="use.capture",
                binding=binding,
            ),
        ],
    )
    connection.execute(
        table("ops.data_derivation").insert(),
        dict(id="derivation", release_id="release:one", intent_id="intent"),
    )
    connection.execute(
        table("ops.data_derivation_output").insert(),
        dict(derivation_id="derivation", product_id="product", member_id=None),
    )
    connection.execute(
        table("sem.data_operation_definition").insert(),
        dict(release_id="release:one", operation_id="pdf.capture", command_class="pdf"),
    )
    connection.execute(
        table("ops.data_completion_intent").insert(),
        dict(
            id="intent",
            payload=dict(execution_evidence=dict(pdf_receipts=[receipt])),
            producer_task_id=17,
            producer_attempt=3,
            producer_holder="producer-holder",
        ),
    )
    connection.execute(
        table("kb.data_product").insert(),
        dict(
            id="product",
            project_id="project",
            original_source="document",
            canonical_body=expected,
        ),
    )
    yield connection, reference, receipt


def test_original_document_capture_reads_exact_retained_bytes(source_capture_control):
    connection, reference, _ = source_capture_control
    value = connection.scalar(
        text("SELECT ops.ddo_original_document_view(CAST(:reference AS jsonb))"),
        dict(reference=json.dumps(reference)),
    )
    body = dict(document="document", content_hash=reference["content_hash"], mime="application/pdf")
    assert value == dict(
        body=body,
        meaning_body=body,
        subject_definition="original-document",
        subject="original-document:coordinate-hash-control",
        original_source="document",
        analyzed_scope=dict(document="document", scope="whole-document"),
        evidence=dict(
            reference=reference,
            document_id=1,
            document_content_hash=reference["content_hash"],
            source_uri="file:source",
            original_path="retained.pdf",
        ),
    )
    connection.execute(table("kb.source_artifact").update().values(content=b"different bytes"))
    with pytest.raises(DBAPIError, match="retained byte digest differs"), connection.begin_nested():
        connection.execute(
            text("SELECT ops.ddo_original_document_view(CAST(:reference AS jsonb))"),
            dict(reference=json.dumps(reference)),
        )


@pytest.mark.parametrize(
    "case,state,message",
    [
        ("valid", None, None),
        ("support", "23514", "support is not admitted"),
        ("project", "23514", "outside exact qualified"),
        ("source", "23514", "outside exact qualified"),
        ("authority", "42501", "authority refused"),
        ("command", "23514", "approved native PDF command"),
        ("receipts", "23514", "one retained sealed publication"),
        ("body", "23514", "body differs"),
        ("output", "P0002", "query returned no rows"),
    ],
)
def test_pdf_capture_receipt_requires_exact_selected_sealed_proof(
    source_capture_control, case, state, message
):
    connection, _, receipt = source_capture_control
    project, source, episode = "project", None, "derivation"
    if case == "support":
        episode = "rejected"
    elif case == "project":
        project = "other"
    elif case == "source":
        source = "other"
    elif case == "authority":
        connection.execute(
            table("ops.data_request")
            .update()
            .where(table("ops.data_request").c.id == "producer")
            .values(binding=dict(authorize=False))
        )
    elif case == "command":
        connection.execute(
            table("sem.data_operation_definition").update().values(command_class="other")
        )
    elif case == "receipts":
        connection.execute(
            table("ops.data_completion_intent")
            .update()
            .values(payload=dict(execution_evidence=dict(pdf_receipts=[])))
        )
    elif case == "body":
        connection.execute(
            table("kb.data_product")
            .update()
            .values(
                canonical_body=dict(
                    document="document", task=18, attempt=3, holder="producer-holder"
                )
            )
        )
    elif case == "output":
        connection.execute(table("ops.data_derivation_output").update().values(member_id="member"))
    query = text("SELECT ops.ddo_pdf_derivation_receipt(:project,'product',:episode,:source)")
    params = dict(project=project, episode=episode, source=source)
    if case == "valid":
        assert connection.scalar(query, params) == receipt
        assert (
            connection.scalar(
                text("SELECT ops.ddo_pdf_derivation_receipt('project','product','derivation')")
            )
            == receipt
        )
    else:
        with pytest.raises(DBAPIError) as refusal, connection.begin_nested():
            connection.execute(query, params)
        assert getattr(refusal.value.orig, "sqlstate", None) == state
        assert message in str(refusal.value)


@pytest.mark.parametrize(
    "case,state",
    [
        ("valid", None),
        ("project", "23514"),
        ("member", "23514"),
        ("support", "23514"),
        ("authority", "42501"),
        ("missing", "P0002"),
    ],
)
def test_pdf_capture_consumer_requires_whole_product_and_support_episode(
    source_capture_control, case, state
):
    connection, _, receipt = source_capture_control
    requests = table("ops.data_request")
    binding = dict(
        inputs=[dict(product_id="product", derivation_id="derivation")],
        support=[dict(derivation_id="derivation")],
    )
    if case == "member":
        binding["inputs"][0]["member_id"] = "member"
        connection.execute(
            requests.update().where(requests.c.id == "consumer").values(binding=binding)
        )
    elif case == "support":
        binding["support"] = []
        connection.execute(
            requests.update().where(requests.c.id == "consumer").values(binding=binding)
        )
    elif case == "authority":
        connection.execute(
            requests.update()
            .where(requests.c.id == "consumer")
            .values(binding={**binding, "authorize": False})
        )
    identity = "missing" if case == "missing" else "consumer"
    if case == "project":
        query = text(
            "SELECT ops.ddo_pdf_capture_source_for_request((SELECT r FROM ops.data_request r WHERE id='consumer'),'other','product','derivation')"
        )
    else:
        query = text(
            "SELECT ops.ddo_pdf_capture_source(:identity,'project','product','derivation')"
        )
    if case == "valid":
        assert connection.scalar(query, dict(identity=identity)) == receipt
    else:
        with pytest.raises(DBAPIError) as refusal, connection.begin_nested():
            connection.execute(query, dict(identity=identity))
        assert getattr(refusal.value.orig, "sqlstate", None) == state


def test_source_capture_generated_assets_keep_original_function_order():
    sources = source_native_sources()
    captured = {item.name: item.content for item in sources}
    assert {
        "native/data-operation-source-capture.sql",
        "native/source-capture-native.py",
    } <= captured.keys()
    from corpus_structure.semantic.data_operation_storage import native_protocol_sources

    complete_sources = native_protocol_sources()
    assert source_native_sql(complete_sources) == source_native_sql()
    sql = source_native_sql(complete_sources)
    names = [
        "ddo_original_document_view",
        "ddo_pdf_derivation_receipt",
        "ddo_pdf_capture_source",
        "ddo_pdf_capture_source_for_request",
        "ddo_impl_read_selected_pdf_source",
    ]
    positions = [sql.index("FUNCTION ops." + name + "(") for name in names]
    assert positions == sorted(positions)
    assert "__DDO_SOURCE_CAPTURE_PROGRAMS__" not in sql
