"""Q-3 probe compiler: SchemaView -> SQLAlchemy 2.1 MetaData (R05 / TM §6 rules, probe scope).

Rules (each derived from a declaration; proposed declarations are named in system_sketch.yaml):
- a class with ci:store table (or in a meta/ops/kb subset with no ci:store) is a table; its PostgreSQL
  schema is the one of those subsets it is in; the table name is the class name in snake case;
- a scalar slot is a column, typed from its type's uri (xsd:long bigint, xsd:short smallint, integer,
  xsd:float real, double, boolean, datetime timestamptz, string text) or the type's ci:sql_type;
- a multivalued scalar slot is an array column; required -> NOT NULL DEFAULT '{}';
- a slot ranged over a nested class (ci:store nested) is jsonb; required and the class has no required
  attribute -> NOT NULL DEFAULT '{}';
- a single-valued slot ranged over a table class is a bigint FK column <slot>_id to its identifier;
  ci:on_delete (proposed) sets the action;
- an identifier slot ranged over Id is bigint GENERATED ALWAYS AS IDENTITY primary key; a class with no
  identifier takes its only unique key as primary key; other unique keys are UNIQUE constraints;
- an enum-ranged slot whose enum is ci:lifecycle static is text with a digest-named
  CheckConstraint(col.in_(members));
- ifabsent int(n) / string(s) / true / false -> server default; ci:generated insert_time (proposed) ->
  DEFAULT now();
- ci:invariant templates -> named CHECKs: ordered(a,b) a < b; ordered_eq(a,b) a <= b;
  iff_present(x, y = v) (y = v) = (x IS NOT NULL); iff_absent(x, y = v) (proposed)
  (y = v) = (x IS NULL); together(a,b) (a IS NULL) = (b IS NULL); exactly_one(a,b)
  (a IS NULL) <> (b IS NULL).
"""

from __future__ import annotations

import hashlib
import re

from linkml_runtime.utils.schemaview import SchemaView
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Double,
    ForeignKey,
    Identity,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    REAL,
    SmallInteger,
    Table,
    Text,
    UniqueConstraint,
    and_,
    text,
)
from sqlalchemy.schema import DefaultClause
from sqlalchemy.dialects.postgresql import JSONB, REGCONFIG, TIMESTAMP

NAMING = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    # CHECK names are given explicitly (digest names); the convention passes them through.
    "ck": "%(constraint_name)s",
}
PG_SCHEMAS = ("meta", "ops", "kb")
URI_TYPES = {
    "xsd:long": BigInteger, "xsd:short": SmallInteger, "xsd:integer": Integer, "xsd:int": Integer,
    "xsd:float": REAL, "xsd:double": Double, "xsd:decimal": Double, "xsd:boolean": Boolean,
    "xsd:dateTime": lambda: TIMESTAMP(timezone=True), "xsd:string": Text,
}
SQL_TYPES = {"regconfig": REGCONFIG}


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:10]


def ann(el, tag: str):
    """An annotation value; induced slots carry annotations as a JsonObj, elements as a dict."""
    if el is None or not el.annotations:
        return None
    a = el.annotations
    items = dict(a._items()) if hasattr(a, "_items") else dict(a.items())
    v = items.get(tag)
    return None if v is None else getattr(v, "value", v)


