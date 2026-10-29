"""A real source snapshot is computed locally then admitted through protected binary COPY."""

from decimal import Decimal

import pyarrow as pa
import pytest
from sqlalchemy import insert, select

from corpus_structure.semantic import (
    PreparationProfile,
    SourceArtifact,
    SourceBundle,
    fact_key,
    occurrence_key,
    prepare_release,
)
from corpus_structure.semantic.analytical_profile import analytical_inputs
from corpus_structure.semantic.analytics import AnalysisScope, load_packet
from corpus_structure.semantic.arrow_publication import (
    ArrowPublicationBatch,
    StaleAnalysisError,
    publish_arrow,
    stage_schema,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import (
    EntityRow,
    EvidenceRow,
    FactRow,
    MembershipRow,
    MembershipSupportRow,
    OccurrenceRow,
    PublicationBatch,
    SupportRow,
    ValueRow,
    publish_batch,
)
from corpus_structure.semantic.query import QuerySpec, read_session
from corpus_structure.semantic.releases import persist_release
from corpus_structure.settings import Settings


def test_native_snapshot_kernel_arrow_publication(
    semantic_db_engine, semantic_reader_engine, semantic_writer_engine
):
    bundle, deps = analytical_inputs(
        SourceBundle(
            "journey",
            (
                SourceArtifact(
                    "journey",
                    b"""id: https://example.org/journey
name: journey
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types: {string: {base: str, uri: 'xsd:string'}, integer: {base: int, uri: 'xsd:integer'}}
classes:
  Thing:
    attributes:
      label: {multivalued: true}
      counter: {range: integer}
""",
                ),
            ),
        )
    )
    release = prepare_release(bundle, deps)
    rid, z, p = release.release_id, "z", "https://example.org/label"
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, deps, PreparationProfile(), release)
        conn.execute(insert(table("data.project")).values(project_id="p"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id=z, release_id=rid, project_id="p"
            )
        )
    fact = fact_key(rid, z, "e", p, "shared", {})
    occurrences = [occurrence_key(rid, z, "source", str(i)) for i in range(2)]
    integer_fact = fact_key(rid, z, "e", "https://example.org/counter", 42, {})
    source = PublicationBatch(
        rid,
        z,
        "source",
        entity=(EntityRow("e"),),
        membership=(MembershipRow("e", "https://example.org/Thing", "source"),),
        typed_value=(
            ValueRow("v", "string", text_value="shared"),
            ValueRow("n", "decimal", decimal_lexical="1.1234567890125"),
            ValueRow("i", "integer", text_value="42", integer_value=Decimal(42)),
        ),
        fact=(
            FactRow(fact, "e", p, "v"),
            FactRow(integer_fact, "e", "https://example.org/counter", "i"),
        ),
        occurrence=tuple(
            OccurrenceRow(o, fact, "source", str(i), "v") for i, o in enumerate(occurrences)
        ),
        support=tuple(SupportRow(fact, o) for o in occurrences),
        evidence=(EvidenceRow("ev", "urn:source", "line:1", "fixture", "1"),),
        membership_support=(MembershipSupportRow("e", "https://example.org/Thing", "ev"),),
    )
    publish_batch(semantic_writer_engine, source)
    uri = semantic_reader_engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    with read_session(semantic_reader_engine, z) as session:
        cls = session.class_handle("Thing")
        counted = session.query(
            QuerySpec(cls, session.property_handle(cls, "counter"), projection="fact")
        )
        assert counted.rows[0].object == 42
        driver_path = Settings().analytics.adbc_driver_path
        packet = load_packet(
            session, uri, driver_path=None if driver_path is None else str(driver_path)
        )
    numeric = next(r for r in packet.relations["typed_value"].to_pylist() if r["value_id"] == "n")
    assert numeric["decimal_value"] == Decimal("1.123456789012")
    assert numeric["decimal_lexical"] == "1.1234567890125"
    with AnalysisScope(packet) as scope:
        result = (
            scope.fact_support()
            .filter("property_id = 'https://example.org/label'")
            .to_arrow_table()
            .to_pylist()
        )
        assert len(result) == 1 and len(result[0]["supports"]) == 2
        raw = scope.declared_view(p).project("fact_id, true AS selected").to_arrow_table()
        selections = pa.Table.from_arrays(raw.columns, schema=stage_schema("selection"))
    batch = ArrowPublicationBatch(
        rid,
        z,
        "analysis",
        {"selection": selections},
        expected_data_revision=packet.binding.data_revision,
    )
    receipt = publish_arrow(semantic_writer_engine, batch)
    assert receipt.data_revision == 2
    assert publish_arrow(semantic_writer_engine, batch) == receipt
    with read_session(semantic_reader_engine, z) as session:
        cls = session.class_handle("Thing")
        prop = session.property_handle(cls, "label")
        assert len(session.query(QuerySpec(cls, prop, projection="accepted")).rows) == 1
    with pytest.raises(StaleAnalysisError):
        publish_arrow(
            semantic_writer_engine,
            ArrowPublicationBatch(
                rid, z, "stale", {"selection": selections}, expected_data_revision=1
            ),
        )
    with semantic_db_engine.connect() as conn:
        assert len(conn.execute(select(table("data.occurrence"))).all()) == 2
