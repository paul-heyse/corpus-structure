"""PDF-only native Docling producer. Heavy imports and models belong to an owned operation."""

from __future__ import annotations

import dataclasses
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
from io import BytesIO
from pathlib import Path
from typing import Any, Literal

from .pdf_health import FormulaOutcome, ObservedFormulaStage
from .pdf_assets import PreparedPdfAssets
from .pdf_candidates import CandidatePage, capture_candidates
from .pdf_hierarchy import NativeSnapshot, native_nodes, snapshot


@dataclass(frozen=True, slots=True)
class PdfRecipe:
    layout_revision: str
    formula_revision: str
    device: Literal["cpu", "cuda"] = "cuda"
    ocr_device: Literal["cpu", "cuda"] = "cpu"
    parser_threads: int = 8
    stage_batch_size: int = 4
    timeout_seconds: float | None = None
    recipe_id: str = "docling-standard-pdf-v1"
    # Content-addressed prepared model assets; caller archives these bindings with recipe.
    model_artifacts: tuple[tuple[str, str], ...] = ()
    model_revisions: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.recipe_id != "docling-standard-pdf-v1":
            raise ValueError("unadmitted PDF recipe")
        for revision in (self.layout_revision, self.formula_revision):
            if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
                raise ValueError("model revision must be an immutable commit")
        if self.device not in {"cpu", "cuda"} or self.ocr_device not in {"cpu", "cuda"}:
            raise ValueError("device must be explicit CPU or CUDA")
        if self.parser_threads < 1 or self.stage_batch_size < 1 or (self.timeout_seconds is not None and self.timeout_seconds <= 0):
            raise ValueError("PDF capacity and deadline must be positive")
        repositories: set[str] = set()
        for repository, revision in self.model_revisions:
            if not repository or repository in repositories or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
                raise ValueError("runtime model repository revisions must be unique immutable commits")
            repositories.add(repository)
        names: set[str] = set()
        for name, digest in self.model_artifacts:
            if not name or name in names or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise ValueError("model artifact bindings require unique names and SHA-256")
            names.add(name)

    def to_bytes(self) -> bytes:
        return json.dumps(dataclasses.asdict(self), sort_keys=True, separators=(",", ":")).encode()

    @classmethod
    def from_bytes(cls, payload: bytes) -> PdfRecipe:
        from pydantic import TypeAdapter
        values = json.loads(payload)
        if not isinstance(values, dict) or set(values) != {f.name for f in dataclasses.fields(cls)}:
            raise ValueError("archived PDF recipe fields differ from this admitted recipe")
        return TypeAdapter(cls).validate_json(payload, strict=True)

    @property
    def digest(self) -> str:
        return sha256(self.to_bytes()).hexdigest()

    def options(self) -> Any:
        """Reconstruct finite native variants, never deserialize polymorphic option JSON."""
        from docling.datamodel.accelerator_options import AcceleratorOptions
        from docling.datamodel.pipeline_options import (
            CodeFormulaVlmOptions,
            HeadingHierarchyOptions,
            LayoutObjectDetectionOptions,
            OcrMode,
            PdfPipelineOptions,
            RapidOcrOptions,
            TableFormerMode,
            TableStructureOptions,
        )
        from docling.datamodel.vlm_engine_options import TransformersVlmEngineOptions

        layout = LayoutObjectDetectionOptions.from_preset("layout_heron_default")
        layout.model_spec.revision = self.layout_revision
        formula = CodeFormulaVlmOptions.from_preset(
            "codeformulav2",
            scale=2.0,
            expansion_factor=0.18,
            stop_on_repetition=True,
            engine_options=TransformersVlmEngineOptions(),
        )
        formula.model_spec.revision = self.formula_revision
        return PdfPipelineOptions(
            do_ocr=True,
            ocr_options=RapidOcrOptions(
                backend="onnxruntime",
                lang=["iso:en"],
                model_size="small",
                mode=OcrMode.PDF_AWARE_LAYOUT_REGIONS,
                replace_broken_text_layer=True,
                rapidocr_params={
                    "EngineConfig.onnxruntime.use_cuda": self.ocr_device == "cuda",
                    "Det.use_cuda": self.ocr_device == "cuda",
                    "Cls.use_cuda": self.ocr_device == "cuda",
                    "Rec.use_cuda": self.ocr_device == "cuda",
                },
            ),
            do_table_structure=True,
            table_structure_options=TableStructureOptions(
                mode=TableFormerMode.ACCURATE, do_cell_matching=True
            ),
            do_formula_enrichment=True,
            code_formula_options=formula,
            layout_options=layout,
            heading_hierarchy_options=HeadingHierarchyOptions(enabled=True),
            accelerator_options=AcceleratorOptions(
                num_threads=self.parser_threads, device=self.device
            ),
            ocr_batch_size=self.stage_batch_size,
            layout_batch_size=self.stage_batch_size,
            table_batch_size=self.stage_batch_size,
            document_timeout=self.timeout_seconds,
        )


