from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.consolidation import SourceItem, assemble
from corpus_structure.semantic.publication import EvidenceRow


def inputs():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    domain = {
        "id": "https://example.org/domain",
        "name": "domain",
        "imports": ["semantic_core"],
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "classes": {"Thing": {"is_a": "Entity", "attributes": {"label": {"range": "string"}}}},
    }
    return SourceBundle(
        "domain",
        (
            SourceArtifact("domain", yaml.safe_dump(domain).encode()),
            SourceArtifact("semantic_core", core.read_bytes()),
        ),
    )


def prepared(bundle=None):
    return prepare_release(
        inputs() if bundle is None else bundle,
        composed_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2"),
    )


def test_repeated_items_keep_occurrences_and_shared_fact_without_selecting_truth():
    release = prepared()
    item = SourceItem(
        "subject",
        "Thing",
        "label",
        "same",
        {"modality": "asserted", "polarity": True},
        "source",
        "item:0",
        "stated",
        (EvidenceRow("evidence", "source", "page#p", "parser", "1"),),
    )
    batch = assemble(release, "realization", "batch", (item, replace(item, item="item:1")))
    assert len(batch.fact) == 1
    assert len(batch.occurrence) == 2
    assert len(batch.support) == 2
    assert batch.selection == ()
    assert len(batch.occurrence_establishment) == 2
    assert len(batch.evidence) == 1
    agent = replace(item, item="agent", establishment="agent_asserted")
    mixed = assemble(release, "realization", "mixed", (item, agent))
    assert mixed.content == assemble(release, "realization", "mixed", (agent, item)).content
    assert mixed.membership[0].establishment == "stated"
    assert {row.establishment for row in mixed.occurrence_establishment} == {
        "stated",
        "agent_asserted",
    }
    assert (
        batch.content
        == assemble(release, "realization", "batch", (replace(item, item="item:1"), item)).content
    )
    with pytest.raises(ValueError, match="different content"):
        assemble(release, "realization", "batch", (item, replace(item, object="changed")))
    with pytest.raises(ValueError, match="inference publishes proofs"):
        assemble(release, "realization", "batch", (replace(item, establishment="derived"),))


def test_different_semantic_scope_does_not_fuse_facts():
    release = prepared()
    item = SourceItem(
        "subject",
        "Thing",
        "label",
        "same",
        {
            "modality": "asserted",
            "polarity": True,
            "scope": {"extent": "section", "locator": "page#one"},
        },
        "source",
        "item:0",
        "stated",
        (EvidenceRow("evidence", "source", "page#p", "parser", "1"),),
    )
    other = replace(
        item,
        item="item:1",
        qualification={**item.qualification, "scope": {"extent": "section", "locator": "page#two"}},
    )
    assert len(assemble(release, "realization", "batch", (item, other)).fact) == 2


def test_assembly_publishes_with_native_identity_and_scoped_source_support(
    semantic_db_engine, semantic_writer_engine
):
    from sqlalchemy import insert, select

    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.publication import publish_batch
    from corpus_structure.semantic.releases import persist_release

    release = prepared()
    with semantic_db_engine.begin() as conn:
        persist_release(
            conn,
            inputs(),
            composed_dependencies(ResolvedDependencies()),
            PreparationProfile(version="semantic-2"),
            release,
        )
        conn.execute(insert(table("data.project")).values(project_id="p"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id="realization", project_id="p", release_id=release.release_id
            )
        )
    item = SourceItem(
        "subject",
        "Thing",
        "label",
        "same",
        {"modality": "asserted", "polarity": True},
        "source",
        "item:0",
        "stated",
        (EvidenceRow("evidence", "source", "page#p", "parser", "1"),),
    )
    identity = replace(item, property_name="id", object="subject", item="identity")
    batch = assemble(
        release, "realization", "batch", (identity, item, replace(item, item="item:1"))
    )
    receipt = publish_batch(semantic_writer_engine, batch)
    assert publish_batch(semantic_writer_engine, batch) == receipt
    with semantic_writer_engine.connect() as conn:
        assert len(conn.execute(select(table("data.occurrence"))).all()) == 3
        assert len(conn.execute(select(table("data.fact"))).all()) == 2
        assert len(conn.execute(select(table("data.occurrence_establishment"))).all()) == 3


