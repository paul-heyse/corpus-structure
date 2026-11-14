"""Actual report consumers distinguish publication from prepared source context."""

import json

import anyio
from fastmcp import Client
from mcp.types import TextContent
from sqlalchemy import text

from corpus_structure.ingest.pdf_section_views import published_section_drafts
from corpus_structure.intervene.semantic_server import SemanticProjectSession, build_semantic_server
from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.source_views import store_source_view
from corpus_structure.settings import Settings
from semantic.pdf_staging_support import private_build as private_build
from semantic.selected_source_native_support import publish_selected


def test_cli_mcp_published_pin_and_preparation_are_separate_read_only_observations(
    private_build, commit_db_engine, commit_writer_engine, commit_reader_engine, tmp_path, cli
):
    published = publish_selected(commit_writer_engine, private_build, tmp_path / "publication")
    with commit_writer_engine.connect() as conn:
        task = conn.execute(
            text("SELECT run_id,unit_id,attempt,claimed_by FROM ops.task WHERE id=:task"),
            dict(task=private_build.task_id),
        ).one()
    settings = Settings(
        database={
            "url": commit_reader_engine.url.set(drivername="postgresql").render_as_string(
                hide_password=False
            )
        }
    )
    pin = dict(
        task_id=private_build.task_id,
        product_key="selected",
        content_digest=published.logical_digest,
    )
    subject = tmp_path / "subject.json"
    subject.write_text(json.dumps(dict(**pin, run_id=task.run_id, section_pointer="#/groups/1")))

    def inspect():
        result = cli(
            "schema",
            "explain-operation",
            "read_source_view",
            "--release",
            private_build.release_id,
            "--subject",
            str(subject),
            "--json",
            settings=lambda: settings,
        )
        assert result.exit_code == 0, result.output
        value = json.loads(result.stdout)
        return value, {check["contract_ref"]: check for check in value["checks"]}

    before, checks = inspect()
    assert checks["published_document"]["status"] == "applicable"
    assert checks["selected_source_views"]["status"] == "unavailable"
    assert not before["complete"]  # An observation does not invent missing live evaluators.
    with commit_writer_engine.begin() as conn:
        assert conn.scalar(text("SELECT count(*) FROM kb.source_view")) == 0
        prepared = open_release(conn, private_build.release_id)
        reader = published_record_reader(conn, ProductReference(**pin), projection_context=prepared)
        assert reader is not None
        drafts = published_section_drafts(
            reader,
            document_id=task.unit_id,
            selections=("Selected chapter",),
            membership="direct",
            scope=None,
            consumer_release=private_build.release_id,
        )
        for position, draft in enumerate(drafts):
            store_source_view(
                conn,
                run_id=task.run_id,
                task_id=private_build.task_id,
                attempt=task.attempt,
                holder=task.claimed_by,
                draft=draft,
                position=position,
            )
    after, checks = inspect()
    assert checks["published_document"]["status"] == "applicable"
    assert checks["selected_source_views"]["status"] == "applicable"
    assert after["observed_revision"] == published.logical_digest
    publication = cli(
        "schema",
        "explain-operation",
        "publish_pdf_region_artifact",
        "--release",
        private_build.release_id,
        "--subject",
        str(subject),
        "--json",
        settings=lambda: settings,
    )
    assert publication.exit_code == 0, publication.output
    publication_checks = {
        item["contract_ref"]: item for item in json.loads(publication.stdout)["checks"]
    }
    assert publication_checks["published_document"]["status"] == "applicable"
    # Exact publication is observable; task ownership and mutation guards remain
    # native execution obligations rather than preflight authorization.
    assert publication_checks["invariant:published_document_address"]["status"] == "unresolved"

    async def journey():
        server = build_semantic_server(SemanticProjectSession(commit_reader_engine, "published"))
        async with Client(server) as client:
            answer = await client.call_tool(
                "explain_operation",
                dict(
                    release=private_build.release_id,
                    operation="read_source_view",
                    **pin,
                    run_id=task.run_id,
                    section_pointer="#/groups/1",
                ),
            )
            assert answer.structured_content is not None
            assert answer.structured_content["checks"] == after["checks"]
            missing = await client.call_tool(
                "explain_operation",
                dict(
                    release=private_build.release_id,
                    operation="read_source_view",
                    **dict(pin, content_digest="0" * 64),
                    run_id=task.run_id,
                ),
            )
            assert missing.structured_content is not None
            missing_checks = {
                check["contract_ref"]: check for check in missing.structured_content["checks"]
            }
            assert missing_checks["published_document"]["status"] == "unavailable"
            assert missing_checks["selected_source_views"]["status"] == "unavailable"
            malformed = await client.call_tool(
                "explain_operation",
                dict(
                    release=private_build.release_id,
                    operation="read_source_view",
                    **dict(pin, task_id=0),
                ),
                raise_on_error=False,
            )
            assert malformed.is_error
            block = malformed.content[0]
            assert isinstance(block, TextContent)
            failure = json.loads(block.text)
            assert failure["validation"]["release_id"] == private_build.release_id
            assert failure["validation"]["model_id"] == after["model_id"]
            observation = failure["validation"]["observations"][0]
            assert observation["operation"] == "read_source_view"
            assert observation["category"] == "invalid_input"
            assert observation["input_path"] == "/task_id"

    anyio.run(journey)
    subject.write_text(json.dumps(dict(pin, task_id=0)))
    invalid = cli(
        "schema",
        "explain-operation",
        "read_source_view",
        "--release",
        private_build.release_id,
        "--subject",
        str(subject),
        "--json",
        settings=lambda: settings,
    )
    assert invalid.exit_code == 1, invalid.output
    validation = json.loads(invalid.stdout)["error"]["validation"]
    assert validation["release_id"] == private_build.release_id
    assert validation["model_id"] == after["model_id"]
    observation = validation["observations"][0]
    assert observation["operation"] == "read_source_view"
    assert observation["category"] == "invalid_input"
    assert observation["input_path"] == "/task_id"
    with commit_reader_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM kb.source_view")) == len(drafts)
    with commit_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM ops.pdf_published_revision")) == 1
