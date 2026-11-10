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
    from .archive_reader import open_release_parts
    from .releases import ReleaseConflict

    try:
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

        prepared = open_release_parts(
            release_id, row, decode(data["inputs"]), decode(data["artifacts"])
        )
        if prepared.artifacts_sha256 != artifacts_digest:
            raise ValueError("candidate artifact set differs")
        return prepared
    except (ValueError, KeyError, TypeError) as exc:
        raise ReleaseConflict(f"cannot open candidate inspection: {exc}") from exc
