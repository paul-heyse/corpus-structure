"""Derivation conformance (coordinator decision 24): every closed-set CHECK in the migrated database
accepts each member of its model set and refuses a value outside it.

This is not an independent oracle: the CHECK and the expected members come from one model. The
independent refusals are `test_invariants.py`'s. Each CHECK is read back from the database
(`pg_get_constraintdef`) and applied to a one-column temporary table, so no other constraint of the
table takes part.
"""

from __future__ import annotations

import re

from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core import db as store
from corpus_structure.schema import model

NOT_A_MEMBER = "zz-not-a-member"


def closed_set_checks() -> list[tuple[str, str, str, list[str]]]:
    """(table, column, CHECK name, the model's members) of every closed-set CHECK."""
    loaded = model.load()
    view = loaded.system
    out = []
    for table in store.metadata.tables.values():
        cls = table.info.get("model_class")
        if cls is None or table.info.get("deferred") or table.is_view:
            continue
        for constraint in table.constraints:
            m = re.fullmatch(rf"ck_{table.name}_(\w+)_[0-9a-f]{{10}}", str(constraint.name or ""))
            if m is None or m.group(1) not in table.c:
                continue
            rng = view.induced_slot(m.group(1), cls).range
            if view.get_enum(str(rng)) is None:
                continue  # a pattern CHECK (parse_reason), not a closed set
            members = [x.text for x in model.expand_enum(view, str(rng))]
            out.append((table.fullname, m.group(1), str(constraint.name), members))
    return out


def test_every_closed_set_check_admits_exactly_its_members(db: Connection) -> None:
    checks = closed_set_checks()
    assert len(checks) > 40
    for table, column, name, members in checks:
        definition = db.execute(
            text(
                "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
                "WHERE c.conname = :n AND c.conrelid = CAST(:t AS regclass)"
            ),
            {"n": name, "t": table},
        ).scalar_one()
        with db.begin_nested():
            db.execute(
                text(
                    f'CREATE TEMP TABLE probe ("{column}" text, CONSTRAINT probe_ck '
                    f"{definition}) ON COMMIT DROP"
                )
            )
            for member in members:
                db.execute(text(f'INSERT INTO probe ("{column}") VALUES (:v)'), {"v": member})
            try:
                with db.begin_nested():
                    db.execute(
                        text(f'INSERT INTO probe ("{column}") VALUES (:v)'), {"v": NOT_A_MEMBER}
                    )
            except DBAPIError as error:
                assert getattr(error.orig, "sqlstate", None) == "23514", name
            else:
                raise AssertionError(f"{name} admits {NOT_A_MEMBER!r}")
            db.execute(text("DROP TABLE probe"))