class Compiler:
    def __init__(self, sv: SchemaView, strict: bool = False) -> None:
        """strict: read only TM §4's vocabulary; the proposed declarations (ci:on_delete, ci:generated,
        ci:sql_type, the iff_absent template) are ignored, so their effect shows up as residue."""
        self.sv = sv
        self.strict = strict
        self.skipped: list[str] = []
        self.md = MetaData(naming_convention=NAMING)
        self.tables: dict[str, Table] = {}
        self.cls_of_table: dict[str, str] = {}

    # -- classification ---------------------------------------------------------------------
    def store(self, cls: str) -> str | None:
        c = self.sv.get_class(cls)
        s = ann(c, "ci:store")
        if s:
            return str(s)
        return "table" if self.pg_schema(cls) else None

    def pg_schema(self, cls: str) -> str | None:
        hits = [s for s in self.sv.get_class(cls).in_subset if s in PG_SCHEMAS]
        return str(hits[0]) if len(hits) == 1 else None

    def table_classes(self) -> list[str]:
        return [c for c in self.sv.all_classes() if self.store(c) == "table"]

    def identifier(self, cls: str):
        for s in self.sv.class_induced_slots(cls):
            if s.identifier:
                return s
        return None

    def sa_type(self, rng: str):
        sv = self.sv
        if rng in sv.all_types():
            t = sv.get_type(rng)
            st = None if self.strict else ann(t, "ci:sql_type")
            if st:
                return SQL_TYPES[str(st)]()
            chain = [rng, *sv.type_ancestors(rng)]
            for name in chain:
                uri = sv.get_type(name).uri
                if uri in URI_TYPES:
                    return URI_TYPES[uri]()
            raise KeyError(f"no SQL type for {rng}")
        raise KeyError(rng)

    # -- compile ----------------------------------------------------------------------------
    def compile(self) -> MetaData:
        order = self.table_classes()
        for cls in order:  # first pass: tables and scalar columns, so FKs can resolve
            self.tables[cls] = Table(snake(cls), self.md, schema=self.pg_schema(cls),
                                     info={"model_class": cls})
        for cls in order:
            self._columns(cls)
        return self.md

    def _columns(self, cls: str) -> None:
        sv, t = self.sv, self.tables[cls]
        tname = t.name
        col_of: dict[str, str] = {}
        ident = self.identifier(cls)
        for s in sv.class_induced_slots(cls):
            rng = s.range or sv.schema.default_range
            required = bool(s.required)
            kw: dict = {"nullable": not required}
            if rng in sv.all_classes() and self.store(rng) == "table":
                target = self.tables[rng]
                tid = self.identifier(rng)
                ondelete = None if self.strict else ann(s, "ci:on_delete")
                col = Column(f"{s.name}_id", BigInteger,
                             ForeignKey(f"{target.fullname}.{tid.name}", ondelete=str(ondelete).upper() if ondelete else None),
                             **kw)
            elif rng in sv.all_classes():  # nested
                c = sv.get_class(rng)
                if str(ann(c, "ci:store") or "nested") != "nested":
                    raise ValueError(f"{cls}.{s.name}: range {rng} is neither table nor nested")
                empty_ok = not any(x.required for x in sv.class_induced_slots(rng))
                if required and empty_ok:
                    kw["server_default"] = text("'{}'")
                col = Column(s.name, JSONB, **kw)
            elif rng in sv.all_enums():
                e = sv.get_enum(rng)
                if str(ann(e, "ci:lifecycle")) != "static":
                    raise NotImplementedError("version-scoped sets: per-version member tables (not in the probe)")
                col = Column(s.name, Text, **kw)
                self._default(col, s)
                members = list(e.permissible_values)
                t.append_column(col)
                t.append_constraint(CheckConstraint(
                    col.in_(members), name=f"ck_{tname}_{s.name}_{digest(rng, *members)}"))
                col_of[s.name] = col.name
                continue
            else:
                typ = self.sa_type(rng)
                if s.multivalued:
                    typ = ARRAY(typ)
                    if required:
                        kw["server_default"] = text("'{}'")
                if ident is not None and s.name == ident.name:
                    if rng == "Id":
                        col = Column(s.name, typ, Identity(always=True), primary_key=True)
                    else:
                        col = Column(s.name, typ, primary_key=True)
                else:
                    col = Column(s.name, typ, **kw)
                self._default(col, s)
            t.append_column(col)
            col_of[s.name] = col.name
        c = sv.get_class(cls)
        uks = list((c.unique_keys or {}).values())
        if ident is None:
            if len(uks) != 1:
                raise ValueError(f"{cls}: no identifier and {len(uks)} unique keys")
            t.append_constraint(PrimaryKeyConstraint(*[col_of[x] for x in uks[0].unique_key_slots]))
            uks = []
        for uk in uks:
            t.append_constraint(UniqueConstraint(*[col_of[x] for x in uk.unique_key_slots]))
        inv = ann(c, "ci:invariant")
        if inv:
            for clause in [x.strip() for x in str(inv).split(";") if x.strip()]:
                if self.strict and clause.startswith("iff_absent("):
                    self.skipped.append(f"{cls}: {clause}")
                    continue
                t.append_constraint(self._invariant(t, col_of, clause))

    def _default(self, col: Column, s) -> None:
        if not self.strict and ann(s, "ci:generated") == "insert_time":
            col._init_items(DefaultClause(text("now()")))
            return
        ia = s.ifabsent
        if not ia:
            return
        m = re.fullmatch(r"(int|string|float)\((.*)\)", ia)
        if m:
            kind, val = m.groups()
            dc = text(val) if kind in ("int", "float") else text("'" + val.replace("'", "''") + "'")
        elif ia.lower() in ("true", "false"):
            dc = text(ia.lower())
        else:
            raise ValueError(f"ifabsent {ia!r}")
        col._init_items(DefaultClause(dc))

    def _invariant(self, t: Table, col_of: dict[str, str], clause: str) -> CheckConstraint:
        m = re.fullmatch(r"(\w+)\((.*)\)", clause)
        tpl, args = m.group(1), [a.strip() for a in m.group(2).split(",")]
        c = lambda slot: t.c[col_of[slot]]  # noqa: E731
        if tpl == "ordered":
            expr = c(args[0]) < c(args[1])
        elif tpl == "ordered_eq":
            expr = c(args[0]) <= c(args[1])
        elif tpl in ("iff_present", "iff_absent"):
            y, v = [x.strip() for x in args[1].split("=")]
            lhs = text(f"({col_of[y]} = '{v}')")
            rhs = text(f"({col_of[args[0]]} IS {'NOT ' if tpl == 'iff_present' else ''}NULL)")
            expr = text(f"{lhs.text} = {rhs.text}")
        elif tpl == "together":
            expr = text(f"({col_of[args[0]]} IS NULL) = ({col_of[args[1]]} IS NULL)")
        elif tpl == "exactly_one":
            expr = text(f"({col_of[args[0]]} IS NULL) <> ({col_of[args[1]]} IS NULL)")
        else:
            raise ValueError(f"unknown template {tpl}")
        return CheckConstraint(expr, name=f"ck_{t.name}_{tpl}_{digest(clause)}")


def search_block_kinds(sv: SchemaView) -> list[str]:
    """The _model.sql.SEARCH_BLOCK constant: segment kinds with the search_block member property."""
    e = sv.get_enum("SegmentKind")
    return [k for k, pv in e.permissible_values.items() if "search_block" in pv.in_subset]


__all__ = ["Compiler", "search_block_kinds", "and_"]
