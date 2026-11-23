"""Symbol scope over admitted mathematical readings and retained source cues."""

from __future__ import annotations

from .data_product_reference import read_semantic_reference
from .declared_math_products import (
    DeclaredMathInput,
    DeclaredMathOccurrenceProduct,
    DeclaredMathScopeProduct,
    DeclaredMathSymbolicProduct,
    _RetainedCharacterization,
)
from .declared_structural_references import DeclaredStructuralSource
from .identity import canonical_bytes
from .reference_resolution import require_selected_whole_reference


def execute_scope(
    receiver, source, occurrences, symbolic, constructions, inherited=(), ancestor_sources=()
):
    from corpus_structure.methods.math.native import (
        _restore_reading,
        before_descendant_columns,
        domain_blocks_columns,
        native_scope_layout,
    )
    from corpus_structure.methods.math.scope import resolve_scopes
    from corpus_structure.methods.math.spans import MathSpan, SpanReading, extract, formula_values

    from .constructions.math_scope import retained_math_scope_products
    from .declared_record_sources import DeclaredNativeFrameSource
    from .source_products import FrozenNativeSource

    profile = receiver.profile
    frame = profile.frame(source)
    if profile.options.math_scope_binders is None:
        raise ValueError("symbol scope requires explicitly acquired binder policy")
    occurrence = DeclaredMathOccurrenceProduct.model_validate(occurrences)
    normalized = DeclaredMathSymbolicProduct.model_validate(symbolic)
    if (
        occurrence.phase != "occurrences"
        or normalized.phase != "symbolic"
        or not occurrence.source.matches_pin(frame.pin.values())
        or occurrence.source != normalized.source
        or occurrence.contexts != normalized.contexts
    ):
        raise ValueError(
            "symbol scope requires exact source and occurrence/normalization correspondence"
        )
    try:
        require_selected_whole_reference(
            read_semantic_reference(normalized.occurrence_input),
            role="occurrences",
            producing=profile.member("symbolic"),
            selected=profile.member("occurrences"),
        )
    except ValueError as error:
        raise ValueError(
            "symbol scope requires exact occurrence/normalization correspondence"
        ) from error
    retained = _RetainedCharacterization(
        profile.member("constructions").product,
        canonical_bytes(constructions),
        profile.prepared,
        "DdoPrimaryConstructionProduct",
    )
    primary = retained_math_scope_products(
        (retained,),
        FrozenNativeSource.acquire(profile.prepared, source),
        binders=profile.options.math_scope_binders,
        rules=profile.options.math_domain_rules,
    )
    domains = domain_blocks_columns(
        root=frame.section_pointer,
        text=frame.text,
        items=frame.items,
        ancestors=frame.ancestors,
        pieces=frame.pieces,
        rules=profile.options.math_domain_rules,
        primary_scope=primary,
    )
    content, segments, selected, topology, sections = native_scope_layout(
        root=frame.section_pointer,
        text=frame.text,
        items=frame.items,
        ancestors=frame.ancestors,
        pieces=frame.pieces,
        domains=domains,
    )
    native = {item["self_ref"]: item for item in frame.items}

    def readings(product):
        rows = []
        seen = set()
        contexts = {context.pointer: context for context in product.contexts}
        if len(contexts) != len(product.contexts) or set(contexts) != {
            record["pointer"] for record in product.items
        }:
            raise ValueError("mathematical scope context inventory differs from its readings")
        for record in product.items:
            profile.check_active()
            pointer = record["pointer"]
            if (
                pointer in seen
                or pointer not in native
                or record["recognized_latex"] != native[pointer]["text"]
            ):
                raise ValueError("mathematical scope reading differs from exact native formula")
            seen.add(pointer)
            if pointer not in segments:
                continue
            captured = contexts[pointer]
            if captured.recognized_latex != record["recognized_latex"]:
                raise ValueError("mathematical scope context differs from its exact formula")
            context = captured.reopen(profile.context_profile, profile.options)
            if context.stage_key("occurrences") != record["occurrence_basis"]:
                raise ValueError(
                    "mathematical scope reading differs from captured occurrence context"
                )
            rows.append(
                SpanReading(
                    MathSpan(
                        segments[pointer],
                        record["recognized_latex"],
                        selected[pointer].projected_start,
                    ),
                    _restore_reading(record, record["recognized_latex"], context),
                )
            )
        return rows

    occurrence_rows = readings(occurrence)
    normalized_rows = readings(normalized)
    if {row.span.segment.attrs["native_pointer"] for row in occurrence_rows} != {
        row.span.segment.attrs["native_pointer"] for row in normalized_rows
    }:
        raise ValueError("symbolic and occurrence populations differ")
    found = extract(occurrence_rows)
    pointers = {id(segment): pointer for pointer, segment in segments.items()}
    scopes = resolve_scopes(
        content,
        formula_values(normalized_rows),
        found.mentions,
        found.relations,
        profile.options.section().macro_table(),
        primary_scope=primary,
        sections_by_position={
            m.start: sections[topology.section(pointers[id(m.segment)])] for m in found.mentions
        },
    )
    issues = list(dict.fromkeys((*occurrence.issues, *normalized.issues)))
    if not primary.complete:
        issues.append("retained source binder coverage unavailable or incomplete")
    if any(item["pointer"] not in segments for item in occurrence.items):
        issues.append("recognized formula has no exact native text projection")
    parents = {}
    source_pins = profile.members("ancestor_sources")
    if len(source_pins) != len(ancestor_sources):
        raise ValueError("scope ancestor source population differs from admitted binding")
    for pin, body in zip(source_pins, ancestor_sources, strict=True):
        parent = DeclaredNativeFrameSource.acquire(
            profile.prepared, body, pin, project=profile.project
        )
        parents[(pin.product, pin.member)] = parent
    pins = profile.members("inherited")
    if len(pins) != len(inherited):
        raise ValueError("scope ancestor reports differ from admitted population")
    candidates = {}
    supplied = set()
    for pin, body in zip(pins, inherited, strict=True):
        product = DeclaredMathScopeProduct.model_validate(body)
        parent = parents.get((product.source.source_product, product.source.source_member))
        if (
            product.phase != "scope"
            or parent is None
            or not product.source.matches_pin(parent.pin.values())
            or product.source.original_source != frame.original_key
            or product.source.section_pointer not in {a["self_ref"] for a in frame.ancestors}
        ):
            raise ValueError("scope inheritance requires an exact retained source ancestor")
        supplied.add(parent.section_pointer)
        if product.outcome != "complete":
            issues.append("partial ancestor symbol scope: " + parent.section_pointer)
        order = {item["self_ref"]: n for n, item in enumerate(parent.items)}
        for row in product.items:
            if (
                row.get("outcome") != "resolved"
                or row.get("scope_pointer") != parent.section_pointer
                or row.get("binding_source") != product.source.model_dump(mode="json")
            ):
                continue
            pointer = row["binding_pointer"]
            before = before_descendant_columns(
                parent_items=parent.items,
                parent_ancestors=parent.ancestors,
                child_items=frame.items,
                child_ancestors=frame.ancestors,
                ancestor=parent.section_pointer,
                child_pointer=frame.section_pointer,
                pointer=pointer,
            )
            if before is None:
                issues.append("ancestor binding order unavailable: " + str(pointer))
            if before is not True:
                continue
            rank = (len(parent.ancestors), order[pointer], row["binding_start"])
            if row["symbol"] not in candidates or rank > candidates[row["symbol"]][0]:
                candidates[row["symbol"]] = (rank, pin, row)
    issues.extend(
        "unavailable ancestor symbol scope: " + a["self_ref"]
        for a in frame.ancestors
        if a.get("label") in {"section_header", "title"} and a["self_ref"] not in supplied
    )
    rows = []
    source_pin = DeclaredStructuralSource.model_validate(frame.pin.values())
    for scope in scopes:
        mention = scope.mention
        pointer = pointers[id(mention.segment)]
        offset = selected[pointer].projected_start
        site = scope.site
        row = {
            "pointer": pointer,
            "recognized_start": mention.start - offset,
            "recognized_end": mention.end - offset,
            "symbol": mention.name,
            "outcome": "unresolved",
            "reason": "native binding unavailable or unresolved",
        }
        if site is not None:
            binding_pointer = pointers[id(site.mention.segment)]
            binding_offset = selected[binding_pointer].projected_start
            row.update(
                outcome="resolved",
                reason=None,
                binding_pointer=binding_pointer,
                binding_start=site.mention.start - binding_offset,
                binding_end=site.mention.end - binding_offset,
                binding_source=source_pin.model_dump(mode="json"),
                binding_input=profile.reference("occurrences").model_dump(mode="json"),
                binding_quote=frame.text[site.sentence.start : site.sentence.end],
                scope_pointer=site.scope.attrs["native_pointer"],
                scope_start=site.start,
                scope_end=site.end,
                extent=str(site.extent),
            )
        elif mention.name in candidates:
            _, pin, basis = candidates[mention.name]
            row.update(
                {
                    key: value
                    for key, value in basis.items()
                    if key.startswith("binding_") or key.startswith("scope_")
                }
            )
            row.update(
                outcome="resolved",
                reason=None,
                extent="section",
                inherited_input=DeclaredMathInput.from_bound(
                    pin, project=profile.project
                ).model_dump(mode="json"),
            )
        rows.append(row)
    complete = (
        not issues
        and primary.complete
        and occurrence.outcome == normalized.outcome == "complete"
        and all(row["outcome"] == "resolved" for row in rows)
    )
    return DeclaredMathScopeProduct(
        source=source_pin,
        phase="scope",
        occurrence_input=profile.reference("occurrences"),
        symbolic_input=profile.reference("symbolic"),
        construction_input=profile.reference("constructions"),
        inherited_inputs=tuple(
            DeclaredMathInput.from_bound(pin, project=profile.project) for pin in pins
        ),
        source_declarations=occurrence.source_declarations,
        items=rows,
        issues=tuple(dict.fromkeys(issues)),
        outcome="complete" if complete else "partial",
    ).model_dump(mode="json")
