"""Compile the trusted physical model from a closed set of declared sources."""

from collections.abc import Callable, Mapping
from hashlib import sha256
from importlib.resources import files
from pathlib import PurePosixPath
from struct import pack
from typing import Any

import yaml
from linkml_runtime.linkml_model.meta import SchemaDefinition
from linkml_runtime.loaders import yaml_loader
from linkml_runtime.utils.schemaview import SchemaView
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader
from sqlalchemy import MetaData

from .model import ModelError
from .relational import compile_metadata

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


def physical_source_closure(root: str, read: Callable[[str], bytes | None]) -> dict[str, bytes]:
    """Acquire only the root and its declared, flat, local import closure."""
    sources, _ = _source_documents(root, read)
    return sources


def _source_documents(
    root: str, read: Callable[[str], bytes | None]
) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    sources: dict[str, bytes] = {}
    documents: dict[str, dict[str, Any]] = {}

    def visit(name: str) -> None:
        if name in sources:
            return
        content = read(name)
        if content is None:
            raise ModelError([f"missing physical import: {name}"])
        sources[name] = content
        document = documents[name] = _document(name, content)
        for imported in _imports(name, document):
            if imported != _LINKML_TYPES:
                visit(imported + ".yaml")

    visit(root)
    return sources, documents


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


def compile_physical(
    sources: Mapping[str, bytes], *, linkml_types: bytes | None = None
) -> MetaData:
    """Compile the exact closure. The only nonlocal import is the pinned LinkML types."""
    closure, documents = _source_documents(PHYSICAL_ROOT, sources.get)
    if set(closure) != set(sources):
        raise ModelError(["unexpected sources in the physical declaration closure"])
    root = documents.pop(PHYSICAL_ROOT)
    importmap: dict[str, str | dict[str, Any]] = {
        name.removesuffix(".yaml"): document for name, document in documents.items()
    }
    types = _document(
        _LINKML_TYPES, linkml_types_source() if linkml_types is None else linkml_types
    )
    if _imports(_LINKML_TYPES, types):
        raise ModelError(["unsupported imports in retained LinkML types"])
    importmap[_LINKML_TYPES] = types
    try:
        schema = yaml_loader.load(root, SchemaDefinition)
        if not isinstance(schema, SchemaDefinition):
            raise ValueError("root is not a SchemaDefinition")
        # Include the root in the map so even a local cycle cannot reach the filesystem.
        importmap[PHYSICAL_ROOT.removesuffix(".yaml")] = root
        metadata = compile_metadata(SchemaView(schema, importmap=importmap), target="semantic")
    except ModelError:
        raise
    except (ValueError, TypeError, KeyError) as error:
        raise ModelError([f"invalid physical declaration: {error}"]) from error
    metadata.info["physical_model_id"] = physical_sources_id(closure)
    metadata.info["physical_sources"] = closure
    return metadata
