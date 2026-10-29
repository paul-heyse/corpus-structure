"""Negative store tests (P0-F-4; R12; coordinator decision 24): one per enforced invariant.

Each case builds a violating row by hand from the text of its invariant, D1 §11 or a D3 rule, and
expects the store's refusal by SQLSTATE: 23514 a CHECK, 23503 a foreign key, 23505 a unique key.
No expectation is read from `_model`, the generated `MetaData` or the overlay. INV-01, INV-04,
INV-06, INV-07 and INV-09 are consolidation's and the query layer's, not the store's; INV-10's range
refusal is the repository's (`test_repo.py`), its order the CHECK below.
"""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

E, C = "core:Statement", "stat:RandomVariable"


def sql(db: Connection, statement: str, **params: Any) -> Any:
    return db.execute(text(statement), params)


def entity(db: Connection, w: SimpleNamespace, key: str, run: int | None = None, **v: Any) -> int:
    values = {
        "run": run or w.run,
        "key": key,
        "sv": w.schema_version,
        "type": C,
        "label": key,
        "scope": "global",
        "seg": None,
        "kind": None,
        "res": None,
        **v,
    }
    return sql(
        db,
        "INSERT INTO kb.entity (run_id, key, schema_version_id, type, label, scope, "
        "scope_segment_id, kind, resolved_to_id) VALUES (:run, :key, :sv, :type, :label, "
        ":scope, :seg, :kind, :res) RETURNING id",
        **values,
    ).scalar_one()


def claim(
    db: Connection, w: SimpleNamespace, key: str, subject: int, run: int | None = None, **v: Any
) -> int:
    values = {
        "run": run or w.run,
        "key": key,
        "subject": subject,
        "pred": "stat:has_distribution",
        "obj": None,
        "val": '{"t": "text", "v": "x"}',
        "sv": w.schema_version,
        "modality": "asserted",
        "attr": None,
        **v,
    }
    return sql(
        db,
        "INSERT INTO kb.claim (run_id, key, subject_id, predicate, object_entity_id, "
        "object_value, schema_version_id, modality, attribution_entity_id, status, "
        "establishment) VALUES (:run, :key, :subject, :pred, :obj, CAST(:val AS jsonb), :sv, "
        ":modality, :attr, 'candidate', 'stated') RETURNING id",
        **values,
    ).scalar_one()


def segment(db: Connection, w: SimpleNamespace, h: SimpleNamespace, **v: Any) -> int:
    ren = sql(
        db,
        "INSERT INTO kb.rendition (document_id, key, content_digest, canonical_text, "
        "parse_status) VALUES (:d, :k, :k, 'abcdef', 'ok') ON CONFLICT DO NOTHING "
        "RETURNING id",
        d=w.document,
        k=v.pop("ren", "ren:1"),
    ).scalar()
    ren = ren or sql(db, "SELECT id FROM kb.rendition LIMIT 1").scalar_one()
    values = {"ren": ren, "key": "seg:1", "start": 0, "end": 6, "status": "ok", "reason": None, **v}
    return sql(
        db,
        "INSERT INTO kb.segment (rendition_id, key, kind, ordinal, depth, start_offset, "
        "end_offset, text, parse_status, parse_reason) VALUES (:ren, :key, 'unit', 0, 0, "
        ":start, :end, 'abcdef', :status, :reason) RETURNING id",
        **values,
    ).scalar_one()


def other_run(db: Connection, w: SimpleNamespace, h: SimpleNamespace) -> int:
    return h.new_run(db, w)


Case = Callable[[Connection, SimpleNamespace, SimpleNamespace], Any]


def _inv02_both(db, w, h):  # a claim's object is exactly one of an entity or a value
    claim(db, w, "clm:b", entity(db, w, "ent:s"), obj=entity(db, w, "ent:o"))


def _inv02_neither(db, w, h):
    claim(db, w, "clm:n", entity(db, w, "ent:s"), val=None)


def _inv03_predicate(db, w, h):  # every predicate used exists in the run's schema version
    claim(db, w, "clm:p", entity(db, w, "ent:s"), pred="stat:no_such_predicate")


