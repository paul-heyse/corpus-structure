"""Compile the trusted physical model from a closed set of declared sources."""

from collections.abc import Callable, Mapping
from hashlib import sha256
from importlib.resources import files
from pathlib import PurePosixPath
from struct import pack
from typing import Any

import yaml
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader
from sqlalchemy import MetaData

from .declarations import ModelError

PHYSICAL_ROOT = "physical.yaml"
_LINKML_TYPES = "linkml:types"


def linkml_types_source() -> bytes:
    return files("linkml_runtime").joinpath("linkml_model/model/schema/types.yaml").read_bytes()


def _document(name: str, content: bytes) -> dict[str, Any]:
    try:
        value = yaml.load(content, Loader=DupCheckYamlLoader)
    except yaml.YAMLError as error:
        raise ModelError([f"invalid physical declaration {name}: {error}"]) from error
    if not isinstance(value, dict):
        raise ModelError([f"invalid physical declaration: {name}"])
    return value


def _imports(name: str, document: dict[str, Any]) -> tuple[str, ...]:
    imports = document.get("imports", [])
    if not isinstance(imports, list) or any(
        not isinstance(item, str)
        or (
            item != _LINKML_TYPES
            and (not item or PurePosixPath(item).name != item or ":" in item or item in {".", ".."})
        )
        for item in imports
    ):
        raise ModelError([f"unsupported physical import in {name}"])
    return tuple(imports)


def _enum_references(document: dict[str, Any]):
    """Resolve only explicitly named local value-set inputs; no ambient acquisition."""
    enums = document.get("enums", {})
    if not isinstance(enums, dict):
        raise ModelError(["physical enums must be a mapping"])
    for enum in enums.values():
        if enum is None:
            continue
        if not isinstance(enum, dict) or not isinstance(enum.get("annotations", {}), dict):
            raise ModelError(["physical enum declaration/annotations must be mappings"])
        reference = enum.get("annotations", {}).get("ph:values_from")
        if reference is None:
            continue
        if not isinstance(reference, str) or "#/" not in reference:
            raise ModelError(["physical enum reference requires a local source and JSON pointer"])
        source, pointer = reference.split("#", 1)
        if (
            not source
            or PurePosixPath(source).name != source
            or ":" in source
            or source in {".", ".."}
            or not source.endswith(".yaml")
        ):
            raise ModelError(["physical enum reference must name a flat local source"])
        if enum.get("permissible_values"):
            raise ModelError(["physical enum cannot author values beside a referenced value set"])
        yield enum, source, pointer


def physical_source_closure(root: str, read: Callable[[str], bytes | None]) -> dict[str, bytes]:
    """Acquire the flat LinkML imports and their explicit referenced value-set sources."""
    sources, _ = _source_documents(root, read)
    return sources


def _source_documents(
    root: str, read: Callable[[str], bytes | None]
) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    sources: dict[str, bytes] = {}
    documents: dict[str, dict[str, Any]] = {}

    def acquire(name: str) -> bytes:
        if name not in sources:
            content = read(name)
            if content is None:
                raise ModelError([f"missing physical import or value-set source: {name}"])
            sources[name] = content
        return sources[name]

    def visit(name: str) -> None:
        if name in documents:
            return
        document = documents[name] = _document(name, acquire(name))
        for imported in _imports(name, document):
            if imported != _LINKML_TYPES:
                visit(imported + ".yaml")
        for _, source, _ in _enum_references(document):
            acquire(source)

    visit(root)
    return sources, documents


def resolve_physical_value_sets(document: dict[str, Any], sources: Mapping[str, bytes]):
    # Documents are freshly parsed from the supplied bytes. Resolving their enum
    # annotations does not mutate retained sources or change historical declarations.
    for enum, source, pointer in tuple(_enum_references(document)):
        value: Any = _document(source, sources[source])
        try:
            for part in pointer.removeprefix("/").split("/"):
                value = value[part.replace("~1", "/").replace("~0", "~")]
        except (KeyError, TypeError) as error:
            raise ModelError([f"unknown physical enum reference {source}#{pointer}"]) from error
        if (
            not isinstance(value, list)
            or not value
            or any(not isinstance(item, str) or not item for item in value)
            or len(value) != len(set(value))
        ):
            raise ModelError(
                [
                    f"physical enum reference is not a nonempty distinct string set: {source}#{pointer}"
                ]
            )
        enum["permissible_values"] = {item: {} for item in value}
        # The resolved LinkML view owns values; dependency custody remains in sources.
        del enum["annotations"]["ph:values_from"]
    return document


def physical_sources_id(sources: Mapping[str, bytes]) -> str:
    """Identify the named physical import closure with its existing framed recipe."""
    digest = sha256(b"corpus-physical-sources-1\0")
    for name, content in sorted(sources.items()):
        encoded = name.encode()
        digest.update(pack(">Q", len(encoded)))
        digest.update(encoded)
        digest.update(pack(">Q", len(content)))
        digest.update(content)
    return "physical:" + digest.hexdigest()


def physical_model_documents(
    sources: Mapping[str, bytes], *, root: str = PHYSICAL_ROOT
) -> dict[str, dict[str, Any]]:
    """Project resolved LinkML documents; referenced raw inputs stay in source custody."""
    closure, documents = _source_documents(root, sources.get)
    if set(closure) != set(sources):
        raise ModelError(["unexpected sources in the physical declaration closure"])
    return {
        name: resolve_physical_value_sets(document, closure) for name, document in documents.items()
    }


def compile_physical(
    sources: Mapping[str, bytes],
    *,
    linkml_types: bytes | None = None,
    root: str = PHYSICAL_ROOT,
    target: str = "semantic",
) -> MetaData:
    """Compile the exact closure. The only nonlocal import is the pinned LinkML types."""
    from corpus_structure.model.compiled import compiled_model

    captured = dict(sources)
    if _LINKML_TYPES in captured:
        raise ModelError(["unexpected sources in the physical declaration closure"])
    types_content = linkml_types_source() if linkml_types is None else linkml_types
    model = compiled_model({**captured, _LINKML_TYPES: types_content})

    def project():
        # Exact explicit-closure admission is a property of these captured bytes,
        # so repeated access must not parse and prove the same closure again.
        physical_model_documents(captured, root=root)
        return model.physical(root, target=target)

    return model.projection(("exact-physical", root, target), project)
