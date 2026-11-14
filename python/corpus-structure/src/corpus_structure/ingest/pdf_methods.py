"""Pure retained PDF configuration, scope projection and conversion readers."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.core.method import SourceViewDraft
from corpus_structure.semantic.product_reference import ProductReference

from .pdf import PdfConversion, PdfRecipe
from .pdf_candidate_source import CandidatePageSource, InMemoryCandidatePageSource
from .pdf_candidates import CandidatePage, InlineCandidate
from .pdf_health import FormulaOutcome
from .pdf_hierarchy import NativeSnapshot, SectionPolicy, load_snapshot, native_nodes, project_section, section_text_recipe, section_view_key


class PdfRuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    layout_revision: str = "8f39ad3c0b4c58e9c2d2c84a38465abf757272d8"
    formula_revision: str = "ecedbe111d15c2dc60bfd4a823cbe80127b58af4"
    model_cache: Path = Field(default_factory=lambda: Path.home() / ".cache/docling/models")
    device: Literal["cpu", "cuda"] = "cuda"
    ocr_device: Literal["cpu", "cuda"] = "cpu"
    timeout_seconds: float | None = None
    parser_threads: int = Field(default=8, ge=1)
    stage_batch_size: int = Field(default=4, ge=1)

    def recipe(self) -> PdfRecipe:
        return PdfRecipe(
            self.layout_revision,
            self.formula_revision,
            self.device,
            self.ocr_device,
            self.parser_threads,
            self.stage_batch_size,
            self.timeout_seconds,
            recipe_id="docling-standard-pdf-stream-v1",
        )


class PdfIngestConfig(PdfRuntimeConfig):
    originals: tuple[str, ...] = ("siegrist_random/Full_PDF/Full.pdf",)
    section_rule: str = "native-organizational-headings-v2"
    section_pattern: str = r"^\d+(?:\.\d+)*\s*[:.)-]?\s+\S"
    organizational_heading_pattern: str = r"\S"
    local_heading_pattern: str = SectionPolicy("default").local_heading_pattern
    sections: tuple[str, ...] = ()
    membership: Literal["direct", "descendants"] = "direct"
    native_product: ProductReference | None = None

    def section_policy(self) -> SectionPolicy:
        return SectionPolicy(
            self.section_rule,
            self.section_pattern,
            organizational_pattern=self.organizational_heading_pattern,
            local_heading_pattern=self.local_heading_pattern,
        )



def _snapshot_from_values(values: Mapping[str, Any]) -> NativeSnapshot:
    from .pdf_hierarchy import NativeSnapshot

    payload = json.dumps(
        values["document"],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return NativeSnapshot(payload, sha256(payload).hexdigest(), values["native_schema_version"])


def _select_sections(
    nodes: Mapping[str, Any], cfg: PdfIngestConfig, *, scope: Any = None
) -> tuple[str, ...]:
    sections = [p for p, n in nodes.items() if str(n.label) in {"section", "chapter"}]
    include_body = not cfg.sections and not (
        isinstance(scope, dict) and scope.get("kind") == "native_sections"
    )
    if not sections:
        if include_body and "#/body" in nodes:
            return ("#/body",)
        raise ValueError(
            "native product has no qualified organizational sections; organize it before adoption"
        )
    matched = [
        p
        for p in sections
        if not cfg.sections or p in cfg.sections or nodes[p].name in cfg.sections
    ]
    if cfg.sections and len(matched) != len(set(cfg.sections)):
        raise ValueError("requested intact section selection is missing or ambiguous")
    if not cfg.sections and isinstance(scope, dict) and scope.get("kind") == "native_sections":
        from corpus_structure.semantic.source_views import resolve_native_sections

        matched = list(
            resolve_native_sections(
                {pointer: nodes[pointer].name for pointer in sections}, scope["sections"]
            )
        )
    matched_set = set(matched)

    def ancestry(pointer):
        node = nodes[pointer]
        while node.parent is not None:
            yield node.parent.cref
            node = nodes[node.parent.cref]

    if cfg.membership == "direct":
        selected = tuple(
            p for p in sections if p in matched_set or any(a in matched_set for a in ancestry(p))
        )
    else:
        selected = tuple(p for p in matched if not any(a in matched_set for a in ancestry(p)))
    return ("#/body", *selected) if include_body else selected


def _member_order(nodes, section_refs, section, membership):
    """Native body preorder for the explicit section membership, reused after mutation."""
    pointers = []

    def collect(pointer):
        item = nodes[pointer]
        if item.content_layer.value != "body" or (
            pointer != section and pointer in section_refs and membership == "direct"
        ):
            return
        pointers.append(pointer)
        for child in item.children:
            collect(child.cref)

    collect(section)
    return tuple(pointers)


def _drafts(
    document_id: int,
    native_product: ProductReference,
    native: NativeSnapshot,
    health: Mapping[str, Any],
    sections: tuple[str, ...],
    membership: Literal["direct", "descendants"],
    consumer_release: str,
    *,
    replacements: Mapping[tuple[str, str], int] | None = None,
    analysis_eligible: bool = True,
    recognition_coverage: Sequence[Mapping[str, Any]] = (),
    document: Any = None,
    node_index: dict[str, Any] | None = None,
    projection_policy: bytes | None = None,
    original_digest: str | None = None,
) -> tuple[SourceViewDraft, ...]:
    doc = load_snapshot(native) if document is None else document
    nodes = native_nodes(doc) if node_index is None else node_index
    section_refs = frozenset(
        p for p, n in nodes.items() if p == "#/body" or str(n.label) in {"section", "chapter"}
    )
    recipe = section_text_recipe(
        native_product, analysis_eligible=analysis_eligible, policy=projection_policy
    )
    from corpus_structure.semantic.source_views import formula_health_summary

    health = {
        **health,
        "formula_outcomes": formula_health_summary(
            health.get("formula_outcomes", ()), native_product
        ),
    }
    drafts = []
    for section in sections:
        selected_membership = "direct" if section == "#/body" else membership
        item_refs = _member_order(nodes, section_refs, section, selected_membership)
        if section == "#/body" and item_refs == ("#/body",):
            continue
        projection = project_section(
            doc,
            native.digest,
            section,
            "direct" if selected_membership == "direct" else "descendant",
            section_refs=section_refs,
            node_index=nodes,
            selected_items=item_refs,
            projection_policy=recipe,
            original_digest=original_digest,
        )
        ancestors = []
        item = nodes[section]
        while item.parent is not None:
            if item.parent.cref not in {"#/body", "#/furniture"}:
                ancestors.append(item.parent.cref)
            item = nodes[item.parent.cref]
        from corpus_structure.semantic.source_views import source_view_health

        view_health = source_view_health(
            health,
            section,
            selected_membership,
            [nodes[p].model_dump(mode="json", by_alias=True) for p in item_refs],
            tuple(reversed(ancestors)),
            recognition_coverage=recognition_coverage,
        )
        key = section_view_key(
            consumer_release,
            native_product,
            section,
            selected_membership,
            analysis_eligible,
            recipe,
        )
        drafts.append(
            SourceViewDraft(
                key,
                document_id,
                native_product,
                section,
                selected_membership,
                projection.text,
                tuple(p.to_wire() for p in projection.pieces),
                tuple(item_refs),
                tuple(reversed(ancestors)),
                view_health,
                recipe,
                replaces_source_view_id=(replacements or {}).get((section, selected_membership)),
                analysis_eligible=analysis_eligible,
            )
        )
    return tuple(drafts)




def _conversion_from_product(
    product, recipe_bytes: bytes, candidate_source: CandidatePageSource | None = None
) -> PdfConversion:
    values = product.values()
    if candidate_source is None:
        # Explicitly materialized native-product callers already own these values.
        # Preserve their observed metadata; the enrichment caller supplies a detached
        # source and never reconstructs the book candidate population here.
        candidate_source = InMemoryCandidatePageSource(
            CandidatePage(
                page["page_no"],
                page["has_words"],
                page["has_chars"],
                tuple(
                    InlineCandidate.from_wire(candidate) for candidate in page.get("candidates", ())
                ),
                page.get("has_vectors", False),
                page.get("native_text_quality", "unassessed"),
                tuple(page.get("ocr_regions", ())),
            )
            for page in values.get("inline_candidate_pages", ())
        )
    return PdfConversion(
        values["artifact_digest"],
        recipe_bytes,
        _snapshot_from_values(values),
        values["health"]["conversion"],
        tuple(values["health"].get("issues", [])),
        tuple(
            FormulaOutcome(row["pointer"], row["outcome"], row.get("error"))
            for row in values["health"].get("formula_outcomes", [])
        ),
        tuple(
            (r["name"], r["version"]) for r in values.get("runtime_report", {}).get("packages", [])
        ),
        (values["page_start"], values["page_end"])
        if values.get("source_scope") == "page_range"
        else None,
        runtime=tuple(
            (r["name"], r["value"]) for r in values.get("runtime_report", {}).get("bindings", [])
        ),
        effective_options=values.get("runtime_report", {}).get("effective_options", "{}").encode(),
        inline_candidates=candidate_source,
        confidence=values.get("runtime_report", {}).get("confidence", "{}").encode(),
    )
