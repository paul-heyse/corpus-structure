"""Typed disk artifacts for exact native preparation, independent of live metadata."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, TypeAdapter, field_serializer

from .identity import canonical_bytes
from .native_objects import NativeDefinition
from .native_program_registry import ProgramManifest
from .types import SourceArtifact

if TYPE_CHECKING:
    from sqlalchemy import MetaData

    from .target_installation import TargetInstallation


FORMAT = "native-program-set-1"
_DEFINITIONS = TypeAdapter(tuple[NativeDefinition, ...])


class ProgramSetArtifact(BaseModel):
    """All replayable bytes and facts of one generated installation."""

    model_config = ConfigDict(
        extra="forbid", frozen=True, ser_json_bytes="hex", val_json_bytes="hex"
    )

    pdf_sources: tuple[SourceArtifact, ...]
    sources: tuple[SourceArtifact, ...]
    native_sources: tuple[SourceArtifact, ...]
    physical_id: str
    programs: tuple[NativeDefinition, ...]
    prerequisites: tuple[NativeDefinition, ...]
    manifest: bytes

    @field_serializer("programs", "prerequisites")
    def definitions(self, values):
        records = _DEFINITIONS.dump_python(values, mode="json")
        for record in records:
            if record["callees"] is not None:
                record["callees"].sort(key=canonical_bytes)
        return records

    @classmethod
    def capture(cls, installation: TargetInstallation):
        return cls(
            pdf_sources=installation.pdf_sources,
            sources=installation.authoring_inputs.sources,
            native_sources=installation.authoring_inputs.native_sources,
            physical_id=installation.authoring_inputs.physical_id,
            programs=installation.programs,
            prerequisites=installation.prerequisites,
            manifest=ProgramManifest.from_definitions(
                (*installation.prerequisites, *installation.programs)
            ).content,
        )

    def hydrate(self, metadata: MetaData) -> TargetInstallation:
        from .native_products import NativeAuthoringInputs
        from .target_installation import FoundationPrograms, TargetInstallation

        if self.physical_id != metadata.info["physical_model_id"]:
            raise ValueError("stored native artifact belongs to another physical model")
        manifest = ProgramManifest.from_definitions((*self.prerequisites, *self.programs))
        if manifest.content != self.manifest:
            raise ValueError("stored native program identities differ from their manifest")
        captured = {source.name: source.content for source in self.sources}
        if captured["native/program-manifest.json"] != self.manifest:
            raise ValueError("stored native program capture differs from its manifest")
        return TargetInstallation(
            metadata=metadata,
            pdf_sources=self.pdf_sources,
            authoring_inputs=NativeAuthoringInputs(
                self.sources, self.physical_id, self.native_sources, ()
            ),
            foundation=FoundationPrograms(
                captured["authoring/identity.sql"].decode(),
                captured["authoring/closure.sql"].decode(),
                captured["authoring/closure-native.sql"].decode(),
                (),
            ),
            pdf_descriptor=(),
            pdf_identity=(),
            programs=self.programs,
            prerequisites=self.prerequisites,
            rendered_only=True,
        )


@cache
def generator_identity():
    from .code_identity import capture_code_identity

    return capture_code_identity(
        Path(__file__).resolve().parents[1],
        ("corpus_structure.semantic.target_installation",),
    )


def store_key(metadata: MetaData, **options) -> bytes | None:
    from hashlib import sha256

    from corpus_structure._query_custody import capture_sources
    from corpus_structure.model.compiled import running_model

    from .file_custody import observed_file

    basis = generator_identity()
    if not basis.complete:
        return None
    root = Path(__file__).resolve().parents[1]
    paths = tuple(root / item.filename for item in basis.modules)
    capture_sources(paths)
    exact = tuple(
        (item.filename, observed_file(root / item.filename).digest) for item in basis.modules
    )

    def source(value):
        return None if value is None else (value.name, value.digest)

    return canonical_bytes(
        dict(
            format=FORMAT,
            model=running_model().identity,
            generator=basis.digest,
            source_bytes=exact,
            physical=sorted(
                (name, sha256(content).hexdigest())
                for name, content in metadata.info["physical_sources"].items()
            ),
            linkml_types=sha256(metadata.info["physical_linkml_types"]).hexdigest(),
            logical=sorted(
                (name, sha256(content).hexdigest())
                for name, content in (options["logical_sources"] or {}).items()
            ),
            pdf_actions=source(options["pdf_actions"]),
            pdf_sources=None
            if options["pdf_sources"] is None
            else tuple(map(source, options["pdf_sources"])),
            extra=tuple(map(source, options["extra_sources"])),
        )
    )


def load_installation(key: bytes, metadata: MetaData) -> TargetInstallation | None:
    from corpus_structure.cache_store import configured_store

    files = configured_store().get("programs", FORMAT, key)
    if files is None:
        return None
    try:
        if set(files) != {"programs.json"}:
            raise ValueError("stored program file inventory differs")
        artifact = ProgramSetArtifact.model_validate_json(files["programs.json"])
        return artifact.hydrate(metadata)
    except ValueError, KeyError, TypeError:
        return None


def save_installation(key: bytes, installation: TargetInstallation) -> None:
    from corpus_structure.cache_store import configured_store

    content = canonical_bytes(ProgramSetArtifact.capture(installation).model_dump(mode="json"))
    configured_store().put("programs", FORMAT, key, {"programs.json": content})
