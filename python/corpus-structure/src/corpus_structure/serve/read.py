"""Composable, batched Core reads on the journey's single semantic ReadSession."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from sqlalchemy import and_, exists, func, or_, select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import same_scope_clause, scope_clause
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.serve.results import ClaimAnswer, EntityAnswer

T = {
    name: table("data." + name)
    for name in (
        "entity",
        "membership",
        "fact",
        "selection",
        "typed_value",
        "value_role",
        "occurrence",
        "occurrence_context",
        "derivation",
        "derivation_premise",
        "coverage",
        "evidence",
        "support",
        "occurrence_evidence",
    )
}


class Reader:
    def __init__(self, ctx: Any):
        self.ctx, self.session, self.conn = ctx, ctx.session, ctx.conn
        self.binding, self.prepared = self.session.binding, self.session.prepared

    def scope(self, relation):
        return scope_clause(self.binding, relation)

    def iri(self, name):
        return self.session.resolve_name(name)

    def referenced_entities(self, root):
        return self.session.referenced_entities(root)

    def qualification_matches(self, name, value):
        return self.session.qualification_matches(name, value)

    def fact_statement(self, **filters):
        return self.session.fact_statement(projection=self.ctx.projection, **filters)

    # Query plugins compose these Core selections; hydration stays a single batched boundary.
    claim_statement = fact_statement

    def claims(
        self, after=None, statement=None, with_premises=False, **filters
    ) -> Iterator[ClaimAnswer]:
        f = T["fact"]
        stmt = self.fact_statement(**filters) if statement is None else statement
        if after is not None and self.ctx.projection != "occurrence":
            if not isinstance(after, str):
                raise SemanticRefusal("invalid semantic fact cursor")
            stmt = stmt.where(f.c.fact_id.collate("C") > after)
        if self.ctx.projection == "occurrence":
            o = T["occurrence"]
            stmt = stmt.with_only_columns(
                f.c.fact_id,
                f.c.subject_id,
                f.c.property_id,
                o.c.report_object_value_id.label("object_value_id"),
                o.c.report_qualification_value_id.label("qualification_value_id"),
                o.c.occurrence_id,
                o.c.source,
                o.c.item,
            ).join(o, and_(same_scope_clause(f, o), f.c.fact_id == o.c.fact_id))
            if after is not None:
                # Occurrence order is the public identity; replace the fact cursor criterion.
                stmt = stmt.where(o.c.occurrence_id.collate("C") > after)
            order = o.c.occurrence_id
        else:
            order = f.c.fact_id
        # Keyset-sized batches avoid an open server cursor during graph hydration.
        cursor = None
        while True:
            page = stmt if cursor is None else stmt.where(order.collate("C") > cursor)
            rows = (
                self.conn.execute(page.order_by(order.collate("C")).limit(self.ctx.row_batch))
                .mappings()
                .all()
            )
            if not rows:
                break
            facts, nodes = self.session.hydrate_rows(rows)
            for fact in facts:
                # Preserve the exact reachable value graph, including scale/lexical forms.
                reachable = {fact.object_value_id, fact.qualification_value_id}
                changed = True
                while changed:
                    prior = len(reachable)
                    reachable.update(
                        role.child_value_id
                        for node in nodes
                        if node.value_id in reachable
                        for role in node.roles
                    )
                    changed = len(reachable) != prior
                yield ClaimAnswer(
                    fact=fact, values=tuple(n for n in nodes if n.value_id in reachable)
                )
            cursor = rows[-1][order.name]
            if len(rows) < self.ctx.row_batch:
                break

    def entity_ids(self, key=None, label=None, class_name=None):
        e, f, v = T["entity"], T["fact"], T["typed_value"]
        stmt = select(e.c.entity_id).where(self.scope(e))
        if key is not None:
            stmt = stmt.where(e.c.entity_id == key)
        if class_name is not None:
            m, h = T["membership"], table("sem.class_hierarchy")
            iri = self.iri(class_name)
            stmt = stmt.where(
                exists(
                    select(1).where(
                        self.scope(m),
                        m.c.entity_id == e.c.entity_id,
                        or_(
                            m.c.class_id == iri,
                            exists(
                                select(1).where(
                                    h.c.release_id == self.binding.release_id,
                                    h.c.class_id == m.c.class_id,
                                    h.c.ancestor_id == iri,
                                )
                            ),
                        ),
                    )
                )
            )
        if label is not None:
            # Labels are semantic property values, never old compiled key normalization.
            iris = {
                p.iri
                for d in self.prepared.definitions
                for p in d.properties
                if p.name in {"label", "aliases", "name", "canonical_name"}
            }
            folded_classes = {
                json.loads(row.body)["iri"]
                for row in self.prepared.registry_rows
                if row.kind == "operation_class"
                and json.loads(row.body).get("cs:case") == "casefold"
            }
            membership = T["membership"]
            folded = exists(
                select(1)
                .where(
                    self.scope(membership),
                    membership.c.entity_id == e.c.entity_id,
                    membership.c.class_id.in_(folded_classes),
                )
                .correlate(e)
            )
            matches = or_(
                v.c.text_value == label,
                and_(
                    folded,
                    func.casefold(v.c.text_value.collate("pg_unicode_fast")) == label.casefold(),
                ),
            )
            stmt = stmt.where(
                exists(
                    select(1)
                    .select_from(
                        f.join(
                            v, and_(same_scope_clause(f, v), f.c.object_value_id == v.c.value_id)
                        )
                    )
                    .where(
                        self.scope(f),
                        f.c.subject_id == e.c.entity_id,
                        f.c.property_id.in_(iris),
                        matches,
                    )
                )
            )
        return stmt

    def resolve(self, value, class_name=None):
        direct = (
            self.conn.execute(self.entity_ids(key=value, class_name=class_name)).scalars().all()
        )
        return (
            direct
            or self.conn.execute(self.entity_ids(label=value, class_name=class_name))
            .scalars()
            .all()
        )

    def entity_rows(self, key=None, label=None, after=None):
        e = T["entity"]
        stmt = self.entity_ids(key, label)
        if after is not None:
            if not isinstance(after, str):
                raise SemanticRefusal("invalid semantic entity cursor")
            stmt = stmt.where(e.c.entity_id.collate("C") > after)
        for ids in (
            self.conn.execute(stmt.order_by(e.c.entity_id.collate("C")))
            .scalars()
            .partitions(self.ctx.row_batch)
        ):
            entities = self.session.load_entities(set(ids))
            facts = list(self.claims(subject_id=list(ids)))
            for id_ in ids:
                properties = tuple(row.fact for row in facts if row.fact.subject.entity_id == id_)
                nodes = {
                    node.value_id: node
                    for row in facts
                    if row.fact.subject.entity_id == id_
                    for node in row.values
                }
                yield EntityAnswer(
                    entity=entities[id_],
                    properties=properties,
                    values=tuple(nodes[k] for k in sorted(nodes)),
                )

    def entities(self, key=None, label=None):
        return list(self.entity_rows(key, label))

    def evidence(self, fact_id):
        return self.session.explain(fact_id).evidence
