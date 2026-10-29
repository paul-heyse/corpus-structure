"""Composable, batched Core reads on the journey's single semantic ReadSession."""
from __future__ import annotations
from collections.abc import Iterator
from typing import Any
import json
from sqlalchemy import and_, exists, func, or_, select
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import QueryRow, _scope, _same_scope
from corpus_structure.serve.results import ClaimAnswer, EntityAnswer

T = {name: table("data." + name) for name in ("entity", "membership", "fact", "selection", "typed_value", "value_role", "occurrence", "occurrence_context", "derivation", "derivation_premise", "coverage", "evidence", "support", "occurrence_evidence")}

class Reader:
    def __init__(self, ctx: Any):
        self.ctx, self.session, self.conn = ctx, ctx.session, ctx.conn
        self.binding, self.prepared = self.session.binding, self.session.prepared
        self._adapters = {}
    def scope(self, relation): return _scope(self.binding, relation)
    def iri(self, name):
        if name.startswith(("http:", "https:", "urn:")): return name
        if ":" in name: return self.prepared.expand_name(name)
        candidates = {p.iri for d in self.prepared.definitions for p in d.properties if p.name == name}
        candidates |= {d.iri for d in self.prepared.definitions if d.name == name}
        if len(candidates) != 1: raise ValueError(f"ambiguous or unknown release name {name!r}")
        return candidates.pop()
    def referenced_entities(self, root):
        """Correlated recursive value closure preserves nested unresolved endpoints."""
        v, role = T["typed_value"], T["value_role"]
        closure = select(v.c.value_id).where(self.scope(v), v.c.value_id == root).correlate(T["fact"]).cte(recursive=True)
        closure = closure.union(select(role.c.child_value_id).join(closure, closure.c.value_id == role.c.parent_value_id).where(self.scope(role)))
        return select(v.c.entity_id).where(self.scope(v), v.c.value_id.in_(select(closure)), v.c.kind == "entity")
    def qualification_matches(self, name, value):
        role, val = T["value_role"].alias(), T["typed_value"].alias()
        return exists(select(1).select_from(role.join(val, and_(_same_scope(role,val),role.c.child_value_id == val.c.value_id))).where(self.scope(role), role.c.parent_value_id == T["fact"].c.qualification_value_id, role.c.role == name, val.c.text_value == value))
    def fact_statement(self, *, include_candidates=False, include_suppositions=False, **filters):
        f, selected = T["fact"], T["selection"]
        stmt = select(f).where(self.scope(f))
        projection = "fact" if include_candidates or filters.get("status") == "candidate" else self.ctx.projection
        if projection == "accepted":
            stmt = stmt.where(exists(select(1).where(self.scope(selected), selected.c.fact_id == f.c.fact_id)))
        if not include_suppositions:
            try:
                excluded = self.prepared.enum_members("ClaimModality", subset="premise_forming")
            except (StopIteration, KeyError): excluded = frozenset()
            for modality in excluded: stmt = stmt.where(~self.qualification_matches("modality", modality))
        for key, value in filters.items():
            if value is None: continue
            column = {"key": f.c.fact_id, "fact_id": f.c.fact_id, "predicate": f.c.property_id, "subject_id": f.c.subject_id}.get(key)
            if key == "predicate": value = self.iri(value)
            if key == "status":
                if value not in {"accepted", "candidate"}: raise ValueError("semantic status must be accepted or candidate")
                criterion = exists(select(1).where(self.scope(selected), selected.c.fact_id == f.c.fact_id))
                stmt = stmt.where(criterion if value == "accepted" else ~criterion)
            elif key == "modality": stmt = stmt.where(self.qualification_matches(key, value))
            elif key == "object_entity_id": stmt = stmt.where(value.in_(self.referenced_entities(f.c.object_value_id)) if hasattr(value,"in_") else exists(self.referenced_entities(f.c.object_value_id).where(T["typed_value"].c.entity_id == value)))
            elif column is not None: stmt = stmt.where(column.in_(value) if isinstance(value,(list,tuple,set)) else column == value)
            else: raise ValueError(f"unsupported semantic fact filter {key}")
        return stmt
    # Query plugins compose these Core selections; hydration stays a single batched boundary.
    claim_statement = fact_statement
    def claims(self, after=None, statement=None, with_premises=False, **filters) -> Iterator[ClaimAnswer]:
        f = T["fact"]
        stmt = self.fact_statement(**filters) if statement is None else statement
        if after is not None and self.ctx.projection != "occurrence":
            if not isinstance(after,str): raise ValueError("invalid semantic fact cursor")
            stmt = stmt.where(f.c.fact_id.collate("C") > after)
        if self.ctx.projection == "occurrence":
            o = T["occurrence"]
            stmt = stmt.with_only_columns(f.c.fact_id,f.c.subject_id,f.c.property_id,o.c.report_object_value_id.label("object_value_id"),o.c.report_qualification_value_id.label("qualification_value_id"),o.c.occurrence_id,o.c.source,o.c.item).join(o,and_(_same_scope(f,o),f.c.fact_id == o.c.fact_id))
            if after is not None:
                # Occurrence order is the public identity; replace the fact cursor criterion.
                stmt = stmt.where(o.c.occurrence_id.collate("C") > after)
            order = o.c.occurrence_id
        else: order = f.c.fact_id
        # Keyset-sized batches avoid an open server cursor during graph hydration.
        cursor = None
        while True:
            page = stmt if cursor is None else stmt.where(order.collate("C") > cursor)
            rows = self.conn.execute(page.order_by(order.collate("C")).limit(self.ctx.row_batch)).mappings().all()
            if not rows: break
            decoded, nodes, entities = self.session._values({row[k] for row in rows for k in ("object_value_id","qualification_value_id") if row[k] is not None}, {row["subject_id"] for row in rows})
            contexts, citations = self.session._occurrence_contexts(tuple(row["occurrence_id"] for row in rows if row.get("occurrence_id") is not None))
            for row in rows:
                memberships = {m.class_iri for m in entities[row["subject_id"]].memberships}
                definition = next((d for d in self.prepared.definitions if d.iri in memberships and any(p.iri == row["property_id"] for p in d.properties)), None)
                if definition is None: raise ValueError("fact property has no release-declared subject membership")
                prop = next(p for p in definition.properties if p.iri == row["property_id"])
                key = (definition.name,prop.name)
                if key not in self._adapters: self._adapters[key] = self.prepared.property_adapter(*key,item=prop.multivalued)
                value = self._adapters[key].validate_python(decoded[row["object_value_id"]],strict=True)
                qualification = None if row["qualification_value_id"] is None else self.session.qualification(row["qualification_value_id"],decoded,nodes)
                occurrence = row.get("occurrence_id")
                fact = QueryRow(fact_id=row["fact_id"],subject=entities[row["subject_id"]],property_iri=row["property_id"],object_value_id=row["object_value_id"],object=value,qualification_value_id=row["qualification_value_id"],qualification=qualification,occurrence_id=occurrence,source=row.get("source"),item=row.get("item"),context=contexts.get(occurrence),citation_roles=citations.get(occurrence,()))
                # Preserve the exact reachable value graph, including scale/lexical forms.
                reachable = {fact.object_value_id,fact.qualification_value_id}
                changed = True
                while changed:
                    prior = len(reachable)
                    reachable.update(role.child_value_id for node in nodes if node.value_id in reachable for role in node.roles)
                    changed = len(reachable) != prior
                yield ClaimAnswer(fact=fact,values=tuple(n for n in nodes if n.value_id in reachable))
            cursor = rows[-1][order.name]
            if len(rows) < self.ctx.row_batch: break
    def entity_ids(self, key=None, label=None, class_name=None):
        e, f, v = T["entity"], T["fact"], T["typed_value"]
        stmt = select(e.c.entity_id).where(self.scope(e))
        if key is not None: stmt = stmt.where(e.c.entity_id == key)
        if class_name is not None:
            m,h = T["membership"],table("sem.class_hierarchy")
            iri = self.iri(class_name)
            stmt = stmt.where(exists(select(1).where(self.scope(m),m.c.entity_id == e.c.entity_id,or_(m.c.class_id == iri, exists(select(1).where(h.c.release_id == self.binding.release_id,h.c.class_id == m.c.class_id,h.c.ancestor_id == iri))))))
        if label is not None:
            # Labels are semantic property values, never old compiled key normalization.
            iris = {p.iri for d in self.prepared.definitions for p in d.properties if p.name in {"label","aliases","name","canonical_name"}}
            folded_classes = {json.loads(row.body)["iri"] for row in self.prepared.registry_rows if row.kind == "operation_class" and json.loads(row.body).get("cs:case") == "casefold"}
            membership = T["membership"]
            folded = exists(select(1).where(self.scope(membership),membership.c.entity_id == e.c.entity_id,membership.c.class_id.in_(folded_classes)).correlate(e))
            matches = or_(v.c.text_value == label, and_(folded,func.casefold(v.c.text_value.collate("pg_unicode_fast")) == label.casefold()))
            stmt = stmt.where(exists(select(1).select_from(f.join(v,and_(_same_scope(f,v),f.c.object_value_id == v.c.value_id))).where(self.scope(f),f.c.subject_id == e.c.entity_id,f.c.property_id.in_(iris),matches)))
        return stmt
    def resolve(self, value, class_name=None):
        e = T["entity"]
        direct = self.conn.execute(self.entity_ids(key=value,class_name=class_name)).scalars().all()
        return direct or self.conn.execute(self.entity_ids(label=value,class_name=class_name)).scalars().all()
    def entity_rows(self,key=None,label=None,after=None):
        e = T["entity"]
        stmt = self.entity_ids(key,label)
        if after is not None: stmt = stmt.where(e.c.entity_id.collate("C") > str(after))
        for ids in self.conn.execute(stmt.order_by(e.c.entity_id.collate("C"))).scalars().partitions(self.ctx.row_batch):
            entities = self.session._entities(set(ids))
            facts = list(self.claims(subject_id=list(ids)))
            for id_ in ids:
                properties = tuple(row.fact for row in facts if row.fact.subject.entity_id == id_)
                nodes = {node.value_id:node for row in facts if row.fact.subject.entity_id == id_ for node in row.values}
                yield EntityAnswer(entity=entities[id_],properties=properties,values=tuple(nodes[k] for k in sorted(nodes)))
    def entities(self,key=None,label=None): return list(self.entity_rows(key,label))
    def evidence(self,fact_id): return self.session.explain(fact_id).evidence
