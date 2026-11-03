"""Composable, batched Core reads on the journey's single semantic ReadSession."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from sqlalchemy import and_, exists, false, func, or_, select

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import ReadLimit, same_scope_clause, scope_clause
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

    def claim_tuple(self, *, statement, max_items=1000, max_bytes=8 * 1024 * 1024):
        """Admit a complete nested scientific claim collection, or refuse it in full."""
        items, size = [], 0
        for row in self.claims(statement=statement):
            size += len(canonical_bytes(row.model_dump(mode="json")))
            if len(items) >= max_items or size > max_bytes:
                raise ReadLimit(
                    "nested claim collection exceeds row/byte budget", reason="work_limit"
                )
            items.append(row)
        return tuple(items)

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
            # Released display roles and per-property case policy own label matching.
            membership = T["membership"]
            groups = {}
            for definition in self.prepared.definitions:
                for prop in self.prepared.display_properties(definition.iri):
                    groups.setdefault((prop.iri, prop.case_policy), set()).add(definition.iri)
            if any(policy == "casefold" for _, policy in groups):
                from corpus_structure.semantic.unicode_identity import (
                    require_unicode_identity_release,
                )

                require_unicode_identity_release(self.conn, self.prepared)
            choices = []
            for (property_iri, case_policy), classes in groups.items():
                text_match = (
                    func.casefold(v.c.text_value.collate("pg_unicode_fast")) == label.casefold()
                    if case_policy == "casefold"
                    else v.c.text_value == label
                )
                choices.append(
                    and_(
                        f.c.property_id == property_iri,
                        text_match,
                        exists(
                            select(1).where(
                                self.scope(membership),
                                membership.c.entity_id == e.c.entity_id,
                                membership.c.class_id.in_(classes),
                            )
                        ).correlate(e),
                    )
                )
            matches = or_(*choices) if choices else false()
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
                        matches,
                    )
                )
            )
        return stmt

    def resolve(self, value, class_name=None, limit=10001):
        direct = (
            self.conn.execute(self.entity_ids(key=value, class_name=class_name).limit(limit))
            .scalars()
            .all()
        )
        found = (
            direct
            or self.conn.execute(self.entity_ids(label=value, class_name=class_name).limit(limit))
            .scalars()
            .all()
        )
        if limit is not None and len(found) >= limit:
            raise ReadLimit(
                "entity resolution population exceeds the admitted limit", reason="work_limit"
            )
        return found

    def entity_rows(self, key=None, label=None, after=None):
        e = T["entity"]
        stmt = self.entity_ids(key, label)
        if after is not None:
            if not isinstance(after, str):
                raise SemanticRefusal("invalid semantic entity cursor")
            stmt = stmt.where(e.c.entity_id.collate("C") > after)
        while True:
            page = stmt if after is None else stmt.where(e.c.entity_id.collate("C") > after)
            ids = (
                self.conn.execute(
                    page.order_by(e.c.entity_id.collate("C")).limit(self.ctx.row_batch)
                )
                .scalars()
                .all()
            )
            if not ids:
                break
            entities = self.session.load_entities(set(ids))
            f = T["fact"]
            scoped = self.fact_statement(subject_id=list(ids)).subquery()
            ranked = select(
                scoped.c.fact_id,
                scoped.c.subject_id,
                func.count().over(partition_by=scoped.c.subject_id).label("population"),
                func.row_number()
                .over(partition_by=scoped.c.subject_id, order_by=scoped.c.fact_id.collate("C"))
                .label("rank"),
            ).subquery()
            chosen = self.conn.execute(select(ranked).where(ranked.c.rank <= 8)).mappings().all()
            counts = {row["subject_id"]: row["population"] for row in chosen}
            facts = list(
                self.claims(
                    statement=self.fact_statement().where(
                        f.c.fact_id.in_([row["fact_id"] for row in chosen])
                    )
                )
            )
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
                    properties_population_complete=counts.get(id_, 0) <= 8,
                    properties_query={"query": "claims", "subject": id_}
                    if counts.get(id_, 0) > 8
                    else None,
                    values=tuple(nodes[k] for k in sorted(nodes)),
                )

            if len(ids) < self.ctx.row_batch:
                break
            after = ids[-1]

    def entities(self, key=None, label=None):
        return list(self.entity_rows(key, label))

    def evidence(self, fact_id, after=None):
        from corpus_structure.semantic.query import Evidence

        token = None
        while True:
            try:
                page = self.session.inventory(
                    fact_id,
                    "evidence",
                    continuation=token,
                    after_identity=after,
                    limit=self.ctx.row_batch,
                    query_binding=getattr(self.ctx, "query_binding", None),
                    selection=getattr(self.ctx, "answer_selection", None),
                )
            except KeyError:
                raise SemanticRefusal(f"no semantic fact {fact_id}") from None
            for row in page.items:
                if after is None or row["evidence_id"] > after:
                    yield Evidence(**{key: row[key] for key in Evidence.model_fields if key in row})
            token = page.next_page_token
            if token is None:
                break