def _inv03_modality(db, w, h):  # an enum value outside the run's schema version
    claim(db, w, "clm:m", entity(db, w, "ent:s"), modality="hearsay")


def _inv03_statement_kind(db, w, h):
    entity(db, w, "stm:1", type=E, kind="koan")


def _inv03_other_schema_version(db, w, h):  # the claim's version is its run's
    other = sql(
        db,
        "INSERT INTO meta.schema_version (project_id, domain, label, content_hash, "
        "model_revision_id, source, created_by) VALUES (:p, 'x', 'x', :h, :m, '{}', 'x') "
        "RETURNING id",
        p=w.project,
        h="b" * 64,
        m=w.revision,
    ).scalar_one()
    sql(
        db,
        "INSERT INTO meta.schema_slot (schema_version_id, name, role) VALUES (:v, "
        "'stat:has_distribution', 'predicate')",
        v=other,
    )
    sql(
        db,
        "INSERT INTO meta.claim_modality (schema_version_id, value) VALUES (:v, 'asserted')",
        v=other,
    )
    claim(db, w, "clm:v", entity(db, w, "ent:s"), sv=other)


def _inv05_local_without_segment(db, w, h):  # a local entity has a scope segment
    entity(db, w, "ent:l", scope="local")


def _inv05_global_with_segment(db, w, h):  # a global entity has none
    entity(db, w, "ent:g", seg=segment(db, w, h))


def _inv08_claim_ref_across_runs(db, w, h):  # condition trees reference claims of the same run
    run2 = other_run(db, w, h)
    mine = claim(db, w, "clm:a", entity(db, w, "ent:s"))
    theirs = claim(db, w, "clm:z", entity(db, w, "ent:t", run=run2), run=run2)
    sql(
        db,
        "INSERT INTO kb.claim_ref (run_id, claim_id, kind, path, target_claim_id) VALUES "
        "(:r, :c, 'condition_premise', '/args/0', :t)",
        r=w.run,
        c=mine,
        t=theirs,
    )


def _claim_entity_ref_across_runs(db, w, h):  # the claim and the entity are of the row's run
    run2 = other_run(db, w, h)
    mine = claim(db, w, "clm:a", entity(db, w, "ent:s"))
    sql(
        db,
        "INSERT INTO kb.claim_entity_ref (run_id, claim_id, role, path, entity_id) VALUES "
        "(:r, :c, 'pred_arg', '/0', :e)",
        r=w.run,
        c=mine,
        e=entity(db, w, "ent:t", run=run2),
    )


def _attribution_across_runs(db, w, h):  # the attribution's entity, of the same run
    run2 = other_run(db, w, h)
    claim(db, w, "clm:a", entity(db, w, "ent:s"), attr=entity(db, w, "ent:t", run=run2))


def _statement_without_kind(db, w, h):  # a statement row always has a kind
    entity(db, w, "stm:1", type=E)


def _kind_on_a_non_statement(db, w, h):
    entity(db, w, "ent:k", kind="theorem")


def _resolution_of_a_non_reference(db, w, h):  # resolved_to only for an ExternalReference
    entity(db, w, "ent:r", res=entity(db, w, "stm:1", type=E, kind="theorem"))


def _resolution_across_runs(db, w, h):  # the statement it resolved to, of the same run
    run2 = other_run(db, w, h)
    target = entity(db, w, "stm:1", run=run2, type=E, kind="theorem")
    entity(db, w, "xrf:1", type="core:ExternalReference", res=target)


def _span_order(db, w, h):  # a span is a non-empty range
    seg = segment(db, w, h)
    sql(
        db,
        "INSERT INTO kb.span (rendition_id, start_offset, end_offset, segment_id, text) "
        "SELECT rendition_id, 3, 3, id, '' FROM kb.segment WHERE id = :s",
        s=seg,
    )


def _segment_order(db, w, h):
    segment(db, w, h, start=5, end=2)


def _segment_ok_with_reason(db, w, h):  # a reason exactly when the status is not ok
    segment(db, w, h, reason="why")


def _segment_failed_without_reason(db, w, h):
    segment(db, w, h, status="failed")


