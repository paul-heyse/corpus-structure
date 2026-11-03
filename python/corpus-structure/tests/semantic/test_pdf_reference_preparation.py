"""Reference preparation preserves representation-independent targets and ambiguity."""

import json
from hashlib import sha256

import pyarrow as pa
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.ingest.pdf_stream_types import PdfReplayRef
from corpus_structure.ingest.pdf_streaming import iter_replay_artifact_batches
from corpus_structure.semantic.pdf_publication import freeze_pdf_build, prepare_pdf_build
from corpus_structure.semantic.pdf_staging import adopt_pdf_batch, stage_schema

from .pdf_staging_support import private_build as private_build
from .test_pdf_publication import stage_complete_native


@pytest.mark.parametrize(
    "case",
    ["inline", "inline_stream", "stream_inline", "stream_stream", "graph", "ambiguous", "explicit"],
)
def test_prepared_reference_resolves_exact_target_or_refuses_ambiguity(
    private_build, semantic_db_engine, semantic_writer_engine, tmp_path, case
):
    build = private_build
    stage_complete_native(semantic_writer_engine, build, tmp_path)
    common = dict(product_id=build.product_id, revision_id=build.revision_id)
    pointer = "#/texts/synthetic"
    target_stream = case in {"inline_stream", "stream_stream"}
    pointer_stream = case in {"stream_inline", "stream_stream"}
    streams = set()
    if target_stream or pointer_stream or case == "ambiguous":
        streams.add("reference-address")
    path = tmp_path / "reference-address.txt"
    path.write_bytes(pointer.encode())
    replay = PdfReplayRef(path, sha256(path.read_bytes()).hexdigest(), path.stat().st_size, "text")
    for stream in streams:
        for family, batch in iter_replay_artifact_batches(
            replay,
            build_id=build.build_id,
            stream_id=stream,
            encoding_profile="pdf-record-scalar-v1:s",
        ):
            with semantic_writer_engine.begin() as conn:
                adopt_pdf_batch(conn, build, "reference-" + family, {family: [batch]})

    def node(record_id, address, stream=None, *, kind="TextItem", scalars=None):
        return dict(
            **common,
            record_id=record_id,
            native_type=kind,
            family="node",
            native_address=address,
            native_address_stream_id=stream,
            scalars_json=json.dumps(scalars or {"text": "independent synthetic node"}),
            structure_json='{"fields":{}}',
        )

    rows = [node("reference-source", "#/graphs/0/links/0")]
    if case == "graph":
        rows.append(
            node("expected-target", "#/graphs/0/cells/0", kind="GraphCell", scalars={"cell_id": 7})
        )
        # Same cell ID in a different graph must not become a second target.
        rows.append(
            node("other-graph", "#/graphs/1/cells/0", kind="GraphCell", scalars={"cell_id": 7})
        )
    else:
        rows.append(
            node(
                "expected-target",
                None if target_stream else pointer,
                "reference-address" if target_stream else None,
            )
        )
    if case == "ambiguous":
        rows.append(node("duplicate-target", None, "reference-address"))
    reference = dict(
        **common,
        reference_id="independent-reference",
        source_id="reference-source",
        field_name="source_cell_id" if case == "graph" else "cref",
        native_pointer=None if pointer_stream else ("7" if case == "graph" else pointer),
        native_pointer_stream_id="reference-address" if pointer_stream else None,
        target_id="reference-source" if case == "explicit" else None,
    )
    with semantic_writer_engine.begin() as conn:
        adopt_pdf_batch(
            conn,
            build,
            "reference-nodes",
            {"native": [pa.RecordBatch.from_pylist(rows, schema=stage_schema("native"))]},
        )
        adopt_pdf_batch(
            conn,
            build,
            "reference-link",
            {
                "reference": [
                    pa.RecordBatch.from_pylist([reference], schema=stage_schema("reference"))
                ]
            },
        )
        frozen = freeze_pdf_build(conn, build, kind="native")
    if case == "ambiguous":
        with (
            pytest.raises(DBAPIError, match="more than one row returned"),
            semantic_writer_engine.begin() as conn,
        ):
            prepare_pdf_build(conn, frozen)
        return
    with semantic_writer_engine.begin() as conn:
        prepare_pdf_build(conn, frozen)
    with semantic_db_engine.connect() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        target = conn.execute(
            text(
                "SELECT target_id FROM kb.pdf_record_reference WHERE product_id=:product "
                "AND reference_id='independent-reference'"
            ),
            {"product": build.product_id},
        ).scalar_one()
    assert target == ("reference-source" if case == "explicit" else "expected-target")
