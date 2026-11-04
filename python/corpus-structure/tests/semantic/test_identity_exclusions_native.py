"""Restricted publication independently enforces exclusion custody and completeness."""

from dataclasses import replace
from typing import Any

import pytest
from pdf_acceptance_support import native_evidence_sources
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.analytics import compile_projection
from corpus_structure.semantic.arrow_publication import (
    SnapshotDerivedPublication,
    publish_arrow_on_connection,
)
from corpus_structure.semantic.domain_operations import _cut_input

from .test_identity_exclusions import exclusion_result


@pytest.mark.parametrize(
    "attack",
    [
        "omit",
        "collapse",
        "raw_reference",
        "reason",
        "missing_citation",
        "missing_primary",
        "extra_citation",
        "identity",
        "locator",
        "attribute_source",
        "attribute_wrong_owner",
        "attribute_index_text",
        "attribute_index_negative",
        "attribute_index_huge",
        "attribute_index_padding",
        "attribute_index_missing",
        "attribute_index_suffix",
        "policy_version",
    ],
)
def test_native_exclusion_publication_refuses_tampering(
    semantic_db_engine, semantic_writer_engine, tmp_path, attack
):
    _prepared, _run, cut, _ = exclusion_result(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path,
        finalize=False,
        citations=2,
        local_ids=("p_", "q"),
        attribute_assertions=attack.startswith("attribute_"),
    )
    inputs = _cut_input(semantic_writer_engine, cut, "excluded-result")
    batch = inputs.batch
    row = batch.identity_exclusion[0]
    expected = (
        "attribute occurrence differs from its own source assertion"
        if attack.startswith("attribute_")
        else {
            "omit": "effective cut identity exclusion omitted",
            "collapse": "check constraint",
            "raw_reference": "source declaration differs",
            "reason": "source declaration differs",
            "missing_citation": "evidence differs from source citations",
            "missing_primary": "identity exclusion lacks located primary custody",
            "extra_citation": "evidence differs from source citations",
            "identity": "identity differs",
            "locator": "native evidence differs from a located supplied citation",
            "policy_version": "operation version differs from release model",
        }[attack]
    )
    if attack.startswith("attribute_"):
        from dataclasses import fields

        from corpus_structure.semantic.identity import occurrence_key

        old = next(o for o in batch.occurrence if o.item.startswith("entities/p_/attributes/"))
        item = {
            "attribute_source": "entities/px/attributes/0",
            "attribute_wrong_owner": "entities/q/attributes/0",
            "attribute_index_text": "entities/p_/attributes/not-an-index",
            "attribute_index_negative": "entities/p_/attributes/-1",
            "attribute_index_huge": "entities/p_/attributes/999999999999999999999999999999",
            "attribute_index_padding": "entities/p_/attributes/00",
            "attribute_index_missing": "entities/p_/attributes/",
            "attribute_index_suffix": "entities/p_/attributes/0/extra",
        }[attack]
        new_id = occurrence_key(batch.release_id, batch.realization_id, old.source, item)
        # The other owner already has an attribute occurrence at this address. Swap
        # both addresses and all child references to preserve distinct row identities
        # while retaining each fact/evidence payload under the wrong source owner.
        occurrence_ids = {old.occurrence_id: new_id}
        items = {old.occurrence_id: item}
        if attack == "attribute_wrong_owner":
            other = next(o for o in batch.occurrence if o.occurrence_id == new_id)
            occurrence_ids[other.occurrence_id] = old.occurrence_id
            items[other.occurrence_id] = old.item
        updates: dict[str, Any] = {}
        from corpus_structure.semantic.publication import STAGE_TYPES

        for name in STAGE_TYPES:
            rows = []
            for current in getattr(batch, name):
                changes = {
                    f.name: occurrence_ids[getattr(current, f.name)]
                    for f in fields(current)
                    if f.name == "occurrence_id" and getattr(current, f.name) in occurrence_ids
                }
                if name == "occurrence" and current.occurrence_id in items:
                    changes["item"] = items[current.occurrence_id]
                rows.append(replace(current, **changes) if changes else current)
            updates[name] = tuple(rows)
        batch = replace(batch, **updates)
    elif attack == "omit":
        batch = replace(batch, identity_exclusion=(), identity_exclusion_evidence=())
    elif attack == "collapse":
        batch = replace(
            batch, identity_exclusion=(replace(row, right_entity_id=row.left_entity_id),)
        )
    elif attack == "policy_version":
        batch = replace(
            batch, identity_exclusion=(replace(row, operation_version="forged-policy"),)
        )
    elif attack == "raw_reference":
        batch = replace(batch, identity_exclusion=(replace(row, left_ref="invented"),))
    elif attack == "reason":
        batch = replace(batch, identity_exclusion=(replace(row, reason="forged"),))
    elif attack == "locator":
        import json

        batch = replace(
            batch,
            evidence=tuple(
                replace(e, locator=json.dumps({**json.loads(e.locator), "locator": "invented"}))
                for e in batch.evidence
            ),
        )
    elif attack == "identity":
        batch = replace(
            batch,
            identity_exclusion=(replace(row, exclusion_id="invented"),),
            identity_exclusion_evidence=tuple(
                replace(e, exclusion_id="invented") for e in batch.identity_exclusion_evidence
            ),
        )
    elif attack == "missing_citation":
        import json

        primary = {
            e.evidence_id for e in batch.evidence if json.loads(e.locator)["role"] == "primary"
        }
        batch = replace(
            batch,
            identity_exclusion_evidence=tuple(
                e for e in batch.identity_exclusion_evidence if e.evidence_id in primary
            ),
        )
    elif attack == "missing_primary":
        import json

        supporting = {
            e.evidence_id for e in batch.evidence if json.loads(e.locator)["role"] == "supporting"
        }
        assert supporting
        batch = replace(
            batch,
            identity_exclusion_evidence=tuple(
                e for e in batch.identity_exclusion_evidence if e.evidence_id in supporting
            ),
        )
    elif attack == "extra_citation":
        e = batch.evidence[0]
        batch = replace(
            batch,
            evidence=(*batch.evidence, replace(e, evidence_id="extra")),
            identity_exclusion_evidence=(
                *batch.identity_exclusion_evidence,
                replace(batch.identity_exclusion_evidence[0], evidence_id="extra"),
            ),
        )
    # Stage exact native SourceView custody through the current typed transport.
    sources = list(native_evidence_sources(inputs))
    if attack == "extra_citation":
        sources.append(
            replace(
                next(
                    source
                    for source in sources
                    if source.evidence_id == batch.evidence[0].evidence_id
                ),
                evidence_id="extra",
            )
        )
    batch = replace(batch, evidence_source=tuple(sources)).bind_preparation(inputs.prepared)
    compiled = compile_projection(inputs.prepared, inputs.source_binding, kind="candidate")
    publication = SnapshotDerivedPublication.from_rows(
        batch,
        source=inputs.source_binding,
        operation_id="evaluate",
        projection_id=compiled.projection_id,
        contract_id="candidate",
        cut_id=cut,
        profile_digest=compiled.profile.digest,
    )
    with (
        pytest.raises(DBAPIError, match=expected) as refusal,
        semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        conn.execute(
            text("SELECT data.begin_evaluation(:cut,:z)"), {"cut": cut, "z": "excluded-result"}
        )
        publish_arrow_on_connection(conn, publication)
        conn.execute(
            text("SELECT data.finish_evaluation(:cut,:z,:b)"),
            {"cut": cut, "z": "excluded-result", "b": batch.batch_id},
        )
    if attack.startswith("attribute_"):
        assert getattr(refusal.value.orig, "sqlstate", None) == "23514"
    with semantic_writer_engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM data.realization WHERE realization_id='excluded-result'")
            )
            == 0
        )


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO data.identity_exclusion_evidence VALUES('z','r','x','e')",
        "UPDATE data.identity_exclusion SET reason='changed'",
        "DELETE FROM data.identity_exclusion",
    ],
)
def test_restricted_writer_cannot_mutate_exclusions(semantic_writer_engine, statement):
    with (
        pytest.raises(DBAPIError, match="permission denied"),
        semantic_writer_engine.begin() as conn,
    ):
        conn.execute(text(statement))


@pytest.mark.parametrize("local_ids", [("p_", "q%"), ("p/attributes/0", "q")])
def test_literal_attribute_source_ids_remain_valid(
    semantic_db_engine, semantic_writer_engine, tmp_path, local_ids
):
    _prepared, _run, _cut, result = exclusion_result(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path,
        local_ids=local_ids,
        attribute_assertions=True,
    )
    assert result is not None
    assert result.realization_id == "excluded-result"
