"""Real PDF rendering and protected artifact persistence share the published address."""

from dataclasses import asdict
from hashlib import sha256
from importlib.resources import files
from io import BytesIO
from types import SimpleNamespace

import pytest
from docling_core.types.doc import (
    BoundingBox,
    DocItemLabel,
    DoclingDocument,
    GroupLabel,
    PageItem,
    ProvenanceItem,
    Size,
)
from PIL import Image
from pydantic import JsonValue, create_model
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.ingest.pdf import PdfConversion, publication_payload
from corpus_structure.ingest.pdf_hierarchy import snapshot
from corpus_structure.ingest.pdf_section_views import published_section_drafts
from corpus_structure.semantic.invariant_failures import (
    InvariantViolation,
    classify_invariant_failure,
)
from corpus_structure.semantic.operation_reporting import validation_failure_report
from corpus_structure.semantic.operations import create_task, record_method
from corpus_structure.semantic.pdf_contracts import pdf_context_for_task, prepare_pdf_product
from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime_binding_store import runtime_binding_for_run
from corpus_structure.semantic.runtime_bindings import prepare_runtime_binding
from corpus_structure.semantic.source_views import (
    load_source_view,
    store_native_source_frame,
    store_region_artifact,
    store_source_view,
)
from corpus_structure.serve.native_regions import render_pdf_region

from .native_record_fixtures import publish_native_record_fixture
from .pdf_staging_support import private_build as private_build


