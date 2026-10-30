"""Finite qualified relational closure and protected, revision-fenced publication.

The work relation contains semantic conclusions, never proof paths. Only direct proofs are
materialized after the common fixed point of all admitted rule groups has been reached.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from sqlalchemy import Column, MetaData, Table, Text, and_, func, literal, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import DBAPIError

from .identity import canonical_bytes
from .metadata import table
from .publication import (
    DerivationPremiseRow,
    DerivationRow,
    FactRow,
    PublicationBatch,
    PublicationReceipt,
    SelectionRow,
    ValueRow,
    _publish,
)
from .query import SnapshotBinding


@dataclass(frozen=True)
class InferenceResult:
    binding: SnapshotBinding
    batch: PublicationBatch

    def __post_init__(self) -> None:
        if (self.binding.release_id, self.binding.realization_id) != (
            self.batch.release_id,
            self.batch.realization_id,
        ):
            raise ValueError("inference output does not match source binding")


def _rules(conn: Connection, release_id: str) -> tuple[dict[str, Any], ...]:
    rows = table("sem.registry_row")
    return tuple(
        json.loads(bytes(body))
        for body in conn.execute(
            select(rows.c.body).where(
                rows.c.release_id == release_id, rows.c.kind == "inference_rule"
            )
        ).scalars()
    )


def derive(connection: Connection, binding: SnapshotBinding) -> InferenceResult:
    """Compute under the caller's REPEATABLE READ/SERIALIZABLE snapshot; never commit.

    No admitted state is mutated. The private temporary table is dropped on success/error.
    Materialized output can outlive this connection; publication rechecks its source revision.
    """
    from .contracts import require_database_operation
    require_database_operation(connection, binding.release_id, "derive")
    if connection.get_isolation_level() not in {"REPEATABLE READ", "SERIALIZABLE"}:
        raise ValueError("inference requires a repeatable snapshot")
    realization = table("data.realization")
    revision = connection.execute(
        select(realization.c.data_revision).where(
            realization.c.release_id == binding.release_id,
            realization.c.realization_id == binding.realization_id,
        )
    ).scalar_one()
    if revision != binding.data_revision:
        raise ValueError("inference source revision changed")
    work = Table(
        "semantic_inference_work",
        MetaData(),
        Column("subject", Text, primary_key=True),
        Column("predicate", Text, primary_key=True),
        Column("object", Text, primary_key=True),
        Column("context", Text),
        Column("qualification", Text),
        Column("context_key", Text, primary_key=True),
        schema="pg_temp",
        prefixes=["TEMPORARY"],
    )
    connection.execute(
        text("SELECT data.begin_inference_workspace(:r,:z,:revision,:snapshot)"),
        {
            "r": binding.release_id,
            "z": binding.realization_id,
            "revision": binding.data_revision,
            "snapshot": binding.capture_id,
        },
    )
    database_failed = False
    try:
        r, z = binding.release_id, binding.realization_id
        connection.execute(
            text("""INSERT INTO pg_temp.semantic_inference_work
          (subject,predicate,object,context,qualification,context_key)
          SELECT f.subject_id,f.property_id,v.entity_id,
          data.canonical_json(data.value_meaning(:r,:z,f.qualification_value_id,'{}',true)),
          min(f.qualification_value_id),encode(sha256(convert_to(
          data.canonical_json(data.value_meaning(:r,:z,f.qualification_value_id,'{}',true)),
          'UTF8')),'hex')
          FROM data.inference_seeds(:r,:z) seed JOIN data.fact f ON f.fact_id=seed.fact_id
           AND f.release_id=:r AND f.realization_id=:z
          JOIN data.typed_value v ON v.release_id=:r AND v.realization_id=:z
           AND v.value_id=f.object_value_id AND v.kind='entity'
          GROUP BY f.subject_id,f.property_id,v.entity_id,
           data.canonical_json(data.value_meaning(:r,:z,f.qualification_value_id,'{}',true))"""),
            {"r": r, "z": z},
        )
        # Choose one stable stored representative for each canonical context. Different source
        # qualification object IDs must not make replay bytes depend on SQL insertion order.
        connection.execute(
            text("""UPDATE pg_temp.semantic_inference_work w SET qualification=c.q
          FROM (SELECT context,min(qualification) q FROM pg_temp.semantic_inference_work
                GROUP BY context) c WHERE w.context=c.context""")
        )
        rules = _rules(connection, r)

        def conclusions(rule: dict[str, Any]):
            a, b = work.alias("a"), work.alias("b")
            kind, p = rule["kind"], rule["predicate"]
            target = rule.get("target") or p
            key = func.encode(func.sha256(func.convert_to(a.c.context, "UTF8")), "hex")
            if kind == "subproperty":
                return select(
                    a.c.subject, literal(target), a.c.object, a.c.context, a.c.qualification, key
                ).where(a.c.predicate == p)
            if kind in {"inverse", "symmetric"}:
                return select(
                    a.c.object, literal(target), a.c.subject, a.c.context, a.c.qualification, key
                ).where(a.c.predicate == p)
            if kind == "transitive":
                return (
                    select(a.c.subject, literal(p), b.c.object, a.c.context, a.c.qualification, key)
                    .select_from(
                        a.join(b, and_(a.c.object == b.c.subject, a.c.context == b.c.context))
                    )
                    .where(a.c.predicate == p, b.c.predicate == p)
                )
            raise ValueError(f"unsupported inference rule {kind}")

        while True:
            added = 0
            for rule in rules:
                stmt = (
                    pg_insert(work)
                    .from_select(
                        [
                            "subject",
                            "predicate",
                            "object",
                            "context",
                            "qualification",
                            "context_key",
                        ],
                        conclusions(rule).distinct(),
                    )
                    .on_conflict_do_nothing()
                    .returning(work.c.subject)
                )
                added += len(connection.execute(stmt).all())
            if not added:
                break
        rows = connection.execute(select(work)).mappings().all()
        existing = set(
            connection.execute(
                select(table("data.fact").c.fact_id).where(
                    table("data.fact").c.release_id == r, table("data.fact").c.realization_id == z
                )
            ).scalars()
        )
        facts: dict[tuple[str, str, str, str], str] = {}
        values: dict[str, ValueRow] = {}
        new_facts = []
        for row in rows:
            key = (row["subject"], row["predicate"], row["object"], row["context"])
            identity = (
                "fact:"
                + sha256(
                    canonical_bytes([r, z, key[0], key[1], ["string", key[2]], json.loads(key[3])])
                ).hexdigest()
            )
            facts[key] = identity
            if identity not in existing:
                vid = "inference-value:" + sha256(key[2].encode()).hexdigest()
                values[vid] = ValueRow(vid, "entity", entity_id=key[2])
                new_facts.append(FactRow(identity, key[0], key[1], vid, row["qualification"]))
        proofs: dict[str, DerivationRow] = {}
        premises = []
        # Each rule's finite direct witnesses, not recursively expanded proof paths.
        for rule in rules:
            a, b = work.alias("pa"), work.alias("pb")
            query = select(a)
            if rule["kind"] == "transitive":
                query = (
                    select(a, b.c.object.label("last"), b.c.predicate.label("bp"))
                    .select_from(
                        a.join(b, and_(a.c.object == b.c.subject, a.c.context == b.c.context))
                    )
                    .where(b.c.predicate == rule["predicate"])
                )
            for row in connection.execute(
                query.where(a.c.predicate == rule["predicate"])
            ).mappings():
                first = (row["subject"], row["predicate"], row["object"], row["context"])
                kind, target = rule["kind"], rule.get("target") or rule["predicate"]
                if kind == "transitive":
                    head = (first[0], target, row["last"], first[3])
                    args = (facts[first], facts[(first[2], row["bp"], row["last"], first[3])])
                else:
                    head = (
                        (first[2], target, first[0], first[3])
                        if kind in {"inverse", "symmetric"}
                        else (first[0], target, first[2], first[3])
                    )
                    args = (facts[first],)
                did = (
                    "derivation:"
                    + sha256(
                        canonical_bytes([rule["rule_id"], rule["rule_version"], facts[head], args])
                    ).hexdigest()
                )
                if did not in proofs:
                    proofs[did] = DerivationRow(
                        did, facts[head], rule["rule_id"], rule["rule_version"]
                    )
                    premises.extend(DerivationPremiseRow(did, i, p) for i, p in enumerate(args))
        batch_id = (
            "inference:"
            + sha256(
                canonical_bytes(
                    [r, z, binding.data_revision, sorted(facts.values()), sorted(proofs)]
                )
            ).hexdigest()
        )
        batch = PublicationBatch(
            r,
            z,
            batch_id,
            typed_value=tuple(values[k] for k in sorted(values)),
            fact=tuple(sorted(new_facts, key=lambda f: f.fact_id)),
            selection=tuple(
                SelectionRow(f.fact_id) for f in sorted(new_facts, key=lambda f: f.fact_id)
            ),
            derivation=tuple(proofs[k] for k in sorted(proofs)),
            derivation_premise=tuple(sorted(premises, key=lambda p: (p.derivation_id, p.position))),
        )
        return InferenceResult(binding, batch)
    except DBAPIError:
        # PostgreSQL has aborted this transaction. Its rollback removes the private table;
        # another DROP here would hide the original database error with an aborted-tx error.
        database_failed = True
        raise
    finally:
        if not database_failed:
            connection.execute(
                text("SELECT data.end_inference_workspace(:r,:z,:revision,:snapshot)"),
                {
                    "r": binding.release_id,
                    "z": binding.realization_id,
                    "revision": binding.data_revision,
                    "snapshot": binding.capture_id,
                },
            )


def publish_inference(
    engine: Engine, result: InferenceResult, *, attempts: int = 3
) -> PublicationReceipt:
    """Use the shared retry owner and native exact-replay/source revision fence."""

    from .arrow_publication import SnapshotDerivedPublication, publish_arrow_on_connection

    publication = SnapshotDerivedPublication.from_rows(
        result.batch,
        source=result.binding,
        operation_id="publish_inference",
        projection_id="accepted",
    )

    def publish(conn: Connection, batch: PublicationBatch) -> PublicationReceipt:
        return publish_arrow_on_connection(conn, publication)

    return _publish(engine, result.batch, publish, attempts=attempts)
