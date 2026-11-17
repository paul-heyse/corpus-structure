"""Pinned public pages over one actual native-selected rich admission."""

from __future__ import annotations

import base64
import unicodedata
from contextlib import contextmanager
from functools import cache, lru_cache
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.demand_queries import _cursor
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.semantic.rich_queries import (
    RichQuery,
    RichQueryIndex,
    RichQueryRefused,
    query_rows,
)
from corpus_structure.semantic.selected_query_cache import (
    SELECTED_QUERY_CACHE,
    bounded_rows,
    byte_bounded_page,
    uncached_rows_from,
)

from .rich_knowledge import read_selected_rich_knowledge, read_selected_rich_reference

VERSION = "selected-rich-query-2"


@contextmanager
def rich_query_implementation(query):
    """Bind actual installed helper objects and selected semantic libraries, never archived code."""
    from corpus_structure._query_custody import RICH_QUERY_SOURCES

    names = tuple(
        name
        for name in RICH_QUERY_SOURCES
        if query.name
        in {
            "family_profile",
            "construction_profile",
            "families_where",
            "parameter_mapping",
            "transformations_of",
            "relations_between",
        }
        or name != "semantic/rich_statistics_queries.py"
    )
    with installed_read_implementation(
        type(query),
        sources=names,
        profile=VERSION,
        extra_libraries=("networkx",) if query.name == "relations_between" else (),
    ) as identity:
        yield identity


@cache
def _library_version(name):
    return version(name)


@lru_cache(maxsize=64)
def _installed_read_basis(contract, sources, profile, extra_libraries):
    from corpus_structure._query_custody import capture_sources

    root = Path(__file__).resolve().parents[1]
    captured = capture_sources(tuple(root / name for name in sources))
    libraries = {
        name: _library_version(name)
        for name in (
            "pydantic",
            "cachetools",
            "pydantic-core",
            "python-rapidjson",
            "regex",
            "PyYAML",
            "jsonschema",
            "referencing",
            "jsonschema-specifications",
            *extra_libraries,
        )
    }
    libraries["unicode"] = unicodedata.unidata_version
    identity = sha256(
        json_bytes(
            dict(
                version=profile,
                sources={
                    str(Path(path).relative_to(root)): digest for path, digest in captured.items()
                },
                query_contract=contract.model_json_schema(),
                libraries=libraries,
            )
        )
    ).hexdigest()
    return identity, captured


@contextmanager
def installed_read_implementation(contract, *, sources, profile, extra_libraries=()):
    """Name authenticated imported code; detect unsupported source/module drift."""
    from corpus_structure._query_custody import query_sources

    identity, captured = _installed_read_basis(
        contract, tuple(sources), profile, tuple(extra_libraries)
    )
    with query_sources(captured):
        yield identity


class RichQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    demand_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    query: RichQuery
    read_id: str | None = None
    expected_cut: str | None = None
    implementation: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    cursor: str | None = Field(default=None, max_length=32768)
    limit: int = Field(default=100, strict=True, ge=1, le=1000)
    max_bytes: int = Field(default=1048576, strict=True, ge=1024, le=67108864)
    max_graph_bytes: int = Field(default=8388608, strict=True, ge=1024, le=67108864)
    max_graph_members: int = Field(default=100000, strict=True, ge=1, le=1000000)

    @model_validator(mode="after")
    def exact_read(self):
        if (self.read_id is None) != (self.expected_cut is None):
            raise ValueError("a pinned rich read requires both read_id and expected_cut")
        return self

    def selection(self):
        return self.model_dump(
            mode="python",
            exclude={"cursor", "limit", "max_bytes", "read_id", "expected_cut", "implementation"},
        )


def decode_rich_cursor(value: str) -> dict:
    try:
        parsed = json_loads(base64.b64decode(value, altchars=b"-_", validate=True))
    except (ValueError, TypeError) as error:
        raise InvalidContinuation(
            "invalid rich query cursor", reason="invalid_continuation"
        ) from error
    if not isinstance(parsed, dict):
        raise InvalidContinuation("invalid rich query cursor", reason="invalid_continuation")
    return parsed


def serve_rich_query(connection, request: RichQueryRequest) -> dict:
    from corpus_structure._query_custody import SourceCustodyError

    try:
        with rich_query_implementation(request.query) as implementation:
            return _serve_rich_query(connection, request, implementation=implementation)
    except SourceCustodyError as error:
        raise RichQueryRefused(str(error)) from error


