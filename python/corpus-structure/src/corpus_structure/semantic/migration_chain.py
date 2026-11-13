"""Exact registered forward bases for deferred-deployment native authoring."""

from __future__ import annotations

import ast
import sys
from collections.abc import Generator
from contextlib import contextmanager
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import BaseModel, ConfigDict

from corpus_structure.semantic.refusals import SemanticRefusal


class NativeMigrationBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    acquired_revision: str
    predecessor: str
    revisions: tuple[str, ...]
    files: tuple[tuple[str, str], ...]
    execution_context: str


def execution_context() -> str:
    """Custody of the native helper interpretation, separate from result recipes."""
    digest = sha256(sys.version.encode())
    for package in ("alembic", "sqlalchemy", "pydantic", "psycopg"):
        digest.update((package + "=" + version(package)).encode())
    for path in sorted(Path(__file__).parent.rglob("*.py")):
        digest.update(path.relative_to(Path(__file__).parent).as_posix().encode())
        digest.update(sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def registered_base(location: Path, acquired: str, predecessor: str) -> NativeMigrationBase:
    """Read literal metadata only; never import a migration while reviewing its bytes."""
    declarations: dict[str, tuple[Path, dict[str, object]]] = {}
    files: dict[str, str] = {"env.py": sha256((location / "env.py").read_bytes()).hexdigest()}
    for path in sorted((location / "versions").glob("*.py")):
        if path.name == "__init__.py":
            continue
        fields: dict[str, object] = {}
        for node in ast.parse(path.read_bytes(), filename=path.name).body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target, value = node.targets[0], node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                target, value = node.target, node.value
            else:
                continue
            if isinstance(target, ast.Name) and (
                target.id in {"revision", "down_revision", "depends_on", "branch_labels"}
                or target.id.startswith("NATIVE_")
            ):
                if target.id in fields:
                    raise SemanticRefusal("duplicate migration metadata: " + path.name)
                try:
                    fields[target.id] = ast.literal_eval(value)
                except (ValueError, TypeError) as error:
                    raise SemanticRefusal("nonliteral migration metadata: " + path.name) from error
        revision = fields.get("revision")
        if not isinstance(revision, str) or revision in declarations:
            raise SemanticRefusal("registered migration requires unique literal revision IDs")
        declarations[revision] = path, fields
    if acquired not in declarations or predecessor not in declarations:
        raise SemanticRefusal("native authoring base is not registered")
    pending: list[str] = []
    current = predecessor
    while current != acquired:
        if current in pending or current not in declarations:
            raise SemanticRefusal("native authoring base has no unambiguous forward chain")
        pending.append(current)
        path, fields = declarations[current]
        parent = fields.get("down_revision")
        if not isinstance(parent, str) or fields.get("depends_on") or fields.get("branch_labels"):
            raise SemanticRefusal("native authoring requires a linear frozen forward chain")
        for kind in ("UPGRADE", "STATE", "ADMISSION"):
            name, digest = fields.get(f"NATIVE_{kind}_FILE"), fields.get(f"NATIVE_{kind}_SHA256")
            if not isinstance(name, str) or Path(name).name != name or not isinstance(digest, str):
                raise SemanticRefusal("pending native migration lacks frozen artifact metadata")
            content = path.with_name(name).read_bytes()
            if sha256(content).hexdigest() != digest:
                raise SemanticRefusal("registered native migration artifact differs: " + name)
            files["versions/" + name] = digest
        current = parent
    # Alembic resolves the predecessor through its ancestry even though those
    # older revisions will not execute. Do not add unrelated descendants to custody.
    ancestor: str | None = predecessor
    seen: set[str] = set()
    while ancestor is not None:
        if ancestor in seen or ancestor not in declarations:
            raise SemanticRefusal("invalid native migration resolver ancestry")
        seen.add(ancestor)
        path, fields = declarations[ancestor]
        files["versions/" + path.name] = sha256(path.read_bytes()).hexdigest()
        parent = fields.get("down_revision")
        if parent is not None and not isinstance(parent, str):
            raise SemanticRefusal("native migration resolver ancestry must be linear")
        ancestor = parent
    return NativeMigrationBase(
        acquired_revision=acquired,
        predecessor=predecessor,
        revisions=tuple(reversed(pending)),
        files=tuple(sorted(files.items())),
        execution_context=execution_context(),
    )


def verify_registered_base(location: Path, base: NativeMigrationBase) -> None:
    actual = registered_base(location, base.acquired_revision, base.predecessor)
    actual_files = dict(actual.files)
    if (
        actual.execution_context != base.execution_context
        or actual.revisions != base.revisions
        or any(actual_files.get(name) != digest for name, digest in base.files)
    ):
        raise SemanticRefusal("registered native authoring chain differs from the preview")


@contextmanager
def frozen_base_location(location: Path, base: NativeMigrationBase) -> Generator[Path]:
    """Execute only verified private copies, immune to later checkout edits/bytecode caches."""
    verify_registered_base(location, base)
    with TemporaryDirectory(prefix="ci-native-base-") as directory:
        frozen = Path(directory)
        (frozen / "versions").mkdir()
        for relative, digest in base.files:
            content = (location / relative).read_bytes()
            if sha256(content).hexdigest() != digest:
                raise SemanticRefusal(
                    "registered native authoring chain changed during acquisition"
                )
            (frozen / relative).write_bytes(content)
        yield frozen
