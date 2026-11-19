"""Current read-boundary reconstruction from exact archived products.

Opening is not compilation or admission. Archived recipes retain their exact meaning.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any

import yaml
from cattrs.errors import BaseValidationError
from pydantic import AwareDatetime

from corpus_structure.caches import declare

from .types import (
    BOUNDARY_ABI_VERSION,
    SEMANTIC_ARCHIVE_FORMAT,
    SEMANTIC_PROFILE_VERSIONS,
    PreparationProfile,
    PreparedArtifact,
    PreparedRelease,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)


def retained_archive_bytes(parts) -> int:
    bundle, dependencies, _, prepared = parts
    return max(
        1,
        len(prepared.manifest)
        + sum(
            len(artifact.content)
            for artifact in (*bundle.sources, *dependencies.artifacts, *prepared.artifacts)
        ),
    )


_PRIMITIVES: dict[str, Any] = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "float": float,
    "double": float,
    "decimal": Decimal,
    "date": date,
    "datetime": AwareDatetime,
    "uri": str,
    "uriorcurie": str,
}


def reconstruct_release(
    products: Any,
    manifest: bytes,
    bundle: SourceBundle,
    profile: PreparationProfile,
    artifacts: tuple[PreparedArtifact, ...],
) -> PreparedRelease:
    """Hydrate a supported archived ABI without preparing or admitting its release."""
    from .archive_wire import ArchiveProducts, decode_products
    from .boundary import build_boundary_adapters
    from .identity import canonical_bytes
    from .types import SEMANTIC_COMPILER_VERSION

    if profile.compiler_version != SEMANTIC_COMPILER_VERSION:
        raise ValueError(f"unsupported archived compiler {profile.compiler_version}")

    products = products if isinstance(products, ArchiveProducts) else decode_products(products)
    definitions = products.definitions
    vocabularies = products.vocabularies
    rows = tuple(row.semantic_row() for row in products.registry_rows)
    if len({(r.kind, r.name) for r in rows}) != len(rows):
        raise ValueError("duplicate archived registry rows")
    artifact_map = {artifact.kind: artifact for artifact in artifacts}
    descriptors = {item.kind: item for item in products.artifacts}
    if (
        len(artifact_map) != len(artifacts)
        or len(descriptors) != len(products.artifacts)
        or descriptors.keys() != artifact_map.keys()
    ):
        raise ValueError("duplicate or missing archived artifacts")
    for expected in products.artifacts:
        if artifact_map[expected.kind].digest != expected.digest:
            raise ValueError("archived artifact digest differs")
    fragments = (
        json.loads(artifact_map["conditional_rules.json"].content)
        if "conditional_rules.json" in artifact_map
        else {}
    )
    recipe = json.loads(artifact_map["boundary_recipe.json"].content)
    if (
        set(recipe) != {"abi", "primitives", "aliases", "descendants", "conditional_scope"}
        or recipe["abi"] != "semantic-boundary-" + BOUNDARY_ABI_VERSION
    ):
        raise ValueError("unsupported archived boundary ABI")
    if recipe["conditional_scope"] != profile.constraint_scope:
        raise ValueError("archived boundary placement differs from profile")
    primitive_types = {name: _PRIMITIVES[token] for name, token in recipe["primitives"].items()}
    aliases = {
        (cls, slot): alias
        for cls, fields in recipe["aliases"].items()
        for slot, alias in fields.items()
    }
    descendants = {name: tuple(items) for name, items in recipe["descendants"].items()}
    models = {}

    def check_schema(name, adapter):
        actual_schema = json.loads(canonical_bytes(adapter.json_schema()))
        expected_schema = json.loads(artifact_map[f"json_schema/{name}"].content)
        if actual_schema != expected_schema:

            def difference(actual: Any, expected: Any, path: str = "") -> str:
                if isinstance(actual, dict) and isinstance(expected, dict):
                    if actual.keys() != expected.keys():
                        return path + ": keys " + repr(sorted(actual.keys() ^ expected.keys()))
                    for key in actual:
                        if actual[key] != expected[key]:
                            return difference(actual[key], expected[key], path + "/" + key)
                if isinstance(actual, list) and isinstance(expected, list):
                    for index, (left, right) in enumerate(zip(actual, expected, strict=False)):
                        if left != right:
                            return difference(left, right, path + "/" + str(index))
                return path + ": " + repr(actual)[:100] + " != " + repr(expected)[:100]

            raise ValueError(
                f"archived boundary schema differs for {name}: "
                f"{difference(actual_schema, expected_schema)}"
            )

    def load_adapter(name):
        staged_models = dict(models)
        built = dict(
            build_boundary_adapters(
                definitions,
                vocabularies,
                primitive_types=primitive_types,
                aliases=aliases,
                conditional_fragments=fragments,
                conditional_scope=profile.constraint_scope,
                finite_fields=True,
                descendant_order=descendants,
                models_out=staged_models,
                class_names=(name,),
            )
        )
        adapter = built[name]
        check_schema(name, adapter)
        models.update(staged_models)
        return adapter

    prepared = PreparedRelease(
        release_id=products.release_id,
        manifest=manifest,
        definitions=definitions,
        vocabularies=vocabularies,
        registry_rows=rows,
        queries=products.queries,
        artifacts=artifacts,
        required_capabilities=products.required_capabilities,
        diagnostics=products.diagnostics,
        _adapters=(),
        _boundary_models=models,
        _adapter_loader=load_adapter,
    )
    from .comparison_projection import comparison_projection

    comparison_projection(prepared)
    return prepared


def _archive_header(conn: Any, release_id: str):
    """Observe finalized authority without acquiring archive or manifest payloads.

    Physical tuple markers only invalidate reuse conservatively (including administrative
    rewrites). They are neither semantic identity nor a replacement for native immutability.
    """
    from sqlalchemy import String, select

    from .native_program import core_reference
    from .releases import _table

    release = _table("sem.release").alias("archive_release")
    finalized = _table("sem.release_finalization").alias("archive_finalized")
    markers = tuple(
        core_reference(alias, name, type_=String()).cast(String()).label(f"{alias}_{name}")
        for alias in ("archive_release", "archive_finalized")
        for name in ("tableoid", "xmin", "ctid")
    )
    return conn.execute(
        select(
            release.c.release_id,
            release.c.profile,
            release.c.content_digest,
            finalized.c.content_digest.label("finalized_digest"),
            *markers,
        )
        .select_from(release.outerjoin(finalized, finalized.c.release_id == release.c.release_id))
        .where(release.c.release_id == release_id)
    ).one_or_none()


def open_release_parts(
    release_id: str, row: Any, input_rows: Any, artifact_rows: Any
) -> PreparedRelease:
    """Authenticate exact archive parts before hydration, independent of storage transport."""
    return _open_release_parts_inputs(release_id, row, input_rows, artifact_rows)[3]


def _open_release_parts_inputs(release_id: str, row: Any, input_rows: Any, artifact_rows: Any):
    """Keep authenticated original inputs beside the reconstructed products."""

    from .determinants import boundary_compatible
    from .releases import ReleaseConflict, _archive_bytes, _digest

    try:
        archive_bytes, manifest_bytes = bytes(row["prepared_bytes"]), bytes(row["manifest_bytes"])
        if _digest(archive_bytes) != row["content_digest"]:
            raise ReleaseConflict("archive digest differs")
        if release_id != "release:" + _digest(manifest_bytes):
            raise ReleaseConflict("archive or manifest identity differs")
        archive, manifest = json.loads(archive_bytes), json.loads(manifest_bytes)
        if archive["format"] != SEMANTIC_ARCHIVE_FORMAT:
            raise ReleaseConflict("unsupported archive format")
        if not boundary_compatible(
            manifest["libraries"], str(manifest["profile"]["compiler_version"])
        ):
            raise ReleaseConflict("archived boundary library versions differ")
        from .archive_wire import decode_products, decode_vocabularies

        products = decode_products(archive["products"])
        source: dict[tuple[str, str], bytes] = {}
        for item in input_rows:
            content = bytes(item["content"])
            if _digest(content) != item["content_digest"]:
                raise ReleaseConflict("input digest differs")
            key = item["input_kind"], item["input_name"]
            if key in source:
                raise ReleaseConflict("duplicate archived input")
            source[key] = content
        bundle = SourceBundle(
            archive["root"],
            tuple(SourceArtifact(name, source["source", name]) for name in archive["sources"]),
        )
        dependencies = tuple(
            SourceArtifact(name, source["dependency", name]) for name in archive["dependencies"]
        )
        if len(source) != len(bundle.sources) + len(dependencies) + 3:
            raise ReleaseConflict("unexpected archived inputs")
        profile = PreparationProfile(**json.loads(source["profile", "profile"]))
        if profile.version not in SEMANTIC_PROFILE_VERSIONS or row["profile"] != profile.version:
            raise ReleaseConflict("unsupported archived profile")
        artifacts: list[PreparedArtifact] = []
        for item in artifact_rows:
            content = bytes(item["content"])
            if (
                _digest(content) != item["content_digest"]
                or item["media_type"] != "application/octet-stream"
            ):
                raise ReleaseConflict("artifact bytes or media type differ")
            artifacts.append(PreparedArtifact(item["artifact_name"], content))
        by_name = {item.kind: item for item in artifacts}
        descriptor_names = {item.kind for item in products.artifacts}
        if (
            len(by_name) != len(artifacts)
            or len(descriptor_names) != len(products.artifacts)
            or descriptor_names != by_name.keys()
        ):
            raise ReleaseConflict("duplicate or missing archived artifacts")
        ordered = tuple(by_name[item.kind] for item in products.artifacts)
        if len(ordered) != len(artifacts):
            raise ReleaseConflict("unexpected archived artifacts")
        target_artifacts = [a for a in ordered if a.kind == "data_operations.json"]
        if target_artifacts:
            if len(target_artifacts) != 1:
                raise ReleaseConflict("ambiguous archived operation model")
            from .data_operation_model import read_effective_data_operations

            read_effective_data_operations(target_artifacts[0].content)
            interface_artifacts = [
                a for a in ordered if a.kind == "data_operation_source_interfaces.json"
            ]
            if interface_artifacts:
                if len(interface_artifacts) != 1:
                    raise ReleaseConflict("ambiguous archived source interface projection")
                from .source_interfaces import SourceInterfaceProjection

                interfaces = SourceInterfaceProjection.model_validate_json(
                    interface_artifacts[0].content
                )
                if interfaces.model_digest != _digest(target_artifacts[0].content):
                    raise ReleaseConflict("source interfaces belong to another effective model")
        prepared = reconstruct_release(products, manifest_bytes, bundle, profile, ordered)
        from .release_identity import release_manifest

        ontology_sources = tuple(json.loads(source["ontology_sources", "ontology_sources"]))
        if (
            release_manifest(
                bundle,
                ResolvedDependencies(dependencies, (), ontology_sources),
                profile,
                prepared,
                manifest["libraries"],
            )
            != manifest_bytes
        ):
            raise ReleaseConflict("archived material inputs or generated products differ")
        supplied = decode_vocabularies(json.loads(source["vocabulary", "vocabulary"]))
        if len({item.enum for item in supplied}) != len(supplied):
            raise ReleaseConflict("duplicate supplied vocabulary snapshots")
        declarations = {
            item.name: json.loads(item.body)
            for item in prepared.registry_rows
            if item.kind == "enum_definition"
        }
        resolved = {item.enum: item for item in prepared.vocabularies}
        for item in supplied:
            declaration = declarations.get(item.enum, {})
            if any(
                declaration.get(key)
                for key in ("reachable_from", "concepts", "include", "minus", "inherits")
            ) and (item.enum not in resolved or item.members != resolved[item.enum].members):
                raise ReleaseConflict(
                    "supplied dynamic vocabulary differs from resolved membership"
                )
        # The compiler uses supplied snapshots only to corroborate dynamic membership;
        # it derives local vocabulary and ontology provenance from the archived sources.
        if (
            prepared.release_id != release_id
            or _archive_bytes(bundle, ResolvedDependencies(dependencies), prepared) != archive_bytes
        ):
            raise ReleaseConflict("archived products differ")
        return (
            bundle,
            ResolvedDependencies(dependencies, supplied, ontology_sources),
            profile,
            prepared,
        )
    except ReleaseConflict:
        raise
    except (
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        BaseValidationError,
        yaml.YAMLError,
    ) as exc:
        raise ReleaseConflict(f"cannot open exact release {release_id}: {exc}") from exc


def open_archived_release(conn: Any, release_id: str) -> PreparedRelease:
    """Read a complete archive in one caller-owned snapshot, retaining row coherence checks."""
    return open_archived_release_inputs(conn, release_id)[3]


def open_archived_release_inputs(conn: Any, release_id: str, *, use_cache: bool = True):
    """Open authenticated archived source/dependency bytes without recompilation."""

    from .releases import ReleaseConflict

    header = _archive_header(conn, release_id)
    if header is None:
        raise KeyError(release_id)
    finalized_digest = header.finalized_digest
    if finalized_digest != header.content_digest:
        raise ReleaseConflict("archive lacks matching protected finalization")
    if not use_cache:
        return _read_archived_release_inputs(conn, release_id, header)

    from .determinants import BOUNDARY_LIBRARIES, determinant_version
    from .storage_target import acquired_database_identity

    runtime = tuple(
        (name, determinant_version(name)) for name in (*BOUNDARY_LIBRARIES, "linkml-runtime")
    )
    return _opened_archive(
        (acquired_database_identity(conn), release_id, tuple(header), runtime),
        conn,
        release_id,
        header,
    )


@declare(
    "opened-archive",
    "release_bytes",
    key=lambda key, conn, release_id, header: key,
    weight=retained_archive_bytes,
)
def _opened_archive(key, conn, release_id, header):
    return _read_archived_release_inputs(conn, release_id, header)


def _read_archived_release_inputs(conn, release_id, header):
    """Authenticate the stored parts in the caller snapshot, independently of retained entries."""
    from sqlalchemy import select

    from .releases import ReleaseConflict, _table

    relation = _table("sem.release")
    row = (
        conn.execute(select(relation).where(relation.c.release_id == release_id))
        .mappings()
        .one_or_none()
    )
    if row is None or (row["profile"], row["content_digest"]) != (
        header.profile,
        header.content_digest,
    ):
        raise ReleaseConflict("archive header changed during opening")
    try:
        inputs = _table("sem.input")
        artifacts = _table("sem.artifact")
        prepared = _open_release_parts_inputs(
            release_id,
            row,
            conn.execute(select(inputs).where(inputs.c.release_id == release_id)).mappings(),
            conn.execute(select(artifacts).where(artifacts.c.release_id == release_id)).mappings(),
        )
        observed = _archive_header(conn, release_id)
        if observed is None or tuple(observed) != tuple(header):
            raise ReleaseConflict("archive header changed during opening")
        return prepared
    except ReleaseConflict:
        raise
    except (
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        BaseValidationError,
        yaml.YAMLError,
    ) as exc:
        raise ReleaseConflict(f"cannot open exact release {release_id}: {exc}") from exc
