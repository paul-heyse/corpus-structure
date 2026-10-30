"""Restricted publication independently enforces exclusion custody and completeness."""

from dataclasses import replace
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.domain_operations import _cut_input
from corpus_structure.semantic.publication import publish_on_connection

from .test_identity_exclusions import exclusion_result


@pytest.mark.parametrize(
    "attack",
    [
        "omit",
        "collapse",
        "raw_reference",
        "reason",
        "missing_citation",
        "extra_citation",
        "identity",
        "locator",
        "attribute_source",
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
    )
    inputs = _cut_input(semantic_writer_engine, cut, "excluded-result")
    batch = inputs.batch
    row = batch.identity_exclusion[0]
    expected = {
        "omit": "effective cut identity exclusion omitted",
        "collapse": "check constraint",
        "raw_reference": "source declaration differs",
        "reason": "source declaration differs",
        "missing_citation": "evidence differs from source citations",
        "extra_citation": "evidence differs from source citations",
        "identity": "identity differs",
        "locator": "evidence span is not a located citation",
        "attribute_source": "occurrence citation is outside bound source claim",
        "policy_version": "operation version differs from release model",
    }[attack]
    if attack == "attribute_source":
        from dataclasses import fields

        from corpus_structure.semantic.identity import occurrence_key

        old = next(o for o in batch.occurrence if o.item.startswith("entities/p_/attributes/"))
        item = old.item.replace("entities/p_/", "entities/px/")
        new_id = occurrence_key(batch.release_id, batch.realization_id, old.source, item)
        updates: dict[str, Any] = {}
        from corpus_structure.semantic.publication import STAGE_TYPES

        for name in STAGE_TYPES:
            rows = []
            for current in getattr(batch, name):
                changes = {
                    f.name: new_id
                    for f in fields(current)
                    if f.name == "occurrence_id" and getattr(current, f.name) == old.occurrence_id
                }
                if name == "occurrence" and current.occurrence_id == old.occurrence_id:
                    changes["item"] = item
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
    # Resolve original source spans exactly as the production publisher does, before staging.
    from sqlalchemy.dialects.postgresql import insert

    from corpus_structure.semantic.metadata import table

    with semantic_writer_engine.begin() as conn:
        sources = []
        for eid, (oid, rid, start, end) in inputs.source_links.items():
            span = table("kb.span")
            conn.execute(
                insert(span)
                .values(rendition_id=rid, start_offset=start, end_offset=end)
                .on_conflict_do_nothing()
            )
            sid = conn.scalar(
                span.select()
                .with_only_columns(span.c.id)
                .where(
                    span.c.rendition_id == rid,
                    span.c.start_offset == start,
                    span.c.end_offset == end,
                )
            )
            from corpus_structure.semantic.publication import EvidenceSourceRow

            sources.append(EvidenceSourceRow(eid, oid, rid, sid))
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
    batch = replace(batch, evidence_source=tuple(sources))
    with (
        pytest.raises(DBAPIError, match=expected),
        semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        conn.execute(
            text("SELECT data.begin_evaluation(:cut,:z)"), {"cut": cut, "z": "excluded-result"}
        )
        publish_on_connection(conn, batch)
        conn.execute(
            text("SELECT data.finish_evaluation(:cut,:z,:b)"),
            {"cut": cut, "z": "excluded-result", "b": batch.batch_id},
        )
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


def test_literal_wildcard_characters_in_source_ids_remain_valid(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    _prepared, _run, _cut, result = exclusion_result(
        semantic_db_engine, semantic_writer_engine, tmp_path, local_ids=("p_", "q%")
    )
    assert result is not None
    assert result.realization_id == "excluded-result"