@dataclass(frozen=True, slots=True)
class PdfConversion:
    original_digest: str
    recipe: bytes
    native: NativeSnapshot
    conversion_status: str
    errors: tuple[str, ...]
    formula_outcomes: tuple[FormulaOutcome, ...]
    packages: tuple[tuple[str, str], ...]
    page_range: tuple[int, int] | None
    runtime: tuple[tuple[str, str], ...] = ()
    effective_options: bytes = b"{}"
    inline_candidates: tuple[CandidatePage, ...] = ()


class PdfConverter:
    """One serial worker's native converter/model lifetime; publication is a separate owner."""

    def __init__(self, recipe: PdfRecipe, *, assets: PreparedPdfAssets | None = None) -> None:
        self.recipe = recipe
        self.assets = assets
        self._candidate_pages: list[CandidatePage] = []
        self._converter: Any = None
        self._formula: ObservedFormulaStage | None = None
        self._pipeline: Any = None
        self._options: Any = None

    def _prepare(self) -> None:
        if self._converter is not None:
            return
        from docling.datamodel.backend_options import ThreadedDoclingParseBackendOptions
        from docling.datamodel.base_models import InputFormat, ItemAndImageEnrichmentElement, Page
        from docling.datamodel.document import ConversionResult
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.models.base_model import GenericEnrichmentModel
        from docling.models.stages.page_assemble.page_assemble_model import PageAssembleModel
        from docling.models.stages.code_formula.code_formula_vlm_model import CodeFormulaVlmModel
        from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
        from docling_core.types.doc import DoclingDocument, NodeItem

        class NativeObservedStage(GenericEnrichmentModel[ItemAndImageEnrichmentElement]):
            progress_step = CodeFormulaVlmModel.progress_step

            def __init__(self, native: CodeFormulaVlmModel, observer: ObservedFormulaStage) -> None:
                self.native = native
                self.observer = observer
                self.elements_batch_size = native.elements_batch_size

            def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
                return self.native.is_processable(doc, element)

            def prepare_element(
                self, conv_res: ConversionResult, element: NodeItem
            ) -> ItemAndImageEnrichmentElement | None:
                return self.native.prepare_element(conv_res, element)

            def __call__(
                self, doc: DoclingDocument, element_batch: Iterable[ItemAndImageEnrichmentElement]
            ) -> Iterable[NodeItem]:
                yield from self.observer(doc, element_batch)

        if self.assets is not None:
            self.assets.verify()
            if self.recipe.model_artifacts != self.assets.files:
                raise ValueError("recipe model manifest differs from prepared runtime assets")
        self._options = self.recipe.options()
        if self.assets is not None:
            self._options.artifacts_path = self.assets.root
        converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=StandardPdfPipeline,
                    pipeline_options=self._options,
                    backend_options=ThreadedDoclingParseBackendOptions(
                        parser_threads=self.recipe.parser_threads,
                        max_concurrent_results=self.recipe.parser_threads,
                    ),
                )
            },
        )
        converter.initialize_pipeline(InputFormat.PDF)
        pipeline = next(iter(converter.initialized_pipelines.values()))
        if not isinstance(pipeline, StandardPdfPipeline):
            raise RuntimeError("PDF conversion did not initialize the admitted StandardPdfPipeline")
        for index, stage in enumerate(pipeline.enrichment_pipe):
            if isinstance(stage, CodeFormulaVlmModel):
                self._formula = ObservedFormulaStage(stage)
                pipeline.enrichment_pipe[index] = NativeObservedStage(stage, self._formula)
                break
        if self._formula is None:
            raise RuntimeError("pinned pipeline lacks the required formula stage")
        native_assembler = pipeline.assemble_model
        capture = self._candidate_pages
        class CandidatePageAssembler(PageAssembleModel):
            def __init__(self) -> None:
                self.options = native_assembler.options

            def __call__(self, conv_res: ConversionResult,
                         page_batch: Iterable[Page]) -> Iterable[Page]:
                for page in native_assembler(conv_res, page_batch):
                    capture.append(capture_candidates(page))
                    yield page
        pipeline.assemble_model = CandidatePageAssembler()
        self._converter = converter
        self._pipeline = pipeline

    def formula_stage(self) -> ObservedFormulaStage:
        """Reuse the native formula engine without initializing unused layout/table/OCR stages."""
        if self._formula is None:
            from docling.datamodel.accelerator_options import AcceleratorOptions
            from docling.models.stages.code_formula.code_formula_vlm_model import CodeFormulaVlmModel
            if self.assets is not None:
                self.assets.verify()
                if self.recipe.model_artifacts != self.assets.files:
                    raise ValueError("formula recipe model manifest differs from prepared assets")
            options=self.recipe.options()
            native=CodeFormulaVlmModel(enabled=True,enable_remote_services=False,
                artifacts_path=self.assets.root if self.assets is not None else None,
                options=options.code_formula_options,
                accelerator_options=AcceleratorOptions(num_threads=self.recipe.parser_threads,device=self.recipe.device))
            native.elements_batch_size=self.recipe.stage_batch_size
            self._formula=ObservedFormulaStage(native)
        return self._formula

    def runtime_bindings(self) -> tuple[tuple[str, str], ...]:
        """Observed execution state; uninitialized OCR stages are explicitly not executed."""
        if self._pipeline is None or self._formula is None:
            return ()
        pipeline = self._pipeline
        entries = [
            ("layout.engine", type(pipeline.layout_model.engine).__name__),
            ("layout.device", str(getattr(pipeline.layout_model.engine, "_device", "unknown"))),
            ("table.device", str(pipeline.table_model.tf_predictor.get_device())),
            ("formula.engine", type(self._formula.native.engine).__name__),
            ("formula.device", str(getattr(self._formula.native.engine, "device", "unknown"))),
        ]
        reader = pipeline.ocr_model.reader
        for name in ("det", "cls", "rec"):
            stage = getattr(reader, "text_" + name)
            providers = (
                "not_executed"
                if stage is None
                else json.dumps(stage.session.session.get_providers())
            )
            entries.append(("ocr." + name + ".providers", providers))
        return tuple(entries)

    def convert(self, path: Path, *, page_range: tuple[int, int] | None = None) -> PdfConversion:
        """Return immutable products. A page range remains an explicitly partial source scope."""
        if path.suffix.lower() != ".pdf":
            raise ValueError("only PDF originals are admitted")
        return self.convert_bytes(path.read_bytes(), name=path.name, page_range=page_range)

    def convert_bytes(self, original: bytes, *, name: str = "original.pdf",
                      page_range: tuple[int, int] | None = None) -> PdfConversion:
        """Consume the already retained immutable original, without reopening an operator path."""
        if Path(name).suffix.lower() != ".pdf":
            raise ValueError("only PDF originals are admitted")
        if b"%PDF-" not in original[:1024]:
            raise ValueError("original does not have a PDF header")
        digest = sha256(original)
        if page_range is not None and not 1 <= page_range[0] <= page_range[1]:
            raise ValueError("page range uses positive physical pages in order")
        self._prepare()
        assert self._formula is not None
        self._formula.outcomes.clear()
        self._candidate_pages.clear()
        options = {} if page_range is None else {"page_range": page_range}
        from docling.datamodel.base_models import DocumentStream

        # The same immutable bytes determine custody and native input even if the operator
        # changes the path while models initialize. Never reopen that path for conversion.
        stream = DocumentStream(name=name, stream=BytesIO(original))
        result = self._converter.convert(stream, raises_on_error=False, **options)
        try:
            document = result.document
            native = snapshot(document)
            outcomes = list(self._formula.outcomes)
            observed = {row.item_ref for row in outcomes}
            for node in native_nodes(document).values():
                if str(node.label) == "formula" and node.self_ref not in observed:
                    outcomes.append(
                        FormulaOutcome(node.self_ref, "unknown", "not prepared for inference")
                    )
            return PdfConversion(
                digest.hexdigest(),
                self.recipe.to_bytes(),
                native,
                str(result.status.value),
                tuple(str(error.model_dump(mode="json")) for error in result.errors),
                tuple(outcomes),
                tuple(
                    (name, version(name)) for name in ("docling", "docling-core", "docling-parse")
                ),
                page_range,
                self.runtime_bindings(),
                self._options.model_dump_json(serialize_as_any=True).encode(),
                tuple(sorted(self._candidate_pages, key=lambda page: page.page_no)),
            )
        finally:
            result.input.release()


