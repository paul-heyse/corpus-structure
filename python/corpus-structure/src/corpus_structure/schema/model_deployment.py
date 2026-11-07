"""Bind an authored candidate to a reviewed model, installed revision and storage target."""

from __future__ import annotations

import json
from collections.abc import Callable, Generator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from corpus_structure.schema.model import ModelError
from corpus_structure.schema.model_change import ChangePreview, checked_path, generator_fingerprint
from corpus_structure.settings import Settings


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace: str
    model_revision: str
    generator: str
    revision: str | None
    predecessor: str | None
    target: str
    release: str
    packs: tuple[str, ...]
    files: dict[str, str | None]
    hashes: dict[str, str]

    @classmethod
    def from_preview(
        cls, preview: ChangePreview, revision: str | None, release: str, products: dict[str, bytes]
    ) -> Candidate:
        if not preview.target or bool(revision) != bool(preview.request.native_predecessor):
            raise ModelError(
                ["candidate requires a target and matching native revision/predecessor"]
            )
        if preview.local_release != release:
            raise ModelError(["prepared release identity differs from the reviewed preview"])
        return cls(
            workspace=preview.workspace,
            model_revision=preview.revision,
            generator=preview.generator,
            revision=revision,
            predecessor=preview.request.native_predecessor,
            target=preview.target,
            release=release,
            packs=preview.request.packs,
            files={
                **preview.inputs,
                **{
                    effect.path: sha256(effect.after.encode()).hexdigest()
                    for effect in preview.files
                },
            },
            hashes={name: sha256(content).hexdigest() for name, content in products.items()},
        )


def target_fingerprint(settings: Settings) -> str:
    """Identify the configured endpoint without copying role credentials into a result."""
    from sqlalchemy.engine import make_url

    source = make_url(settings.database.url)
    if source.database in {
        None,
        "",
        "postgres",
        "template0",
        "template1",
        settings.database.template,
    }:
        raise ModelError(["model effects require an explicit non-system, non-template database"])
    query = {
        key: value
        for key, value in source.query.items()
        if key not in {"user", "password", "passfile"}
    }
    data = [source.database, source.host, source.port, query]
    return sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


@contextmanager
def predecessor_fence(settings: Settings, target: str, predecessor: str) -> Generator[None]:
    from corpus_structure.semantic.migrations import current_revision, migration_fence
    from corpus_structure.semantic.runtime import open_runtime_engine

    if target_fingerprint(settings) != target:
        raise ModelError(["configured target differs from the model preview"])
    with (
        open_runtime_engine(settings, "ci-model-predecessor", purpose="maintenance") as engine,
        engine.begin() as conn,
    ):
        migration_fence(conn)
        if current_revision(conn) != predecessor:
            raise ModelError(["installed native predecessor differs from the model preview"])
        yield


def verify_predecessor(settings: Settings, target: str, predecessor: str) -> None:
    with predecessor_fence(settings, target, predecessor):
        pass


def _verify_installed_revision(binding: Candidate) -> None:
    """Only the repository migration owner may execute an admitted frozen revision."""
    from alembic.script import ScriptDirectory
    from alembic.util.exc import CommandError

    from corpus_structure.semantic.migrations import alembic_config

    if binding.revision is None:
        return
    scripts = ScriptDirectory.from_config(alembic_config())
    try:
        script = scripts.get_revision(binding.revision)
    except CommandError as error:
        raise ModelError(
            ["install the registered revision with its frozen candidate artifacts"]
        ) from error
    if (
        script is None
        or script.revision != binding.revision
        or script.down_revision != binding.predecessor
    ):
        raise ModelError(
            ["installed migration differs from the exact candidate revision and predecessor"]
        )
    for kind, product in (
        ("UPGRADE", "native_candidate.py"),
        ("STATE", "native_operations.json"),
        ("ADMISSION", "native_admission.sql"),
    ):
        name = getattr(script.module, f"NATIVE_{kind}_FILE", None)
        digest = getattr(script.module, f"NATIVE_{kind}_SHA256", None)
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or digest != binding.hashes.get(product)
        ):
            raise ModelError([f"installed migration does not bind the candidate's {product}"])
        content = Path(script.path).with_name(name).read_bytes()
        if sha256(content).hexdigest() != digest:
            raise ModelError([f"installed migration artifact differs: {name}"])


def deploy_candidate(
    root: Path,
    settings: Settings,
    binding: Candidate,
    deployment: tuple,
    *,
    report: Callable[[str], None],
) -> None:
    from corpus_structure.semantic.authored_sql import (
        admit_archived_sql,
        analyze_archived_sql,
        has_authored_sql,
    )
    from corpus_structure.semantic.migrations import current_revision, migration_fence, upgrade
    from corpus_structure.semantic.publication import admit_release
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.releases import open_release, persist_release
    from corpus_structure.semantic.runtime import open_runtime_engine

    if str(root) != binding.workspace or generator_fingerprint(root) != binding.generator:
        raise ModelError(["candidate belongs to another workspace or generator"])
    if target_fingerprint(settings) != binding.target:
        raise ModelError(["configured deployment target differs from the candidate"])
    for relative, expected in binding.files.items():
        file = checked_path(root, relative)
        actual = sha256(file.read_bytes()).hexdigest() if file.exists() else None
        if actual != expected:
            raise ModelError([f"candidate input has changed: {relative}"])
    bundle, deps, profile, prepared = deployment
    if prepared.release_id != binding.release:
        raise ModelError(["prepared release identity differs from the candidate"])
    _verify_installed_revision(binding)
    with (
        open_runtime_engine(settings, "ci-model-migrate", purpose="maintenance") as maintenance,
        maintenance.connect() as conn,
    ):
        if binding.revision is not None:
            with conn.begin():
                upgrade(conn, binding.revision, expected_predecessor=binding.predecessor)
            report("migration")
        with conn.begin():
            migration_fence(conn)
            if binding.revision is not None and current_revision(conn) != binding.revision:
                raise ModelError(["native revision changed before archive/admission"])
            with open_runtime_engine(settings, "ci-model-admit", purpose="admit") as admission:
                with admission.begin() as writer:
                    persist_release(writer, bundle, deps, profile, prepared)
                report("archive")
                with open_runtime_engine(settings, "ci-model-verify", purpose="read") as reader:
                    if has_authored_sql(prepared):
                        with reader.connect() as sql_connection:
                            analyzed = analyze_archived_sql(sql_connection, binding.release)
                    else:
                        analyzed = None
                    with admission.begin() as writer:
                        if analyzed is not None:
                            admit_archived_sql(writer, binding.release, analyzed=analyzed)
                        admit_release(prepared, connection=writer)
                    report("admission")
                    with read_snapshot(reader) as snapshot:
                        if open_release(snapshot, binding.release).release_id != binding.release:
                            raise ModelError(["admitted release does not match the candidate"])
                    report("verified")
