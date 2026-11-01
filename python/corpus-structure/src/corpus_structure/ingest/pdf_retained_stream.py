"""One-pass lossless storage migration of retained PDF envelopes.

Only the selected native document is materialized for the explicitly supported
native phase. Companion arrays are emitted one record at a time. Exact historical
byte identity is checked independently of decoded JSON values before publication.
"""

from __future__ import annotations

import gzip
from collections.abc import Iterable, Iterator, Mapping
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast

from ijson import get_backend
from ijson.common import ObjectBuilder

from corpus_structure.semantic.product_reference import ProductReference

if TYPE_CHECKING:
    from corpus_structure.semantic.pdf_payloads import PreparedPayloadFamily


class ReadableBytes(Protocol):
    def read(self, size: int = -1, /) -> bytes: ...


class JsonEventBackend(Protocol):
    def parse(
        self,
        source: ReadableBytes,
        *,
        use_float: bool,
    ) -> Iterator[tuple[str, str, Any]]: ...


# ijson installs parse dynamically when enriching its selected backend module.
# This protocol describes that documented public entrypoint at the library boundary.
_backend = cast(JsonEventBackend, get_backend("python"))


class _DigestReader:
    def __init__(self, stream: ReadableBytes):
        self.stream = stream
        self.digest = sha256()
        self.byte_length = 0

    def read(self, size: int = -1) -> bytes:
        value = self.stream.read(size)
        self.digest.update(value)
        self.byte_length += len(value)
        return value


_ARRAYS = {
    "inputs.item": "input",
    "occurrences.item": "occurrence",
    "relations.item": "relation",
    "mapping_reports.item": "mapping_report",
    "coverage.item": "coverage",
    "content.recognition_coverage.item": "recognition_coverage",
    "recognition_coverage.item": "recognition_coverage",
}
_VALUES = {
    "document": "document",
    "content.document": "document",
    "health": "health",
    "content.health": "native_health",
    "parent_task_id": "parent_task_id",
    "parent_product_key": "parent_product_key",
    "parent_digest": "parent_digest",
    "artifact_digest": "artifact_digest",
    "content.artifact_digest": "artifact_digest",
    "source_scope": "source_scope",
    "content.source_scope": "source_scope",
}

for _kind in (
    "inline_candidate_pages",
    "derivation_mappings",
    "cell_reports",
    "inline_alignment_reports",
    "recognition_coverage",
):
    for _prefix in ("", "content."):
        _ARRAYS[_prefix + _kind + ".item"] = "native_metadata:" + _kind
for _prefix in ("", "content."):
    _VALUES[_prefix + "runtime_report"] = "native_metadata:runtime_report"


def iter_retained_pdf_values(
    stream: ReadableBytes,
    *,
    expected_sha256: str,
) -> Iterator[tuple[str, Any]]:
    """Consume to exhaustion before freezing; a partial iterator verifies nothing.

    Python ijson with use_float=True deliberately matches json.loads' binary64
    native JSON profile while retaining arbitrary-size integer tokens. The C
    backend's use_float integer overflow does not satisfy that profile.
    """
    reader = _DigestReader(stream)
    builder: ObjectBuilder | None = None
    selected = ""
    depth = 0
    seen_document = False
    for prefix, event, value in _backend.parse(reader, use_float=True):
        if builder is None:
            family = _VALUES.get(prefix) or _ARRAYS.get(prefix)
            if family is None or event in {"end_map", "end_array", "map_key"}:
                continue
            if family == "document":
                if seen_document:
                    raise ValueError("retained PDF envelope has multiple native documents")
                seen_document = True
            if event not in {"start_map", "start_array"}:
                yield family, value
                continue
            builder = ObjectBuilder()
            selected = family
            depth = 0
        builder.event(event, value)
        if event in {"start_map", "start_array"}:
            depth += 1
        elif event in {"end_map", "end_array"}:
            depth -= 1
        if depth == 0:
            yield selected, builder.value
            builder = None
    if not seen_document:
        raise ValueError("retained PDF envelope has no native document")
    if reader.digest.hexdigest() != expected_sha256:
        raise ValueError("retained PDF exact serialization digest differs")


