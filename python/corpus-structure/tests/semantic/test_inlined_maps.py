"""LinkML maps are keyed collections; list order must not become domain meaning."""

from dataclasses import replace
from decimal import Decimal
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
from corpus_structure.semantic.consolidation import SourceItem, assemble
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import (
    EvidenceRow,
    PublicationBatch,
    RoleRow,
    ValueRow,
    publish_batch,
)
from corpus_structure.semantic.releases import persist_release


def inputs():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    schema = {
        "id": "https://example.org/maps",
        "name": "maps",
        "imports": ["semantic_core"],
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "classes": {
            "Thing": {"attributes": {"label": {}}},
            "Parameter": {
                "attributes": {
                    "key": {"identifier": True},
                    "value": {"range": "decimal", "required": True},
                }
            },
            "MappedQualification": {
                "is_a": "Qualification",
                "attributes": {
                    "parameters": {"range": "Parameter", "multivalued": True, "inlined": True}
                },
            },
        },
    }
    return SourceBundle(
        "maps",
        (
            SourceArtifact("maps", yaml.safe_dump(schema).encode()),
            SourceArtifact("semantic_core", core.read_bytes()),
        ),
    )


def test_keyed_member_shape_rejects_mismatched_identifier():
    p = prepare_release(inputs())
    with pytest.raises(ValidationError, match="identifier"):
        p.validate_python(
            "MappedQualification",
            {
                "modality": "asserted",
                "polarity": True,
                "parameters": {"wrong": {"key": "scale", "value": Decimal("2")}},
            },
        )


def test_map_order_does_not_split_facts_and_native_keys_cannot_be_forged(
    semantic_db_engine, semantic_writer_engine
):
    p = prepare_release(inputs())
    with semantic_db_engine.begin() as conn:
        persist_release(conn, inputs(), ResolvedDependencies(), PreparationProfile(), p)
        conn.execute(insert(table("data.project")).values(project_id="p"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id="z", project_id="p", release_id=p.release_id
            )
        )
    parameters = {
        "scale": {"key": "scale", "value": Decimal("2.00")},
        "shape": {"key": "shape", "value": Decimal("3.00")},
    }
    item = SourceItem(
        "subject",
        "Thing",
        "label",
        "report",
        {"modality": "asserted", "polarity": True, "parameters": parameters},
        "source",
        "one",
        "stated",
        (EvidenceRow("ev", "source", "page#p", "parser", "1"),),
        qualification_class="MappedQualification",
    )
    other = replace(
        item,
        item="two",
        qualification={
            **item.qualification,
            "parameters": dict(reversed(tuple(parameters.items()))),
        },
    )
    batch = assemble(p, "z", "maps", (item, other))
    assert len(batch.fact) == 1
    assert len(batch.occurrence) == 2
    publish_batch(semantic_writer_engine, batch)
    with semantic_writer_engine.connect() as conn:
        assert (
            conn.execute(select(table("data.fact").c.fact_id)).scalar_one() == batch.fact[0].fact_id
        )
    map_id = next(r.parent_value_id for r in batch.value_role if r.role == "scale")
    # A disconnected typed qualifier still requires native structural conformance.
    # This bypasses Python validation without changing any existing fact identity.
    qualifier = next(
        value
        for value in batch.typed_value
        if value.datatype == next(d.iri for d in p.definitions if d.name == "MappedQualification")
    )
    scalar_roles = tuple(
        RoleRow("forged-q", role.role, 0, role.child_value_id)
        for role in batch.value_role
        if role.parent_value_id == qualifier.value_id and role.role != "parameters"
    )
    member = next(
        role.child_value_id
        for role in batch.value_role
        if role.parent_value_id == map_id and role.role == "scale"
    )
    forged = PublicationBatch(
        p.release_id,
        "z",
        "forged",
        typed_value=(
            ValueRow("forged-q", "record", datatype=qualifier.datatype),
            ValueRow("forged-map", "mapping"),
        ),
        value_role=(
            *scalar_roles,
            RoleRow("forged-q", "parameters", 0, "forged-map"),
            RoleRow("forged-map", "wrong", 0, member),
        ),
    )
    with pytest.raises(DBAPIError, match="inlined map key"):
        publish_batch(semantic_writer_engine, forged)
