"""Shared controlled inputs and builders for inference support."""

from __future__ import annotations

from typing import Any

import yaml
from sqlalchemy import insert

from corpus_structure.semantic.identity import fact_key, occurrence_key
from corpus_structure.semantic.inference import derive
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import (
    EntityRow,
    EvidenceRow,
    FactRow,
    MembershipRow,
    MembershipSupportRow,
    OccurrenceEstablishmentRow,
    OccurrenceEvidenceRow,
    OccurrenceRow,
    PublicationBatch,
    RoleRow,
    SelectionRow,
    SupportRow,
    ValueRow,
    publish_batch,
)
from corpus_structure.semantic.query import SnapshotBinding

R, Z, C, P, Q = (
    "release:infer",
    "realization:infer",
    "https://example/Thing",
    "https://example/p",
    "https://example/q",
)


def setup(
    admin,
    writer,
    edges,
    *,
    rules=("transitive", "inverse"),
    contexts=None,
    positive=True,
    prepared=None,
    bundle=None,
    evidence=True,
    predicate=P,
    modality="asserted",
    establishment="stated",
    selected=True,
    subproperty=False,
):
    if prepared is None:
        from corpus_structure.semantic import (
            PreparationProfile,
            ResolvedDependencies,
            SourceArtifact,
            SourceBundle,
            prepare_release,
        )
        from corpus_structure.semantic.composed import composed_dependencies

        schema: dict[str, Any] = {
            "id": "https://example/inference-fixture",
            "name": "inference",
            "prefixes": {"ex": "https://example/"},
            "default_prefix": "ex",
            "types": {"string": {"base": "str"}, "boolean": {"base": "bool"}},
            "classes": {"Thing": {"slots": ["p", "q"]}},
            "slots": {
                "p": {"range": "Thing", "multivalued": True},
                "q": {"range": "Thing", "multivalued": True},
            },
        }
        if subproperty:
            schema["classes"]["Thing"]["slots"].append("child")
            schema["slots"]["child"] = {
                "range": "Thing",
                "multivalued": True,
                "is_a": "p",
                "transitive": False,
                "inverse": "q",
            }
        for kind in rules:
            if kind == "inverse":
                schema["slots"]["p"]["inverse"] = "q"
            else:
                schema["slots"]["p"][kind] = True
        bundle = SourceBundle("model", (SourceArtifact("model", yaml.safe_dump(schema).encode()),))
        prepared = prepare_release(
            bundle,
            composed_dependencies(ResolvedDependencies()),
            PreparationProfile(version="semantic-2"),
        )
        typed_qualification = False
    else:
        typed_qualification = True
    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.releases import persist_release

    r = prepared.release_id
    with admin.begin() as conn:
        assert bundle is not None
        persist_release(
            conn,
            bundle,
            composed_dependencies(ResolvedDependencies()),
            PreparationProfile(version="semantic-2"),
            prepared,
        )
        conn.execute(insert(table("data.project")).values(project_id="p"))
        conn.execute(
            insert(table("data.realization")).values(realization_id=Z, project_id="p", release_id=r)
        )
    entities = sorted({e for edge in edges for e in edge})
    contexts = contexts or ["same"] * len(edges)
    values = [ValueRow("v:" + e, "entity", entity_id=e) for e in entities]
    values += [
        ValueRow("modality", "string", text_value=modality),
        ValueRow("polarity", "boolean", boolean_value=positive),
    ]
    roles = []
    facts = []
    occurrences = []
    supports = []
    for i, ((s, o), ctx) in enumerate(zip(edges, contexts, strict=True)):
        q = "qual:" + str(i)
        values.extend(
            (
                ValueRow(
                    q,
                    "record" if typed_qualification else "mapping",
                    datatype="https://example/Qualification" if typed_qualification else None,
                ),
                ValueRow("scope:" + str(i), "string", text_value=ctx),
            )
        )
        roles.extend(
            (
                RoleRow(q, "modality", 0, "modality"),
                RoleRow(q, "polarity", 0, "polarity"),
                RoleRow(q, "scope", 0, "scope:" + str(i)),
            )
        )
        fid = fact_key(
            r, Z, s, predicate, o, {"modality": modality, "polarity": positive, "scope": ctx}
        )
        facts.append(FactRow(fid, s, predicate, "v:" + o, q))
        oid = occurrence_key(r, Z, "source", str(i))
        occurrences.append(OccurrenceRow(oid, fid, "source", str(i), "v:" + o, q))
        supports.append(SupportRow(fid, oid))
    batch = PublicationBatch(
        r,
        Z,
        "sources",
        entity=tuple(EntityRow(e) for e in entities),
        membership=tuple(MembershipRow(e, C, "stated") for e in entities),
        membership_support=tuple(MembershipSupportRow(e, C, "ev") for e in entities),
        occurrence_evidence=tuple(OccurrenceEvidenceRow(o.occurrence_id, "ev") for o in occurrences)
        if evidence
        else (),
        evidence=(EvidenceRow("ev", "source", "page#unit", "test", "1"),),
        typed_value=tuple(values),
        value_role=tuple(roles),
        fact=tuple(facts),
        occurrence=tuple(occurrences),
        occurrence_establishment=tuple(
            OccurrenceEstablishmentRow(o.occurrence_id, establishment) for o in occurrences
        ),
        support=tuple(supports),
        selection=tuple(SelectionRow(f.fact_id, selected) for f in facts),
    )
    receipt = publish_batch(writer, batch)
    return SnapshotBinding(r, Z, receipt.data_revision, "test"), batch


def compute(writer, binding):
    with (
        writer.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
        conn.begin(),
    ):
        return derive(conn, binding)


def _inference_publication_state(conn, release_id, realization_id):
    """Independent persisted effects, receipts and revision of inference publication."""
    from sqlalchemy import select

    state = {}
    for name in (
        "data.realization",
        "data.batch",
        "data.fact",
        "data.typed_value",
        "data.value_role",
        "data.selection",
        "data.support",
        "data.derivation",
        "data.derivation_premise",
    ):
        relation = table(name)
        state[name] = tuple(
            dict(row)
            for row in conn.execute(
                select(relation)
                .where(
                    relation.c.release_id == release_id,
                    relation.c.realization_id == realization_id,
                )
                .order_by(*relation.primary_key.columns)
            ).mappings()
        )
    return state
