"""The relational compiler (`schema/relational.py`, P0-M-2): references, keys, CHECKs, rendering."""

from __future__ import annotations

import re
import types
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, MetaData, Table, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from corpus_structure.core.db import _tables
from corpus_structure.schema import model, relational

MODEL = Path(model.__file__).resolve().parents[1] / "model"


@pytest.fixture(scope="module")
def loaded() -> model.Model:
    return model.load()


@pytest.fixture(scope="module")
def compiled(loaded: model.Model) -> MetaData:
    return relational.compile_metadata(loaded.system)


def fks(table: Table) -> dict[tuple[str, ...], tuple[str, tuple[str, ...], str | None]]:
    out = {}
    for c in table.constraints:
        if isinstance(c, ForeignKeyConstraint):
            target = c.elements[0].column.table.fullname
            out[tuple(c.columns.keys())] = (
                target,
                tuple(e.column.name for e in c.elements),
                c.ondelete,
            )
    return out


# Written from D3 §3-§7 and TM §6, not from the compiler: the foreign keys whose form M2 decides.
EXPECTED_FKS = {
    "kb.claim": {
        ("schema_version_id", "run_id"): ("ops.run", ("schema_version_id", "id"), "CASCADE"),
        ("subject_id",): ("kb.entity", ("id",), None),
        ("schema_version_id", "predicate"): (
            "meta.schema_slot",
            ("schema_version_id", "name"),
            None,
        ),
        ("object_entity_id",): ("kb.entity", ("id",), None),
        ("schema_version_id", "modality"): (
            "meta.claim_modality",
            ("schema_version_id", "value"),
            None,
        ),
        ("run_id", "attribution_entity_id"): ("kb.entity", ("run_id", "id"), None),
        ("statement_id",): ("kb.entity", ("id",), None),
    },
    "kb.entity": {
        ("schema_version_id", "run_id"): ("ops.run", ("schema_version_id", "id"), "CASCADE"),
        ("scope_segment_id",): ("kb.segment", ("id",), None),
        ("schema_version_id", "kind"): (
            "meta.statement_kind",
            ("schema_version_id", "value"),
            None,
        ),
        ("run_id", "resolved_to_id"): ("kb.entity", ("run_id", "id"), None),
    },
    "kb.claim_ref": {
        ("run_id", "claim_id"): ("kb.claim", ("run_id", "id"), "CASCADE"),
        ("run_id", "target_claim_id"): ("kb.claim", ("run_id", "id"), "CASCADE"),
    },
    "kb.claim_entity_ref": {
        ("run_id", "claim_id"): ("kb.claim", ("run_id", "id"), "CASCADE"),
        ("run_id", "entity_id"): ("kb.entity", ("run_id", "id"), "CASCADE"),
    },
    "kb.entity_identity": {
        ("entity_id",): ("kb.entity", ("id",), "CASCADE"),
        ("value_entity_id",): ("kb.entity", ("id",), "CASCADE"),  # P0-C-1: with either entity
    },
    "meta.statement_kind": {
        ("schema_version_id",): ("meta.schema_version", ("id",), "CASCADE"),
    },
    "eval.citation_frame": {
        ("golden_pass_id",): ("eval.golden_pass", ("id",), "CASCADE"),
        ("parent_id",): ("eval.citation_frame", ("id",), None),
    },
}


@pytest.mark.parametrize("table", sorted(EXPECTED_FKS))
def test_the_decided_foreign_keys(compiled: MetaData, table: str) -> None:
    assert fks(compiled.tables[table]) == EXPECTED_FKS[table]


def test_every_reference_targets_the_table_its_slot_names(
    loaded: model.Model, compiled: MetaData
) -> None:
    """Every class-ranged slot of a table class is a column whose foreign key (or a composite one
    that implies it) references the table of the slot's range."""
    view = loaded.system
    by_class = {
        t.info["model_class"]: t for t in compiled.tables.values() if "model_class" in t.info
    }
    checked = 0
    for cls, table in by_class.items():
        keys = fks(table)
        for slot in view.class_induced_slots(cls):
            target = by_class.get(str(slot.range))
            if target is None:
                continue
            column = f"{slot.name}_id" if f"{slot.name}_id" in table.c else str(slot.name)
            assert column in table.c, f"{cls}.{slot.name}"
            covering = [v for k, v in keys.items() if column in k]
            assert covering, f"{cls}.{slot.name}: no foreign key"
            if any(v[0] == target.fullname for v in covering):
                checked += 1
                continue
            # a shared column (run_id, schema_version_id): a composite key implies its validity
            assert all(len(k) > 1 for k in keys if column in k), f"{cls}.{slot.name}"
            checked += 1
    assert checked > 80


def test_version_scoped_sets_are_member_tables(compiled: MetaData) -> None:
    for name in ("meta.statement_kind", "meta.claim_modality"):
        table = compiled.tables[name]
        assert [c.name for c in table.columns] == ["schema_version_id", "value", "properties"]
        assert [c.name for c in table.primary_key.columns] == ["schema_version_id", "value"]
    claim = compiled.tables["kb.claim"]
    assert not [
        c
        for c in claim.constraints
        if isinstance(c, CheckConstraint) and "modality" in str(c.sqltext)
    ]


