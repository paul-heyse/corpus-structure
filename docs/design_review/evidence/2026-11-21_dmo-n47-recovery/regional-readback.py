"""Verify the generated stage regional trial using separate native reads."""

from collections import Counter
import json
from pathlib import Path

from sqlalchemy import URL, create_engine, select

from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.storage_target import acquired_target

root = Path("build/dmo01-07/n47-regional-reacquired")
def read(name):
    return json.loads((root / (name + ".json")).read_bytes())
def stage(role):
    return create_engine(URL.create(
        "postgresql+psycopg", username=role, database="corpus_structure_ddo_stage",
        query={"host": "/var/run/postgresql", "port": "5434"},
    ))
registration = read("registered")
held = read("withheld")
settlement = read("held-release")
final = read("final")
repeat = read("unchanged-repeat")
demand = registration["demand"]
assert final["snapshot"]["demand_id"] == repeat["snapshot"]["demand_id"] == demand
assert held["population_members"] == 2 and settlement["state"] == "released"
assert final["receipt_count"] > 0 and repeat["receipt_count"] == 0
before = held["snapshot"]
operation_by_id = {row["obligation_id"]: row["operation_id"] for row in before["obligations"]}
finished_sibling = next(
    row for row in before["uses"]
    if row["fate"] == "fulfilled" and operation_by_id[row["obligation_id"]] == "segment.sentences/source-native"
)
resumed_by_id = {row["obligation_id"]: row for row in final["snapshot"]["uses"]}
assert resumed_by_id[finished_sibling["obligation_id"]]["derivation_id"] == finished_sibling["derivation_id"]
admin, reader = stage("paul"), stage("corpus_sem_reader")
try:
    with admin.connect().execution_options(postgresql_readonly=True) as connection:
        tasks = table("ops.task")
        row = connection.execute(select(
            tasks.c.id, tasks.c.status, tasks.c.attempt, tasks.c.lease_until,
        ).where(tasks.c.id == held["held"]["task_id"])).mappings().one()
        task = dict(row)
    with reader.begin() as connection:
        assert acquired_target(connection, purpose="read").database_oid == 130661481
        final_read = DataOperationStorage(connection).read_demand_result({
            "demand_id": demand, "limit": 100, "view": "frontier",
        })
finally:
    admin.dispose()
    reader.dispose()
assert task["lease_until"] is None and task["status"] == "done" and task["attempt"] == 2
assert final_read["release_id"] == registration["release"]
assert final_read["runtime_id"] == registration["runtime"]
assert final_read["project_id"] == final["snapshot"]["project_id"]
fates = Counter(row["fate"] for row in final_read["obligations"])
assert set(fates) == {"fulfilled"}
print(json.dumps({
    "held": task, "sibling_derivation": finished_sibling["derivation_id"],
    "native_fates": dict(fates), "resume_receipts": final["receipt_count"],
    "repeat_receipts": repeat["receipt_count"],
    "read": final_read["read_id"],
}, indent=2))
