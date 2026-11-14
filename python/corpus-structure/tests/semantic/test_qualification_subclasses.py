"""An explicitly selected qualification subtype preserves its actual semantic key policy."""

from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from sqlalchemy import insert, select
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.consolidation import SourceItem, assemble
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import EvidenceRow, publish_batch
from corpus_structure.semantic.releases import persist_release


def inputs():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    schema = {
        "id": "https://example.org/qualified",
        "name": "qualified",
        "imports": ["semantic_core"],
        "prefixes": {"ex": "https://example.org/", "cs": "https://corpus-structure.dev/semantic/"},
        "default_prefix": "ex",
        "classes": {
            "Thing": {"is_a": "Entity", "attributes": {"label": {"range": "string"}}},
            "ReportQualification": {
                "is_a": "Qualification",
                "attributes": {
                    "reporter": {"range": "string", "annotations": {"cs:key_role": "provenance"}},
                    "channel": {"range": "string", "annotations": {"cs:case": "casefold"}},
                },
            },
            "DomainQualification": {
                "is_a": "ReportQualification",
                "attributes": {"hedge": {"range": "string"}},
            },
            "Unrelated": {"attributes": {"modality": {}, "polarity": {"range": "boolean"}}},
        },
    }
    return SourceBundle(
        "qualified",
        (
            SourceArtifact("qualified", yaml.safe_dump(schema).encode()),
            SourceArtifact("semantic_core", core.read_bytes()),
        ),
    )


def items():
    q = {
        "modality": "asserted",
        "polarity": True,
        "reporter": "Alice",
        "channel": "Straße",
        "hedge": "measured",
    }
    item = SourceItem(
        "subject",
        "Thing",
        "label",
        "same",
        q,
        "source",
        "one",
        "stated",
        (EvidenceRow("ev", "source", "page#unit", "parser", "1"),),
        "DomainQualification",
    )
    return (
        replace(item, property_name="id", object="subject", item="identity"),
        item,
        replace(item, item="two", qualification={**q, "reporter": "Bob", "channel": "STRASSE"}),
    )


def test_explicit_subtype_boundary_and_identity_policy():
    release = prepare_release(
        inputs(),
        composed_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2"),
    )
    batch = assemble(release, "z", "b", items())
    assert len(batch.fact) == 2  # identity and label; reporter is provenance, channel casefolds.
    assert len(batch.occurrence) == 3
    leaf = next(d for d in release.definitions if d.name == "DomainQualification")
    assert {v.datatype for v in batch.typed_value if v.kind == "record"} == {leaf.iri}
    with pytest.raises(ValueError, match="undeclared qualification reporter"):
        release.fact_identity("z", "subject", "property", "object", items()[1].qualification)
    with pytest.raises(ValueError, match="not an admitted Qualification"):
        assemble(release, "z", "wrong", (replace(items()[1], qualification_class="Unrelated"),))
    with pytest.raises(ValidationError):
        assemble(
            release, "z", "missing", (replace(items()[1], qualification={"reporter": "Alice"}),)
        )
    changed = replace(
        items()[1], item="three", qualification={**items()[1].qualification, "hedge": "inferred"}
    )
    assert len(assemble(release, "z", "different", (items()[1], changed)).fact) == 2


def test_native_subtype_shape_and_key_roles(commit_db_engine, commit_writer_engine):
    bundle = inputs()
    release = prepare_release(
        bundle,
        composed_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2"),
    )
    with commit_db_engine.begin() as conn:
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
    batch = assemble(release, "z", "b", items())
    receipt = publish_batch(commit_writer_engine, batch)
    assert publish_batch(commit_writer_engine, batch) == receipt
    with commit_writer_engine.connect() as conn:
        assert len(conn.execute(select(table("data.fact"))).all()) == 2
        assert len(conn.execute(select(table("data.occurrence"))).all()) == 3


def test_native_unrelated_record_cannot_pose_as_qualification(
    commit_db_engine, commit_writer_engine
):
    bundle = inputs()
    release = prepare_release(
        bundle,
        composed_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2"),
    )
    with commit_db_engine.begin() as conn:
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
    batch = assemble(release, "z", "bad", items())
    leaf = next(d.iri for d in release.definitions if d.name == "DomainQualification")
    unrelated = next(d.iri for d in release.definitions if d.name == "Unrelated")
    forged = replace(
        batch,
        typed_value=tuple(
            replace(v, datatype=unrelated) if v.datatype == leaf else v for v in batch.typed_value
        ),
    ).bind_preparation(release)
    with pytest.raises(DBAPIError, match="typed qualification"):
        publish_batch(commit_writer_engine, forged)
