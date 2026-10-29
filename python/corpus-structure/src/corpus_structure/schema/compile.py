"""Compiling a schema version: artifacts, their identity and `CompiledSchema` (P0-S-1).

Schema and rules §3.3; D2 §7; D3 §3. Each compiler is a pure function of the loaded packs and the
model, returning `CompiledArtifact(compiler, compiler_version, kind, body, hash)`: the hash is the
SHA-256 of the body's canonical JSON, a text artifact is a JSON string, and a float in a body is a
compile error (canonical JSON refuses it). The compiler version joins the compiler's own version
with the versions of the libraries that shape its output, so a library bump is a new identity.

The kinds built here: `schema_tables/tables`, `json_schema/batch.model_facing`, `batch.stored` and
`batch.decoding`, and `annotator_reference/reference`. The compiled rules are S2's (P0-S-2).
`CompiledSchema` bundles the lookup, the compiled `KeySchema`, the name map, the batch adapters,
the reference and the artifacts; it is immutable and built once per process per schema version.
"""

from __future__ import annotations

import importlib.metadata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from corpus_structure.core._model import revision
from corpus_structure.core.canonical import digest
from corpus_structure.core.keys import KeySchema
from corpus_structure.schema.batches import BatchCompiler, decoding_form, schema_id
from corpus_structure.schema.lookup import (
    NameMap,
    SchemaLookup,
    build_lookup,
    compile_key_schema,
    name_map,
)
from corpus_structure.schema.pack import CORE_RULES, Pack, load_pack, schema_version
from corpus_structure.schema.reference import Reference, build_reference
from corpus_structure.schema.tables import schema_tables

COMPILERS = {"schema_tables": "1", "json_schema": "1", "annotator_reference": "1"}
_LIBRARIES = {
    "schema_tables": ("linkml-runtime",),
    "json_schema": ("pydantic", "linkml-runtime"),
    "annotator_reference": ("pydantic", "linkml-runtime"),
}


def compiler_version(compiler: str) -> str:
    """`<compiler version>+<library>=<version>…`, e.g. `1+pydantic=2.14.1+linkml-runtime=1.12.1`."""
    libraries = "".join(f"+{lib}={importlib.metadata.version(lib)}" for lib in _LIBRARIES[compiler])
    return f"{COMPILERS[compiler]}{libraries}"


@dataclass(frozen=True)
class CompiledArtifact:
    compiler: str
    compiler_version: str
    kind: str
    body: Any
    hash: str


def artifact(compiler: str, kind: str, body: Any) -> CompiledArtifact:
    return CompiledArtifact(compiler, compiler_version(compiler), kind, body, digest(body))


@dataclass(frozen=True)
class CompiledSchema:
    """One schema version, compiled (module doc)."""

    packs: tuple[Pack, ...]
    schema_version: str
    model_revision: str
    lookup: SchemaLookup
    key_schema: KeySchema
    names: NameMap
    batches: BatchCompiler
    reference: Reference
    artifacts: tuple[CompiledArtifact, ...]

    def artifact(self, compiler: str, kind: str) -> CompiledArtifact:
        return next(a for a in self.artifacts if (a.compiler, a.kind) == (compiler, kind))


def compile_schema(
    packs: Sequence[Pack],
    core_rules: Path = CORE_RULES,
    model_revision: str = revision.CONTENT_HASH,
    key_scheme: int = revision.KEY_SCHEME,
) -> CompiledSchema:
    """Compile the packs into one schema version over the installed model revision."""
    version = schema_version(packs, core_rules, model_revision)
    lookup = build_lookup(packs)
    names = name_map(packs)
    keys = compile_key_schema(lookup, key_scheme)
    batches = BatchCompiler(lookup, names)
    model = batches.json_schema("model", schema_id(model_revision, version, "model_facing"))
    stored = batches.json_schema("stored", schema_id(model_revision, version, "stored"))
    decoding = decoding_form(model, schema_id(model_revision, version, "decoding"))
    reference = build_reference(packs, lookup, batches)
    artifacts = (
        artifact("schema_tables", "tables", schema_tables(packs, lookup)),
        artifact("json_schema", "batch.model_facing", model),
        artifact("json_schema", "batch.stored", stored),
        artifact("json_schema", "batch.decoding", decoding),
        artifact("annotator_reference", "reference", reference.markdown()),
    )
    return CompiledSchema(
        tuple(packs), version, model_revision, lookup, keys, names, batches, reference, artifacts
    )


def compile_paths(roots: Sequence[Path], **kwargs: Any) -> CompiledSchema:
    """Load the packs at `roots` and compile them into one schema version."""
    return compile_schema([load_pack(root) for root in roots], **kwargs)
