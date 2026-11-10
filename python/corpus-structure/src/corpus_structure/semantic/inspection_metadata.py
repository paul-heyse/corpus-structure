"""Derived authoring detail, retained before LinkML discards declaration context.

Effective meaning remains in prepared definitions and boundary/operation products. A
contributor records participation, not an inferred per-field winner or execution grant.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from .identity import canonical_bytes
from .types import PreparedArtifact

if TYPE_CHECKING:
    from linkml_runtime.utils.schemaview import SchemaView

    from .types import ClassDefinition, PreparedRelease, SourceArtifact

ARTIFACT = "inspection/effective-model.json"
_METADATA = frozenset({"title", "description", "aliases", "in_subset", "annotations"})
_FIELDS = _METADATA | {
    "is_a",
    "mixins",
    "slots",
    "typeof",
    "base",
    "class_uri",
    "slot_uri",
    "uri",
    "range",
    "required",
    "value_presence",
    "multivalued",
    "identifier",
    "inlined",
    "inlined_as_list",
    "minimum_cardinality",
    "maximum_cardinality",
    "minimum_value",
    "maximum_value",
    "pattern",
    "equals_string",
    "alias",
    "inverse",
    "symmetric",
    "transitive",
    "unique_keys",
    "rules",
    "meaning",
    "inherits",
    "include",
    "minus",
    "concepts",
    "reachable_from",
}


def capture_declarations(index: dict[str, Any], source: SourceArtifact, body: dict) -> None:
    """Capture admitted raw fields during the existing parse, before materialization."""
    index.setdefault("sources", {})[source.name] = {
        "source_digest": source.digest,
        "declaration": deepcopy(
            {
                key: body[key]
                for key in ("id", "name", "default_prefix", "default_range", "prefixes")
                if key in body
            }
        ),
    }
    declarations = index.setdefault("declarations", {})

    def retain(path, value):
        declarations[path] = {
            "module": source.name,
            "path": path,
            "source_digest": source.digest,
            "declaration": deepcopy({key: value[key] for key in _FIELDS if key in value}),
        }

    for kind in ("classes", "slots", "types", "enums"):
        for name, value in (body.get(kind) or {}).items():
            value = value or {}
            retain(f"{kind}/{name}", value)
            if kind == "enums":
                for member, declaration in (value.get("permissible_values") or {}).items():
                    retain(f"enums/{name}/permissible_values/{member}", declaration or {})
            if kind == "classes":
                for layer in ("attributes", "slot_usage"):
                    for slot, usage in (value.get(layer) or {}).items():
                        retain(f"classes/{name}/{layer}/{slot}", usage or {})


def prepare_inspection(
    index: dict, view: SchemaView, definitions: tuple[ClassDefinition, ...]
) -> PreparedArtifact:
    """Connect retained declarations to effective subjects without reimplementing induction."""
    from linkml_runtime.dumpers import json_dumper

    declarations = index["declarations"]

    def contributor(path, role):
        record = declarations.get(path)
        return dict(record, role=role) if record is not None else None

    def append(items, path, role):
        record = contributor(path, role)
        if record is not None and record not in items:
            items.append(record)

    def slot_chain(name, seen=()):
        if name in seen:
            return ()
        record = declarations.get(f"slots/{name}")
        if record is None:
            return ()
        declared = record["declaration"]
        parents = ([declared["is_a"]] if declared.get("is_a") else []) + list(
            declared.get("mixins") or ()
        )
        return (
            name,
            *(parent for ancestor in parents for parent in slot_chain(ancestor, (*seen, name))),
        )

    classes = {}
    for definition in definitions:
        name = definition.name
        ancestors = tuple(str(item) for item in view.class_ancestors(name, reflexive=True))
        class_contributors = []
        for ancestor in ancestors:
            append(
                class_contributors,
                f"classes/{ancestor}",
                "local" if ancestor == name else "ancestor_or_mixin",
            )
        local = declarations.get(f"classes/{name}", {}).get("declaration", {})
        properties = {}
        for prop in definition.properties:
            contributors = []
            has_attribute = any(
                f"classes/{ancestor}/attributes/{prop.name}" in declarations
                for ancestor in ancestors
            )
            for slot in slot_chain(prop.name):
                role = (
                    "shadowed_declaration"
                    if has_attribute
                    else "reused_slot"
                    if slot == prop.name
                    else "slot_ancestor_or_mixin"
                )
                append(contributors, f"slots/{slot}", role)
            for ancestor in ancestors:
                for layer in ("attributes", "slot_usage"):
                    append(
                        contributors,
                        f"classes/{ancestor}/{layer}/{prop.name}",
                        "local" if ancestor == name else "ancestor_or_mixin",
                    )
            type_name, seen = prop.range, set()
            while type_name not in seen:
                seen.add(type_name)
                record = declarations.get(f"types/{type_name}")
                if record is None:
                    break
                append(contributors, f"types/{type_name}", "type_constraint")
                raw = record["declaration"]
                type_name = str(raw.get("typeof") or raw.get("base") or "")
            normalizations = []
            if prop.name in definition.identity_slots:
                normalizations.append("identifier_implies_required")
            if prop.multivalued:
                normalizations.append("compiler_cardinality_normalization")
            modules = sorted({item["module"] for item in contributors})
            for module in modules:
                source = index["sources"][module]
                contributors.append(
                    {
                        "module": module,
                        "path": "",
                        "source_digest": source["source_digest"],
                        "role": "source_defaults",
                        "declaration": {
                            key: value
                            for key, value in source["declaration"].items()
                            if key != "prefixes"
                        },
                    }
                )
            effective_slot = json_dumper.to_dict(view.induced_slot(prop.name, name))
            properties[prop.name] = {
                "metadata": {
                    key: effective_slot[key] for key in sorted(_METADATA) if key in effective_slot
                },
                "contributors": contributors,
                "attribution": "known_contributors",
                "attribution_detail": (
                    "Known contributors establish applicability; effective constraints come from "
                    "the prepared definition. Per-field precedence is unresolved here."
                ),
                "normalizations": normalizations,
            }
        classes[name] = {
            "metadata": {key: local[key] for key in sorted(_METADATA) if key in local},
            "contributors": class_contributors,
            "properties": properties,
        }
    enums = {}
    for name in sorted(view.all_enums()):
        enum_path = f"enums/{name}"
        records = [
            dict(record, role="enum_declaration")
            for path, record in declarations.items()
            if path == enum_path or path.startswith(enum_path + "/")
        ]
        enums[name] = {"contributors": records}
    return PreparedArtifact(
        ARTIFACT,
        canonical_bytes(
            {"version": 2, "sources": index["sources"], "classes": classes, "enums": enums}
        ),
    )


def _decode_inspection(prepared: PreparedRelease) -> dict[str, Any]:
    artifact = next((item for item in prepared.artifacts if item.kind == ARTIFACT), None)
    if artifact is None:
        compiler = json.loads(prepared.manifest)["profile"]["compiler_version"]
        legacy = int(compiler) < 20
        return {
            "status": "unavailable" if legacy else "corrupt",
            "reason": "detail unavailable in this archive"
            if legacy
            else "required inspection artifact is missing",
            "artifact_digest": None,
            "classes": {},
        }
    base = {"artifact_digest": artifact.digest, "classes": {}}
    try:
        body = json.loads(artifact.content)
        if not isinstance(body, dict) or type(body.get("version")) is not int:
            raise ValueError("invalid inspection header")
        if body["version"] not in {1, 2}:
            return dict(base, status="unsupported", reason="unsupported inspection payload version")
        if (
            set(body)
            != (
                {"version", "sources", "classes", "enums"}
                if body["version"] == 2
                else {"version", "sources", "classes"}
            )
            or not isinstance(body["sources"], dict)
            or not isinstance(body["classes"], dict)
        ):
            raise ValueError("invalid inspection payload")
        manifest_sources = dict(json.loads(prepared.manifest)["sources"])
        if set(body["sources"]) != set(manifest_sources) or any(
            record["source_digest"] != manifest_sources[module]
            for module, record in body["sources"].items()
        ):
            raise ValueError("inspection source identities differ")
        # Require the product to describe exactly the opened release's class/property universe.
        if set(body["classes"]) != {item.name for item in prepared.definitions}:
            raise ValueError("inspection class universe differs")
        for definition in prepared.definitions:
            item = body["classes"][definition.name]
            if not isinstance(item, dict) or set(item) != {
                "metadata",
                "contributors",
                "properties",
            }:
                raise ValueError("invalid class inspection record")
            if (
                not isinstance(item["metadata"], dict)
                or not isinstance(item["contributors"], list)
                or not isinstance(item["properties"], dict)
            ):
                raise ValueError("invalid class inspection fields")
            if set(item["properties"]) != {prop.name for prop in definition.properties}:
                raise ValueError("inspection property universe differs")
            for prop in item["properties"].values():
                if not isinstance(prop, dict) or set(prop) != {
                    "metadata",
                    "contributors",
                    "attribution",
                    "attribution_detail",
                    "normalizations",
                }:
                    raise ValueError("invalid property inspection record")
                if (
                    not isinstance(prop["metadata"], dict)
                    or not isinstance(prop["contributors"], list)
                    or not isinstance(prop["normalizations"], list)
                    or prop["attribution"] != "known_contributors"
                    or not isinstance(prop["attribution_detail"], str)
                ):
                    raise ValueError("invalid property inspection fields")
            for record in [
                *item["contributors"],
                *(c for prop in item["properties"].values() for c in prop["contributors"]),
            ]:
                if set(record) != {"module", "path", "source_digest", "role", "declaration"}:
                    raise ValueError("invalid contributor")
                if not isinstance(record["declaration"], dict) or not all(
                    isinstance(record[key], str)
                    for key in ("module", "path", "source_digest", "role")
                ):
                    raise ValueError("invalid contributor fields")
                source = body["sources"][record["module"]]
                if record["source_digest"] != source["source_digest"]:
                    raise ValueError("contributor source digest differs")
        if body["version"] == 2:
            if not isinstance(body["enums"], dict) or set(body["enums"]) != {
                v.enum for v in prepared.vocabularies
            }:
                raise ValueError("inspection enum universe differs")
            for item in body["enums"].values():
                if (
                    not isinstance(item, dict)
                    or set(item) != {"contributors"}
                    or not isinstance(item["contributors"], list)
                ):
                    raise ValueError("invalid enum locator")
                for record in item["contributors"]:
                    if (
                        set(record) != {"module", "path", "source_digest", "role", "declaration"}
                        or record["source_digest"] != manifest_sources[record["module"]]
                        or not isinstance(record["declaration"], dict)
                        or not all(
                            isinstance(record[key], str)
                            for key in ("module", "path", "source_digest", "role")
                        )
                    ):
                        raise ValueError("invalid enum contributor")
        return dict(
            body,
            status="available",
            reason=None,
            artifact_digest=artifact.digest,
            enum_detail_status="available" if body["version"] == 2 else "unavailable",
        )
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return dict(base, status="corrupt", reason=f"invalid inspection detail: {exc}")


def get_inspection(prepared: PreparedRelease) -> Mapping[str, Any]:
    """Read release-owned detail; unsupported detail never changes executable meaning."""
    return prepared.inspection_metadata


def freeze_inspection(value: Any) -> Any:
    """Keep the release-local decoded product immutable, including nested metadata."""
    if isinstance(value, dict):
        return MappingProxyType({key: freeze_inspection(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(freeze_inspection(item) for item in value)
    return value
