"""The relational projection (model and projections §3.4; ADR-0020; TM §6): the model to `MetaData`.

`compile_metadata(view)` is a pure function of the `system` module's `SchemaView` (with `core`
imported); `render(metadata)` writes it as the checked-in `core/db/_tables.py`. The physical
overlay (`core/db/overlay.py`) adds every access path; the model declares none (TM §4).

**Tables.** A `system` class in one of the subsets `meta`, `ops`, `kb`, `eval` with no other
`ci:store` is a table in that schema, named by its native `local_names: {sql: …}` entry or the
snake case of the class name. Its primary key is its identifier, or else its unique key named
`primary_key`; other unique keys are `UNIQUE` constraints. Each `schema_version` closed set
(`ci:lifecycle`) is also a table, `meta.<snake name>`, of per-version members
`(schema_version_id, value, properties)`, keyed by both.

**Columns.** Every slot of a table class is a column, in declaration order:
- a scalar slot is typed from its type's `ci:sql_type`, else the first `uri` of the type and its
  ancestors (`xsd:long` bigint, `xsd:short` smallint, `xsd:integer` integer, `xsd:float` real,
  `xsd:double` double precision, `xsd:boolean`, `xsd:dateTime` timestamptz, `xsd:string` text);
- a multivalued scalar is an array, never null: required has no default, optional `DEFAULT '{}'`;
- a slot ranged over a class that is not a table (a payload or core value class) is `jsonb`;
- a static closed set is `text` with a digest-named `CHECK (col IN (…))`;
- a schema-version-scoped closed set is `text` referencing its member table by the composite
  foreign key `(schema_version_id, col)`;
- the identifier ranged over `Id` is `bigint GENERATED ALWAYS AS IDENTITY`;
- `ifabsent` (`string(…)`, `int(…)`, `true`, `false`) is the server default, cast for a
  `regconfig` column (`'english'::regconfig`, as PostgreSQL stores it: compared uncast, the literal
  resolves `oid = oid` and fails with 22P02, probe Q-3), and
  `ci:generated: insert_time` is `DEFAULT now()`;
- a slot's own `pattern` on a text column is a digest-named `CHECK (col ~ '<pattern>')`, searched
  as the generated validator searches it (`kb.segment.parse_reason`: never empty).

**References.** A single-valued slot ranged over a table class:
- to a table with an identifier: a `bigint` column `<slot>_id` referencing it;
- to a table keyed by `(<shared slots>, <key>)` with no identifier (`meta.schema_slot`): a column
  `<slot>` of the key's type, and the composite foreign key `(<shared columns>, <slot>)`; the
  referencing class has each shared slot, with the same range;
- `ci:same: <slot>` makes the foreign key composite: the referenced row has this row's value of
  `<slot>` (`kb.claim.attribution_entity` with `run`: the same run). The target needs a unique key
  over that slot and its identifier;
- `ci:on_delete` is the referential action.

A column that is a shared column of a composite foreign key whose columns are all `NOT NULL` gets
no foreign key of its own: the composite one implies it (`kb.claim_ref.run_id`). A foreign key to
a table declared later is added after both tables (`use_alter`), which breaks the two cycles
(`meta.project.promoted_run_id`, `ops.run.cut_m19_task_id`). Each composite foreign key records its
shared columns in `info["shared"]`; the overlay's supporting-index check reads them.

**Invariants.** Each `ci:invariant` template of a table class (its own and inherited) is a CHECK,
beside the validator Stage A generates from the same declaration: `ordered(a, b)` `a < b`;
`ordered_eq` `a <= b`; `iff_present(x, y = v)` `(y = v) = (x IS NOT NULL)`; `iff_absent`
`(y = v) = (x IS NULL)`; `only_when(x, y = v)` `(y = v) OR x IS NULL`; `together(a, b)`
`(a IS NULL) = (b IS NULL)`; `exactly_one(a, b)` `(a IS NULL) <> (b IS NULL)` (with more fields,
`num_nulls` and `num_nonnulls`).

**Names.** `NAMING_CONVENTION` names primary keys, unique and foreign keys. Every CHECK is named
`ck_<table>_<column or template>_<digest>`, the digest the first 10 hex digits of the SHA-256 of its
SQL, so a changed expression is a new name that Alembic's `checkconstraint_byname` sees.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Double,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    SmallInteger,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, JSONB, REAL, REGCONFIG, TIMESTAMP
from sqlalchemy.schema import DefaultClause
from sqlalchemy.types import TypeEngine, UserDefinedType

from corpus_structure.schema.model import (
    Invariant,
    ModelError,
    View,
    ci_annotations,
    expand_enum,
    invariants_of,
)

# Bump on any change to what the compiler or the renderer writes for the same model.
COMPILER_VERSION = "4"  # 3: physical inherited types, field constraints and read-role declarations
COMPILER = "corpus_structure.schema.relational"

PG_SCHEMAS = ("meta", "ops", "kb", "eval")
VERSION_CLASS = "SchemaVersion"  # the table that scopes schema-version closed sets
MAX_NAME = 63  # PostgreSQL's identifier length

NAMING_CONVENTION: Mapping[str, str] = {
    "pk": "pk_%(table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "ck": "%(constraint_name)s",  # CHECKs carry their digest name
}


class HalfVec(UserDefinedType):
    """pgvector's `halfvec`, dimension unset (D3 §5: fixed by S7, OPEN-D3-2)."""

    cache_ok = True

    def get_col_spec(self, **kw: Any) -> str:
        return "halfvec"


