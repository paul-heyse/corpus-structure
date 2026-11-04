"""Materialize a new draft forward revision from the prospective authoring products."""
import ast
import sys
import json
from hashlib import sha256
from pathlib import Path

root = Path.cwd()
source = Path(__file__).with_name(sys.argv[1] if len(sys.argv)>1 else "candidate-002")
versions = root / "python/corpus-structure/semantic_alembic/versions"
state_bytes = (source / "native_operations.json").read_bytes()
admission = (source / "native_admission.sql").read_bytes()
state = json.loads(state_bytes)
module = ast.parse((source / "native_candidate.py").read_text())
index = 0
physical_sql = None
class ExternalizeNative(ast.NodeTransformer):
    def visit_Call(self, node):
        global index, physical_sql
        if (isinstance(node.func, ast.Attribute) and node.func.attr == "execute"
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "op"
            and len(node.args) == 1 and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value.startswith("INSERT INTO sem.physical_contract")):
            assert physical_sql is None
            physical_sql = node.args[0].value.encode("utf-8")
            node.args[0] = ast.parse('_read(PHYSICAL_STATE_FILE,PHYSICAL_STATE_SHA256).decode("utf-8")', mode="eval").body
        if isinstance(node.func, ast.Attribute) and node.func.attr == "native_transition":
            assert isinstance(node.func.value, ast.Name) and node.func.value.id == "op"
            replacement = ast.parse(f'Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][{index}]))', mode="eval").body
            index += 1
            return replacement
        return self.generic_visit(node)
ExternalizeNative().visit(module)
assert index == len(state["operations"])
assert physical_sql is not None
function = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "upgrade")
function.body[0:0] = ast.parse('''state = json.loads(_read(NATIVE_STATE_FILE,NATIVE_STATE_SHA256))
_read(NATIVE_ADMISSION_FILE,NATIVE_ADMISSION_SHA256)
if state["predecessor"] != down_revision or state["version"] != 1:
    raise RuntimeError("incompatible audit-closure native predecessor")
''').body
function.body.extend(ast.parse('''admit_native(op.get_bind(),tuple(NativeObject.from_payload(item) for item in state["desired"]))''').body)
header = f'''"""Audit-closure semantic authority and immutable split decisions; forward from frozen101.

Native and physical sidecars are hash-bound; the owning plan records qualification scope.
"""
import json
from pathlib import Path
from hashlib import sha256
from corpus_structure.semantic.native_objects import NativeObject, admit_native
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from alembic.operations import Operations

revision = "semantic_audit_closure_20261103"
down_revision = "semantic_m1_records_20261103"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_audit_closure_20261103_native.json"
NATIVE_STATE_SHA256 = "{sha256(state_bytes).hexdigest()}"
NATIVE_ADMISSION_FILE = "semantic_audit_closure_20261103_admission.sql"
NATIVE_ADMISSION_SHA256 = "{sha256(admission).hexdigest()}"
PHYSICAL_STATE_FILE = "semantic_audit_closure_20261103_physical.sql"
PHYSICAL_STATE_SHA256 = "{sha256(physical_sql).hexdigest()}"

def _read(name,digest):
    content=Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest()!=digest:
        raise RuntimeError("audit-closure native artifact differs: "+name)
    return content
'''
code = header + "\n" + ast.unparse(ast.fix_missing_locations(module)) + '''\n\ndef downgrade():
    raise RuntimeError("destructive audit-closure downgrade refused; rebuild an owned database")
'''
combined=ast.parse(code)
combined.body=[combined.body[0],*[n for n in combined.body[1:] if isinstance(n,(ast.Import,ast.ImportFrom)) and not (isinstance(n,ast.ImportFrom) and n.module=="corpus_structure.semantic" and any(a.name=="alembic_native" for a in n.names))],*[n for n in combined.body[1:] if not isinstance(n,(ast.Import,ast.ImportFrom))]]
code=ast.unparse(ast.fix_missing_locations(combined))+"\n"
for relation in ("data.scientific_representative", "data.entity_resolution"):
    prefix = "GRANT SELECT ON " + relation + " TO "
    roles = "corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    code = code.replace(repr(prefix + roles), repr(prefix) + "\n        " + repr(roles))
compile(code, "0102_audit_closure.py", "exec")
(versions / "0102_audit_closure.py").write_text(code)
(versions / "semantic_audit_closure_20261103_native.json").write_bytes(state_bytes)
(versions / "semantic_audit_closure_20261103_admission.sql").write_bytes(admission)
(versions / "semantic_audit_closure_20261103_physical.sql").write_bytes(physical_sql)
p = root / "python/corpus-structure/src/corpus_structure/semantic/execution_admission.py"
text = p.read_text()
import re
for name, constant in [("execution_contract_descriptor","_DESCRIPTOR_SHA256"),("require_execution_release","_REQUIRE_SHA256")]:
    item=next(x for x in state["desired"] if x["identity"]["schema"]=="data" and x["identity"]["name"]==name)
    digest=sha256(item["catalog"]["body"].encode()).hexdigest()
    text=re.sub(rf'{constant} = "[a-f0-9]+"', f'{constant} = "{digest}"', text)
text=text.replace("# Frozen from reviewed migration ASTs through semantic_m1_private_20261103.","# Frozen from reviewed audit-closure forward artifacts; historical wrappers stay immutable.")
p.write_text(text)
print({"draft_revision": "semantic_audit_closure_20261103", "native_operations": index})