@dataclass(frozen=True, slots=True)
class CellCandidate:
    table_ref: str
    cell_index: int
    page_no: int


@dataclass(frozen=True, slots=True)
class CellEnrichment:
    source_digest: str
    native: NativeSnapshot
    outcomes: tuple[FormulaOutcome, ...]
    mappings: tuple[dict[str, Any], ...] = ()


def enrich_cells(
    source: NativeSnapshot,
    candidates: tuple[CellCandidate, ...],
    *,
    stage: ObservedFormulaStage,
    render_region: Any,
) -> CellEnrichment:
    """Recognize explicitly selected cells using an owned region-rendering port.

    Candidate discovery/coverage is a separate admitted operation. This function makes no
    all-table or inline coverage claim. Renderers receive physical page and native bbox,
    retaining origin; no visual-order string cleanup stands in for model inference.
    """
    from docling.datamodel.base_models import ItemAndImageEnrichmentElement
    from docling_core.types.doc import DocItemLabel, ProvenanceItem, RichTableCell

    from .pdf_hierarchy import load_snapshot

    document = load_snapshot(source)
    outcomes,mappings = apply_cells(document,candidates,stage=stage,render_region=render_region)
    return CellEnrichment(source.digest,snapshot(document),outcomes,mappings)


def apply_cells(document: Any,candidates: tuple[CellCandidate,...],*,
                stage: ObservedFormulaStage,render_region: Any):
    """Mutate an operation-owned native document; the enclosing operation finalizes identity."""
    from docling.datamodel.base_models import ItemAndImageEnrichmentElement
    from docling_core.types.doc import DocItemLabel,ProvenanceItem,RichTableCell
    nodes = native_nodes(document)
    if len(set(candidates)) != len(candidates):
        raise ValueError("duplicate cell candidate")
    start = len(stage.outcomes)
    mappings: list[dict[str, Any]] = []
    batch_size = max(1, stage.elements_batch_size)
    for offset in range(0, len(candidates), batch_size):
        elements = []
        for candidate in candidates[offset:offset + batch_size]:
            table = nodes.get(candidate.table_ref)
            if table is None or not hasattr(table, "data") or not hasattr(table.data, "table_cells"):
                raise ValueError("candidate does not name a native table")
            if not 0 <= candidate.cell_index < len(table.data.table_cells):
                raise ValueError("cell index outside native table")
            cell = table.data.table_cells[candidate.cell_index]
            if getattr(cell, "ref", None) is not None:
                raise ValueError("cell already has a qualified rich reference")
            if cell.bbox is None or candidate.page_no not in document.pages:
                raise ValueError("cell candidate lacks native geometry")
            if candidate.page_no not in {p.page_no for p in table.prov}:
                raise ValueError("candidate page is outside table provenance")
            image = render_region(candidate.page_no, cell.bbox)
            item = document.add_text(
                label=DocItemLabel.FORMULA,
                text=cell.text,
                orig=cell.text,
                parent=table,
                prov=ProvenanceItem(
                    page_no=candidate.page_no, bbox=cell.bbox, charspan=(0, len(cell.text))
                ),
            )
            mappings.append(dict(pointer=item.self_ref,origin_pointer=table.self_ref,
                source_field="cell_text",start=0,end=len(cell.text),cell_index=candidate.cell_index,kind="table_cell"))
            elements.append(ItemAndImageEnrichmentElement(item=item, image=image))
            table.data.table_cells[candidate.cell_index] = RichTableCell(
                **cell.model_dump(), ref=item.get_ref()
            )
        try:
            if len(list(stage(document, elements))) != len(elements):
                raise RuntimeError("cell enrichment did not return its complete native batch")
        finally:
            for element in elements:
                element.image.close()
    return tuple(stage.outcomes[start:]), tuple(mappings)


