"""Run-pinned relational readers shared by generic and pack queries (D3 §9)."""

from __future__ import annotations

from collections.abc import Iterator
from functools import cached_property
from typing import Any

from sqlalchemy import or_, select, tuple_

from corpus_structure.core.db import metadata, repo
from corpus_structure.core.keys import LabelRules, condition_nodes, normalize_label
from corpus_structure.core.locators import LocatorIndex, page_of, parse
from corpus_structure.core.values import CONDITION_ADAPTERS, StoredPhraseNode
from corpus_structure.schema import registry

T = metadata.tables


class Reader:
    def __init__(self, ctx: Any):
        self.ctx = ctx
        self.conn, self.run = ctx.conn, ctx.run_id
        self._entities: dict[int, dict[str, Any]] = {}
        self._evidence: dict[int, list[dict[str, Any]]] = {}
        self._anchors: dict[int, Any] = {}
        self._entity_answers: dict[int, dict[str, Any]] = {}
        self._indices: dict[int, tuple[LocatorIndex, dict[int, Any]]] = {}

    @cached_property
    def compiled(self) -> Any:
        r = T["ops.run"]
        version = self.conn.execute(
            select(r.c.schema_version_id).where(r.c.id == self.run)
        ).scalar_one()
        return registry.compiled_for(self.conn, version)

    @cached_property
    def labels(self) -> LabelRules:
        from corpus_structure.consolidate.pass_ import config_of

        return config_of(self.conn, self.run, "finalize").labels(self.compiled.names.to_prefixed)

    def index(self, rendition: int) -> tuple[LocatorIndex, dict[int, Any]]:
        if rendition not in self._indices:
            rr, d, s = T["kb.run_rendition"], T["kb.document"], T["kb.segment"]
            uri = self.conn.execute(
                select(d.c.source_uri)
                .join(rr, rr.c.document_id == d.c.id)
                .where(rr.c.run_id == self.run, rr.c.rendition_id == rendition)
            ).scalar_one()
            # The stored source URI ends at the page; retain relative source paths.
            from sqlalchemy import text

            root = self.conn.execute(
                text(
                    "SELECT c.params -> 'source_profile' ->> 'root' FROM "
                    "kb.rendition_build b JOIN ops.method_config c ON "
                    "c.id=b.method_config_id WHERE b.rendition_id=:r LIMIT 1"
                ),
                {"r": rendition},
            ).scalar()
            content = repo.read_rendition(self.conn, rendition)
            idx = LocatorIndex(content, page_of(uri, root) if root else uri)
            segments = {(x.kind.value, x.start, x.end): x for x, _ in idx}
            ids = {
                row.id: segments[(row.kind, row.start_offset, row.end_offset)]
                for row in self.conn.execute(
                    select(s.c.id, s.c.kind, s.c.start_offset, s.c.end_offset).where(
                        s.c.rendition_id == rendition
                    )
                )
            }
            self._indices[rendition] = idx, ids
        return self._indices[rendition]

    def locator(
        self, rendition: int, segment: int, start: int, end: int, text: str
    ) -> dict[str, Any]:
        idx, ids = self.index(rendition)
        seg = ids[segment]
        return {
            "locator": str(idx.generate(seg)),
            "start": start - seg.start,
            "end": end - seg.start,
            "text": text,
        }

    def prime_entities(self, ids: set[int]) -> None:
        missing = ids - self._entities.keys()
        if not missing:
            return
        e, i = T["kb.entity"], T["kb.entity_identity"]
        rows = self.conn.execute(
            select(e).where(e.c.run_id == self.run, e.c.id.in_(missing))
        ).mappings()
        for row in rows:
            self._entities[row["id"]] = dict(row) | {"identity": {}}
        segment = T["kb.segment"]
        anchors = {
            r["scope_segment_id"]
            for id_, r in self._entities.items()
            if id_ in missing and r.get("scope_segment_id")
        } - self._anchors.keys()
        if anchors:
            self._anchors.update(
                {
                    r["id"]: r
                    for r in self.conn.execute(
                        select(segment).where(segment.c.id.in_(anchors))
                    ).mappings()
                }
            )
        resolutions = {
            r["resolved_to_id"]
            for id_, r in self._entities.items()
            if id_ in missing and r.get("resolved_to_id")
        }
        if resolutions:
            self.prime_entities(resolutions)
        target = e.alias("identity_target")
        for row in self.conn.execute(
            select(i, target.c.key.label("target_key"))
            .outerjoin(target, target.c.id == i.c.value_entity_id)
            .where(i.c.entity_id.in_(missing))
        ).mappings():
            self._entities[row["entity_id"]]["identity"][row["slot"]] = (
                {"ref": row["target_key"]}
                if row["value_entity_id"] is not None
                else row["value_text"]
            )

    def entity(self, id_: int | None) -> dict[str, Any] | None:
        if id_ is None:
            return None
        if id_ in self._entity_answers:
            return self._entity_answers[id_]
        self.prime_entities({id_})
        row = self._entities[id_]
        out = {k: row[k] for k in ("key", "type", "label", "kind", "identity")}
        out["scope"] = row["scope"]
        out["statement_ordinal"] = row.get("statement_ordinal")
        if row.get("scope_segment_id"):
            anchor = self._anchors[row["scope_segment_id"]]
            idx, segments = self.index(anchor["rendition_id"])
            out["scope_locator"] = str(idx.generate(segments[anchor["id"]]))
            if row["kind"] is not None:
                out["locator"] = out["scope_locator"]
        if row.get("resolved_to_id"):
            out["resolved_to"] = self.entity(row["resolved_to_id"])
        if row["type"] == "core:ExternalReference":
            out["unresolved"] = row.get("resolved_to_id") is None
            out["descriptor"] = row.get("reference_descriptor")
            out["display"] = (
                f"an unresolved reference: {row['label']}"
                if out["unresolved"]
                else out["resolved_to"]["label"]
            )
            if row.get("scope_segment_id"):
                r = self._anchors[row["scope_segment_id"]]
                d = row.get("reference_descriptor") or {}
                out["citation"] = self.locator(
                    r["rendition_id"],
                    r["id"],
                    d.get("start", r["start_offset"]),
                    d.get("end", r["end_offset"]),
                    row["label"],
                )
        self._entity_answers[id_] = out
        return out

    def entity_rows(
        self, key: str | None = None, label: str | None = None, after: Any = None
    ) -> Iterator[dict[str, Any]]:
        e, a = T["kb.entity"], T["kb.entity_alias"]
        stmt = select(e.c.id).where(e.c.run_id == self.run)
        if key:
            stmt = stmt.where(e.c.key == key)
        if label:
            # Normalize within each declared class, including its case policy.
            choices = []
            for cls in self.compiled.lookup.entity_classes.values():
                case = cls
                normalized = normalize_label(label, cls.prefixed, self.labels, case.label_case)
                choices.append(
                    (e.c.type == cls.prefixed)
                    & e.c.id.in_(select(a.c.entity_id).where(a.c.normalized == normalized))
                )
            stmt = stmt.where(or_(*choices))
        if after is not None:
            if not isinstance(after, str):
                raise ValueError("invalid entity cursor")
            stmt = stmt.where(e.c.key > after)
        with self.conn.execute(stmt.order_by(e.c.key).execution_options(yield_per=64)) as result:
            for batch in result.scalars().partitions(64):
                ids = list(batch)
                self.prime_entities(set(ids))
                for id_ in ids:
                    entity = self.entity(id_)
                    if entity is not None:
                        yield entity

    def entities(self, key: str | None = None, label: str | None = None) -> list[dict[str, Any]]:
        return list(self.entity_rows(key, label))

    def prime_evidence(self, ids: list[int]) -> None:
        ce, sp = T["kb.claim_evidence"], T["kb.span"]
        for id_ in ids:
            self._evidence[id_] = []
        stmt = (
            select(ce.c.claim_id, ce.c.role, sp)
            .join(sp, sp.c.id == ce.c.span_id)
            .where(ce.c.claim_id.in_(ids))
            .order_by(
                ce.c.claim_id, sp.c.rendition_id, sp.c.start_offset, sp.c.end_offset, ce.c.role
            )
        )
        for r in self.conn.execute(stmt).mappings():
            loc = self.locator(
                r["rendition_id"], r["segment_id"], r["start_offset"], r["end_offset"], r["text"]
            )
            idx, _ = self.index(r["rendition_id"])
            sentences = [
                s
                for s, _ in idx
                if s.kind.value == "sentence"
                and s.start <= r["start_offset"]
                and r["end_offset"] <= s.end
            ]
            text_ = idx.rendition.canonical_text
            units = [
                u
                for u in idx.annotation_units().units
                if u.segment.start <= r["start_offset"] and r["end_offset"] <= u.segment.end
            ]
            loc["unit_key"] = units[0].key if units else None
            loc |= {
                "role": r["role"],
                "sentence": text_[sentences[0].start : sentences[0].end]
                if sentences
                else r["text"],
            }
            self._evidence[r["claim_id"]].append(loc)

    def evidence_rows(
        self, claim_key: str, after: Any = None
    ) -> Iterator[tuple[dict[str, Any], list[Any]]]:
        c, ce, sp = T["kb.claim"], T["kb.claim_evidence"], T["kb.span"]
        order = (sp.c.rendition_id, sp.c.start_offset, sp.c.end_offset, ce.c.role, sp.c.id)
        stmt = (
            select(ce.c.role, sp)
            .join(ce, ce.c.span_id == sp.c.id)
            .join(c, c.c.id == ce.c.claim_id)
            .where(c.c.run_id == self.run, c.c.key == claim_key)
        )
        if after is not None:
            if not isinstance(after, list) or len(after) != 5:
                raise ValueError("invalid evidence cursor")
            stmt = stmt.where(tuple_(*order) > tuple_(*after))
        with self.conn.execute(stmt.order_by(*order).execution_options(yield_per=32)) as result:
            for r in result.mappings():
                loc = self.locator(
                    r["rendition_id"],
                    r["segment_id"],
                    r["start_offset"],
                    r["end_offset"],
                    r["text"],
                )
                idx, _ = self.index(r["rendition_id"])
                sentences = [
                    s
                    for s, _ in idx
                    if s.kind.value == "sentence"
                    and s.start <= r["start_offset"]
                    and r["end_offset"] <= s.end
                ]
                units = [
                    u
                    for u in idx.annotation_units().units
                    if u.segment.start <= r["start_offset"] and r["end_offset"] <= u.segment.end
                ]
                loc |= {
                    "role": r["role"],
                    "sentence": idx.rendition.text(sentences[0]) if sentences else r["text"],
                    "unit_key": units[0].key if units else None,
                }
                yield (
                    loc,
                    [r["rendition_id"], r["start_offset"], r["end_offset"], r["role"], r["id"]],
                )

    def evidence_scope(self, claim_key: str) -> Any:
        from corpus_structure.serve.protocol import Scope

        c, ce, sp, t, seg = (
            T[n] for n in ("kb.claim", "kb.claim_evidence", "kb.span", "ops.task", "kb.segment")
        )
        stmt = (
            select(t.c.unit_key)
            .select_from(c)
            .join(ce, ce.c.claim_id == c.c.id)
            .join(sp, sp.c.id == ce.c.span_id)
            .join(
                seg,
                (seg.c.rendition_id == sp.c.rendition_id)
                & (seg.c.start_offset <= sp.c.start_offset)
                & (seg.c.end_offset >= sp.c.end_offset),
            )
            .join(
                t, (t.c.unit_id == seg.c.id) & (t.c.run_id == self.run) & (t.c.stage == "propose")
            )
            .where(c.c.run_id == self.run, c.c.key == claim_key)
            .distinct()
        )
        return Scope.of_units(list(self.conn.execute(stmt).scalars()))

    def evidence(self, claim_key: str) -> list[dict[str, Any]]:
        c = T["kb.claim"]
        id_ = self.conn.execute(
            select(c.c.id).where(c.c.run_id == self.run, c.c.key == claim_key)
        ).scalar_one_or_none()
        if id_ is None:
            return []
        if id_ not in self._evidence:
            self.prime_evidence([id_])
        return self._evidence[id_]

    def claim_statement(self, **filters: Any) -> Any:
        c = T["kb.claim"]
        stmt = select(c).where(c.c.run_id == self.run)
        if not filters.pop("include_candidates", False) and "status" not in filters:
            stmt = stmt.where(c.c.status == "accepted")
        if not filters.pop("include_suppositions", False):
            excluded = self.compiled.lookup.version_sets["ClaimModality"].property(
                "premise_forming"
            )
            stmt = stmt.where(c.c.modality.not_in(excluded))
        for name, value in filters.items():
            if value is not None:
                col = c.c.get(name)
                if col is not None:
                    stmt = stmt.where(
                        col.in_(value) if isinstance(value, list | tuple | set) else col == value
                    )
        return stmt

    def claims(
        self,
        after: str | None = None,
        statement: Any = None,
        with_premises: bool = True,
        **filters: Any,
    ) -> Iterator[dict[str, Any]]:
        c, cr, er = T["kb.claim"], T["kb.claim_ref"], T["kb.claim_entity_ref"]
        stmt = statement if statement is not None else self.claim_statement(**filters)
        if with_premises:
            roots = (
                stmt.with_only_columns(c.c.id).order_by(None).cte("included_claims", recursive=True)
            )
            roots = roots.union(
                select(cr.c.target_claim_id)
                .join(roots, roots.c.id == cr.c.claim_id)
                .where(cr.c.kind == "condition_premise", cr.c.run_id == self.run)
            )
            stmt = select(c).where(c.c.run_id == self.run, c.c.id.in_(select(roots.c.id)))
        if after is not None:
            if not isinstance(after, str):
                raise ValueError("invalid claim cursor")
            stmt = stmt.where(c.c.key > after)
        with self.conn.execute(stmt.order_by(c.c.key).execution_options(yield_per=64)) as result:
            for batch in result.mappings().partitions(64):
                rows = list(batch)
                ids = [r["id"] for r in rows]
                entity_ids = {
                    r[col]
                    for r in rows
                    for col in (
                        "subject_id",
                        "object_entity_id",
                        "statement_id",
                        "attribution_entity_id",
                    )
                    if r[col] is not None
                }
                refs: dict[int, list[dict[str, Any]]] = {id_: [] for id_ in ids}
                target = c.alias("target")
                for r in self.conn.execute(
                    select(cr, target.c.key.label("target_key"))
                    .join(target, target.c.id == cr.c.target_claim_id)
                    .where(cr.c.claim_id.in_(ids))
                ).mappings():
                    refs[r["claim_id"]].append(
                        {"kind": r["kind"], "path": r["path"], "key": r["target_key"]}
                    )
                erefs: dict[int, list[dict[str, Any]]] = {id_: [] for id_ in ids}
                for r in self.conn.execute(select(er).where(er.c.claim_id.in_(ids))).mappings():
                    entity_ids.add(r["entity_id"])
                    erefs[r["claim_id"]].append(dict(r))
                self.prime_entities(entity_ids)
                self.prime_evidence(ids)
                for r in rows:
                    q = r["qualifiers"] or {}
                    entities = [
                        self.entity(r[col])
                        for col in ("subject_id", "object_entity_id", "attribution_entity_id")
                        if r[col] is not None
                    ]
                    entities += [self.entity(x["entity_id"]) for x in erefs[r["id"]]]
                    condition = q.get("core:conditions", q.get("conditions"))
                    typed_condition = (
                        CONDITION_ADAPTERS["stored"].validate_python(condition)
                        if condition is not None
                        else None
                    )
                    conditional = (
                        typed_condition is not None
                        and any(
                            isinstance(node, StoredPhraseNode)
                            for node in condition_nodes(typed_condition)
                        )
                    ) or any(x and x.get("unresolved") for x in entities)
                    yield {
                        "key": r["key"],
                        "predicate": r["predicate"],
                        "subject": self.entity(r["subject_id"]),
                        "object": self.entity(r["object_entity_id"])
                        if r["object_entity_id"]
                        else r["object_value"],
                        "qualifiers": q,
                        "conditions": q.get("core:conditions", q.get("conditions")),
                        "conditions_text": str(q.get("core:conditions", q.get("conditions", ""))),
                        "modality": r["modality"],
                        "polarity": r["polarity"],
                        "attribution": self.entity(r["attribution_entity_id"]),
                        "status": r["status"],
                        "statement": self.entity(r["statement_id"]),
                        "role": r["statement_role"],
                        "evidence": self._evidence[r["id"]],
                        "premises": sorted(
                            refs[r["id"]], key=lambda x: (x["kind"], x["path"], x["key"])
                        ),
                        "entity_references": [
                            {
                                "role": x["role"],
                                "path": x["path"],
                                "slot": x["slot"],
                                "entity": self.entity(x["entity_id"]),
                            }
                            for x in sorted(erefs[r["id"]], key=lambda x: (x["role"], x["path"]))
                        ],
                        "conditional": conditional,
                        "premise": r["modality"]
                        in self.compiled.lookup.version_sets["ClaimModality"].property(
                            "premise_forming"
                        ),
                    }

    def statement_scope(self, value: str) -> Any:
        from corpus_structure.serve.protocol import Scope

        ids, _ = self.resolve_statement(value)
        self.prime_entities(set(ids))
        units = set()
        for id_ in ids:
            segment_id = self._entities[id_].get("scope_segment_id")
            if segment_id is None:
                continue
            row = self._anchors[segment_id]
            idx, segments = self.index(row["rendition_id"])
            anchor = segments[segment_id]
            containing = [
                u
                for u in idx.annotation_units().units
                if u.segment.start <= anchor.start and anchor.end <= u.segment.end
            ]
            units.update(u.key for u in containing)
        return Scope.of_units(list(units))

    def resolve_statement(self, value: str) -> tuple[list[int], str | None]:
        e, rr = T["kb.entity"], T["kb.run_rendition"]
        if value.startswith(("stm:", "ent:")):
            ids = list(
                self.conn.execute(
                    select(e.c.id).where(
                        e.c.run_id == self.run, e.c.key == value, e.c.kind.is_not(None)
                    )
                ).scalars()
            )
            return ids, None
        loc = parse(value)
        renditions = self.conn.execute(
            select(rr.c.rendition_id).where(rr.c.run_id == self.run)
        ).scalars()
        for rendition in renditions:
            idx, ids = self.index(rendition)
            if idx.page != loc.page:
                continue
            segment = idx.resolve(loc)
            segment_ids = [
                id_ for id_, x in ids.items() if segment.start <= x.start and x.end <= segment.end
            ]
            entity_ids = list(
                self.conn.execute(
                    select(e.c.id).where(
                        e.c.run_id == self.run,
                        e.c.kind.is_not(None),
                        e.c.scope_segment_id.in_(segment_ids),
                    )
                ).scalars()
            )
            return entity_ids, str(idx.generate(segment))
        from corpus_structure.serve.journey import QueryRefused

        raise QueryRefused(f"no rendition for {loc.page}")
