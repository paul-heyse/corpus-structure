"""Apply an exact descriptor metadata transition, verify native/physical parity, then stamp current WCE."""
from pathlib import Path
import json
from hashlib import sha256

from alembic import command
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine,text
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.migrations import alembic_config
from corpus_structure.semantic.native_candidate import prepare_series_candidate
from corpus_structure.semantic.native_objects import NativeObject,admit_native
from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID

folder=Path(__file__).resolve().parent
versions=Path.cwd()/"python/corpus-structure/semantic_alembic/versions"
state=json.loads((versions/"semantic_wce_target_20261106_native.json").read_text())
objects=tuple(NativeObject.from_payload(item) for item in state["desired"])
old=NativeObject.from_payload(json.loads((folder/"cutover-descriptor-before.json").read_text()))
new=next(item for item in objects if item.identity==old.identity)
def descriptor(item):
    return json.loads(item.catalog["body"].strip()[8:-8].replace("''","'"))
before,after=descriptor(old),descriptor(new)
old_inputs={item["name"]:item["sha256"] for item in before["inputs"]}
new_inputs={item["name"]:item["sha256"] for item in after["inputs"]}
assert old_inputs.keys()==new_inputs.keys()
changed={name:dict(before=old_inputs[name],after=new_inputs[name]) for name in old_inputs if old_inputs[name]!=new_inputs[name]}
assert set(changed)=={"execution/catalog.yaml","execution/implementation/capture/operation-report-schemas.json"}
assert {k:v for k,v in before.items() if k not in {"inputs","model_id"}}=={k:v for k,v in after.items() if k not in {"inputs","model_id"}}
receipt=dict(database="corpus_structure_dev",old_revision="semantic_wce_premise_20261106",head="semantic_wce_target_20261106",descriptor_inputs_changed=changed,old_execution_model=before["model_id"],execution_model=after["model_id"],descriptor_sha256=sha256(new.catalog["body"].encode()).hexdigest())
engine=create_engine("postgresql+psycopg://paul@/corpus_structure_dev?host=/var/run/postgresql&port=5434",isolation_level="REPEATABLE READ")
def counts(conn):
    return {name:conn.scalar(text("SELECT count(*) FROM "+name)) for name in ("ops.source_build","kb.source_view","kb.source_artifact","ops.run","ops.task","ops.task_result","sem.release")}
try:
    with engine.begin() as conn:
        assert conn.scalar(text("SELECT current_database()"))==receipt["database"]
        assert conn.scalar(text("SELECT version_num FROM semantic_alembic_version"))==receipt["old_revision"]
        baseline=counts(conn)
        admit_native(conn,tuple(old if item.identity==old.identity else item for item in objects))
        Operations(MigrationContext.configure(conn)).invoke(NativeTransitionOp(old,new))
        admit_native(conn,objects)
        script,authoring=prepare_series_candidate(conn,predecessor=objects,owned_authoring=True)
        assert script.upgrade_ops is not None and not script.upgrade_ops.ops
        receipt.update(native_objects_verified=len(objects),native_and_physical_diff_count=0,physical_id=PHYSICAL_MODEL_ID,counts_before=baseline,verified_before_stamp=True)
        command.stamp(alembic_config(conn),receipt["head"],purge=True)
        assert conn.scalar(text("SELECT version_num FROM semantic_alembic_version"))==receipt["head"]
        assert counts(conn)==baseline
        receipt.update(counts_after=counts(conn),data_changed=False,outcome="passed")
    (folder/"current-cutover-dev-stamp.json").write_text(json.dumps(receipt,sort_keys=True)+"\n")
    print(json.dumps(receipt),flush=True)
except BaseException as error:
    receipt.update(outcome="failed",error_type=type(error).__name__,error=str(error))
    (folder/"current-cutover-dev-stamp-failed.json").write_text(json.dumps(receipt,sort_keys=True)+"\n")
    raise
finally:
    engine.dispose()