def test_composite_targets_are_unique_keys(compiled: MetaData) -> None:
    for table in compiled.tables.values():
        for fk in table.constraints:
            if not isinstance(fk, ForeignKeyConstraint) or len(fk.columns) < 2:
                continue
            target = fk.elements[0].column.table
            wanted = {e.column.name for e in fk.elements}
            keys = [{c.name for c in target.primary_key.columns}] + [
                {c.name for c in u.columns}
                for u in target.constraints
                if isinstance(u, UniqueConstraint)
            ]
            assert wanted in keys, f"{table.fullname} {list(fk.columns.keys())}"
            assert fk.info["shared"], table.fullname


def test_every_check_is_digest_named_by_its_sql(compiled: MetaData) -> None:
    names = set()
    for table in compiled.tables.values():
        for c in table.constraints:
            if isinstance(c, CheckConstraint):
                sql = str(c.sqltext)
                m = re.fullmatch(rf"ck_{table.name}_\w+_([0-9a-f]{{10}})", str(c.name))
                assert m, c.name
                assert m.group(1) == relational.digest(sql)
                assert len(str(c.name)) <= 63
                names.add(str(c.name))
    assert len(names) > 50


def test_a_changed_member_list_is_a_new_check_name(tmp_path: Path) -> None:
    text = (MODEL / "system.yaml").read_text(encoding="utf-8")
    seeded = text.replace(
        "      awaiting_agent: {}\n", "      awaiting_agent: {}\n      paused: {}\n", 1
    )
    assert seeded != text
    (tmp_path / "system.yaml").write_text(seeded, encoding="utf-8")
    (tmp_path / "core.yaml").write_text((MODEL / "core.yaml").read_text(), encoding="utf-8")
    before = relational.compile_metadata(model.load().system)
    after = relational.compile_metadata(
        model.load(tmp_path / "core.yaml", tmp_path / "system.yaml").system
    )

    def names(md: MetaData) -> set[str]:
        return {
            str(c.name)
            for t in md.tables.values()
            for c in t.constraints
            if isinstance(c, CheckConstraint)
        }

    changed = names(before) ^ names(after)
    assert changed and all(n.startswith(("ck_run_status_", "ck_task_status_")) for n in changed)


def test_compiling_is_deterministic(loaded: model.Model, compiled: MetaData) -> None:
    again = relational.compile_metadata(loaded.system)
    assert relational.render(again, "x") == relational.render(compiled, "x")


def ddl(md: MetaData) -> dict[str, list[str]]:
    """Each table's CREATE TABLE lines, sorted (constraints are a set on `Table`)."""
    d = postgresql.dialect()
    return {
        n: sorted(
            line.strip().rstrip(",") for line in str(CreateTable(t).compile(dialect=d)).splitlines()
        )
        for n, t in md.tables.items()
    }


def test_the_rendered_module_builds_the_compiled_metadata(compiled: MetaData) -> None:
    namespace = types.ModuleType("rendered")
    exec(compile(relational.render(compiled, "x"), "<rendered>", "exec"), namespace.__dict__)
    rendered: Any = namespace
    assert ddl(rendered.metadata) == ddl(compiled)
    # and the checked-in module is that rendering (the drift test checks its bytes)
    generated = {n: t for n, t in _tables.metadata.tables.items() if not t.is_view}
    assert set(generated) == set(compiled.tables)


def _seeded_error(tmp_path: Path, old: str, new: str, count: int = 1) -> list[str]:
    text = (MODEL / "system.yaml").read_text(encoding="utf-8")
    assert text.count(old) >= 1, old
    (tmp_path / "system.yaml").write_text(text.replace(old, new, count), encoding="utf-8")
    (tmp_path / "core.yaml").write_text((MODEL / "core.yaml").read_text(), encoding="utf-8")
    with pytest.raises(model.ModelError) as err:
        relational.compile_metadata(
            model.load(tmp_path / "core.yaml", tmp_path / "system.yaml").system
        )
    return err.value.problems


def test_a_class_named_like_an_enum_is_refused(tmp_path: Path) -> None:
    problems = _seeded_error(tmp_path, "EvalGoldenPass", "GoldenPass", count=-1)
    assert any("a class and an enum share the name" in p for p in problems)


def test_ci_same_without_the_target_key_is_refused(tmp_path: Path) -> None:
    problems = _seeded_error(tmp_path, "        - id\n        - schema_version\n", "        - id\n")
    assert any("has no unique key (schema_version, id)" in p for p in problems)


def test_ci_same_naming_a_missing_slot_is_refused(tmp_path: Path) -> None:
    problems = _seeded_error(tmp_path, "          ci:same: run\n", "          ci:same: rum\n")
    assert any("ci:same rum is not a slot" in p for p in problems)