def _segment_kind_outside_the_kinds(db, w, h):
    seg = segment(db, w, h)
    sql(db, "UPDATE kb.segment SET kind = 'blob' WHERE id = :s", s=seg)


def _derive_rule_with_severity(db, w, h):  # derive rules have neither severity nor check
    sql(
        db,
        "INSERT INTO meta.schema_rule (schema_version_id, rule_id, grp, applies_to, severity, "
        "when_expr) VALUES (:v, 'r', 'derive', '{any}', 'warning', 'true')",
        v=w.schema_version,
    )


def _frame_version_one_with_a_parent(db, w, h):  # version 1 exactly when there is no parent
    unit_pass = _golden_pass(db, w, h)
    first = sql(
        db,
        "INSERT INTO eval.citation_frame (golden_pass_id, version, frame, reason) "
        "VALUES (:p, 1, '{}', 'authored') RETURNING id",
        p=unit_pass,
    ).scalar_one()
    sql(
        db,
        "INSERT INTO eval.citation_frame (golden_pass_id, version, parent_id, frame, reason) "
        "VALUES (:p, 1, :f, '{}', 'x')",
        p=unit_pass,
        f=first,
    )


def _frame_later_version_without_parent(db, w, h):
    sql(
        db,
        "INSERT INTO eval.citation_frame (golden_pass_id, version, frame, reason) VALUES "
        "(:p, 2, '{}', 'x')",
        p=_golden_pass(db, w, h),
    )


def _golden_pass(db, w, h) -> int:
    guideline = sql(
        db,
        "INSERT INTO meta.guideline_version (project_id, domain, label, "
        "content_hash, body, schema_version_id, created_by) VALUES (:p, 'd', 'g', "
        "'g', '', :v, 'x') RETURNING id",
        p=w.project,
        v=w.schema_version,
    ).scalar_one()
    gset = sql(
        db,
        "INSERT INTO eval.golden_set (project_id, label, split, schema_version_id, "
        "guideline_version_id, sampling) VALUES (:p, 's', 'dev', :v, :g, '{}') RETURNING id",
        p=w.project,
        v=w.schema_version,
        g=guideline,
    ).scalar_one()
    seg = segment(db, w, h)
    ren = sql(db, "SELECT rendition_id FROM kb.segment WHERE id = :s", s=seg).scalar_one()
    unit = sql(
        db,
        "INSERT INTO eval.golden_unit (golden_set_id, unit_key, current_locator, "
        "authored_rendition_id, status) VALUES (:s, 'u', 'u', :r, 'draft') RETURNING id",
        s=gset,
        r=ren,
    ).scalar_one()
    return sql(
        db,
        "INSERT INTO eval.golden_pass (golden_unit_id, pass, guideline_version_id, "
        "batch, session_ref, model, inputs, payload_schema_id) VALUES (:u, 'a', :g, '{}', "
        "'s', 'm', '{}', :ps) RETURNING id",
        u=unit,
        g=guideline,
        ps=w.payload["golden_batch"],
    ).scalar_one()


def _observation_ordinal_twice(db, w, h):  # one observation per (task, ordinal)
    for _ in range(2):
        sql(
            db,
            "INSERT INTO kb.observation (task_id, ordinal, kind, payload, payload_schema_id, "
            "outcome) VALUES (:t, 0, 'mention', '{}', :ps, 'produced')",
            t=w.task,
            ps=w.payload["mention"],
        )


def _claim_key_twice_in_a_run(db, w, h):  # a claim key is unique within its run
    subject = entity(db, w, "ent:s")
    claim(db, w, "clm:1", subject)
    claim(db, w, "clm:1", subject)


def _rendition_twice(db, w, h):  # one rendition per (document, content digest)
    for key in ("ren:a", "ren:b"):
        sql(
            db,
            "INSERT INTO kb.rendition (document_id, key, content_digest, canonical_text, "
            "parse_status) VALUES (:d, :k, 'same', 't', 'ok')",
            d=w.document,
            k=key,
        )


