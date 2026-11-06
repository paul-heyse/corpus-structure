"""Author the single current WCE cutover against a genuinely migrated, isolated 155 database."""
from pathlib import Path
import json
import subprocess
import sys
from uuid import uuid4

root = Path.cwd()
sys.path.insert(0, str(root / "scripts"))
from native_test_support import PgAdmin
from corpus_structure.semantic.migrations import current_revision, upgrade
from corpus_structure.settings import Settings

folder = Path(__file__).resolve().parent
server = PgAdmin("postgresql+psycopg://paul@/corpus_structure_dev?host=/var/run/postgresql&port=5434", "cs_template", settings=Settings())
outname = sys.argv[1] if len(sys.argv)>1 else "native-candidate-current-cutover"
name = "cs_wce_cutover_155_" + uuid4().hex[:12]
policy = server.policy("corpus_structure_dev")
with server.database(name, "cs_template", policy=policy) as engine:
    with engine.begin() as conn:
        applied = upgrade(conn, "semantic_wce_roles_20261106")
        assert current_revision(conn) == "semantic_wce_roles_20261106"
    print("isolated155 ready: " + name, flush=True)
    command = [str(Path(sys.executable).with_name("ci")), "schema", "native-candidate", "--authoring-database", name, "--out", str(folder / outname), "--json"]
    with (folder / (outname+".log")).open("wb") as output:
        result = subprocess.run(command, cwd=root, stdout=output, stderr=subprocess.STDOUT)
    (folder / (outname+"-authoring.json")).write_text(json.dumps(dict(database=name, predecessor="semantic_wce_roles_20261106", migration_count=len(applied), candidate_returncode=result.returncode, persistent_database_changed=False), sort_keys=True)+"\n")
    result.check_returncode()
print("isolated authoring database disposed", flush=True)
