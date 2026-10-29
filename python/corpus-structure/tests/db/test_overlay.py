"""The physical overlay binds to the generated tables by name and fails at import (P0-M-2)."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest
from sqlalchemy import ForeignKeyConstraint

from corpus_structure.core import db
from corpus_structure.core.db import overlay

TABLES = Path(db.__file__).resolve().parent / "_tables.py"


def seeded_tables(old: str, new: str) -> types.ModuleType:
    """`_tables.py` with one seeded edit, as a module of its own."""
    text = TABLES.read_text(encoding="utf-8")
    assert text.count(old) == 1, old
    module = types.ModuleType("corpus_structure.core.db._tables")
    exec(compile(text.replace(old, new), str(TABLES), "exec"), module.__dict__)
    return module


TS_CONFIG = (
    '    Column("ts_config", REGCONFIG(), nullable=False, '
    "server_default=text(\"'english'::regconfig\")),\n"
)


def test_importing_the_overlay_fails_on_a_missing_column(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        sys.modules, "corpus_structure.core.db._tables", seeded_tables(TS_CONFIG, "")
    )
    monkeypatch.delitem(sys.modules, "corpus_structure.core.db.overlay")
    monkeypatch.setattr(db, "_tables", sys.modules["corpus_structure.core.db._tables"])
    # the freshly imported module defines its own OverlayBindingError, a LookupError
    with pytest.raises(LookupError, match=r"no column kb\.segment\.ts_config") as err:
        importlib.import_module("corpus_structure.core.db.overlay")
    assert type(err.value).__name__ == "OverlayBindingError"


def test_a_missing_table_fails() -> None:
    module = seeded_tables('    "task",\n    metadata,\n', '    "task_renamed",\n    metadata,\n')
    with pytest.raises(overlay.OverlayBindingError, match=r"no table ops\.task"):
        overlay.apply(module.metadata)


def test_a_composite_foreign_key_without_a_supporting_index_fails() -> None:
    module = seeded_tables(TS_CONFIG, TS_CONFIG)
    claim = module.metadata.tables["kb.claim"]
    claim.append_constraint(
        ForeignKeyConstraint(
            ["run_id", "object_entity_id"],
            ["kb.entity.run_id", "kb.entity.id"],
            info={"shared": ("run_id",)},
        )
    )
    overlay.indexes(module.metadata)  # claim_object (run_id, object_entity_id) supports it
    assert overlay.unsupported_foreign_keys(module.metadata) == []
    fresh = seeded_tables(TS_CONFIG, TS_CONFIG)  # no index leads with confidence
    fresh.metadata.tables["kb.claim"].append_constraint(
        ForeignKeyConstraint(
            ["run_id", "confidence"],
            ["kb.entity.run_id", "kb.entity.confidence"],
            info={"shared": ("run_id",)},
        )
    )
    with pytest.raises(overlay.OverlayBindingError, match=r"kb\.claim \(run_id, confidence\)"):
        overlay.apply(fresh.metadata)


def test_every_composite_foreign_key_is_supported() -> None:
    assert overlay.unsupported_foreign_keys(db.metadata) == []
    composite = [
        (t.fullname, tuple(c.columns.keys()))
        for t in db.metadata.tables.values()
        for c in t.constraints
        if isinstance(c, ForeignKeyConstraint) and len(c.columns) > 1
    ]
    assert len(composite) == 11  # 4 same-run, 2 ties, 3 version-scoped, 2 edge claim ids


def test_the_bm25_predicate_is_the_search_block_kinds() -> None:
    from corpus_structure.core._model.sql import SEARCH_BLOCK

    (index,) = [i for i in db.OVERLAY.indexes if i.name == "segment_bm25"]
    where = str(
        index.dialect_options["postgresql"]["where"].compile(compile_kwargs={"literal_binds": True})
    )
    assert all(f"'{k}'" in where for k in SEARCH_BLOCK)
    assert index.dialect_options["postgresql"]["using"] == "bm25"


def test_views_are_marked_for_include_object() -> None:
    assert {v.fullname for v in db.OVERLAY.views} == {
        "kb.run_observation",
        "ops.run_measurement",
        "kb.run_rendition",
    }
    for view in db.OVERLAY.views:
        assert view.is_view and view.info["is_view"] is True
        assert view.fullname in db.metadata.tables