def _initial_payload_schema_with_a_parent(db, w, h):  # a first version has no parent
    sql(
        db,
        "INSERT INTO meta.payload_schema (model_revision_id, class, kind, version, parent_id, "
        "compatibility_class, json_schema_id, arrow_schema, reason, authorized_by) VALUES (:m, "
        "'sys:X', 'x', 2, :p, 'initial', 'i', '', 'r', 'a')",
        m=w.revision,
        p=w.payload["mention"],
    )


def _observation_with_an_unregistered_schema(db, w, h):
    sql(
        db,
        "INSERT INTO kb.observation (task_id, ordinal, kind, payload, payload_schema_id, "
        "outcome) VALUES (:t, 0, 'mention', '{}', 0, 'produced')",
        t=w.task,
    )


CASES: dict[str, tuple[Case, str]] = {
    "INV-02 entity and value": (_inv02_both, "23514"),
    "INV-02 neither": (_inv02_neither, "23514"),
    "INV-03 predicate": (_inv03_predicate, "23503"),
    "INV-03 modality": (_inv03_modality, "23503"),
    "INV-03 statement kind": (_inv03_statement_kind, "23503"),
    "INV-03 another schema version": (_inv03_other_schema_version, "23503"),
    "INV-05 local without segment": (_inv05_local_without_segment, "23514"),
    "INV-05 global with segment": (_inv05_global_with_segment, "23514"),
    "INV-08 claim_ref across runs": (_inv08_claim_ref_across_runs, "23503"),
    "claim_entity_ref across runs": (_claim_entity_ref_across_runs, "23503"),
    "attribution across runs": (_attribution_across_runs, "23503"),
    "statement without kind": (_statement_without_kind, "23514"),
    "kind on a non-statement": (_kind_on_a_non_statement, "23514"),
    "resolution of a non-reference": (_resolution_of_a_non_reference, "23514"),
    "resolution across runs": (_resolution_across_runs, "23503"),
    "INV-10 empty span": (_span_order, "23514"),
    "segment order": (_segment_order, "23514"),
    "segment ok with a reason": (_segment_ok_with_reason, "23514"),
    "segment failed without a reason": (_segment_failed_without_reason, "23514"),
    "segment kind": (_segment_kind_outside_the_kinds, "23514"),
    "derive rule with severity": (_derive_rule_with_severity, "23514"),
    "frame version 1 with a parent": (_frame_version_one_with_a_parent, "23514"),
    "frame version 2 without a parent": (_frame_later_version_without_parent, "23514"),
    "observation ordinal twice": (_observation_ordinal_twice, "23505"),
    "claim key twice in a run": (_claim_key_twice_in_a_run, "23505"),
    "rendition twice": (_rendition_twice, "23505"),
    "initial payload schema with a parent": (_initial_payload_schema_with_a_parent, "23514"),
    "unregistered payload schema": (_observation_with_an_unregistered_schema, "23503"),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_store_refuses_the_violation(
    db: Connection, world: SimpleNamespace, helpers: SimpleNamespace, name: str
) -> None:
    case, sqlstate = CASES[name]
    with pytest.raises(DBAPIError) as err, db.begin_nested():
        case(db, world, helpers)
    assert getattr(err.value.orig, "sqlstate", None) == sqlstate, err.value


def test_valid_rows_are_accepted(db: Connection, world: SimpleNamespace, helpers: Any) -> None:
    """The cases' builders write valid rows when nothing is violated (the refusals are real)."""
    seg = segment(db, world, helpers)
    subject = entity(db, world, "ent:s")
    stm = entity(db, world, "stm:1", type=E, kind="theorem")
    entity(db, world, "ent:l", scope="local", seg=seg)
    xrf = entity(db, world, "xrf:1", type="core:ExternalReference", res=stm)
    first = claim(db, world, "clm:1", subject, attr=xrf)
    second = claim(db, world, "clm:2", subject, obj=stm, val=None, modality="supposed")
    sql(
        db,
        "INSERT INTO kb.claim_ref (run_id, claim_id, kind, path, target_claim_id) VALUES "
        "(:r, :c, 'condition_premise', '/args/0', :t)",
        r=world.run,
        c=first,
        t=second,
    )
    segment(db, world, helpers, key="seg:2", status="partial", reason="unclosed $")
