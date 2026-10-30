"""Portable source-bound text/TeX product assembly; publication belongs to semantic operations."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from dataclasses import asdict
from typing import Any

from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.text_structure import (
    ADAPTER_ID, TEX_COMPONENT_CATEGORIES, TextComponent, canonical_partition, capture_text,
)
from corpus_structure.core.tex import MacroBinding, Token, effective_macros, tokens
from corpus_structure.ingest.macros import MacroEvent, MacroRead, MacroSource



def text_product_payload(canonical: str, *, root: Mapping[str, Any],
                         math_ranges: Sequence[tuple[int, int, str | None, str | None]] = (),
                         macro_sources: Sequence[MacroSource] = (),
                         fallback_macros: Mapping[str, MacroDef] | None = None,
                         fallback_source_ref: str | None = None,
                         structure: bool = True, product_key: str = "text",
                         expand_macros: bool = True,
                         canonical_regions: Sequence[TextComponent] = ()) -> dict[str, Any]:
    """Archive complete lexical capture, selected native structure and expansion custody.

    ``math_ranges`` uses canonical offsets and explicit source delimiters. An empty sequence
    requests only canonical capture (including text outside sentence blocks). Fallback definitions
    are archived as structured artifacts and a named derived TeX projection, never page bytes.
    ``expand_macros=False`` leaves expansion unrequested while preserving structural specs.
    Canonical prose uses text/whitespace runs; supplied ``canonical_regions`` retain source
    categories and boundaries outside declared mathematical ranges.
    """
    fallback = fallback_macros or {}
    if fallback and not fallback_source_ref:
        raise ValueError("fallback macros require an explicit dependency source reference")
    p: dict[str, Any] = dict(product_key=product_key, kind="text", root=dict(root),
        operation="prepare_parsing_text", adapter_id=ADAPTER_ID, lifecycle="available",
        semantic_state="ok", coverage="complete", representations=[], components=[], nodes=[],
        relationships=[], endpoints=[], mappings=[], mapping_endpoints=[],
        dependencies=[dict(name="source", kind="product", target_task_id=root["task_id"],
                           target_product_key=root["product_key"], target_content_digest=root["content_digest"])],
        interpretations=[], assessments=[])
    representations: dict[str, str] = {}

    def representation(key: str, text: str, kind: str) -> None:
        if key in representations:
            if representations[key] != text:
                raise ValueError("conflicting representation source reference: " + key)
            return
        representations[key] = text
        declared = dict(representation_id=key, kind=kind, unit="codepoint",
            extent_length=len(text), text_content=text, partition_state="complete", recognition_state="complete")
        p["representations"].append(declared)
        parts = canonical_partition(text, [(a, b) for a, b, _, _ in math_ranges], regions=canonical_regions) if kind == "canonical" else (
            TextComponent(TEX_COMPONENT_CATEGORIES[t.kind], t.start, t.end) for t in tokens(text)
        )
        for ordinal, part in enumerate(parts):
            if part.category == "unknown":
                declared["recognition_state"] = "partial"
            p["components"].append(dict(component_id=f"{key}:{ordinal}", ordinal=ordinal,
                category=part.category, representation_id=key, unit="codepoint",
                start_offset=part.start, end_offset=part.end))

    def mapping(operation: str, sources: Sequence[tuple[str, int, int]],
                targets: Sequence[tuple[str, int, int]], *, reason: str, fidelity: str = "exact",
                source_root: bool = False) -> None:
        key = f"m{len(p['mappings'])}"
        p["mappings"].append(dict(mapping_id=key, operation=operation, reason=reason, fidelity=fidelity))
        for side, extents in (("source", sources), ("target", targets)):
            for ordinal, (rep, a, b) in enumerate(extents):
                row = dict(mapping_id=key, side=side, ordinal=ordinal, representation_id=rep,
                           unit="codepoint", start_offset=a, end_offset=b)
                if source_root and side == "source":
                    row.update(dependency_name="source", target_task_id=root["task_id"], target_product_key=root["product_key"],
                               target_content_digest=root["content_digest"])
                p["mapping_endpoints"].append(row)

    def node(key: str, kind: str, rep: str, a: int, b: int, *, name: str | None = None,
             value: str | None = None, ordinal: int | None = None) -> None:
        row = dict(node_id=key, kind=kind, representation_id=rep, unit="codepoint",
                   start_offset=a, end_offset=b, origin="literal")
        if name is not None:
            row["name"] = name
        if value is not None:
            row["value"] = value
        if ordinal is not None:
            row["ordinal"] = ordinal
        p["nodes"].append(row)

    def relation(kind: str, a: str, b: str, roles: tuple[str, str] = ("parent", "child")) -> None:
        key = f"r{len(p['relationships'])}"
        p["relationships"].append(dict(relationship_id=key, kind=kind))
        for ordinal, (role, endpoint) in enumerate(zip(roles, (a, b), strict=True)):
            p["endpoints"].append(dict(relationship_id=key, ordinal=ordinal, role=role, node_id=endpoint))

    representation("canonical", canonical, "canonical")
    mapping("copy", [("canonical", 0, len(canonical))], [("canonical", 0, len(canonical))],
            reason="root canonical representation", source_root=True)
    sources = list(macro_sources)
    if fallback:
        artifact_text = json.dumps({name: definition.model_dump(mode="json") for name, definition in sorted(fallback.items())},
                                   sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        artifact_ref = str(fallback_source_ref)
        representation(artifact_ref, artifact_text, "artifact")
        lines: list[str] = []
        events: list[MacroEvent] = []
        projection_ref = artifact_ref + ":definitions"
        offset = 0

        def shifted(value: str, at: int) -> tuple[Token, ...]:
            return tuple(Token(t.kind, t.text, at + t.start, at + t.end) for t in tokens(value))

        for name, definition in sorted(fallback.items()):
            count = f"[{definition.nargs}]" if definition.nargs else ""
            default = f"[{definition.default}]" if definition.default is not None else ""
            prefix = r"\newcommand{" + name + "}" + count + default + "{"
            line = prefix + definition.body + "}"
            body_start = offset + len(prefix)
            default_start = offset + len(r"\newcommand{") + len(name) + 1 + len(count) + 1
            count_start = offset + len(r"\newcommand{") + len(name) + 2
            events.append(MacroEvent(projection_ref,
                Token("word", r"\newcommand", offset, offset + len(r"\newcommand")),
                name, shifted(name, offset + len(r"\newcommand{")),
                shifted(definition.body, body_start),
                shifted(definition.default, default_start) if definition.default is not None else (),
                shifted(str(definition.nargs), count_start) if definition.nargs else (),
                offset, offset + len(line), "accepted", definition))
            lines.append(line)
            offset += len(line) + 1
        projected = "\n".join(lines)
        # The fallback table is already structured input. Construct its projection directly:
        # re-reading generated TeX could alter malformed-but-retained bodies or defaults.
        read = MacroRead(dict(fallback), [], tuple(tokens(projected)), tuple(events))
        sources.insert(0, MacroSource(projection_ref, projected, read))
        mapping("project", [(artifact_ref, 0, len(artifact_text))], [(projection_ref, 0, len(projected))],
                reason="structured fallback table to derived TeX artifact; no raw text offset claim", fidelity="transformed")
        p["dependencies"].append(dict(name=artifact_ref, kind="artifact", artifact_digest=sha256(artifact_text.encode()).hexdigest()))

    selected_source = {event.name: source.source_ref for source in sources
                       for event in source.read.events if event.status == "accepted"}
    page_table: dict[str, MacroDef] = {}
    bindings: dict[str, MacroBinding] = {}
    definition_nodes: dict[str, str] = {}
    for source_index, source in enumerate(sources):
        representation(source.source_ref, source.text, "artifact")
        p["dependencies"].append(dict(name=source.source_ref, kind="artifact", artifact_digest=sha256(source.text.encode()).hexdigest()))
        for fragment in source.fragments:
            mapping("copy", [("decoded", a, b) for a, b in fragment.decoded_sources],
                    [(source.source_ref, fragment.start, fragment.end)], source_root=True,
                    reason=fragment.reason, fidelity="transformed" if fragment.decoded_sources else "unknown")
        for event_index, event in enumerate(source.read.events):
            key = f"macro:{source_index}:{event_index}"
            details = dict(status=event.status, selected=event.status == "accepted" and selected_source.get(event.name) == event.source_ref, command=event.command.text,
                name_ranges=[(t.start, t.end) for t in event.name_tokens],
                body_ranges=[(t.start, t.end) for t in event.body_tokens],
                default_ranges=[(t.start, t.end) for t in event.default_tokens],
                count_ranges=[(t.start, t.end) for t in event.count_tokens])
            node(key, "macro_event", source.source_ref, event.start, event.end,
                 name=event.name, value=json.dumps(details, sort_keys=True))
            if event.definition is not None:
                definition_key = key + ":definition"
                node(definition_key, "macro_definition", source.source_ref, event.start, event.end,
                     name=event.name, value=event.definition.model_dump_json())
                relation("contains", key, definition_key)
                if event.status == "accepted":
                    page_table[event.name] = event.definition
                    bindings[event.name] = source.read.bindings[event.name]
                    definition_nodes[event.name] = definition_key
    # Sources are ordered fallback first, then page blocks; page selection overrides fallback
    # even where the producer marked an earlier block's event replaced.
    table = effective_macros(page_table, fallback)
    previous_end = 0
    for index, (a, b, opener, closer) in enumerate(sorted(math_ranges)):
        if not previous_end <= a < b <= len(canonical):
            raise ValueError("math extents overlap or lie outside canonical source")
        previous_end = b
        capture = capture_text(canonical[a:b], start=a, opener=opener, closer=closer,
                               structure=structure, macros=table, bindings=bindings, expand_macros=expand_macros)
        if capture.structure_outcome in {"partial", "invalid"}:
            p["coverage"] = "partial"
        view_ref = f"parse:{index}"
        representation(view_ref, capture.view.text, "parse_view")
        view_key = f"view:{index}"
        node(view_key, "parse_view", "canonical", capture.view.start, capture.view.end,
             value=json.dumps(dict(structure_outcome=capture.structure_outcome, issues=capture.issues)))
        mapping("copy", [("canonical", capture.view.start, capture.view.end)],
                [(view_ref, 0, len(capture.view.text))], reason="explicit inner parse view")
        for item in capture.nodes:
            key = f"tex:{index}:{item.node_id}"
            node(key, item.kind, "canonical", item.start, item.end, name=item.name,
                 ordinal=item.argument_index)
            relation("structural_parent", f"tex:{index}:{item.parent}" if item.parent else view_key, key)
        expansion = capture.expansion
        if expansion is None:
            continue
        expanded_ref = f"expanded:{index}"
        representation(expanded_ref, "".join(expansion.tokens), "expanded")
        for invocation_index, invocation in enumerate(expansion.invocations):
            key = f"invocation:{index}:{invocation_index}"
            # Nested invocations may originate in a definition artifact. Their own source
            # extents remain there, rather than being guessed inside the outer invocation.
            origin = invocation.origins[0]
            local_origins = [o for o in invocation.origins if o.source_ref == origin.source_ref]
            node(key, "macro_invocation", origin.source_ref, min(o.start for o in local_origins),
                 max(o.end for o in local_origins), name=invocation.name,
                 value=json.dumps(asdict(invocation), sort_keys=True))
            if invocation.name in definition_nodes:
                relation("binds", key, definition_nodes[invocation.name], ("invocation", "definition"))
        for piece in expansion.pieces:
            origins = [(o.source_ref, o.start, o.end) for o in piece.origins if o.source_ref in representations]
            mapping("expand", origins, [(expanded_ref, piece.start, piece.end)],
                    reason="bounded expansion; invocations=" + ",".join(str(i) for i in piece.invocations),
                    fidelity="transformed" if origins else "unknown")
    return p


def text_product_artifacts(payload: Mapping[str, Any]) -> tuple[bytes, ...]:
    """Exact archived bytes for each named immutable macro artifact dependency."""
    return tuple(dict.fromkeys(rep["text_content"].encode("utf-8")
                               for rep in payload["representations"] if rep["kind"] == "artifact"))
