"""Versioned read-boundary reconstruction from exact archived products.

Opening is not compilation or admission. The sole historical adapter recovers the
missing v10 aliases from supplied source bytes; vocabulary and constraints stay archived.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from datetime import date
from decimal import Decimal
from threading import RLock
from typing import Any, cast
from weakref import WeakKeyDictionary

import yaml
from cattrs import Converter
from cattrs.errors import BaseValidationError
from linkml_runtime.linkml_model import SchemaDefinition, SchemaDefinitionName
from linkml_runtime.loaders import yaml_loader
from linkml_runtime.utils.schemaview import SchemaView
from pydantic import AwareDatetime

from .types import (
    BOUNDARY_ABI_VERSION,
    ClassDefinition,
    Diagnostic,
    PreparationProfile,
    PreparedArtifact,
    PreparedRelease,
    QueryDescriptor,
    RegistryRow,
    SourceArtifact,
    SourceBundle,
    VocabularySnapshot,
)

# Engine lifetime bounds database authority; keys additionally bind snapshot-observed bytes
# and the actual validation runtime. Mutable selection, authorization and facts never enter it.
_OPEN_CACHE: WeakKeyDictionary[Any, OrderedDict[tuple, PreparedRelease]] = WeakKeyDictionary()
_CACHE_LOCK = RLock()

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


def _converter() -> Converter:
    converter = Converter(forbid_extra_keys=True, detailed_validation=True)

    def exact(value: Any, expected: type) -> Any:
        if type(value) is not expected:
            raise TypeError(f"expected {expected.__name__}")
        return value

    for primitive in (str, int, bool, float, bytes):
        converter.register_structure_hook(primitive, exact)
    return converter


_CONVERTER = _converter()


def _v10_aliases(bundle: SourceBundle, definitions: tuple[ClassDefinition, ...]):
    """Recover only missing alias/dispatch recipes with a closed, offline import map.

    This intentionally does not call current preparation inspection or generators.
    Imported attributes retain their source defaults before imports are merged, as v10 did.
    """
    schemas: dict[str, SchemaDefinition] = {}
    for source in bundle.sources:
        body = yaml.safe_load(source.content)
        if not isinstance(body, dict):
            raise ValueError("archived schema must be a mapping")
        schema = cast(SchemaDefinition, yaml_loader.load(body, SchemaDefinition))
        for cls in cast(dict[str, Any], schema.classes or {}).values():
            for slot in cast(dict[str, Any], cls.attributes or {}).values():
                if slot.range is None:
                    slot.range = schema.default_range or "string"
        for slot in cast(dict[str, Any], schema.slots or {}).values():
            if slot.range is None:
                slot.range = schema.default_range or "string"
        schemas[source.name] = schema
    if len(schemas) != len(bundle.sources) or bundle.root not in schemas:
        raise ValueError("invalid archived source identity")
    for schema in schemas.values():
        if any(str(name) not in schemas for name in schema.imports or ()):
            raise ValueError("archived alias recipe has an unavailable import")
    view = SchemaView(schemas[bundle.root])
    view.schema_map = {cast(SchemaDefinitionName, name): schema for name, schema in schemas.items()}
    view.schema_map[SchemaDefinitionName(str(schemas[bundle.root].name))] = schemas[bundle.root]
    view.merge_imports()
    assert view.schema is not None
    view.schema.imports = []
    view = SchemaView(view.schema)
    aliases: dict[tuple[str, str], str] = {}
    descendants: dict[str, tuple[str, ...]] = {}
    if set(view.all_classes()) != {definition.name for definition in definitions}:
        raise ValueError("archived alias classes differ from normalized products")
    for definition in definitions:
        slots = {str(slot.name): slot for slot in view.class_induced_slots(definition.name)}
        if set(slots) != {prop.name for prop in definition.properties}:
            raise ValueError("archived alias properties differ from normalized products")
        for prop in definition.properties:
            slot = slots[prop.name]
            if str(slot.range or "string") != prop.range:
                raise ValueError("archived alias range differs from normalized products")
            aliases[definition.name, prop.name] = slot.alias or prop.name
        concrete = []
        for name in view.class_descendants(definition.name, reflexive=False):
            child = view.get_class(name)
            if child is None:
                raise ValueError("unavailable archived descendant")
            if not child.abstract:
                concrete.append(str(name))
        descendants[definition.name] = tuple(concrete)
    return aliases, descendants


def _v10_primitives(rows: tuple[RegistryRow, ...]) -> dict[str, Any]:
    types = {row.name: json.loads(row.body) for row in rows if row.kind == "type"}
    result = dict(_PRIMITIVES)

    def resolve(name: str, seen: tuple[str, ...] = ()) -> Any:
        if name in result:
            return result[name]
        if name in seen or name not in types:
            raise ValueError(f"unavailable archived primitive recipe {name}")
        declaration = types[name]
        base = declaration.get("typeof") or declaration.get("base") or "string"
        base = {"str": "string", "int": "integer", "bool": "boolean", "Decimal": "decimal"}.get(
            base, base
        )
        result[name] = resolve(base, (*seen, name))
        return result[name]

    for name in types:
        resolve(name)
    return result


def reconstruct_release(
    products: dict[str, Any],
    manifest: bytes,
    bundle: SourceBundle,
    profile: PreparationProfile,
    artifacts: tuple[PreparedArtifact, ...],
) -> PreparedRelease:
    """Hydrate a supported archived ABI without preparing or admitting its release."""
    from .boundary import build_boundary_adapters
    from .identity import canonical_bytes

    allowed = {
        "release_id",
        "definitions",
        "vocabularies",
        "registry_rows",
        "queries",
        "artifacts",
        "required_capabilities",
        "diagnostics",
        "execution_model_id",
    }
    if set(products) - allowed or allowed - {"execution_model_id"} - set(products):
        raise ValueError("unsupported archived product fields")
    definitions = _CONVERTER.structure(products["definitions"], tuple[ClassDefinition, ...])
    vocabularies = _CONVERTER.structure(products["vocabularies"], tuple[VocabularySnapshot, ...])
    rows = tuple(
        RegistryRow(row["kind"], row["name"], bytes.fromhex(row["body_hex"]))
        for row in products["registry_rows"]
        if set(row) == {"kind", "name", "body_hex"}
    )
    if len(rows) != len(products["registry_rows"]) or len({(r.kind, r.name) for r in rows}) != len(
        rows
    ):
        raise ValueError("invalid archived registry rows")
    artifact_map = {artifact.kind: artifact for artifact in artifacts}
    if len(artifact_map) != len(artifacts) or len(products["artifacts"]) != len(artifacts):
        raise ValueError("duplicate or missing archived artifacts")
    for expected in products["artifacts"]:
        if (
            set(expected) != {"kind", "digest"}
            or artifact_map[expected["kind"]].digest != expected["digest"]
        ):
            raise ValueError("archived artifact digest differs")
    fragments = (
        json.loads(artifact_map["conditional_rules.json"].content)
        if "conditional_rules.json" in artifact_map
        else {}
    )
    if profile.compiler_version == "10":
        aliases, descendants = _v10_aliases(bundle, definitions)
        primitive_types = _v10_primitives(rows)
    elif profile.compiler_version in {"11", "12", "13"}:
        recipe = json.loads(artifact_map["boundary_recipe.json"].content)
        if set(recipe) != {
            "abi",
            "primitives",
            "aliases",
            "descendants",
            "conditional_scope",
        } or recipe["abi"] != "semantic-boundary-" + (
            "11" if profile.compiler_version == "11" else BOUNDARY_ABI_VERSION
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
    else:
        raise ValueError(f"unsupported archived compiler {profile.compiler_version}")
    models = {}

    def build(class_names=None, target_models=None):
        return build_boundary_adapters(
            definitions,
            vocabularies,
            primitive_types=primitive_types,
            aliases=aliases,
            conditional_fragments=fragments,
            conditional_scope=profile.constraint_scope,
            legacy_v10=profile.compiler_version == "10",
            finite_fields=profile.compiler_version in {"12", "13"},
            descendant_order=descendants,
            models_out=models if target_models is None else target_models,
            class_names=class_names,
        )

    adapters = () if profile.compiler_version in {"12", "13"} else build()

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

    for name, adapter in adapters:
        check_schema(name, adapter)

    def load_adapter(name):
        staged_models = dict(models)
        built = dict(build((name,), staged_models))
        adapter = built[name]
        check_schema(name, adapter)
        models.update(staged_models)
        return adapter

    return PreparedRelease(
        release_id=products["release_id"],
        manifest=manifest,
        definitions=definitions,
        vocabularies=vocabularies,
        registry_rows=rows,
        queries=_CONVERTER.structure(products["queries"], tuple[QueryDescriptor, ...]),
        artifacts=artifacts,
        required_capabilities=_CONVERTER.structure(
            products["required_capabilities"], tuple[str, ...]
        ),
        diagnostics=_CONVERTER.structure(products["diagnostics"], tuple[Diagnostic, ...]),
        _adapters=adapters,
        execution_model_id=products.get("execution_model_id"),
        _boundary_models=models,
        _adapter_loader=load_adapter if profile.compiler_version in {"12", "13"} else None,
    )


def open_archived_release(conn: Any, release_id: str) -> PreparedRelease:
    """Read a complete archive in one caller-owned snapshot, retaining row coherence checks."""
    from dataclasses import asdict

    from sqlalchemy import select

    from .determinants import boundary_compatible
    from .identity import canonical_bytes
    from .releases import (
        ReleaseConflict,
        _archive_bytes,
        _compare_rows,
        _digest,
        _projection_rows,
        _table,
    )
    from .types import ResolvedDependencies

    relation = _table("sem.release")
    row = (
        conn.execute(select(relation).where(relation.c.release_id == release_id))
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise KeyError(release_id)
    finalization = _table("sem.release_finalization")
    finalized_digest = conn.execute(
        select(finalization.c.content_digest).where(finalization.c.release_id == release_id)
    ).scalar_one_or_none()
    from .determinants import BOUNDARY_LIBRARIES, determinant_version

    runtime = tuple(
        (name, determinant_version(name)) for name in (*BOUNDARY_LIBRARIES, "linkml-runtime")
    )
    if _digest(bytes(row["prepared_bytes"])) != row["content_digest"]:
        raise ReleaseConflict("archive digest differs")
    cache_key = (release_id, row["content_digest"], _digest(bytes(row["manifest_bytes"])), runtime)
    if finalized_digest == row["content_digest"]:
        with _CACHE_LOCK:
            cache = _OPEN_CACHE.get(conn.engine)
            if cache is not None and cache_key in cache:
                cache.move_to_end(cache_key)
                return cache[cache_key]
    try:
        archive_bytes, manifest_bytes = bytes(row["prepared_bytes"]), bytes(row["manifest_bytes"])
        if _digest(archive_bytes) != row["content_digest"] or release_id != "release:" + _digest(
            manifest_bytes
        ):
            raise ReleaseConflict("archive or manifest identity differs")
        archive, manifest = json.loads(archive_bytes), json.loads(manifest_bytes)
        if archive["format"] not in {
            "semantic-release-archive-1",
            "semantic-release-archive-2",
            "semantic-release-archive-3",
        }:
            raise ReleaseConflict("unsupported archive format")
        if not boundary_compatible(
            manifest["libraries"], str(manifest["profile"]["compiler_version"])
        ):
            raise ReleaseConflict("archived boundary library versions differ")
        relation = _table("sem.input")
        source: dict[tuple[str, str], bytes] = {}
        for item in conn.execute(
            select(relation).where(relation.c.release_id == release_id)
        ).mappings():
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
        if profile.version not in {"semantic-1", "semantic-2"} or row["profile"] != profile.version:
            raise ReleaseConflict("unsupported archived profile")
        expected: dict[str, Any] = {
            "root": bundle.root,
            "profile": asdict(profile),
            "libraries": manifest["libraries"],
            "sources": sorted((item.name, item.digest) for item in bundle.sources),
            "dependencies": sorted((item.name, item.digest) for item in dependencies),
            "ontology_sources": sorted(json.loads(source["ontology_sources", "ontology_sources"])),
            # The input contains supplied dependency snapshots; the manifest contains
            # resolved vocabularies, including enums authored in the source schema.
            "vocabularies": archive["products"]["vocabularies"],
        }
        execution_id = archive["products"].get("execution_model_id")
        if profile.version == "semantic-2":
            if not execution_id:
                raise ReleaseConflict("composed archive lacks execution identity")
            expected["execution_model_id"] = execution_id
        elif execution_id is not None:
            raise ReleaseConflict("execution model requires semantic-2")
        if canonical_bytes(expected) != manifest_bytes:
            raise ReleaseConflict("archived input manifest differs")
        relation = _table("sem.artifact")
        artifacts: list[PreparedArtifact] = []
        for item in conn.execute(
            select(relation).where(relation.c.release_id == release_id)
        ).mappings():
            content = bytes(item["content"])
            if (
                _digest(content) != item["content_digest"]
                or item["media_type"] != "application/octet-stream"
            ):
                raise ReleaseConflict("artifact bytes or media type differ")
            artifacts.append(PreparedArtifact(item["artifact_name"], content))
        by_name = {item.kind: item for item in artifacts}
        ordered = tuple(by_name[item["kind"]] for item in archive["products"]["artifacts"])
        if len(ordered) != len(artifacts):
            raise ReleaseConflict("unexpected archived artifacts")
        prepared = reconstruct_release(
            archive["products"], manifest_bytes, bundle, profile, ordered
        )
        supplied = _CONVERTER.structure(
            json.loads(source["vocabulary", "vocabulary"]), tuple[VocabularySnapshot, ...]
        )
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
        if finalized_digest != row["content_digest"]:
            # Required historical archives without protected finalization retain the
            # complete snapshot coherence path; they never populate the cache.
            for name, expected_rows in _projection_rows(prepared).items():
                _compare_rows(conn, name, release_id, expected_rows)
        else:
            with _CACHE_LOCK:
                cache = _OPEN_CACHE.setdefault(conn.engine, OrderedDict())
                if cache_key in cache:
                    # A concurrent cold opener may already have published this owner.
                    cache.move_to_end(cache_key)
                    return cache[cache_key]
                cache[cache_key] = prepared
                cache.move_to_end(cache_key)
                while len(cache) > 8:
                    cache.popitem(last=False)
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
