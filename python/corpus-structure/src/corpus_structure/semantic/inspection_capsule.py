"""Managed candidate custody for existing archive-3 products; opening never compiles."""

import json
from dataclasses import asdict
from hashlib import sha256

from .identity import canonical_bytes
from .types import PreparationProfile, PreparedRelease, ResolvedDependencies, SourceBundle


def make_capsule(
    bundle: SourceBundle,
    dependencies: ResolvedDependencies,
    profile: PreparationProfile,
    prepared: PreparedRelease,
) -> bytes:
    from .releases import _archive_bytes, _validate_manifest

    _validate_manifest(bundle, dependencies, profile, prepared)
    archive = _archive_bytes(bundle, dependencies, prepared)
    inputs = [
        dict(
            input_kind=kind,
            input_name=item.name,
            content=item.content.hex(),
            content_digest=item.digest,
        )
        for kind, items in (("source", bundle.sources), ("dependency", dependencies.artifacts))
        for item in items
    ]
    for kind, value in (
        ("profile", asdict(profile)),
        ("vocabulary", [asdict(v) for v in dependencies.vocabularies]),
        ("ontology_sources", list(dependencies.ontology_sources)),
    ):
        content = canonical_bytes(value)
        inputs.append(
            dict(
                input_kind=kind,
                input_name=kind,
                content=content.hex(),
                content_digest=sha256(content).hexdigest(),
            )
        )
    return canonical_bytes(
        dict(
            version=1,
            release_id=prepared.release_id,
            release=dict(
                profile=profile.version,
                prepared_bytes=archive.hex(),
                manifest_bytes=prepared.manifest.hex(),
                content_digest=sha256(archive).hexdigest(),
            ),
            inputs=inputs,
            artifacts=[
                dict(
                    artifact_name=a.kind,
                    content=a.content.hex(),
                    content_digest=a.digest,
                    media_type="application/octet-stream",
                )
                for a in prepared.artifacts
            ],
        )
    )


def open_capsule(
    content: bytes, *, digest: str, release_id: str, manifest_digest: str, artifacts_digest: str
) -> PreparedRelease:
    return open_capsule_inputs(
        content,
        digest=digest,
        release_id=release_id,
        manifest_digest=manifest_digest,
        artifacts_digest=artifacts_digest,
    )[3]


def open_capsule_inputs(
    content: bytes,
    *,
    digest: str | None,
    release_id: str | None,
    manifest_digest: str | None,
    artifacts_digest: str | None,
) -> tuple[SourceBundle, ResolvedDependencies, PreparationProfile, PreparedRelease]:
    """Authenticate the retained complete preparation, without invoking its compiler."""
    from .archive_reader import _open_release_parts_inputs
    from .releases import ReleaseConflict

    try:
        if (
            digest is None
            or release_id is None
            or manifest_digest is None
            or artifacts_digest is None
        ):
            raise ValueError(
                "retained preparation lacks exact product custody; prepare a fresh preview"
            )
        if sha256(content).hexdigest() != digest:
            raise ValueError("candidate inspection capsule digest differs")
        data = json.loads(content)
        if (
            set(data) != {"version", "release_id", "release", "inputs", "artifacts"}
            or data["version"] != 1
            or data["release_id"] != release_id
            or canonical_bytes(data) != content
        ):
            raise ValueError("unsupported candidate inspection capsule")
        row = dict(data["release"])
        row["prepared_bytes"] = bytes.fromhex(row["prepared_bytes"])
        row["manifest_bytes"] = bytes.fromhex(row["manifest_bytes"])
        if sha256(row["manifest_bytes"]).hexdigest() != manifest_digest:
            raise ValueError("candidate manifest differs")

        def decode(rows):
            return [dict(item, content=bytes.fromhex(item["content"])) for item in rows]

        opened = _open_release_parts_inputs(
            release_id, row, decode(data["inputs"]), decode(data["artifacts"])
        )
        if opened[3].artifacts_sha256 != artifacts_digest:
            raise ValueError("candidate artifact set differs")
        return opened
    except (ValueError, KeyError, TypeError) as exc:
        raise ReleaseConflict(f"cannot open candidate inspection: {exc}") from exc
