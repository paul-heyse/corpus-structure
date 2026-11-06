"""Exercise the consolidated forward migration and compare its complete declared native/physical state."""
from pathlib import Path
import json
import sys
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from corpus_structure.semantic.native_candidate import prepare_series_candidate
from corpus_structure.semantic.native_objects import NativeObject, admit_native
from corpus_structure.settings import Settings

root=Path.cwd()
sys.path.insert(0,str(root/"scripts"))
from native_test_support import PgAdmin
folder=Path(__file__).resolve().parent
versions=Path(sys.argv[1]).resolve()
state=json.loads((versions/"semantic_wce_target_20261106_native.json").read_text())
objects=tuple(NativeObject.from_payload(item) for item in state["desired"])
server=PgAdmin("postgresql+psycopg://paul@/corpus_structure_dev?host=/var/run/postgresql&port=5434","cs_template",settings=Settings())
name="cs_wce_current_"+uuid4().hex[:12]
with server.database(name,"cs_template",policy=server.policy("corpus_structure_dev")) as engine:
    with engine.begin() as conn:
        cfg=Config();cfg.set_main_option("script_location",str(versions.parent));cfg.attributes["connection"]=conn
        command.upgrade(cfg,"semantic_wce_target_20261106")
        assert conn.scalar(text("SELECT version_num FROM semantic_alembic_version"))=="semantic_wce_target_20261106"
        admit_native(conn,objects)
        script,authoring=prepare_series_candidate(conn,predecessor=objects,owned_authoring=True)
        assert script.upgrade_ops is not None
        for item in script.upgrade_ops.ops:
            print("REMAINING",type(item).__name__,getattr(item,"identity",None),getattr(item,"sqltext",None),getattr(item,"table_name",None),flush=True)
        assert not script.upgrade_ops.ops
        result=dict(outcome="passed",database=name,head="semantic_wce_target_20261106",native_objects=len(objects),native_and_physical_diff_count=0,server=conn.scalar(text("SELECT version()")))
    (folder/"current-cutover-fresh-migration.json").write_text(json.dumps(result,sort_keys=True)+"\n")
    print(json.dumps(result),flush=True)
print("isolated verification database disposed",flush=True)
