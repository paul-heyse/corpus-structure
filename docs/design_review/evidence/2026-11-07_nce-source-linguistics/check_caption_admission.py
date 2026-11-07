"""Read-only checks of the deployed caption guard against one actual recovered view."""

import argparse
from copy import deepcopy

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

GUARD = text("""
    SELECT ops.validate_projected_table_captions(
        :build, :section, CAST(:projection AS jsonb)
    )
""")


def check(conn, view_id, pointer):
    view = conn.execute(
        text("SELECT native_build_id, section_pointer, projection FROM kb.source_view WHERE id=:id"),
        {"id": view_id},
    ).mappings().one()
    projection = view["projection"]
    params = {"build": view["native_build_id"], "section": view["section_pointer"]}

    def validate(value):
        conn.execute(GUARD, {**params, "projection": canonical_bytes(value).decode()})

    validate(projection)
    validate(projection)
    pieces = projection["pieces"]
    (caption,) = [piece for piece in pieces if piece.get("item_ref") == pointer]
    forged = deepcopy(caption)
    forged["cell_index"] = 0
    mutations = {
        "missing": [piece for piece in pieces if piece is not caption],
        "forged_rich_duplicate": [*pieces, forged],
        "before_cells": [caption, *(piece for piece in pieces if piece is not caption)],
    }
    outcomes = {"valid": "passed", "valid_retry": "passed"}
    for name, changed in mutations.items():
        try:
            with conn.begin_nested():
                validate({**projection, "pieces": changed})
        except DBAPIError as error:
            if getattr(error.orig, "sqlstate", None) != "23514":
                raise
            outcomes[name] = "refused"
        else:
            raise ValueError(f"native caption guard accepted {name}")
    return {"view_id": view_id, "caption": pointer, "outcomes": outcomes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("view_id", type=int)
    parser.add_argument("pointer")
    args = parser.parse_args()
    with open_runtime_engine(Settings(), "nce-caption-guards", purpose="maintenance") as engine:
        with read_snapshot(engine) as conn:
            print(canonical_bytes(check(conn, args.view_id, args.pointer)).decode())


if __name__ == "__main__":
    main()
