"""Selected native source views from exact published values, without whole-book hydration."""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Literal

from corpus_structure.core.method import SourceViewDraft
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.source_views import resolve_native_sections, source_view_health

from .pdf_hierarchy import project_section_nodes


class NoQualifiedSections(ValueError):
    """A published native graph needs its explicit global organization phase."""


def select_published_sections(rows, selections, membership, scope):
    names = {row["pointer"]: row["name"] for row in rows}
    matched = [
        row["pointer"]
        for row in rows
        if not selections or row["pointer"] in selections or row["name"] in selections
    ]
    if not rows:
        raise NoQualifiedSections(
            "native product has no qualified organizational sections; organize it before adoption"
        )
    if selections and len(matched) != len(set(selections)):
        raise ValueError("requested intact section selection is missing or ambiguous")
    if (
        membership == "descendants"
        and not selections
        and isinstance(scope, dict)
        and scope.get("kind") == "native_sections"
    ):
        matched = list(resolve_native_sections(names, scope["sections"]))
    chosen = set(matched)
    if membership == "direct":
        return tuple(
            row["pointer"]
            for row in rows
            if row["pointer"] in chosen or chosen.intersection(row["ancestors"])
        )
    return tuple(
        row["pointer"]
        for row in rows
        if row["pointer"] in chosen and not chosen.intersection(row["ancestors"])
    )


def published_section_drafts(
    reader: PublishedPdfReader,
    *,
    document_id: int,
    selections: tuple[str, ...],
    membership: Literal["direct", "descendants"],
    scope: Any,
    consumer_release: str,
) -> tuple[SourceViewDraft, ...]:
    sections = reader.sections()
    selected_sections = select_published_sections(sections, selections, membership, scope)
    section_refs = frozenset(row["pointer"] for row in sections)
    wrappers = [row for row in reader.iter_companions("health") if "source_scope" in row]
    if (
        len(wrappers) != 1
        or wrappers[0]["source_scope"] != "whole_document"
        or wrappers[0].get("conversion") != "success"
    ):
        raise ValueError("retained integrated source is not a whole PDF product")
    coverage_present = reader.has_native_metadata("recognition_coverage")
    common_health = {
        key: value
        for key, value in wrappers[0].items()
        if key not in {"source_scope", "page_start", "page_end", "formula_outcomes"}
    }
    reference = reader.reference
    recipe = canonical_bytes(
        dict(
            recipe="native-section-text-v6",
            content_layers=["body"],
            analysis_eligible=True,
            organization_owner=reference.values(),
        )
    )
    result = []
    for section in selected_sections:
        rows = reader.section_nodes(section, membership)
        members = tuple(row["pointer"] for row in rows if row["role"] == "selected")
        ancestors = tuple(row["pointer"] for row in rows if row["role"] == "ancestor")
        nodes = {row["pointer"]: row["native_json"] for row in rows}
        if len(nodes) != len(rows) or section not in members:
            raise ValueError("published section closure is absent or ambiguous")
        projection = project_section_nodes(
            nodes,
            reference.content_digest,
            section,
            "direct" if membership == "direct" else "descendant",
            section_refs=section_refs,
        )
        reports = reader.section_reports(members, (section, *ancestors))
        outcomes, coverage = [], []
        for report in reports:
            body = report["body"]
            if body["kind"] == "formula_outcomes":
                value = dict(pointer=body["pointer"], outcome=body["outcome"])
                if body.get("has_diagnostic"):
                    value["diagnostic_ref"] = dict(
                        reference.values(), family="native_metadata", local_id=report["local_id"]
                    )
                outcomes.append(value)
            elif body["kind"] == "recognition_coverage":
                coverage.append(body["value"])
        health = source_view_health(
            dict(common_health, formula_outcomes=outcomes),
            section,
            membership,
            [nodes[pointer] for pointer in members],
            ancestors,
            recognition_coverage=coverage,
            recognition_coverage_present=coverage_present,
        )
        key = (
            "source-view:"
            + sha256(
                canonical_bytes(
                    dict(
                        consumer_release=consumer_release,
                        native=reference.values(),
                        section=section,
                        membership=membership,
                        analysis_eligible=True,
                        recipe=sha256(recipe).hexdigest(),
                    )
                )
            ).hexdigest()
        )
        result.append(
            SourceViewDraft(
                key,
                document_id,
                reference,
                section,
                membership,
                projection.text,
                tuple(piece.to_wire() for piece in projection.pieces),
                members,
                ancestors,
                health,
                recipe,
            )
        )
    return tuple(result)
