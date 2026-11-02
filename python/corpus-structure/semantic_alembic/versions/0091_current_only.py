"""Frozen current-only runtime and physical retirement.

Replace current guards/read views before dropping the 36 retired stored relations.
All artifact payloads are digest checked; deployment never invokes current generators.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import (
    NativeObject,
    admit_native,
    execute_native_sql,
    native_owner,
)

revision = "semantic_current_only_20261102"
down_revision = "semantic_pdf_header_20261102"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_current_only_20261102_native.json"
NATIVE_STATE_SHA256 = "62ea19ee6ffec10aadf8b8fbd675f225bd54615137784243842ccb37238d8486"
NATIVE_ADMISSION_FILE = "semantic_current_only_20261102_admission.sql"
NATIVE_ADMISSION_SHA256 = "a73cb6ab838a1f8f36a482f439a89a47ad1e410c1e6ce2ecd85515633f5b3ee8"
PHYSICAL_BEFORE_FILE = "semantic_current_only_20261102_before.sql"
PHYSICAL_BEFORE_SHA256 = "f3adb0bb17641038ec1431835ffcfc54e5570d12bfc8f083165daa6ce5a22326"
PHYSICAL_RETIRE_FILE = "semantic_current_only_20261102_retire.sql"
PHYSICAL_RETIRE_SHA256 = "f3fa3d78826fb848ca6168c7b5b6d2f93dc091337c7c12eb98d716b483b249ef"
PHYSICAL_RECEIPT_FILE = "semantic_current_only_20261102_physical.sql"
PHYSICAL_RECEIPT_SHA256 = "130e6ec13cfd82c82b5200bc7fd815f48673c05325f983205db0242347b5b004"


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen current-only artifact differs: " + name)
    return content


def upgrade() -> None:
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    before = _read_artifact(PHYSICAL_BEFORE_FILE, PHYSICAL_BEFORE_SHA256).decode()
    retire = _read_artifact(PHYSICAL_RETIRE_FILE, PHYSICAL_RETIRE_SHA256).decode()
    physical = _read_artifact(PHYSICAL_RECEIPT_FILE, PHYSICAL_RECEIPT_SHA256).decode()
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen current-only native state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    transitions = tuple(NativeTransitionOp.from_payload(item) for item in state["operations"])
    connection = op.get_bind()
    execute_native_sql(connection, before)
    operations = Operations(op.get_context())
    for transition in transitions:
        operations.invoke(transition)
    execute_native_sql(connection, retire)
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, physical)
    admit_native(connection, desired)


def downgrade() -> None:
    raise RuntimeError("current-only downgrade refused; rebuild owned realization")