def publication_payload(
    conversion: PdfConversion,
    *,
    product_key: str,
    schema_digest: str,
    native: NativeSnapshot | None = None,
    section_refs: frozenset[str] = frozenset(),
    parent: tuple[int, str, str] | None = None,
    enrichment: CellEnrichment | None = None,
) -> dict[str, Any]:
    """Prepare declared native access rows for the shared semantic publication boundary.

    The trusted PDF contract validates this payload and its original/schema/recipe bytes.
    This adapter never assigns complete inline/cell coverage merely from detected formula items.
    """
    from .pdf_hierarchy import load_snapshot

    selected = conversion.native if native is None else native
    if native is not None and native.digest != conversion.native.digest and parent is None:
        raise ValueError("derived native document requires its qualified parent product")
    document = load_snapshot(selected)
    nodes = native_nodes(document)
    if not section_refs <= nodes.keys():
        raise ValueError("section membership names missing native nodes")
    # Native SQL checks this same declared traversal, including the deprecated retained root.
    order: list[str] = []
    visited: set[str] = set()

    def walk(pointer: str) -> None:
        if pointer in visited:
            raise ValueError("native traversal repeats an occurrence")
        visited.add(pointer)
        order.append(pointer)
        for child in nodes[pointer].children:
            walk(child.cref)

    walk(document.body.self_ref)
    walk("#/furniture")
    order.extend(sorted(nodes.keys() - visited))
    outcomes = list(conversion.formula_outcomes)
    if enrichment is not None:
        if enrichment.source_digest != conversion.native.digest or enrichment.native != selected:
            raise ValueError(
                "additional formula health is not qualified by the source/derived documents"
            )
        outcomes.extend(enrichment.outcomes)
    health_by_pointer: dict[str, FormulaOutcome] = {}
    for outcome in outcomes:
        if outcome.item_ref not in nodes or str(nodes[outcome.item_ref].label) != "formula":
            raise ValueError("formula health names a missing or non-formula occurrence")
        if outcome.item_ref in health_by_pointer:
            raise ValueError("duplicate formula health occurrence")
        health_by_pointer[outcome.item_ref] = outcome
    for pointer in order:
        if str(nodes[pointer].label) == "formula" and pointer not in health_by_pointer:
            health_by_pointer[pointer] = FormulaOutcome(
                pointer, "unknown", "no attributable inference outcome"
            )
    display_pointers = [pointer for pointer, item in nodes.items()
        if str(item.label) == "formula" and (item.parent is None or
            str(nodes[item.parent.cref].label) not in {"table", "inline"})]
    display_complete = conversion.conversion_status == "success" and all(
        health_by_pointer[pointer].outcome == "succeeded" for pointer in display_pointers)
    items: list[dict[str, Any]] = []
    regions: list[dict[str, Any]] = []
    for ordinal, pointer in enumerate(order):
        item = nodes[pointer]
        row: dict[str, Any] = {
            "pointer": pointer,
            "ordinal": ordinal,
            "label": str(item.label),
            "content_layer": item.content_layer.value,
        }
        if item.parent is not None:
            row["parent_pointer"] = item.parent.cref
        if hasattr(item, "text"):
            row["text"] = item.text
        owner = item
        visited: set[str] = set()
        while owner.self_ref not in section_refs and owner.parent is not None:
            if owner.self_ref in visited:
                raise ValueError("cyclic native containment")
            visited.add(owner.self_ref)
            owner = nodes[owner.parent.cref]
        if owner.self_ref in section_refs:
            row["section_pointer"] = owner.self_ref
        items.append(row)
        for index, prov in enumerate(getattr(item, "prov", ())):
            page = document.pages[prov.page_no]
            box = prov.bbox
            regions.append(
                {
                    "pointer": pointer,
                    "region_index": index,
                    "page_no": prov.page_no,
                    "page_width": page.size.width,
                    "page_height": page.size.height,
                    "left": box.l,
                    "top": box.t,
                    "right": box.r,
                    "bottom": box.b,
                    "origin": {"TOPLEFT": "top_left", "BOTTOMLEFT": "bottom_left"}[
                        str(box.coord_origin.value)
                    ],
                }
            )
    result: dict[str, Any] = {
        "recipe": "pdf-native-v1",
        "artifact_digest": conversion.original_digest,
        "source_scope": "whole_document" if conversion.page_range is None else "page_range",
        **(
            {"page_start": conversion.page_range[0], "page_end": conversion.page_range[1]}
            if conversion.page_range is not None
            else {}
        ),
        "product_key": product_key,
        "schema_digest": schema_digest,
        "recipe_digest": sha256(conversion.recipe).hexdigest(),
        "native_schema_version": selected.schema_version,
        "document": json.loads(selected.payload),
        "inline_candidate_pages": [dataclasses.asdict(page) for page in conversion.inline_candidates],
        "derivation_mappings": list(enrichment.mappings) if enrichment is not None else [],
        "health": {
            "conversion": conversion.conversion_status,
            "display_coverage": "complete" if display_complete else "partial",
            "inline_coverage": "unknown",
            "cell_coverage": "unknown",
            "issues": list(conversion.errors),
            "formula_outcomes": [
                {
                    "pointer": outcome.item_ref,
                    "outcome": outcome.outcome,
                    **({"error": outcome.error} if outcome.error else {}),
                }
                for outcome in health_by_pointer.values()
            ],
        },
        "items": items,
        "regions": regions,
    }
    if parent is not None:
        result.update(
            parent_task_id=parent[0], parent_product_key=parent[1], parent_digest=parent[2]
        )
    return result