def derive_retained_native_projection(document: Mapping[str, Any]) -> tuple[dict[str, Any], int]:
    """Remove only verified serialization-only TableData grids before identity.

    Docling owns the native computed property; the retained validation contract
    selects the supported historical serialization profile. Each table is checked
    separately. Other fields, cell values and the caller's supplied value survive
    unchanged. Exact historical bytes are retained independently by the caller.
    """
    from copy import deepcopy
    from importlib.metadata import version

    from docling_core.types.doc import TableData

    from corpus_structure.semantic.pdf_records import _difference, native_validation_contract

    contract = native_validation_contract()
    if version("docling-core") != contract["docling_core_version"]:
        raise ValueError("retained native projection requires the pinned Docling core")
    policy = contract["retained_serialization_projection"]
    computed = policy["computed_field"]
    if policy["native_class"] != "TableData" or computed not in TableData.model_computed_fields:
        raise ValueError("unsupported retained computed-field projection policy")
    count = 0

    def table_data(value: Mapping[str, Any], address: str) -> Mapping[str, Any]:
        nonlocal count
        undeclared = set(value) - set(TableData.model_fields) - {computed}
        if undeclared:
            raise ValueError(f"{address}: undeclared TableData fields: {sorted(undeclared)}")
        if computed not in value:
            return value
        declared = {key: child for key, child in value.items() if key != computed}
        validation_input = deepcopy(declared)
        native = TableData.model_validate(validation_input)
        unchanged = native.model_dump(
            mode="json",
            by_alias=True,
            exclude_unset=True,
            exclude_computed_fields=True,
        )
        difference = _difference(declared, validation_input)
        if difference is None:
            difference = _difference(declared, unchanged)
        if difference is not None:
            raise ValueError(
                f"{address}{difference[1:]}: native TableData validation changed supplied data"
            )
        expected = native.model_dump(include={computed}, **policy["serialization"])[computed]
        difference = _difference(value[computed], expected)
        if difference is not None:
            raise ValueError(
                f"{address}/{computed}{difference[1:]}: retained computed grid differs"
            )
        count += 1
        return declared

    projected = dict(document)
    tables = list(document.get("tables", ()))
    for index, table in enumerate(tables):
        if isinstance(table, Mapping) and isinstance(table.get("data"), Mapping):
            derived = table_data(table["data"], f"#/tables/{index}/data")
            if derived is not table["data"]:
                tables[index] = {**table, "data": derived}
    if "tables" in document:
        projected["tables"] = tables
    pictures = list(document.get("pictures", ()))
    for index, picture in enumerate(pictures):
        changed = dict(picture)
        meta = picture.get("meta")
        if isinstance(meta, Mapping) and isinstance(meta.get("tabular_chart"), Mapping):
            chart = meta["tabular_chart"]
            if isinstance(chart.get("chart_data"), Mapping):
                derived = table_data(
                    chart["chart_data"], f"#/pictures/{index}/meta/tabular_chart/chart_data"
                )
                if derived is not chart["chart_data"]:
                    changed["meta"] = {**meta, "tabular_chart": {**chart, "chart_data": derived}}
        if "annotations" in picture:
            annotations = list(picture["annotations"])
            for number, annotation in enumerate(annotations):
                if annotation.get("kind") == "tabular_chart_data" and isinstance(
                    annotation.get("chart_data"), Mapping
                ):
                    derived = table_data(
                        annotation["chart_data"],
                        f"#/pictures/{index}/annotations/{number}/chart_data",
                    )
                    if derived is not annotation["chart_data"]:
                        annotations[number] = {**annotation, "chart_data": derived}
            changed["annotations"] = annotations
        pictures[index] = changed
    if "pictures" in document:
        projected["pictures"] = pictures
    return projected, count


