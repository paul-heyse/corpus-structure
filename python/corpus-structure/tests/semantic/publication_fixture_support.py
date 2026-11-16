"""Explicit publication transport fixtures, independent of old source/task scenarios."""

from functools import cache, wraps
from typing import Any, Literal

import yaml
from corpus_structure.semantic.contracts import implementation_overridden
from sqlalchemy import insert

from corpus_structure.semantic.identity import fact_key, occurrence_key
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import (
    EntityRow,
    EvidenceRow,
    FactRow,
    MembershipRow,
    MembershipSupportRow,
    OccurrenceRow,
    PublicationBatch,
    SelectionRow,
    SupportRow,
    ValueRow,
)

Z = "realization:test"
C = "https://example/Thing"
P = "https://example/label"


def _assemble_fixture_model(
    scope: Literal["shape", "accepted_value", "occurrence", "context"] = "accepted_value",
    unique=False,
    label_range="string",
    inlined=False,
    record_target=False,
    minimum=None,
    maximum=None,
    qualification=False,
    conditional=False,
    composed=True,
):
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release

    label: dict[str, Any] = {
        "range": label_range,
        "inlined": inlined,
        "annotations": {"cs:constraint_scope": scope, "cs:case": "casefold"},
    }
    if minimum is not None:
        label["minimum_value"] = minimum
    if maximum is not None:
        label["maximum_value"] = maximum
    thing: dict[str, Any] = {"attributes": {"label": label}}
    if unique:
        thing["unique_keys"] = {"label_identity": {"unique_key_slots": ["label"]}}
    schema: dict[str, Any] = {
        "id": "https://example/publication-fixture",
        "name": "publication",
        "prefixes": {"ex": "https://example/"},
        "default_prefix": "ex",
        "types": {
            "string": {"base": "str", "uri": "http://www.w3.org/2001/XMLSchema#string"},
            "decimal": {"base": "Decimal", "uri": "http://www.w3.org/2001/XMLSchema#decimal"},
            "boolean": {"base": "bool", "uri": "http://www.w3.org/2001/XMLSchema#boolean"},
        },
        "classes": {
            "Thing": thing,
            "Record": {
                "attributes": {
                    "target": {
                        "range": "Thing",
                        "required": True,
                        "annotations": {"cs:constraint_scope": "shape"},
                    }
                }
            }
            if record_target
            else {},
            "ExpectedRecord": {},
            "OtherRecord": {},
            "Qualification": {
                "attributes": {
                    "modality": {
                        "range": "string",
                        "required": True,
                        "annotations": {"cs:constraint_scope": "shape"},
                    },
                    "polarity": {
                        "range": "boolean",
                        "required": True,
                        "annotations": {"cs:constraint_scope": "shape"},
                    },
                    "attribution": {
                        "range": "string",
                        "annotations": {
                            "cs:key_role": "provenance",
                            "cs:constraint_scope": "shape",
                        },
                    },
                    "score": {
                        "range": "decimal",
                        "minimum_value": 0,
                        "annotations": {"cs:constraint_scope": "accepted_value"},
                    },
                }
            },
        },
    }
    if conditional:
        thing["rules"] = [
            {
                "preconditions": {"slot_conditions": {"label": {"value_presence": "PRESENT"}}},
                "postconditions": {"slot_conditions": {"label": {"equals_string": "ready"}}},
            }
        ]
    if not qualification:
        del schema["classes"]["Qualification"]
    bundle = SourceBundle("model", (SourceArtifact("model", yaml.safe_dump(schema).encode()),))
    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies
    from corpus_structure.semantic.composed import composed_dependencies

    deps = (
        composed_dependencies(ResolvedDependencies())
        if conditional or composed
        else ResolvedDependencies()
    )
    profile = PreparationProfile(
        version="semantic-2" if conditional or composed else "semantic-1", constraint_scope=scope
    )
    return bundle, prepare_release(bundle, deps, profile)


_cached_fixture_model = cache(_assemble_fixture_model)


@wraps(_assemble_fixture_model)
def fixture_model(*args, **kwargs):
    if implementation_overridden():
        return _assemble_fixture_model(*args, **kwargs)
    return _cached_fixture_model(*args, **kwargs)


def seed(
    engine,
    *,
    scope: Literal["shape", "accepted_value", "occurrence", "context"] = "accepted_value",
    unique=False,
    **model_options,
):
    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.releases import persist_release

    bundle, prepared = fixture_model(scope, unique, **model_options)
    composed = model_options.get("conditional", False) or model_options.get("composed", True)
    deps = composed_dependencies(ResolvedDependencies()) if composed else ResolvedDependencies()
    profile = PreparationProfile(
        version="semantic-2" if composed else "semantic-1", constraint_scope=scope
    )
    with engine.begin() as conn:
        persist_release(conn, bundle, deps, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="p"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id=Z, release_id=prepared.release_id, project_id="p"
            )
        )
    return prepared


def batch(identity="b", *, entity="e", label="Straße", selected=True, release_id):
    f = fact_key(release_id, Z, entity, P, label, {})
    o1 = occurrence_key(release_id, Z, "source", "1" + identity)
    o2 = occurrence_key(release_id, Z, "source", "2" + identity)
    return PublicationBatch(
        release_id,
        Z,
        identity,
        entity=(EntityRow(entity),),
        membership=(MembershipRow(entity, C, "source assertion"),),
        typed_value=(ValueRow("v" + identity, "string", text_value=label),),
        fact=(FactRow(f, entity, P, "v" + identity),),
        occurrence=(
            OccurrenceRow(o1, f, "source", "1" + identity, "v" + identity),
            OccurrenceRow(o2, f, "source", "2" + identity, "v" + identity),
        ),
        support=(SupportRow(f, o1), SupportRow(f, o2)),
        selection=(SelectionRow(f),) if selected else (),
        evidence=(EvidenceRow("evidence" + identity, "urn:source", "line:1", "test", "1"),),
        membership_support=(MembershipSupportRow(entity, C, "evidence" + identity),),
    )
