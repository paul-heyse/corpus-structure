"""Owned semantic set kernels and the typed operation views they consume.

These projections use occurrence/fact identifiers supplied by the bound operation.
They are independent of the retired pool's storage or reference-class vocabulary.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

import pyarrow as pa
from duckdb import DuckDBPyRelation, coalesce, col, fn, list_type, lit, sqltype, when


def _schema(name: str, *fields: pa.Field) -> pa.Schema:
    return pa.schema(fields, metadata={b"cs.relation": name.encode()})


VIEW_CLAIMS = _schema(
    "view_claims",
    pa.field("claim", pa.string(), nullable=False),
    pa.field("predicate", pa.string(), nullable=False),
    pa.field("subject", pa.string(), nullable=False),
    pa.field("object", pa.string()),
    pa.field("statement", pa.string()),
)
VIEW_ENTITIES = _schema(
    "view_entities",
    pa.field("entity", pa.string(), nullable=False),
    pa.field("key", pa.string()),
    pa.field("class_id", pa.string(), nullable=False),
    pa.field("label", pa.string(), nullable=False),
    pa.field("symbol", pa.string()),
)
VIEW_IDENTITY = _schema(
    "view_identity",
    pa.field("entity", pa.string(), nullable=False),
    pa.field("slot", pa.string(), nullable=False),
    pa.field("value", pa.string(), nullable=False),
)
VIEW_ALTERNATIVES = _schema(
    "view_alternatives",
    pa.field("group", pa.string(), nullable=False),
    pa.field("claim", pa.string(), nullable=False),
)
VIEW_FACTS = _schema(
    "view_facts",
    pa.field("claim", pa.string(), nullable=False),
    pa.field("view", pa.string(), nullable=False),
    pa.field("facts", pa.list_(pa.field("item", pa.string(), nullable=False)), nullable=False),
)
VIEW_SPECS = pa.schema(
    [
        (name, pa.string())
        for name in ("view", "source", "match_source", "match_claim", "head", "attr", "slot")
    ]
)
VIEW_APPLIES = pa.schema([("view", pa.string()), ("predicate", pa.string())])
SAME_SLOT, ALTERNATIVE_OF = "same_slot", "alternative_of"
PROJECTED = ("id", "key", "types", "label", "symbol")
type Side = Literal["subject", "object"]


@dataclass(frozen=True)
class ViewSpec:
    name: str
    applies_to: frozenset[str]
    source: str
    match_source: Side
    match_claim: Side
    head: Side
    attr: str
    slot: str | None = None

    def __post_init__(self) -> None:
        if not self.name or self.name in {SAME_SLOT, ALTERNATIVE_OF}:
            raise ValueError("declared view shadows a generic fact or has no name")
        if (
            self.match_source not in {"subject", "object"}
            or self.match_claim not in {"subject", "object"}
            or self.head not in {"subject", "object"}
        ):
            raise ValueError("view sides must be subject or object")
        if not (
            (self.attr in PROJECTED and self.slot is None)
            or (self.attr == "identity" and self.slot)
        ):
            raise ValueError("unsupported view projection")

    @classmethod
    def from_declaration(
        cls, name: str, declaration: Mapping[str, Any], applies_to: Iterable[str]
    ) -> ViewSpec:
        head, _, rest = str(declaration["project"]).partition(".")
        attr, _, slot = rest.partition(".")
        if head not in ("subject", "object") or not (
            (attr in PROJECTED and not slot) or (attr == "identity" and slot)
        ):
            raise ValueError(f"view {name}: cannot project {declaration['project']!r}")
        selected_head: Side = "subject" if head == "subject" else "object"
        match = declaration["match"]
        return cls(
            name,
            frozenset(applies_to),
            str(declaration["source"]),
            match["source"],
            match["claim"],
            selected_head,
            attr,
            slot or None,
        )


def operation_view_tables(
    specs: Iterable[ViewSpec], property_ids: Iterable[str]
) -> tuple[pa.Table, pa.Table]:
    """Validate actual declared property references and realize the fixed view inputs."""
    specs = tuple(specs)
    names = [spec.name for spec in specs]
    if len(set(names)) != len(names) or {SAME_SLOT, ALTERNATIVE_OF} & set(names):
        raise ValueError("view names repeat or shadow a generic fact")
    declared = set(property_ids)
    for spec in specs:
        if spec.source not in declared or not spec.applies_to <= declared:
            raise ValueError("view uses a property outside this release")
    rows = [
        {
            "view": spec.name,
            "source": spec.source,
            "match_source": spec.match_source,
            "match_claim": spec.match_claim,
            "head": spec.head,
            "attr": spec.attr,
            "slot": spec.slot,
        }
        for spec in specs
    ]
    applies = [
        {"view": spec.name, "predicate": predicate}
        for spec in specs
        for predicate in sorted(spec.applies_to)
    ]
    return pa.Table.from_pylist(rows, schema=VIEW_SPECS), pa.Table.from_pylist(
        applies, schema=VIEW_APPLIES
    )


def disagreements(meanings: DuckDBPyRelation) -> DuckDBPyRelation:
    distinct = meanings.distinct()
    conflicting = (
        distinct.aggregate([col("key"), fn("count", lit(1)).alias("n")])
        .filter(col("n") > 1)
        .select(col("key").alias("conflicting_key"))
        .set_alias("conflicting")
    )
    return (
        distinct.join(conflicting, col("key") == col("conflicting_key"))
        .select(col("key"), col("meaning"))
        .sort(col("key"), col("meaning").asc().nulls_first())
    )


def _facts(value):
    empty = lit([]).cast(list_type(sqltype("VARCHAR")))
    return coalesce(fn("list_sort", fn("list_distinct", fn("list", value))), empty)


def fuse(candidates: DuckDBPyRelation) -> DuckDBPyRelation:
    evidence = (
        candidates.select(
            col("fact_id").alias("evidence_fact"), fn("unnest", col("evidence")).alias("item")
        )
        .aggregate([col("evidence_fact"), _facts(col("item")).alias("evidence")])
        .set_alias("evidence_sets")
    )
    supports = candidates.aggregate(
        [
            col("fact_id"),
            _facts(col("occurrence_id")).alias("supports"),
            fn("count", lit(1)).alias("candidates"),
        ]
    )
    empty = lit([]).cast(list_type(sqltype("VARCHAR")))
    return (
        supports.join(evidence, col("fact_id") == col("evidence_fact"), how="left")
        .select(
            col("fact_id"),
            col("supports"),
            col("candidates"),
            coalesce(col("evidence"), empty).alias("evidence"),
        )
        .sort(col("fact_id"))
    )


def _prefixed(relation: DuckDBPyRelation, prefix: str) -> DuckDBPyRelation:
    return relation.select(
        *(col(name).alias(prefix + name) for name in relation.columns)
    ).set_alias(prefix)


def operation_views(
    claims: DuckDBPyRelation,
    entities: DuckDBPyRelation,
    identity: DuckDBPyRelation,
    alternatives: DuckDBPyRelation,
    specs: DuckDBPyRelation,
    applies: DuckDBPyRelation,
) -> DuckDBPyRelation:
    c, d = _prefixed(claims, "c_"), _prefixed(claims, "d_")
    a, b = _prefixed(alternatives, "a_"), _prefixed(alternatives, "b_")
    s, e, i = _prefixed(specs, "s_"), _prefixed(entities, "e_"), _prefixed(identity, "i_")
    declared_applies = _prefixed(applies, "a_")
    null_statements = col("c_statement").is_null() & col("d_statement").is_null()
    same_slot = (
        c.join(
            d,
            (
                (col("c_predicate") == col("d_predicate"))
                & (col("c_subject") == col("d_subject"))
                & ((col("c_statement") == col("d_statement")) | null_statements)
                & (col("c_claim") != col("d_claim"))
            ),
            how="left",
        )
        .aggregate(
            [
                col("c_claim").alias("claim"),
                _facts(col("d_claim")).alias("facts"),
            ]
        )
        .select(col("claim"), lit(SAME_SLOT).alias("view"), col("facts"))
    )
    pairs = (
        a.join(b, (col("a_group") == col("b_group")) & (col("a_claim") != col("b_claim")))
        .join(d, col("b_claim") == col("d_claim"), how="semi")
        .select(col("a_claim").alias("pair_claim"), col("b_claim").alias("other"))
        .distinct()
    )
    alternative_view = (
        c.join(pairs, col("c_claim") == col("pair_claim"), how="left")
        .aggregate(
            [
                col("c_claim").alias("claim"),
                _facts(col("other")).alias("facts"),
            ]
        )
        .select(col("claim"), lit(ALTERNATIVE_OF).alias("view"), col("facts"))
    )
    target = (
        s.join(declared_applies, col("s_view") == col("a_view"))
        .join(c, col("c_predicate") == col("a_predicate"))
        .select(
            col("s_view").alias("target_view"),
            col("c_claim").alias("claim"),
            when(col("s_match_claim") == "subject")
            .then(col("c_subject"))
            .otherwise(col("c_object"))
            .alias("target_match"),
        )
        .distinct()
    )
    projected = (
        s.join(d, col("d_predicate") == col("s_source"))
        .join(
            e,
            col("e_entity")
            == when(col("s_head") == "subject").then(col("d_subject")).otherwise(col("d_object")),
        )
        .join(
            i,
            (col("s_attr") == "identity")
            & (col("i_entity") == col("e_entity"))
            & (col("i_slot") == col("s_slot")),
            how="left",
        )
    )
    value = when(col("s_attr") == "id").then(col("e_entity"))
    for attr, field in (
        ("key", "key"),
        ("types", "class_id"),
        ("label", "label"),
        ("symbol", "symbol"),
    ):
        value = value.when(col("s_attr") == attr).then(col("e_" + field))
    value = value.when(col("s_attr") == "identity").then(col("i_value")).otherwise(lit(None))
    projected = projected.select(
        col("s_view").alias("projected_view"),
        when(col("s_match_source") == "subject")
        .then(col("d_subject"))
        .otherwise(col("d_object"))
        .alias("projected_match"),
        value.alias("value"),
    )
    declared = target.join(
        projected,
        (col("target_view") == col("projected_view"))
        & (col("target_match") == col("projected_match")),
        how="left",
    ).aggregate(
        [
            col("claim"),
            col("target_view").alias("view"),
            _facts(col("value")).alias("facts"),
        ]
    )
    return same_slot.union(alternative_view).union(declared).sort(col("claim"), col("view"))
