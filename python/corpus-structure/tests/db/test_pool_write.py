"""The Arrow-native writer (P0-P-3; pool and interchange §3.4, §6 "Writer"): every generated table
that holds rows round-trips losslessly through `pool.load.read_tables` (ADBC, M3's schemas) and
the existing row repository boundary, with absent versus JSON null kept. Arbitrary admitted
Arrow table writing has been retired; semantic Arrow publication is tested separately."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pyarrow as pa
import pytest
from psycopg.types.json import Jsonb
from sqlalchemy import Engine, text

from corpus_structure.core.db import legacy_metadata as store
from corpus_structure.core.db import overlay, repo
from corpus_structure.pool.load import connect, read_tables
from corpus_structure.schema import interchange


def tables_with_rows(engine: Engine) -> list[str]:
    with engine.connect() as conn:
        return [
            t.fullname
            for t in overlay.deployed(store.metadata)
            if conn.execute(text(f"SELECT EXISTS (SELECT 1 FROM {t.fullname})")).scalar()
        ]


def read_all(url: str, names: list[str]) -> dict[str, pa.Table]:
    tables = store.metadata.tables
    queries = {}
    for name in names:
        key = ", ".join(f't."{c.name}"' for c in tables[name].primary_key.columns)
        queries[name] = (f"{name} t", key)
    with connect(url) as conn:
        return read_tables(conn, queries)


@pytest.fixture
def populated(committing_db: Engine, helpers: SimpleNamespace) -> SimpleNamespace:
    """The store test world, with knowledge rows whose JSON holds a null and absent values."""
    ins = helpers.ins
    with committing_db.begin() as conn:
        w = helpers.build_world(conn)
        stm = ins(
            conn,
            "kb.entity",
            run_id=w.run,
            key="stm:" + "1" * 32,
            schema_version_id=w.schema_version,
            type="core:Statement",
            label="theorem",
            scope="global",
            kind="theorem",
        )
        ent = ins(
            conn,
            "kb.entity",
            run_id=w.run,
            key="ent:" + "2" * 32,
            schema_version_id=w.schema_version,
            type="stat:DistributionFamily",
            label="normal",
            scope="global",
            attrs={"note": None},
        )
        conn.execute(
            store.metadata.tables["kb.entity_identity"]
            .insert()
            .values(entity_id=ent, slot="stat:canonical_name", value_text="normal")
        )
        ins(
            conn,
            "kb.claim",
            run_id=w.run,
            key="clm:" + "3" * 32,
            subject_id=ent,
            predicate="stat:has_distribution",
            object_value={"t": "formula", "latex": "x"},
            schema_version_id=w.schema_version,
            qualifiers={"stat:q": None},
            statement_id=stm,
            status="accepted",
            establishment="stated",
        )
        ins(
            conn,
            "kb.claim",
            run_id=w.run,
            key="clm:" + "4" * 32,
            subject_id=stm,
            predicate="core:proves",
            object_entity_id=stm,
            schema_version_id=w.schema_version,
            status="accepted",
            establishment="stated",
        )
    url = committing_db.url.set(drivername="postgresql").render_as_string(hide_password=False)
    return SimpleNamespace(engine=committing_db, url=url, run=w.run)


def test_every_table_with_rows_round_trips_losslessly(populated: SimpleNamespace) -> None:
    names = tables_with_rows(populated.engine)
    assert {
        "meta.payload_schema",
        "ops.run",
        "ops.task",
        "kb.entity",
        "kb.claim",
        "kb.entity_identity",
    } <= set(names)
    before = read_all(populated.url, names)
    with populated.engine.begin() as conn:
        for name in reversed(names):
            conn.execute(text(f"DELETE FROM {name}"))
        for name in names:
            # This legacy reader fidelity control restores its fixture through the
            # legitimate row repository. It grants no arbitrary-table Arrow write API.
            source = before[name]
            schema = interchange.installed().tables[name]
            columns = []
            for field in source.schema:
                values = source.column(field.name).to_pylist()
                if schema.field(field.name).type == interchange.JSON:
                    values = [
                        None if value is None else Jsonb(json.loads(value)) for value in values
                    ]
                columns.append(values)
            assert (
                repo.copy_rows(
                    conn,
                    store.metadata.tables[name],
                    source.column_names,
                    list(zip(*columns, strict=True)),
                )
                == source.num_rows
            )
    after = read_all(populated.url, names)
    for name in names:
        assert after[name].equals(before[name], check_metadata=True), name
    claims = {r["key"][4:5]: r for r in after["kb.claim"].to_pylist()}
    assert claims["3"]["qualifiers"] == '{"stat:q": null}'  # a JSON null inside
    assert claims["4"]["object_value"] is None  # absent: SQL NULL, not JSON null
    entities = {r["kind"]: r for r in after["kb.entity"].to_pylist()}
    assert entities[None]["attrs"] == '{"note": null}'


def test_arbitrary_admitted_arrow_write_api_is_retired() -> None:
    from corpus_structure.pool import write

    assert not hasattr(write, "write_arrow")
    assert callable(write.publish_arrow)