@pytest.mark.parametrize("private_build", ["renderable_pdf"], indirect=True)
def test_published_region_render_frame_artifact_replay_and_invalid_address(
    private_build,
    semantic_db_engine,
    semantic_writer_engine,
    tmp_path,
):
    with semantic_writer_engine.connect() as conn:
        task = conn.execute(
            text("SELECT run_id,unit_id,attempt,claimed_by FROM ops.task WHERE id=:task"),
            dict(task=private_build.task_id),
        ).one()
        original = bytes(
            conn.scalar(
                text("SELECT content FROM kb.source_artifact WHERE artifact_digest=:digest"),
                dict(digest=private_build.source_digest),
            )
        )
        recipe = bytes(
            conn.scalar(
                text("SELECT content FROM kb.source_artifact WHERE artifact_digest=:digest"),
                dict(digest=private_build.recipe_digest),
            )
        )
        context = pdf_context_for_task(conn, private_build.task_id)
    document = DoclingDocument(name="Qualified render source")
    document.pages[1] = PageItem(page_no=1, size=Size(width=612, height=792))
    section = document.add_group(label=GroupLabel.SECTION, name="Region section")
    item = document.add_text(
        label=DocItemLabel.TEXT,
        text="evidence",
        orig="evidence",
        parent=section,
        prov=ProvenanceItem(
            page_no=1,
            charspan=(0, 8),
            bbox=BoundingBox(l=20, t=30, r=80, b=70, coord_origin="TOPLEFT"),
        ),
    )
    schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    conversion = PdfConversion(
        sha256(original).hexdigest(),
        recipe,
        snapshot(document),
        "success",
        (),
        (),
        (),
        None,
    )
    payload = publication_payload(
        conversion,
        product_key="region-source",
        schema_digest=sha256(schema).hexdigest(),
    )
    product = prepare_pdf_product(payload, original, schema, recipe, context=context)
    published = publish_native_record_fixture(
        semantic_writer_engine,
        tmp_path / "records",
        task_id=private_build.task_id,
        attempt=private_build.attempt,
        holder=private_build.holder,
        product=product,
        document=document,
    )
    reference = ProductReference(private_build.task_id, "region-source", published.logical_digest)
    with semantic_writer_engine.begin() as conn:
        prepared = open_release(conn, private_build.release_id)
        reader = published_record_reader(conn, reference, projection_context=prepared)
        assert reader is not None
        region = reader.region(item.self_ref, 0)
        drafts = published_section_drafts(
            reader,
            document_id=task.unit_id,
            selections=("Region section",),
            membership="direct",
            scope=None,
            consumer_release=private_build.release_id,
        )
        assert len(drafts) == 1
        view_id = store_source_view(
            conn,
            run_id=task.run_id,
            task_id=private_build.task_id,
            attempt=private_build.attempt,
            holder=private_build.holder,
            draft=drafts[0],
            position=0,
        )
        view = load_source_view(conn, view_id, analysis=False)
        frame = native_source_frame(view, ())
        config = record_method(
            conn,
            SimpleNamespace(
                name="native.region-frame",
                version="1",
                family="agent",
                tier="agent",
                confidence_source=None,
                unit_type="source_view",
                Config=create_model("RegionFrameConfig"),
            ),
            "default",
            {},
            "region-frame",
            prepared=prepared,
        )
        agent_task = create_task(
            conn,
            run_id=task.run_id,
            config_id=config,
            stage="agent",
            unit_type="source_view",
            unit_id=view_id,
            unit_key=view.ref.key,
            input_hash="region-frame",
            agent=True,
            packet_hash="a" * 64,
        )
        store_native_source_frame(
            conn, task_id=agent_task, packet_hash="a" * 64, frame=asdict(frame)
        )
    rendered = render_pdf_region(original, region, scale=2)
    with Image.open(BytesIO(rendered)) as image:
        assert image.size == (120, 80)
        assert image.convert("RGB").getpixel((40, 40)) == (255, 0, 0)
        assert image.convert("RGB").getpixel((100, 20)) == (0, 128, 0)
    selection: dict[str, JsonValue] = dict(
        task_id=reference.task_id,
        product_key=reference.product_key,
        content_digest=reference.content_digest,
        pointer=item.self_ref,
        region_index=0,
    )

    def store(conn, selected: dict[str, JsonValue], *, holder: str = private_build.holder):
        return store_region_artifact(
            conn,
            task_id=private_build.task_id,
            attempt=private_build.attempt,
            holder=holder,
            selection=selected,
            recipe_bytes=b'{"recipe":"qualified-region-control"}',
            content=rendered,
        )

    with semantic_writer_engine.begin() as conn:
        digest = store(conn, selection)
        assert store(conn, selection) == digest == sha256(rendered).hexdigest()
    for changed in (
        dict(selection, pointer="#/texts/999"),
        dict(selection, content_digest="0" * 64),
    ):
        with semantic_writer_engine.begin() as conn, pytest.raises(DBAPIError):
            store(conn, changed)
    with semantic_writer_engine.begin() as conn, pytest.raises(DBAPIError):
        store(conn, selection, holder="stale-renderer")
    # Exercise the actual composite endpoint constraint independently of the
    # protected writer's own address lookup. Both the private build and public
    # pin exist; they must not be combined into a fabricated placement.
    assert private_build.build_id != published.build_id
    with pytest.raises(DBAPIError) as misplaced, semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.execute(
            text(
                "INSERT INTO ops.native_region_artifact "
                "(task_id,native_task_id,native_product_key,native_content_digest,"
                "native_build_id,native_revision_id,pointer,region_index,"
                "recipe_digest,artifact_digest) "
                "VALUES(:task,:producer,:product,:digest,:build,:build,:pointer,0,:recipe,:artifact)"
            ),
            dict(
                task=agent_task,
                producer=reference.task_id,
                product=reference.product_key,
                digest=reference.content_digest,
                build=private_build.build_id,
                pointer=item.self_ref,
                recipe=sha256(b'{"recipe":"qualified-region-control"}').hexdigest(),
                artifact=digest,
            ),
        )
    failure = classify_invariant_failure(
        context.execution,
        "publish_pdf_region_artifact",
        misplaced.value,
        release_id=private_build.release_id,
    )
    assert failure is not None, str(misplaced.value.orig)
    assert failure.code == "pdf.published_document_address"
    diagnostic = validation_failure_report(InvariantViolation(failure)).model_dump(mode="json")
    assert diagnostic["model_id"] == context.execution.model_id
    assert diagnostic["release_id"] == private_build.release_id
    with semantic_db_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT a.native_build_id,a.native_revision_id,a.pointer,a.region_index,s.content "
                "FROM ops.native_region_artifact a JOIN kb.source_artifact s "
                "ON s.artifact_digest=a.artifact_digest WHERE a.task_id=:task"
            ),
            dict(task=private_build.task_id),
        ).one()
        assert tuple(row[:4]) == (published.build_id, published.build_id, item.self_ref, 0)
        assert bytes(row.content) == rendered
        assert conn.scalar(text("SELECT count(*) FROM ops.native_region_artifact")) == 1
        assert conn.scalar(text("SELECT count(*) FROM ops.native_source_frame")) == 1

    # The actual mutating MCP tool renders/persists first; inline delivery has its
    # own byte disposition and must never erase the committed artifact reference.
    import anyio
    from fastmcp import Client
    from mcp.types import CallToolResult as WireToolResult
    from sqlalchemy import event

    from corpus_structure.intervene.semantic_server import (
        SemanticAgentSession,
        _rendered_artifact_result,
        build_semantic_server,
    )
    from corpus_structure.semantic.native_requests import NativeRequestResult

    server = build_semantic_server(SemanticAgentSession(semantic_writer_engine, task.run_id))
    deliveries = []

    async def image_delivery():
        async with Client(server) as client:
            for cap in (1024 * 1024, 1024):
                delivered = await client.call_tool(
                    "render_source_region",
                    {
                        "run_id": task.run_id,
                        "source_view_id": view_id,
                        "pointer": item.self_ref,
                        "region_index": 0,
                        "scale": 8,
                        "max_bytes": cap,
                    },
                    raise_on_error=False,
                )
                deliveries.append(delivered)

    anyio.run(image_delivery)
    included, refused = deliveries
    included_body, refused_body = included.structured_content, refused.structured_content
    assert included_body is not None and refused_body is not None, [
        content.text
        for delivery in deliveries
        for content in delivery.content
        if content.type == "text"
    ]
    assert not included.is_error and included_body["inline_image"]["disposition"] == "included"
    assert any(content.type == "image" for content in included.content)
    assert refused.is_error and refused_body["inline_image"]["disposition"] == "refused"
    assert all(content.type != "image" for content in refused.content)
    assert refused_body["artifact_digest"] == included_body["artifact_digest"]
    assert refused_body["inline_image"]["reason"] == "oversized_item"
    expected_runtime = prepare_runtime_binding(prepared)
    with semantic_db_engine.connect() as conn:
        for body in (included_body, refused_body):
            assert (
                conn.scalar(
                    text("SELECT run_id FROM ops.task WHERE id=:task"),
                    {"task": body["task_id"]},
                )
                == body["run_id"]
            )
            assert runtime_binding_for_run(conn, body["run_id"], prepared) == expected_runtime
        artifact_digest = refused_body["artifact_digest"]
        assert (
            conn.scalar(
                text("SELECT count(*) FROM kb.source_artifact WHERE artifact_digest=:digest"),
                {"digest": artifact_digest},
            )
            == 1
        )
        origin = included_body["task_id"]
        assert conn.scalar(text("SELECT status FROM ops.task WHERE id=:id"), {"id": origin}) in {
            "empty",
            "reused",
        }
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM ops.native_region_artifact WHERE artifact_digest=:digest"
                ),
                {"digest": artifact_digest},
            )
            >= 1
        )

    # A direct delivery replay proves the large artifact body is never selected
    # when its retained scalar length already excludes inline transfer.
    selected_sql = []

    def record_sql(conn, cursor, statement, parameters, context, executemany):
        selected_sql.append(statement)

    event.listen(semantic_writer_engine, "before_cursor_execute", record_sql)
    try:
        native = NativeRequestResult(
            **{
                key: included_body[key]
                for key in (
                    "run_id",
                    "task_id",
                    "cut_id",
                    "status",
                    "source_view_id",
                    "product_digest",
                    "artifact_digest",
                    "result",
                    "error",
                )
            }
        )
        bounded = _rendered_artifact_result(semantic_writer_engine, native, 1024)
    finally:
        event.remove(semantic_writer_engine, "before_cursor_execute", record_sql)
    wire = bounded.to_mcp_result()
    assert isinstance(wire, WireToolResult)
    assert wire.is_error
    assert len(wire.model_dump_json(by_alias=True, exclude_none=True).encode()) <= 1024
    assert any("octet_length" in statement for statement in selected_sql)
    assert not any("SELECT kb.source_artifact.content" in statement for statement in selected_sql)
