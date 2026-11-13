"""Retained diagnostic meaning in current generic source inspection/export."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.serve.native_source import (
    _published_alignment_reports,
    _published_derivations,
    _published_parent_product,
)

from . import pdf_integration_support as integrated_fixtures

native_source = integrated_fixtures.native_source


@pytest.mark.parametrize("runtime", [False, True])
def test_published_header_reads_bounded_native_metadata_without_body_or_legacy_reads(runtime):
    from corpus_structure.serve.native_source import _published_native_header

    closed = []
    native = dict(
        source_scope="whole_document",
        conversion="success",
        inline_coverage="unknown",
        formula_outcomes=[{"irrelevant": "excluded"}],
    )
    report = {"effective_options": '{"opaque":"retained\\u0000Ω"}'}

    class HeaderReader:
        def __init__(self):
            self.revision = dict(
                release_id="producer", logical_digest="a" * 64, source_digest="b" * 64
            )

        def iter_rows(self, family, filters, *, batch_size):
            assert family == "companion" and filters == {"family": "health"} and batch_size == 3
            try:
                yield native
                yield {"source_fidelity": "unassessed"}
            finally:
                closed.append("health")

        def decode_companion_row(self, row):
            return row

        def native_metadata(self, kind):
            assert runtime and kind == "runtime_report"
            try:
                yield report
            finally:
                closed.append("runtime")

    header = _published_native_header(HeaderReader(), 17, runtime=runtime)
    assert header.origin_run == 17 and header.release_id == "producer"
    assert header.health == dict(conversion="success", inline_coverage="unknown")
    assert header.runtime_report == (report if runtime else None)
    assert closed == (["health", "runtime"] if runtime else ["health"])


@pytest.mark.parametrize("defect", ["missing-health", "ambiguous-health", "ambiguous-runtime"])
def test_published_header_refuses_missing_or_ambiguous_native_metadata(defect):
    from corpus_structure.serve.native_source import _published_native_header

    class HeaderReader:
        def iter_rows(self, *_, **__):
            yield from (
                []
                if defect == "missing-health"
                else [dict(source_scope="whole_document")]
                * (3 if defect == "ambiguous-health" else 1)
            )

        def decode_companion_row(self, row):
            return row

        def native_metadata(self, kind):
            yield from ({"effective_options": "{}"}, {"effective_options": "{}"})

    with pytest.raises(ValueError, match=r"unavailable or ambiguous|runtime metadata is ambiguous"):
        _published_native_header(HeaderReader(), 17, runtime=True)


class DiagnosticReader:
    reference = ProductReference(42, "integrated", "a" * 64)

    def __init__(self, reports=(), *, available=True):
        self.reports = reports
        self.available = available
        self.requests = []

    def has_native_metadata(self, kind):
        assert kind == "inline_alignment_reports"
        return self.available

    def selected_item_reports(self, pointers, *, kinds):
        self.requests.append(tuple(pointers))
        return self.reports

    def candidate_bases(self, addresses):
        return {address: "native-vector-gap-v1" for address in addresses}


def test_derivation_preserves_original_ordinal_range_and_product_custody():
    reader = DiagnosticReader(
        [
            dict(body=dict(kind="cell_reports", value=dict(cell_index=0))),
            dict(
                body=dict(
                    kind="derivation_mappings",
                    ordinal=17,
                    value=dict(
                        pointer="#/texts/9",
                        origin_pointer="#/texts/3",
                        source_field="text",
                        start=4,
                        end=11,
                        kind="native_text_range",
                    ),
                )
            ),
        ]
    )
    assert list(_published_derivations(reader, ("#/texts/9",))) == [
        dict(
            task_id=42,
            product_key="integrated",
            pointer="#/texts/9",
            mapping_index=17,
            origin_pointer="#/texts/3",
            source_field="text",
            start_offset=4,
            end_offset=11,
            cell_index=None,
            kind="native_text_range",
        )
    ]
    assert reader.requests == [("#/texts/9",)]


def test_alignment_retains_original_prose_pointers_without_relabelling_them():
    report = dict(
        page_no=85,
        candidate_index=3,
        item_pointers=["#/texts/3"],
        outcome="unresolved",
        basis="ambiguous",
        detail="two matches",
    )
    reader = DiagnosticReader(
        [
            dict(body=dict(kind="inline_alignment_reports", value=report)),
            dict(body=dict(kind="cell_reports", value=dict(cell_index=0))),
        ]
    )
    assert _published_alignment_reports(reader, "#/texts/9") == [
        dict(report, candidate_basis="native-vector-gap-v1")
    ]
    assert "candidate_basis" not in report
    assert reader.requests == [("#/texts/9",)]


def test_absent_diagnostic_profile_is_distinct_from_an_assessed_empty_selection():
    unavailable = DiagnosticReader(available=False)
    assert _published_alignment_reports(unavailable, "#/texts/9") is None
    assert unavailable.requests == []
    assessed = DiagnosticReader()
    assert _published_alignment_reports(assessed, "#/texts/9") == []
    assert assessed.requests == [("#/texts/9",)]


def test_structural_input_preserves_original_product_custody():
    class Inputs:
        def iter_companions(self, family):
            assert family == "input"
            yield dict(role="recognition", task_id=9, product_key="ocr", content_digest="b" * 64)
            yield dict(
                role="structural", task_id=3, product_key="organized", content_digest="c" * 64
            )

    assert _published_parent_product(Inputs()) == dict(
        task_id=3, product_key="organized", content_digest="c" * 64
    )


@pytest.mark.parametrize(
    "change",
    [
        None,
        "helper_bytes",
        "schema",
        "release",
        "contract",
        "kind",
        "abi",
        "missing_receipt",
        "receipt_frozen",
        "unpassed",
    ],
)
def test_record_identity_requires_qualified_producer_archive(monkeypatch, change):
    from corpus_structure.semantic import pdf_contracts, pdf_record_reader, pdf_storage
    from corpus_structure.semantic._operation_calls import PdfBuildValidation

    context = replace(pdf_contracts.trusted_pdf_context(), release_id="producer-release")
    revision = dict(
        build_id="bound-build",
        frozen_digest="e" * 64,
        logical_digest="a" * 64,
        release_id=context.release_id,
        schema_digest=context.native_schema_digest,
        kind="integrated",
    )
    identity = dict(contract_digest="d" * 64, kind="integrated")
    receipt = PdfBuildValidation(
        build_id="bound-build",
        frozen_digest="e" * 64,
        logical_digest="a" * 64,
        contract_digest="d" * 64,
        native_callbacks=True,
        native_contract_digest="b" * 64,
    )
    assert identity["contract_digest"] != context.contract_digest
    if change == "helper_bytes":
        context = replace(
            context,
            _execution=replace(
                context.execution,
                implementation_digests=tuple(
                    (name, "0" * 64 if name in {"pdf/storage.py", "pdf/integrated.py"} else digest)
                    for name, digest in context.execution.implementation_digests
                ),
            ),
        )
    elif change == "abi":
        context = replace(
            context,
            _execution=replace(
                context.execution,
                implementations=tuple(
                    replace(binding, version="unsupported")
                    if binding.id == "read_pdf_product"
                    else binding
                    for binding in context.execution.implementations
                ),
            ),
        )
    elif change == "schema":
        revision["schema_digest"] = "0" * 64
    elif change == "release":
        revision["release_id"] = "consumer-release"
    elif change == "contract":
        identity["contract_digest"] = "0" * 64
    elif change == "kind":
        revision["kind"] = "native"
    elif change == "missing_receipt":
        receipt = None
    elif change == "receipt_frozen":
        receipt = receipt.model_copy(update={"frozen_digest": "0" * 64})
    elif change == "unpassed":
        receipt = receipt.model_copy(update={"native_callbacks": False})
    monkeypatch.setattr(pdf_contracts, "pdf_context_for_task", lambda *_: context)
    monkeypatch.setattr(
        pdf_record_reader,
        "published_record_reader",
        lambda *_args, **_kwargs: SimpleNamespace(
            revision=revision, validation_receipt=lambda: receipt
        ),
    )
    connection = MagicMock()
    connection.execute.return_value.mappings.return_value.one.return_value = identity
    if change not in {None, "helper_bytes"}:
        with pytest.raises(pdf_storage.NativeDocumentUnavailable):
            pdf_storage._pdf_product_identity(connection, 42, "selected", "a" * 64)
    else:
        assert pdf_storage._pdf_product_identity(connection, 42, "selected", "a" * 64) == identity


def test_exact_cell_context_does_not_broaden_same_pointer_or_foreign_occurrence_id():
    from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
    from corpus_structure.semantic.pdf_storage import _record_occurrence_value

    cell = "#/tables/0/data/table_cells/0"
    native_digest = "b" * 64
    selected = dict(
        local_id=cell,
        body=dict(
            occurrence_id=cell,
            pointer="#/tables/0",
            kind="cell",
            cell_index=0,
            precision="cell",
            address_space="native_cell",
        ),
    )
    own_endpoint = dict(
        relation_id="selected-cell",
        ordinal=1,
        role="output",
        occurrence_id=cell,
        target_task_id=0,
        target_product_key="@self",
        target_content_digest="@self",
    )
    foreign_endpoint = dict(
        own_endpoint,
        relation_id="foreign-same-id",
        target_task_id=99,
        target_product_key="foreign",
        target_content_digest="c" * 64,
    )
    original_endpoint = dict(
        own_endpoint,
        ordinal=0,
        role="input",
        target_task_id=41,
        target_product_key="native",
        target_content_digest=native_digest,
    )

    class Reader(PublishedPdfReader):
        def __init__(self):
            self.reference = ProductReference(42, "selected", "a" * 64)
            self.revision = dict(kind="integrated")
            self.native_addresses = []

        def iter_rows(self, family, filters=None, **kwargs):
            assert family == "endpoint"
            assert filters is not None
            if "occurrence_id" in filters:
                yield foreign_endpoint
                yield own_endpoint
            else:
                assert filters == {"relation_id": "selected-cell"}
                yield original_endpoint
                yield own_endpoint

        def _one(self, family, filters=None):
            assert family == "companion"
            if filters == {"family": "relation", "local_id": "selected-cell"}:
                return dict(
                    local_id="selected-cell",
                    ordinal=0,
                    body=dict(
                        kind="decision",
                        relation_id="selected-cell",
                        outcome="selected",
                        endpoints=[
                            dict(role="input", input_index=0, occurrence_id=cell),
                            dict(role="output", occurrence_id=cell),
                        ],
                    ),
                )
            assert filters == {"family": "input", "local_id": "0"}
            return dict(
                body=dict(
                    role="structural",
                    task_id=41,
                    product_key="native",
                    content_digest=native_digest,
                )
            )

        def context_rows(self, family, pointers, section_pointer):
            assert pointers == ["#/tables/0"] and section_pointer == "#/body"
            if family == "coverage":
                yield dict(local_id="whole", body=dict(scope="whole_document", supports=[]))
            else:
                assert family == "mapping_report"

        def native_items(self, pointers):
            self.native_addresses.extend(pointers)
            assert pointers == (cell,)
            return {cell: dict(text="opaque\x00é", bbox=dict(l=10, t=100, r=60, b=120))}

        def source_context(self, *args, **kwargs):
            raise AssertionError("exact occurrence must not request table-wide context")

    reader = Reader()
    actual = reader.occurrence_context((selected,), "#/body", row_budget=6)
    assert [row["occurrence_id"] for row in actual["occurrences"]] == [cell]
    assert [row["relation_id"] for row in actual["relations"]] == ["selected-cell"]
    assert [
        (row["target_task_id"], row["target_product_key"], row["role"])
        for row in actual["relations"][0]["endpoints"]
    ] == [(41, "native", "input"), (42, "selected", "output")]
    detailed = _record_occurrence_value(reader, actual["occurrences"][0]["body"])
    assert detailed["native_value"] == dict(text="opaque\x00é", bbox=dict(l=10, t=100, r=60, b=120))
    assert reader.native_addresses == [cell]
    with pytest.raises(ValueError, match="row budget"):
        reader.occurrence_context((selected,), "#/body", row_budget=5)


def test_native_cell_detail_decodes_only_its_exact_retained_record(monkeypatch, native_source):
    from copy import deepcopy

    from docling_core.types.doc import DoclingDocument

    from corpus_structure.semantic.pdf_storage import _record_occurrence_value

    from .test_pdf_record_reader import NativeRows

    document = DoclingDocument.model_validate(native_source.payload["document"]).model_dump(
        mode="json", by_alias=True, exclude_computed_fields=True
    )
    cell = document["tables"][0]["data"]["table_cells"][0]
    cell["text"] = "retained\x00é"
    expected = deepcopy(cell)
    reader = NativeRows(document)

    def refuse_document():
        raise AssertionError("cell detail must not hydrate the table or document")

    monkeypatch.setattr(reader, "hydrate_document", refuse_document)
    body = dict(pointer="#/tables/0", kind="cell", cell_index=0)
    assert _record_occurrence_value(reader, body)["native_value"] == expected
    assert body == dict(pointer="#/tables/0", kind="cell", cell_index=0)


@pytest.mark.parametrize("port", ["items", "regions"])
@pytest.mark.parametrize("custody", ["supported", "missing", "changed_bytes", "unsupported"])
def test_published_native_ports_qualify_retained_schema_before_legacy_gate(
    monkeypatch, port, custody
):
    import json
    from hashlib import sha256

    from corpus_structure.semantic import pdf_contracts, pdf_record_reader, pdf_storage
    from corpus_structure.semantic.pdf_records import native_schema_bytes

    installed = native_schema_bytes()
    declaration = json.loads(installed)
    if custody == "unsupported":
        declaration["properties"]["name"]["type"] = "integer"
    # Different retained bytes, with the same supported schema meaning in the positive case.
    retained = json.dumps(declaration, sort_keys=True).encode()
    digest = sha256(retained).hexdigest()
    assert digest != sha256(installed).hexdigest()
    producer = SimpleNamespace(
        release_id="retained-producer",
        contract_digest="c" * 64,
        native_schema_digest=digest,
        execution=SimpleNamespace(
            require_operation=lambda name: SimpleNamespace(implementation="read_pdf_product"),
            implementations=(
                SimpleNamespace(
                    id="read_pdf_product", owner="semantic.pdf_storage", symbol="read_pdf_product"
                ),
            ),
        ),
    )
    consumer = SimpleNamespace(release_id="current-consumer")
    connection = MagicMock()
    selected = []
    from corpus_structure.semantic._operation_calls import PdfBuildValidation

    receipt = PdfBuildValidation(
        build_id="bound-build",
        frozen_digest="e" * 64,
        logical_digest="f" * 64,
        contract_digest="d" * 64,
        native_callbacks=True,
        native_contract_digest="b" * 64,
    )

    def execute(statement):
        query = str(statement)
        result = MagicMock()
        result.__enter__.return_value = result
        if "FROM ops.pdf_product" in query:
            result.mappings.return_value.one.return_value = dict(
                kind="native",
                contract_digest=receipt.contract_digest,
            )
        elif "FROM kb.source_artifact" in query:
            result.scalar_one_or_none.return_value = (
                None
                if custody == "missing"
                else installed
                if custody == "changed_bytes"
                else retained
            )
        else:
            raise AssertionError("published read must not consult legacy selected-product headers")
        return result

    connection.execute.side_effect = execute

    class Reader(pdf_record_reader.PublishedPdfReader):
        def __init__(self):
            self.conn = connection
            self.reference = ProductReference(42, "native", "f" * 64)
            self.revision = dict(
                build_id="bound-build",
                release_id=producer.release_id,
                schema_digest=digest,
                frozen_digest=receipt.frozen_digest,
                logical_digest=receipt.logical_digest,
                kind="native",
            )

        def validation_receipt(self):
            return receipt

        def item_page(self, **selectors):
            assert self._prepared_native_mapping.digest == digest
            selected.append(selectors)
            return [
                dict(
                    product_id="bound-build",
                    revision_id="bound-build",
                    pointer="#/texts/0",
                    text="Retained text",
                )
            ]

        def regions(self, pointer):
            assert self._prepared_native_mapping.digest == digest
            return [
                dict(
                    product_id="bound-build",
                    revision_id="bound-build",
                    pointer=pointer,
                    region_index=0,
                    page_no=1,
                )
            ]

    reader = Reader()
    monkeypatch.setattr(reader, "_payload_context", lambda: producer)

    def published(conn, reference, **kwargs):
        assert conn is connection and reference == reader.reference
        assert kwargs["projection_context"] is consumer
        return reader

    monkeypatch.setattr(pdf_record_reader, "published_record_reader", published)
    monkeypatch.setattr(pdf_contracts, "pdf_context_for_task", lambda *_: producer)
    read = pdf_storage.read_native_items if port == "items" else pdf_storage.read_native_regions
    arguments = dict(
        task_id=42,
        product_key="native",
        content_digest="f" * 64,
        pointer="#/texts/0",
        projection_context=consumer,
    )
    if custody != "supported":
        expected = {
            "missing": "artifact is missing",
            "changed_bytes": "bytes differ",
            "unsupported": "no supported mapping",
        }[custody]
        with pytest.raises(pdf_storage.NativeDocumentUnavailable, match=expected):
            read(connection, **arguments)
        assert selected == []
    else:
        result = read(connection, **arguments)
        assert result[0]["task_id"] == 42 and result[0]["pointer"] == "#/texts/0"
        assert selected and "product_id" not in result[0] and "revision_id" not in result[0]
        assert (result[0]["text"] if port == "items" else result[0]["region_index"]) == (
            "Retained text" if port == "items" else 0
        )