@pytest.mark.parametrize("confidence", (Decimal("0.9500"), Decimal("-0.0000")))
def test_assessment_confidence_stays_exact_through_arrow_and_native_receipts(
    semantic_db_engine, semantic_writer_engine, confidence
):
    from sqlalchemy import insert, select

    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies
    from corpus_structure.semantic.arrow_publication import ArrowPublicationBatch, publish_arrow
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.publication import AssessmentRow, PublicationBatch, publish_batch
    from corpus_structure.semantic.releases import persist_release

    release = prepared()
    with semantic_db_engine.begin() as conn:
        persist_release(
            conn,
            inputs(),
            composed_dependencies(ResolvedDependencies()),
            PreparationProfile(version="semantic-2"),
            release,
        )
        conn.execute(insert(table("data.project")).values(project_id="p"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id="realization", project_id="p", release_id=release.release_id
            )
        )
    item = SourceItem(
        "subject",
        "Thing",
        "id",
        "subject",
        {"modality": "asserted", "polarity": True},
        "source",
        "identity",
        "stated",
        (EvidenceRow("evidence", "source", "page#p", "parser", "1"),),
    )
    source = assemble(release, "realization", "source", (item,))
    publish_batch(semantic_writer_engine, source)
    assessment = PublicationBatch(
        release.release_id,
        "realization",
        "assessment",
        assessment=(
            AssessmentRow(
                "a",
                "operation",
                "1",
                "undecided",
                fact_id=source.fact[0].fact_id,
                confidence=confidence,
                uncertainty="symbolic comparison incomplete",
            ),
        ),
    )
    arrow = ArrowPublicationBatch.from_rows(assessment)
    assert arrow.content == assessment.content
    assert publish_arrow(semantic_writer_engine, arrow) == publish_batch(
        semantic_writer_engine, assessment
    )
    with semantic_writer_engine.connect() as conn:
        assert (
            conn.execute(select(table("data.assessment").c.confidence)).scalar_one() == confidence
        )


def test_non_utc_instants_publish_with_equivalent_identity(
    semantic_db_engine, semantic_writer_engine
):
    from datetime import UTC, datetime, timedelta, timezone

    from sqlalchemy import insert, select

    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.publication import publish_batch
    from corpus_structure.semantic.releases import persist_release

    bundle = inputs()
    body = yaml.safe_load(bundle.sources[0].content)
    body["classes"]["Thing"]["attributes"]["when"] = {"range": "datetime"}
    bundle = SourceBundle(
        bundle.root,
        (
            SourceArtifact(bundle.sources[0].name, yaml.safe_dump(body).encode()),
            *bundle.sources[1:],
        ),
    )
    release = prepared(bundle)
    with semantic_db_engine.begin() as conn:
        persist_release(
            conn,
            bundle,
            composed_dependencies(ResolvedDependencies()),
            PreparationProfile(version="semantic-2"),
            release,
        )
        conn.execute(insert(table("data.project")).values(project_id="p"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id="z", project_id="p", release_id=release.release_id
            )
        )
    local = datetime(2026, 10, 29, 12, tzinfo=timezone(timedelta(hours=2)))
    item = SourceItem(
        "subject",
        "Thing",
        "when",
        local,
        {"modality": "asserted", "polarity": True},
        "source",
        "local",
        "stated",
        (EvidenceRow("ev", "source", "page#p", "parser", "1"),),
    )
    identity = replace(item, property_name="id", object="subject", item="identity")
    batch = assemble(
        release,
        "z",
        "time",
        (identity, item, replace(item, item="utc", object=local.astimezone(UTC))),
    )
    assert len([f for f in batch.fact if f.property_id.endswith("/when")]) == 1
    publish_batch(semantic_writer_engine, batch)
    with semantic_writer_engine.connect() as conn:
        values = table("data.typed_value")
        assert (
            conn.execute(select(values.c.text_value).where(values.c.kind == "datetime"))
            .scalars()
            .all()
            == ["2026-10-29T10:00:00+00:00"] * 2
        )


def test_report_decimal_representations_survive_fact_fusion(
    semantic_db_engine, semantic_writer_engine
):
    from sqlalchemy import insert, text

    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.publication import publish_batch
    from corpus_structure.semantic.releases import persist_release

    bundle = inputs()
    body = yaml.safe_load(bundle.sources[0].content)
    body["classes"]["Thing"]["attributes"]["amount"] = {"range": "decimal"}
    bundle = SourceBundle(
        bundle.root,
        (
            SourceArtifact(bundle.sources[0].name, yaml.safe_dump(body).encode()),
            *bundle.sources[1:],
        ),
    )
    release = prepared(bundle)
    with semantic_db_engine.begin() as conn:
        persist_release(
            conn,
            bundle,
            composed_dependencies(ResolvedDependencies()),
            PreparationProfile(version="semantic-2"),
            release,
        )
        conn.execute(insert(table("data.project")).values(project_id="p"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id="z", project_id="p", release_id=release.release_id
            )
        )
    first = SourceItem(
        "subject",
        "Thing",
        "amount",
        Decimal("1.2300"),
        {"modality": "asserted", "polarity": True},
        "source",
        "one",
        "stated",
        (EvidenceRow("ev", "source", "page#p", "parser", "1"),),
    )
    second = replace(first, item="two", object=Decimal("1.23"))
    identity = replace(first, item="id", property_name="id", object="subject")
    batch = assemble(release, "z", "representations", (identity, first, second))
    assert (
        batch.content
        == assemble(release, "z", "representations", (second, identity, first)).content
    )
    assert len(batch.fact) == 2  # amount plus declared identity, not one fact per representation
    publish_batch(semantic_writer_engine, batch)
    with semantic_writer_engine.connect() as conn:
        found = (
            conn.execute(
                text(
                    "SELECT v.decimal_lexical FROM data.occurrence o JOIN data.typed_value v "
                    "ON "
                    "(v.release_id,v.realization_id,v.value_id)="
                    "(o.release_id,o.realization_id,o.report_object_value_id) "
                    "WHERE v.kind='decimal' ORDER BY o.item"
                )
            )
            .scalars()
            .all()
        )
        assert found == ["1.2300", "1.23"]