URI_TYPES: Mapping[str, Any] = {
    "xsd:long": BigInteger,
    "xsd:short": SmallInteger,
    "xsd:integer": Integer,
    "xsd:int": Integer,
    "xsd:float": REAL,
    "xsd:double": Double,
    "xsd:boolean": Boolean,
    "xsd:dateTime": lambda: TIMESTAMP(timezone=True),
    "xsd:string": Text,
}
SQL_TYPES: Mapping[str, Any] = {
    "bytea": BYTEA,
    "jsonb": JSONB,
    "regconfig": REGCONFIG,
    "halfvec": HalfVec,
}


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def digest(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()[:10]


def quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def in_check(column: str, members: Iterable[str]) -> str:
    """A closed set's CHECK: `col IN ('a', 'b')`, members sorted (the order carries no meaning)."""
    return f"{column} IN ({', '.join(quote(m) for m in sorted(members))})"


def check_name(table: str, what: str, sql: str) -> str:
    name = f"ck_{table}_{what}_{digest(sql)}"
    if len(name) > MAX_NAME:
        raise ModelError([f"CHECK name {name} exceeds {MAX_NAME} characters"])
    return name


# --- Compilation -------------------------------------------------------------------------------


@dataclass(frozen=True)
class _ForeignKey:
    """A foreign key before it is attached: `shared` are the columns `mine` shares with the target
    (`ci:same`, or a keyed reference's shared key slots); empty for a simple foreign key."""

    mine: tuple[str, ...]
    table: str  # the referenced table's full name
    theirs: tuple[str, ...]
    ondelete: str | None
    use_alter: bool
    shared: tuple[str, ...]
    where: str


@dataclass
class _Target:
    """A referenced table: its table object and, by slot name, its columns."""

    table: Table
    columns: dict[str, str]  # slot (or member-table field) -> column
    identifier: str | None  # the identifier's column
    keys: list[tuple[str, ...]]  # primary and unique keys, as slot tuples
    order: int


class _Compiler:
    def __init__(self, view: View) -> None:
        self.view = view
        self.md = MetaData(naming_convention=dict(NAMING_CONVENTION))
        self.targets: dict[str, _Target] = {}  # class or enum name -> target
        self.problems: list[str] = []

    # -- classification

    def schema_of(self, cls: str) -> str | None:
        element = self.view.get_class(cls)
        if element is None:
            return None
        store = ci_annotations(element).get("ci:store")
        if store not in (None, "table"):
            return None
        hits = [str(s) for s in element.in_subset or () if str(s) in PG_SCHEMAS]
        if len(hits) > 1:
            self.problems.append(f"{cls}: in more than one schema subset {hits}")
        return hits[0] if len(hits) == 1 else None

    def table_name(self, cls: str) -> str:
        local = self.view.get_class(cls).local_names or {}
        if "sql" in local:
            return str(local["sql"].local_name_value)
        return snake(cls)

    def lifecycle(self, enum: str) -> str:
        return str(ci_annotations(self.view.get_enum(enum)).get("ci:lifecycle"))

    def scalar_type(self, rng: str) -> TypeEngine:
        view = self.view
        sql_type = ci_annotations(view.get_type(rng)).get("ci:sql_type")
        if sql_type is not None:
            if sql_type not in SQL_TYPES:
                raise ModelError([f"type {rng}: ci:sql_type {sql_type!r} has no SQL type"])
            return SQL_TYPES[sql_type]()
        for name in (rng, *view.type_ancestors(rng)):
            uri = view.get_type(name).uri
            if uri in URI_TYPES:
                return URI_TYPES[uri]()
        raise ModelError([f"type {rng}: no SQL type for its uri"])

    # -- the passes

    def compile(self) -> MetaData:
        classes = [str(c) for c in self.view.schema.classes]
        enums = {str(e) for e in self.view.all_enums()}
        self.problems += [f"{c}: a class and an enum share the name" for c in classes if c in enums]
        tables = [c for c in classes if self.schema_of(c)]
        order = 0
        for cls in tables:
            schema = self.schema_of(cls)
            assert schema is not None
            table = Table(self.table_name(cls), self.md, schema=schema, info={"model_class": cls})
            self.targets[cls] = _Target(table, {}, None, [], order)
            order += 1
            if cls == VERSION_CLASS:
                for enum in self.version_scoped():
                    self.targets[enum] = self.member_table(enum, order)
                    order += 1
        if VERSION_CLASS not in self.targets:
            raise ModelError([f"no {VERSION_CLASS} table for the schema-version closed sets"])
        for cls in tables:  # identifiers and keys first, so references resolve
            self.keys(cls)
        for cls in tables:
            self.columns(cls)
        if self.problems:
            raise ModelError(self.problems)
        return self.md

    def version_scoped(self) -> list[str]:
        return [str(e) for e in self.view.all_enums() if self.lifecycle(str(e)) == "schema_version"]

    def member_table(self, enum: str, order: int) -> _Target:
        """The per-version members of a schema-version closed set (D3 §3)."""
        version = self.targets[VERSION_CLASS].table
        name = snake(enum)
        table = Table(
            name,
            self.md,
            Column("schema_version_id", BigInteger, nullable=False, autoincrement=False),
            Column("value", Text, nullable=False),
            Column("properties", ARRAY(Text), nullable=False, server_default=text("'{}'")),
            PrimaryKeyConstraint("schema_version_id", "value"),
            ForeignKeyConstraint(
                ["schema_version_id"], [f"{version.fullname}.id"], ondelete="CASCADE"
            ),
            schema="meta",
            info={"model_enum": enum},
        )
        columns = {"schema_version": "schema_version_id", "value": "value"}
        return _Target(table, columns, None, [("schema_version", "value")], order)

    def keys(self, cls: str) -> None:
        target = self.targets[cls]
        element = self.view.get_class(cls)
        for slot in self.view.class_induced_slots(cls):
            if slot.identifier:
                target.identifier = str(slot.name)
        for name, uk in (element.unique_keys or {}).items():
            slots = tuple(str(s) for s in uk.unique_key_slots)
            if target.identifier is None and name == "primary_key":
                target.keys.insert(0, slots)
            else:
                target.keys.append(slots)
        if target.identifier is not None:
            target.keys.insert(0, (target.identifier,))

    def columns(self, cls: str) -> None:
        view, target = self.view, self.targets[cls]
        table = target.table
        fks: list[_ForeignKey] = []
        checks: list[CheckConstraint] = []
        for slot in view.class_induced_slots(cls):
            name, rng = str(slot.name), str(slot.range or view.schema.default_range)
            ann = ci_annotations(slot)
            where = f"{cls}.{name}"
            nullable = not slot.required
            kw: dict[str, Any] = {"nullable": nullable, "autoincrement": False}
            on_delete = ann.get("ci:on_delete")
            ondelete = str(on_delete).replace("_", " ").upper() if on_delete else None
            same = ann.get("ci:same")
            if same is not None and rng not in self.targets:
                self.problems.append(f"{where}: ci:same on a slot that is not a reference")
            if rng in self.targets and self.schema_of(rng):
                if slot.multivalued:
                    self.problems.append(f"{where}: a multivalued reference needs an edge class")
                    continue
                ref = self.targets[rng]
                use_alter = ref.order > target.order
                if ref.identifier is not None:
                    column = f"{name}_id"
                    table.append_column(Column(column, BigInteger, **kw))
                    target.columns[name] = column
                    id_col = ref.columns.get(ref.identifier, ref.identifier)
                    if same is None:
                        fks.append(
                            _ForeignKey(
                                (column,),
                                ref.table.fullname,
                                (id_col,),
                                ondelete,
                                use_alter,
                                (),
                                where,
                            )
                        )
                    else:
                        shared = self._shared(cls, rng, str(same), where)
                        if shared is not None:
                            mine, theirs = shared
                            if not self._has_key(ref, (str(same), ref.identifier)):
                                self.problems.append(
                                    f"{where}: ci:same {same}: {rng} has no unique key "
                                    f"({same}, {ref.identifier})"
                                )
                            fks.append(
                                _ForeignKey(
                                    (mine, column),
                                    ref.table.fullname,
                                    (theirs, id_col),
                                    ondelete,
                                    use_alter,
                                    (mine,),
                                    where,
                                )
                            )
                    continue
                # a keyed reference: the target's primary key less the slots this class shares
                pk = ref.keys[0] if ref.keys else ()
                shared_slots = [s for s in pk if s in self._slot_names(cls)]
                rest = [s for s in pk if s not in shared_slots]
                if len(rest) != 1 or not shared_slots:
                    self.problems.append(f"{where}: {rng} has no key to reference by {pk}")
                    continue
                key_col = self._target_column(ref, rest[0])
                key_type = ref.table.c[key_col].type
                table.append_column(Column(name, key_type.copy(), **kw))
                target.columns[name] = name
                mine = tuple(self._column(cls, s) for s in shared_slots)
                theirs = tuple(self._target_column(ref, s) for s in shared_slots)
                fks.append(
                    _ForeignKey(
                        (*mine, name),
                        ref.table.fullname,
                        (*theirs, key_col),
                        ondelete,
                        use_alter,
                        mine,
                        where,
                    )
                )
                continue
            if on_delete is not None:
                self.problems.append(f"{where}: ci:on_delete on a slot that is not a reference")
            if view.get_class(rng) is not None:  # nested: a payload or core value class
                column = Column(name, JSONB, **kw)
            elif view.get_enum(rng) is not None:
                column = Column(name, Text, **kw)
                if self.lifecycle(rng) == "static":
                    members = [m.text for m in expand_enum(view, rng)]
                    sql = in_check(name, members)
                    checks.append(CheckConstraint(sql, name=check_name(table.name, name, sql)))
                else:  # schema-version scoped: the member table
                    ref = self.targets[rng]
                    version = self._version_slot(cls, where)
                    if version is not None:
                        mine = self._column(cls, version)
                        fks.append(
                            _ForeignKey(
                                (mine, name),
                                ref.table.fullname,
                                ("schema_version_id", "value"),
                                None,
                                ref.order > target.order,
                                (mine,),
                                where,
                            )
                        )
            else:
                typ = self.scalar_type(rng)
                if slot.multivalued:
                    typ = ARRAY(typ)
                    kw["nullable"] = False
                    if not slot.required:
                        kw["server_default"] = text("'{}'")
                if slot.identifier:
                    if rng == "Id":
                        column = Column(name, typ, Identity(always=True), primary_key=True)
                    else:
                        column = Column(name, typ, primary_key=True, autoincrement=False)
                else:
                    column = Column(name, typ, **kw)
            self._default(column, slot, ann, where)
            if slot.pattern:
                if not isinstance(column.type, Text):
                    self.problems.append(f"{where}: pattern on a column that is not text")
                else:  # searched, as the generated validator does (re.search)
                    sql = f"{name} ~ {quote(str(slot.pattern))}"
                    checks.append(CheckConstraint(sql, name=check_name(table.name, name, sql)))
            table.append_column(column)
            target.columns[name] = name
        self._constraints(cls, fks, checks)

    def _slot_names(self, cls: str) -> set[str]:
        return {str(s.name) for s in self.view.class_induced_slots(cls)}

    def _column(self, cls: str, slot: str) -> str:
        """A slot's column name, as its own pass names it (`<slot>_id` for an id reference)."""
        rng = self.view.induced_slot(slot, cls).range
        if rng in self.targets and self.schema_of(rng) and self.targets[rng].identifier:
            return f"{slot}_id"
        return slot

    def _target_column(self, ref: _Target, slot: str) -> str:
        if slot in ref.columns:
            return ref.columns[slot]
        return self._column(str(ref.table.info["model_class"]), slot)

    def _shared(self, cls: str, rng: str, same: str, where: str) -> tuple[str, str] | None:
        if same not in self._slot_names(cls) or same not in self._slot_names(rng):
            self.problems.append(f"{where}: ci:same {same} is not a slot of {cls} and {rng}")
            return None
        mine_rng = self.view.induced_slot(same, cls).range
        theirs_rng = self.view.induced_slot(same, rng).range
        if mine_rng != theirs_rng:
            self.problems.append(f"{where}: ci:same {same} has ranges {mine_rng} and {theirs_rng}")
            return None
        return self._column(cls, same), self._column(rng, same)

    def _has_key(self, ref: _Target, slots: tuple[str, ...]) -> bool:
        return any(set(k) == set(slots) for k in ref.keys)

    def _version_slot(self, cls: str, where: str) -> str | None:
        hits = [str(s.name) for s in self.view.class_induced_slots(cls) if s.range == VERSION_CLASS]
        if len(hits) != 1:
            self.problems.append(
                f"{where}: a schema-version closed set needs one {VERSION_CLASS} "
                f"slot in {cls}, found {hits}"
            )
            return None
        return hits[0]

    def _default(self, column: Column, slot: Any, ann: Mapping[str, Any], where: str) -> None:
        if ann.get("ci:generated") == "insert_time":
            column._init_items(_server_default("now()"))
            return
        ia = slot.ifabsent
        if not ia:
            return
        m = re.fullmatch(r"(int|string)\((.*)\)", str(ia))
        if m:
            kind, value = m.groups()
            sql = value if kind == "int" else quote(value)
            if isinstance(column.type, REGCONFIG):  # an oid alias: cast, as the server stores it
                sql = f"{sql}::regconfig"
        elif str(ia).lower() in ("true", "false"):
            sql = str(ia).lower()
        else:
            self.problems.append(f"{where}: ifabsent {ia!r} has no SQL default")
            return
        column._init_items(_server_default(sql))

    def _constraints(self, cls: str, fks: list[_ForeignKey], checks: list[CheckConstraint]) -> None:
        target = self.targets[cls]
        table, col = target.table, target.columns
        for i, slots in enumerate(target.keys):
            if target.identifier is not None and i == 0:
                continue
            columns = [col[s] for s in slots]
            if i == 0 and target.identifier is None:
                table.append_constraint(PrimaryKeyConstraint(*columns))
            else:
                table.append_constraint(UniqueConstraint(*columns))
        if not target.keys:
            self.problems.append(f"{cls}: no identifier and no primary_key unique key")
        # a column whose validity a NOT NULL composite foreign key implies gets none of its own
        implied: set[str] = set()
        for fk in fks:
            if fk.shared and all(not table.c[c].nullable for c in fk.mine):
                implied |= set(fk.shared)
        for fk in fks:
            if not fk.shared and fk.mine[0] in implied:
                if fk.ondelete is not None:
                    self.problems.append(
                        f"{fk.where}: ci:on_delete on a foreign key that a composite one implies"
                    )
                continue
            kw: dict[str, Any] = {}
            if fk.ondelete:
                kw["ondelete"] = fk.ondelete
            if fk.use_alter:
                kw["use_alter"] = True
            if fk.shared:
                kw["info"] = {"shared": fk.shared}
            table.append_constraint(
                ForeignKeyConstraint(list(fk.mine), [f"{fk.table}.{c}" for c in fk.theirs], **kw)
            )
        for constraint in self._invariants(cls):
            table.append_constraint(constraint)
        for constraint in checks:
            table.append_constraint(constraint)

    def _invariants(self, cls: str) -> list[CheckConstraint]:
        target = self.targets[cls]
        out = []
        for inv in invariants_of(self.view, cls):
            sql = invariant_sql(inv, target.columns, self._literal(cls, inv))
            out.append(CheckConstraint(sql, name=check_name(target.table.name, inv.template, sql)))
        return out

    def _literal(self, cls: str, inv: Invariant) -> list[str]:
        if inv.condition is None:
            return []
        rng = self.view.induced_slot(inv.condition, cls).range
        if rng in ("integer", "SmallInt", "Id"):
            return [str(int(v)) for v in inv.values]
        return [quote(v) for v in inv.values]


def _server_default(sql: str) -> Any:
    """A server default for `Column._init_items` (typed as a `SchemaItem`; it accepts one)."""
    return DefaultClause(text(sql))


def invariant_sql(inv: Invariant, columns: Mapping[str, str], literals: list[str]) -> str:
    """One `ci:invariant` template as SQL over the table's columns (module doc)."""
    c = [columns[f] for f in inv.fields]
    if inv.condition is not None:
        y = columns[inv.condition]
        test = f"{y} = {literals[0]}" if len(literals) == 1 else f"{y} IN ({', '.join(literals)})"
        x = c[0]
        if inv.template == "iff_present":
            return f"({test}) = ({x} IS NOT NULL)"
        if inv.template == "iff_absent":
            return f"({test}) = ({x} IS NULL)"
        if inv.template == "only_when":
            return f"({test}) OR {x} IS NULL"
    elif inv.template == "ordered":
        return f"{c[0]} < {c[1]}"
    elif inv.template == "ordered_eq":
        return f"{c[0]} <= {c[1]}"
    elif inv.template == "together":
        if len(c) == 2:
            return f"({c[0]} IS NULL) = ({c[1]} IS NULL)"
        return f"num_nulls({', '.join(c)}) IN (0, {len(c)})"
    elif inv.template == "exactly_one":
        if len(c) == 2:
            return f"({c[0]} IS NULL) <> ({c[1]} IS NULL)"
        return f"num_nonnulls({', '.join(c)}) = 1"
    raise ModelError([f"invariant {inv}: no SQL template"])


def compile_metadata(view: View, *, target: str = "legacy") -> MetaData:
    """Compile the selected trusted model; legacy rendering remains byte compatible.

    ``semantic`` is an explicit compiler target for the application-owned physical module.
    Runtime candidate schemas are never passed to this target by release preparation.
    """
    if target == "semantic":
        return _compile_physical(view)
    if target != "legacy":
        raise ModelError([f"unknown relational target {target!r}"])
    return _Compiler(view).compile()


def _compile_physical(view: View) -> MetaData:
    if str(view.schema.id) != "https://corpus-structure.org/model/semantic/physical":
        raise ModelError(["semantic target requires the trusted physical module"])
    md = MetaData(naming_convention=dict(NAMING_CONVENTION))
    physical_types = {
        "bytea": BYTEA,
        "jsonb": JSONB,
        "numeric": Numeric,
        "timestamptz": lambda: TIMESTAMP(timezone=True),
    }
    for name, cls in view.schema.classes.items():
        subsets = [str(s) for s in cls.in_subset]
        if len(subsets) != 1 or subsets[0] not in {"sem", "data", "ops", "kb", "eval"}:
            raise ModelError([f"{name}: physical table needs exactly one trusted physical subset"])
        columns = []
        for slot in view.class_induced_slots(name):
            rng = str(slot.range or "string")
            declared = view.get_type(rng)
            sql_type = ci_annotations(declared).get("ph:sql_type")
            typ: TypeEngine[Any]
            if sql_type is not None:
                typ = physical_types[str(sql_type)]()
            elif view.get_enum(rng) is not None:
                typ = Text()
            elif rng == "integer":
                typ = BigInteger()
            elif rng == "boolean":
                typ = Boolean()
            elif rng == "string":
                typ = Text()
            elif declared is not None and str(declared.uri) in URI_TYPES:
                typ = URI_TYPES[str(declared.uri)]()
            else:
                raise ModelError([f"{name}.{slot.name}: unsupported physical range {rng}"])
            default = ci_annotations(slot).get("ph:default")
            columns.append(
                Column[Any](
                    str(slot.name),
                    typ,
                    *(
                        [Identity(always=True)]
                        if ci_annotations(slot).get("ph:identity") == "true"
                        else []
                    ),
                    nullable=not slot.required,
                    server_default=text(default) if default is not None else None,
                    info={
                        "minimum": slot.minimum_value,
                        "maximum": slot.maximum_value,
                        "pattern": slot.pattern,
                        "enum": (str(slot.equals_string),)
                        if slot.equals_string is not None
                        else tuple(m.text for m in expand_enum(view, rng))
                        if view.get_enum(rng) is not None
                        else (),
                    },
                )
            )
        table_info: dict[str, Any] = {
            "model_class": str(name),
            "immutability": ci_annotations(cls).get("ph:immutability"),
        }
        # Preserve the model-owned upload/derived boundary through physical inheritance.
        # Downstream PDF wire selection must use this projection, including counterfactuals.
        for ancestor in view.class_ancestors(str(name), reflexive=True):
            boundary_role = ci_annotations(view.get_class(ancestor)).get("pds:record_boundary_role")
            if boundary_role is not None:
                table_info["pdf_record_boundary_role"] = str(boundary_role)
                break
        read_roles = ci_annotations(cls).get("ph:read_roles")
        if read_roles is not None:
            table_info["read_roles"] = json.loads(read_roles)
        table = Table(str(name), md, *columns, schema=subsets[0], info=table_info)
        for slot in view.class_induced_slots(name):
            if slot.equals_string is not None:
                sql = str(slot.name) + " = " + quote(str(slot.equals_string))
                table.append_constraint(
                    CheckConstraint(sql, name=check_name(table.name, str(slot.name), sql))
                )
            if view.get_enum(str(slot.range)) is not None:
                sql = in_check(str(slot.name), (m.text for m in expand_enum(view, str(slot.range))))
                table.append_constraint(
                    CheckConstraint(sql, name=check_name(table.name, str(slot.name), sql))
                )
            for bound, operator in ((slot.minimum_value, ">="), (slot.maximum_value, "<=")):
                if bound is not None:
                    sql = f"{slot.name} {operator} {bound}"
                    table.append_constraint(
                        CheckConstraint(sql, name=check_name(table.name, str(slot.name), sql))
                    )
            if slot.pattern:
                sql = str(slot.name) + " ~ " + quote(str(slot.pattern))
                table.append_constraint(
                    CheckConstraint(sql, name=check_name(table.name, str(slot.name), sql))
                )
        for key_name, key in cls.unique_keys.items():
            constraint = PrimaryKeyConstraint if key_name == "primary_key" else UniqueConstraint
            table.append_constraint(constraint(*map(str, key.unique_key_slots)))
    for name, cls in view.schema.classes.items():
        schema = str(cls.in_subset[0])
        table = md.tables[f"{schema}.{name}"]
        ann = ci_annotations(cls)
        for fk in json.loads(ann.get("ph:foreign_keys", "[]")):
            target_name, remote = fk["target"].rsplit(".", 1)
            local = fk["columns"]
            target = [f"{target_name}.{col}" for col in remote.split(",")]
            table.append_constraint(
                ForeignKeyConstraint(local, target, info={"shared": tuple(local[:-1])})
            )
        for sql in json.loads(ann.get("ph:checks", "[]")):
            table.append_constraint(
                CheckConstraint(sql, name=check_name(table.name, "physical", sql))
            )
        for declaration in json.loads(ann.get("ph:indexes", "[]")):
            if isinstance(declaration, dict):
                expressions = (
                    (text(declaration["expression"]),)
                    if "expression" in declaration
                    else tuple(table.c[c] for c in declaration["columns"])
                )
                index = Index(
                    declaration.get("name"),
                    *expressions,
                    postgresql_where=text(declaration["where"]) if "where" in declaration else None,
                    postgresql_using=declaration.get("using", "btree"),
                )
                if "expression" in declaration:
                    table.append_constraint(index)
            else:
                Index(None, *(table.c[c] for c in declaration))
    return md


# --- Rendering ---------------------------------------------------------------------------------


def _type_source(typ: TypeEngine) -> str:
    if isinstance(typ, ARRAY):
        return f"ARRAY({_type_source(typ.item_type)})"
    if isinstance(typ, TIMESTAMP):
        return "TIMESTAMP(timezone=True)"
    if isinstance(typ, HalfVec):
        return "HalfVec()"
    names: dict[type[Any], str] = {
        BigInteger: "BigInteger",
        SmallInteger: "SmallInteger",
        Integer: "Integer",
        Text: "Text",
        Boolean: "Boolean",
        REAL: "REAL",
        Double: "Double",
        JSONB: "JSONB",
        BYTEA: "BYTEA",
        REGCONFIG: "REGCONFIG",
    }
    if type(typ) not in names:
        raise ModelError([f"no source for SQL type {typ!r}"])
    return f"{names[type(typ)]}()"


def _default_sql(column: Column) -> str | None:
    default = column.server_default
    if not isinstance(default, DefaultClause) or column.identity is not None:
        return None
    return str(getattr(default.arg, "text", default.arg))


def _column_source(column: Column) -> str:
    args = [repr(column.name), _type_source(column.type)]
    if column.identity is not None:
        args.append("Identity(always=True)")
    if column.primary_key and len(column.table.primary_key.columns) == 1:
        args.append("primary_key=True")
    elif not column.nullable:
        args.append("nullable=False")
    if column.primary_key and column.identity is None:
        args.append("autoincrement=False")
    sql = _default_sql(column)
    if sql is not None:
        args.append(f"server_default=text({sql!r})")
    return f"Column({', '.join(args)})"


def _constraint_source(constraint: Any) -> str | None:
    if isinstance(constraint, PrimaryKeyConstraint):
        cols = list(constraint.columns.keys())
        return None if len(cols) == 1 else f"PrimaryKeyConstraint({', '.join(map(repr, cols))})"
    if isinstance(constraint, UniqueConstraint):
        return f"UniqueConstraint({', '.join(repr(c.name) for c in constraint.columns)})"
    if isinstance(constraint, ForeignKeyConstraint):
        mine = [e.parent.name for e in constraint.elements]
        theirs = [e.target_fullname for e in constraint.elements]
        args = [repr(mine), repr(theirs)]
        if constraint.ondelete:
            args.append(f"ondelete={constraint.ondelete!r}")
        if constraint.use_alter:
            args.append("use_alter=True")
        if constraint.info:
            args.append(f"info={dict(constraint.info)!r}")
        return f"ForeignKeyConstraint({', '.join(args)})"
    if isinstance(constraint, CheckConstraint):
        sql = str(constraint.sqltext.text)
        m = re.fullmatch(r"(\w+) IN \((.*)\)", sql)
        if m:
            members = re.findall(r"'((?:[^']|'')*)'", m.group(2))
            items = "".join(f"            {v.replace(chr(39) * 2, chr(39))!r},\n" for v in members)
            pad = " " * 12
            body = f"in_check(\n{pad}{m.group(1)!r},\n{pad}(\n{items}{pad}),\n        )"
        else:
            body = repr(sql)
        return f"CheckConstraint({body}, name={str(constraint.name)!r})"
    raise ModelError([f"no source for constraint {constraint!r}"])


def _constraint_order(constraint: Any) -> tuple[int, str]:
    """Constraints are a set on `Table`: order them by kind, then by their source text."""
    kinds = (PrimaryKeyConstraint, UniqueConstraint, ForeignKeyConstraint, CheckConstraint)
    rank = next(i for i, k in enumerate(kinds) if isinstance(constraint, k))
    return rank, _constraint_source(constraint) or ""


def render(metadata: MetaData, revision: str) -> str:
    """`core/db/_tables.py`: the `MetaData` construction, deterministic in model order."""
    names = [t.name for t in metadata.tables.values()]
    if len(names) != len(set(names)):
        raise ModelError(["two tables share a name across schemas; the module names them by table"])
    out = [
        '"""The model\'s tables (model and projections §3.4; ADR-0020): the generated `MetaData`.',
        "",
        "Every table of `model/system.yaml` with its columns, keys, foreign keys and CHECKs, and",
        "the per-version member table of each schema-version closed set. Indexes, views and the",
        "extension assertion are the physical overlay's (`core/db/overlay.py`); import",
        "`core.db`, which applies it.",
        "",
        f"Generated by `{COMPILER}` from model revision {revision} (`just model",
        "generate`); do not edit.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from collections.abc import Iterable",
        "from typing import Any, Final",
        "",
        "from sqlalchemy import (",
        "    BigInteger,",
        "    Boolean,",
        "    CheckConstraint,",
        "    Column,",
        "    Double,",
        "    ForeignKeyConstraint,",
        "    Identity,",
        "    Integer,",
        "    MetaData,",
        "    PrimaryKeyConstraint,",
        "    SmallInteger,",
        "    Table,",
        "    Text,",
        "    UniqueConstraint,",
        "    text,",
        ")",
        "from sqlalchemy.dialects.postgresql import (",
        "    ARRAY,",
        "    BYTEA,",
        "    JSONB,",
        "    REAL,",
        "    REGCONFIG,",
        "    TIMESTAMP,",
        ")",
        "from sqlalchemy.types import UserDefinedType",
        "",
        "",
        "class HalfVec(UserDefinedType):",
        '    """pgvector\'s `halfvec`, dimension unset (D3 §5: fixed by S7, OPEN-D3-2)."""',
        "",
        "    cache_ok = True",
        "",
        "    def get_col_spec(self, **kw: Any) -> str:",
        '        return "halfvec"',
        "",
        "",
        "def in_check(column: str, members: Iterable[str]) -> str:",
        '    """A closed set\'s CHECK: `col IN (\'a\', \'b\')`, members sorted."""',
        '    quoted = ("\'" + m.replace("\'", "\'\'") + "\'" for m in sorted(members))',
        "    return f\"{column} IN ({', '.join(quoted)})\"",
        "",
        "",
        f"NAMING_CONVENTION: Final = {dict(NAMING_CONVENTION)!r}",
        "metadata = MetaData(naming_convention=NAMING_CONVENTION)",
    ]
    for table in metadata.tables.values():
        items = [_column_source(c) for c in table.columns]
        constraints = sorted(
            (c for c in table.constraints if _constraint_source(c) is not None),
            key=_constraint_order,
        )
        items += [s for c in constraints if (s := _constraint_source(c)) is not None]
        items += [f"schema={table.schema!r}", f"info={dict(table.info)!r}"]
        body = "".join(f"    {item},\n" for item in items)
        out += ["", f"{table.name} = Table(\n    {table.name!r},\n    metadata,\n{body})"]
    return "\n".join(out) + "\n"


def render_typed_column_class(name: str, columns: Iterable[Column[Any]]) -> str:
    """Render a static SQLAlchemy surface from already compiled model columns.

    Also accepts columns selected for a protected function's return projection; callers
    must supply the model-owned selection, rather than separately authored annotations.
    """
    if not name.isidentifier():
        raise ModelError([f"invalid TypedColumns class name {name!r}"])
    result = [f"class {name}(TypedColumns):"]
    for column in columns:
        if not column.name.isidentifier():
            raise ModelError([f"invalid typed column name {column.name!r}"])
        if isinstance(column.type, JSONB):
            kind = "JsonValue"
        elif isinstance(column.type, ARRAY):
            kind = f"list[{column.type.item_type.python_type.__name__}]"
        else:
            try:
                kind = column.type.python_type.__name__
            except NotImplementedError as exc:
                raise ModelError([f"unsupported typed column {column}"]) from exc
        if column.nullable:
            kind += " | None"
        result.append(f"    {column.name}: Named[{kind}]")
    if len(result) == 1:
        result.append("    pass")
    return "\n".join(result) + "\n"


def render_typed_column_protocol(name: str, columns: Iterable[Column[Any]]) -> str:
    """Narrow attribute access without ColumnCollection's dynamic-name fallback."""
    declaration = render_typed_column_class(name, columns)
    return declaration.replace("(TypedColumns):", "(Protocol):").replace("Named[", "Column[")


def render_typed_columns(metadata: MetaData, names: Iterable[str], revision: str) -> str:
    """Generate declarations and typed views of existing model-owned Core tables."""
    out = [
        '"""Generated model column surfaces; '
        'python -m corpus_structure.semantic.typed_generation."""',
        "",
        "from __future__ import annotations",
        "",
        "from datetime import date, datetime, time",
        "from decimal import Decimal",
        "",
        "from typing import Protocol, cast",
        "",
        "from pydantic import JsonValue",
        "from sqlalchemy import Column, Named, TypedColumns",
        "",
        "from .metadata import table",
        "",
        f"PHYSICAL_MODEL_ID = {revision!r}",
    ]
    for fullname in names:
        source = metadata.tables[fullname]
        variable = fullname.replace(".", "_")
        class_name = "".join(part.title() for part in variable.split("_")) + "Columns"
        out += [
            "",
            "",
            render_typed_column_class(class_name, source.columns).rstrip(),
            "",
            "",
            render_typed_column_protocol(class_name + "Set", source.columns).rstrip(),
            "",
            "",
            f"{variable} = table({fullname!r}).with_cols({class_name})",
            f"{variable}_columns = cast({class_name}Set, {variable}.c)",
        ]
    return "\n".join(out) + "\n"