def _serve_rich_query(connection, request: RichQueryRequest, *, implementation: str) -> dict:
    if request.implementation is not None and request.implementation != implementation:
        raise InvalidContinuation(
            "rich resource requires its actual installed implementation",
            reason="invalid_continuation",
        )
    selection = sha256(json_bytes(semantic_value(request.selection()))).hexdigest()
    cursor = None if request.cursor is None else decode_rich_cursor(request.cursor)
    if cursor is not None and (
        set(cursor)
        != {"version", "implementation", "selection", "read", "cut", "reference", "ordinal"}
        or cursor["version"] != VERSION
        or cursor["implementation"] != implementation
        or cursor["selection"] != selection
    ):
        raise InvalidContinuation(
            "rich cursor differs from its actual query selection", reason="invalid_continuation"
        )
    continuation = None if cursor is None else cursor["read"]
    cut = None if cursor is None else CutSelection(json_bytes(cursor["cut"]))
    if request.read_id is not None:
        if cut is not None and (
            cut.record["read_id"] != request.read_id or cut.identity != request.expected_cut
        ):
            raise InvalidContinuation(
                "rich cursor differs from the requested native read", reason="invalid_continuation"
            )
        if continuation is None:
            continuation = dict(
                demand_id=request.demand_id,
                read_id=request.read_id,
                view="frontier",
                scope={"operation_id": "rich.admit", "product_ids": [request.product_id]},
            )
    selected = read_selected_rich_reference(
        connection,
        request.demand_id,
        project_id=request.project_id,
        product_id=request.product_id,
        continuation=continuation,
        cut=cut,
        max_bytes=request.max_graph_bytes,
    )
    if request.expected_cut is not None and selected.cut.identity != request.expected_cut:
        raise InvalidContinuation(
            "rich query differs from its pinned cut", reason="invalid_continuation"
        )
    reference = selected.reference.model_dump(mode="python")
    if cursor is not None and json_bytes(cursor["reference"]) != json_bytes(reference):
        raise InvalidContinuation(
            "rich query changed its actual root support", reason="invalid_continuation"
        )
    offset = 0 if cursor is None else cursor["ordinal"]
    if type(offset) is not int or offset < 0:
        raise InvalidContinuation("invalid rich row ordinal", reason="invalid_continuation")
    key = json_bytes(["rich", selected.cut.identity, implementation, reference, selection])
    entry = SELECTED_QUERY_CACHE.get(key)
    remaining = None
    metadata_provider = entry.record if entry is not None else None
    if entry is None:
        native_request = dict(json_loads(selected.read_request), view="products")
        whole = read_selected_rich_knowledge(
            connection,
            request.demand_id,
            project_id=request.project_id,
            product_id=request.product_id,
            continuation=native_request,
            cut=selected.cut,
            max_bytes=request.max_graph_bytes,
        )
        if whole.reference != selected.reference or whole.context != selected.context:
            raise InvalidContinuation(
                "rich body differs from its freshly acquired root", reason="invalid_continuation"
            )
        index = RichQueryIndex(whole.state, max_members=request.max_graph_members)

        def source():
            for row in query_rows(index, request.query):
                yield dict(
                    value=row.value,
                    unknowns=[index.unknowns[key] for key in sorted(index.unknowns)],
                )

        def current_metadata():
            return dict(unknowns=[index.unknowns[key] for key in sorted(index.unknowns)])
        metadata_provider = current_metadata
        entry, remaining = bounded_rows(source(), metadata_provider)
        if entry is not None:
            SELECTED_QUERY_CACHE.put(key, entry)
    assert metadata_provider is not None
    metadata = metadata_provider()
    rows = entry.rows(offset) if entry is not None else uncached_rows_from(remaining, offset)

    observed_unknowns = metadata["unknowns"]

    def public_rows():
        nonlocal observed_unknowns
        for packet in rows:
            observed_unknowns = packet["unknowns"]
            yield packet["value"]
        observed_unknowns = metadata_provider()["unknowns"]

    def report(end, values, more):
        next_cursor = (
            None
            if not more
            else _cursor(
                dict(
                    version=VERSION,
                    implementation=implementation,
                    selection=selection,
                    read=json_loads(selected.read_request),
                    cut=selected.cut.record,
                    reference=reference,
                    ordinal=end,
                )
            )
        )
        pinned = request.model_copy(
            update=dict(
                read_id=selected.cut.record["read_id"],
                expected_cut=selected.cut.identity,
                implementation=implementation,
            )
        )
        return dict(
            format=VERSION,
            implementation=implementation,
            cut_id=selected.cut.identity,
            cut=selected.cut.record,
            root=reference,
            query=request.query.model_dump(mode="python"),
            rows=values,
            cursor=next_cursor,
            scope=dict(
                knowledge_subject=selected.context.subject,
                subject_definition=selected.context.subject_definition,
                population=request.query.population,
                examined="one-selected-whole-admission",
                global_completeness="unknown",
            ),
            unknowns=observed_unknowns,
            resource_handle=_cursor(pinned.model_dump(mode="python")),
        )

    try:
        return byte_bounded_page(
            public_rows(),
            offset=offset,
            limit=request.limit,
            max_bytes=request.max_bytes,
            report=report,
            row_fields={"rows": lambda value: (value,)},
        )
    except InvalidContinuation:
        raise
    except ValueError as error:
        raise RichQueryRefused(str(error)) from error
    finally:
        if remaining is not None:
            remaining.close()
