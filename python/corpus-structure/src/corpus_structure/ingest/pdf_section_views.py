"""Selected native source views from exact published values, without whole-book hydration."""

from __future__ import annotations

from typing import Any, Literal

from corpus_structure.core.method import SourceViewDraft
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.source_views import resolve_native_sections, source_view_health

from .pdf_hierarchy import project_section_nodes, section_text_recipe, section_view_key


class NoQualifiedSections(ValueError):
    """An explicitly requested section requires native organization."""


def select_published_sections(rows, selections, membership, scope):
    scoped_sections = isinstance(scope, dict) and scope.get("kind") == "native_sections"
    include_body = not selections and not scoped_sections
    names = {row["pointer"]: row["name"] for row in rows}
    matched = [
        row["pointer"]
        for row in rows
        if not selections or row["pointer"] in selections or row["name"] in selections
    ]
    if not rows:
        if include_body:
            return ("#/body",)
        raise NoQualifiedSections("native product has no requested organizational sections")
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
        selected = tuple(
            row["pointer"]
            for row in rows
            if row["pointer"] in chosen or chosen.intersection(row["ancestors"])
        )
    else:
        selected = tuple(
            row["pointer"]
            for row in rows
            if row["pointer"] in chosen and not chosen.intersection(row["ancestors"])
        )
    return ("#/body", *selected) if include_body else selected


def published_section_drafts(
    reader: PublishedPdfReader,
    *,
    document_id: int,
    selections: tuple[str, ...],
    membership: Literal["direct", "descendants"],
    scope: Any,
    consumer_release: str,
    projection_policy: bytes | None = None,
) -> tuple[SourceViewDraft, ...]:
    sections = reader.sections()
    selected_sections = select_published_sections(sections, selections, membership, scope)
    # The root is an authentic residual scope, never an invented section heading.
    section_refs = frozenset({"#/body", *(row["pointer"] for row in sections)})
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
    recipe = section_text_recipe(reference, analysis_eligible=True, policy=projection_policy)
    result = []
    for section in selected_sections:
        selected_membership = "direct" if section == "#/body" else membership
        rows = reader.section_nodes(section, selected_membership)
        members = tuple(row["pointer"] for row in rows if row["role"] == "selected")
        ancestors = tuple(row["pointer"] for row in rows if row["role"] == "ancestor")
        nodes = {row["pointer"]: row["native_json"] for row in rows}
        if len(nodes) != len(rows) or section not in members:
            raise ValueError("published section closure is absent or ambiguous")
        if section == "#/body" and members == ("#/body",):
            continue
        # The relational membership is body-only, while admitted native values keep
        # their original children, including furniture. Qualify that excluded
        # frontier under the same immutable pin before the projector follows it;
        # these values never become selected members or source-frame items.
        frontier = {
            child["$ref"]
            for pointer in members
            for child in nodes[pointer].get("children", ())
            if child["$ref"] not in nodes
            and not (selected_membership == "direct" and child["$ref"] in section_refs)
        }
        if frontier:
            excluded = reader.selected_native_items(tuple(sorted(frontier)))
            if set(excluded) != frontier:
                pointer = min(set(excluded).symmetric_difference(frontier))
                raise ValueError(
                    f"published section {section} has an unqualified missing child {pointer}: "
                    "exact frontier selection differs"
                )
            for pointer, value in excluded.items():
                layer = value.get("content_layer", "body")
                if (
                    value.get("self_ref") != pointer
                    or not isinstance(layer, str)
                    or layer == "body"
                ):
                    raise ValueError(
                        f"published section {section} has an unqualified missing child {pointer}: "
                        f"identity={value.get('self_ref')!r}, "
                        f"content_layer={value.get('content_layer', 'body')!r}"
                    )
            nodes.update(excluded)
        projection = project_section_nodes(
            nodes,
            reference.content_digest,
            section,
            "direct" if selected_membership == "direct" else "descendant",
            section_refs=section_refs,
            selected_items=members,
            projection_policy=recipe,
            original_digest=reader.revision["source_digest"],
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
            selected_membership,
            [nodes[pointer] for pointer in members],
            ancestors,
            recognition_coverage=coverage,
            recognition_coverage_present=coverage_present,
        )
        key = section_view_key(
            consumer_release, reference, section, selected_membership, True, recipe
        )
        result.append(
            SourceViewDraft(
                key,
                document_id,
                reference,
                section,
                selected_membership,
                projection.text,
                tuple(piece.to_wire() for piece in projection.pieces),
                members,
                ancestors,
                health,
                recipe,
            )
        )
    return tuple(result)