def retained_pdf_draft(
    path: Path,
    *,
    expected_sha256: str,
    product_key: str,
    original: bytes,
    schema_bytes: bytes,
    recipe_bytes: bytes,
    directory: Path,
    kind: Literal["native", "integrated"],
    structural_parent: ProductReference | None = None,
    payload_family: PreparedPayloadFamily | None = None,
):
    """Own the companion journal while the caller stages and seals this draft."""
    from contextlib import contextmanager

    from corpus_structure.core.method import PdfRecordPublicationDraft, RetainedPdfSerialization

    from .pdf_stream_reconciliation import ReconciliationJournal

    @contextmanager
    def owned():
        journal = ReconciliationJournal(directory)
        document = None
        health: Mapping[str, Any] | None = None
        integration_health: Mapping[str, Any] | None = None
        metadata_ordinals: dict[str, int] = {}
        retained_parent: dict[str, Any] = {}
        candidate_codec = payload_family
        opener = gzip.open if path.suffix == ".gz" else Path.open
        try:
            with opener(path, "rb") as source:
                for family, value in iter_retained_pdf_values(
                    source,
                    expected_sha256=expected_sha256,
                ):
                    if family in {"parent_task_id", "parent_product_key", "parent_digest"}:
                        retained_parent[family] = value
                    elif family == "document":
                        document = value
                    elif family == "artifact_digest":
                        if value != sha256(original).hexdigest():
                            raise ValueError("retained envelope original custody differs")
                    elif family == "source_scope":
                        if value != "whole_document":
                            raise ValueError(
                                "retained storage migration requires whole-document scope"
                            )
                    elif family == "native_health":
                        health = value
                    elif family == "health":
                        integration_health = value
                    elif family.startswith("native_metadata:"):
                        metadata_kind = family.split(":", 1)[1]
                        if metadata_kind == "inline_candidate_pages":
                            from corpus_structure.semantic.pdf_payloads import (
                                EncodedPagePayload,
                                prepare_payload_family,
                            )

                            if candidate_codec is None:
                                candidate_codec = prepare_payload_family()
                            value = EncodedPagePayload(
                                candidate_codec.encode(value),
                                candidate_codec.schema_digest,
                                candidate_codec.logical_digest(value),
                                value["page_no"],
                            )
                        ordinal = metadata_ordinals.get(metadata_kind, 0)
                        journal.collection("native_metadata").append(
                            {
                                "kind": metadata_kind,
                                "ordinal": ordinal,
                                "value": value,
                            }
                        )
                        metadata_ordinals[metadata_kind] = ordinal + 1
                    else:
                        journal.collection(family).append(value)
            journal.seal()
            if health is None:
                health = integration_health
                integration_health = None
            if document is None or health is None:
                raise ValueError("retained PDF requires native content and qualified health")
            if retained_parent and (
                len(retained_parent) != 3 or any(v is None for v in retained_parent.values())
            ):
                raise ValueError("retained native parent identity is incomplete")
            if bool(retained_parent) != (structural_parent is not None):
                raise ValueError(
                    "retained native parent requires explicit current structural mapping"
                )
            if retained_parent:
                ProductReference(
                    retained_parent["parent_task_id"],
                    retained_parent["parent_product_key"],
                    retained_parent["parent_digest"],
                )
            document, projected_grid_count = derive_retained_native_projection(document)
            from corpus_structure.semantic.identity import canonical_bytes
            from corpus_structure.semantic.pdf_records import native_validation_contract

            profile = native_validation_contract()["retained_serialization_projection"]["profile"]
            derived_recipe = canonical_bytes(
                {
                    "recipe_id": "retained-pdf-record-derivation-v1",
                    "source_recipe_sha256": sha256(recipe_bytes).hexdigest(),
                    "source_envelope_sha256": expected_sha256,
                    "native_projection_profile": profile,
                    "computed_grid_count": projected_grid_count,
                    **(
                        {
                            "retained_parent": retained_parent,
                            "structural_parent": structural_parent.values(),
                        }
                        if structural_parent
                        else {}
                    ),
                }
            )
            companions: dict[str, Iterable[Mapping[str, Any]]] = {
                family: journal.collection(family)
                for family in (
                    "input",
                    "occurrence",
                    "relation",
                    "mapping_report",
                    "coverage",
                    "native_metadata",
                )
            }
            # Legacy native envelopes have no occurrence index. Leave it absent
            # so publication derives the shared native projection; an explicit
            # nonempty or integrated index remains authoritative.
            if kind == "native" and not len(journal.collection("occurrence")):
                companions.pop("occurrence")
            if structural_parent is not None:
                if kind != "native":
                    raise ValueError("structural parent remapping is only a native derivation")
                companions["input"] = ({"role": "structural", **structural_parent.values()},)
            # Conversion health, integration health and storage derivation have
            # distinct contracts. Provenance belongs to the bound recipe above.
            companions["health"] = (
                {"health": dict(health), "source_scope": "whole_document"},
                *((dict(integration_health),) if integration_health is not None else ()),
            )
            yield PdfRecordPublicationDraft(
                document,
                product_key,
                original,
                schema_bytes,
                derived_recipe,
                health,
                companions=companions,
                kind=kind,
                retained_serialization=RetainedPdfSerialization(
                    path,
                    expected_sha256,
                    "gzip" if path.suffix == ".gz" else "none",
                ),
            )
        finally:
            journal.close()

    return owned()
