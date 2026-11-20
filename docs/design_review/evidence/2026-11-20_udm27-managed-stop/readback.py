"""Independently check the exact stage demand's task and native lease standing."""

import json
import sys

from prepare import DESTINATION
from sqlalchemy import create_engine, text

DATABASE = "corpus_structure_ddo_stage"
NATIVE_HEAD = "semantic_ddo_pe_n36"


def main(snapshot):
    report = json.loads((DESTINATION / snapshot).read_text())
    demand = report["bindings"]["demand_id"]
    assert demand.startswith("demand:")
    engine = create_engine(
        f"postgresql+psycopg://paul@/{DATABASE}?host=/var/run/postgresql&port=5434"
    )
    with engine.connect() as connection:
        stage = connection.execute(
            text(
                "SELECT current_database(), (SELECT oid FROM pg_database WHERE datname = current_database()), "
                "(SELECT version_num FROM public.semantic_alembic_version)"
            )
        ).one()
        assert tuple(stage) == (DATABASE, 130661481, NATIVE_HEAD)
        tasks = [
            dict(row)
            for row in connection.execute(
                text(
                    "SELECT id, status, attempt, lease_until, "
                    "COALESCE(lease_until > clock_timestamp(), false) AS live_lease "
                    "FROM ops.task WHERE EXISTS ("
                    "SELECT 1 FROM ops.demand_use AS use "
                    "WHERE use.demand_id=:demand AND use.request_id=task.data_request_id "
                    "AND use.generation=task.data_generation) ORDER BY id"
                ),
                {"demand": demand},
            ).mappings()
        ]
    print(json.dumps({"demand": demand, "tasks": tasks}, indent=2, default=str))
    assert tasks and not any(task["live_lease"] for task in tasks), tasks


if __name__ == "__main__":
    main(sys.argv[1])
