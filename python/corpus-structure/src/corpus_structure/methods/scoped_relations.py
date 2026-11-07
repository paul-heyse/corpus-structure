"""Bounded native structural joins. Retained proposals are not semantic admission."""

import json
import re
from collections.abc import Iterable
from typing import Any, Literal, Self, cast

from pydantic import Field, JsonValue, model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.source_preparation import native_table_geometry
from corpus_structure.semantic.artifact_identity import SourceArtifactOccurrence, normalized_code
from corpus_structure.semantic.contributions import (
    contribution_identity,
    occurrence_identity,
    operation_identity,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    NativeSourcePin,
    SourceSlice,
    evidence_anchor,
    record_source_pin,
)
from corpus_structure.semantic.structural_products import (
    RetainedStructuralRef,
    StructuralInput,
    StructuralProductReport,
    StructuralValue,
)


class SourceWorkBinding(StructuralValue):
    native_content_digest: str = Field(pattern="^[0-9a-f]{64}$")
    source_work: str = Field(min_length=1)
    provenance: str = Field(min_length=1)


PROCEDURE_OPERATION_VERSION = "2"


class ScopedRelationsConfig(StructuralValue):
    inputs: StructuralInput | None = None
    structural_input_digest: str | None = None
    work_bindings: tuple[SourceWorkBinding, ...] = ()
    interpretation_mode: Literal["feasibility", "independent", "coupled"] = "coupled"
    interpretation_weight_scale: float = Field(default=1.0, strict=True)
    sentences: SentenceConfig = Field(default_factory=lambda: SentenceConfig(exclude=("ner",)))
    formula_seconds: float = Field(default=0.5, gt=0)
    max_formula_chars: int = Field(default=2048, gt=0, strict=True)
    classification_refs: tuple[RetainedStructuralRef, ...] = ()

    @model_validator(mode="after")
    def bound_inputs(self) -> Self:
        if self.interpretation_weight_scale not in (0.5, 1.0, 2.0):
            raise ValueError("table interpretation weight scale must be 0.5, 1, or 2")
        if self.inputs is None:
            if self.structural_input_digest is not None or self.classification_refs:
                raise ValueError("original annotation inputs and digest must be supplied together")
        elif self.structural_input_digest != self.inputs.identity:
            raise ValueError(
                "original annotation inputs require their exact structural input digest"
            )
        elif len(set(self.classification_refs)) != len(self.classification_refs) or any(
            ref.product_id not in self.inputs.dependencies for ref in self.classification_refs
        ):
            raise ValueError("classification requires distinct retained report dependencies")
        return self


ARTIFACT_REFERENCE_CUE = re.compile(r"\b(?:in|see|from)\s+$", re.I)


def artifact_spans(text):
    """Locate numbered mentions; never copy nearby captions into references."""
    pattern = re.compile(r"\b(Table|Figure|Theorem|Section)\s+([A-Z]?\d[\w./-]*)", re.IGNORECASE)
    for match in pattern.finditer(text):
        code = match[2].removesuffix(".")
        yield dict(
            start=match.start(),
            end=match.start(2) + len(code),
            artifact_kind=match[1].lower(),
            controlled_code=code,
        )


def _measure_table_geometry(node: dict[str, Any]) -> dict[str, Any]:
    """Recognize nested sample-size bands without modifying the native annotations."""
    data = node.get("data", {})
    cells: list[dict[str, Any]] = data.get("table_cells", [])
    bands = [
        c
        for c in cells
        if c.get("start_row_offset_idx") == 0
        and c.get("end_row_offset_idx") == 1
        and c.get("end_col_offset_idx", 0) - c.get("start_col_offset_idx", 0) > 1
        and re.fullmatch(r"n\s*=\s*[\d,]+", c.get("text", "").strip())
    ]
    if len(bands) < 2:
        return node
    labels = {"frequency", "relative frequency"}
    measures = [
        c
        for c in cells
        if c.get("start_row_offset_idx") == 1
        and c.get("end_row_offset_idx") == 2
        and c.get("text", "").strip().casefold() in labels
    ]
    for band in bands:
        if {
            c["text"].strip().casefold()
            for c in measures
            if band["start_col_offset_idx"] <= c.get("start_col_offset_idx", -1)
            and c.get("end_col_offset_idx", -1) <= band["end_col_offset_idx"]
        } != labels:
            return node
    row_key = next(
        (
            c
            for c in cells
            if c.get("start_col_offset_idx") == 0
            and c.get("end_col_offset_idx") == 1
            and c.get("start_row_offset_idx") == 1
            and c.get("text", "").strip().casefold() in {"winning", "outcome"}
        ),
        None,
    )
    return {
        **node,
        "data": {
            **data,
            "table_cells": [
                {**cell, "column_header": True}
                if cell in bands or cell in measures or cell is row_key
                else {**cell, "row_header": True}
                if row_key is not None
                and cell.get("start_row_offset_idx", -1) >= 2
                and cell.get("start_col_offset_idx") == 0
                and cell.get("end_col_offset_idx") == 1
                else cell
                for cell in cells
            ],
        },
    }


def _note_scope(note: str, cells, targets):
    """Return only explicitly named rows, column bands, or the whole table."""
    if re.fullmatch(r"(?:This note applies to )?all rows[.!]?", note.strip(), re.I):
        return targets
    named = re.match(r"^(?:Only )?the (.+?) (row|column|band)\b", note.strip(), re.I)
    if named is None:
        return ()
    label, axis = named[1].casefold(), named[2].casefold()
    paths = "row_path" if axis == "row" else "header_path"
    qualified = {
        i
        for target in targets
        for i in getattr(target, paths)
        if cells[i].get("text", "").strip().casefold() == label
    }
    if len(qualified) != 1:
        return ()
    index = next(iter(qualified))
    return tuple(target for target in targets if index in getattr(target, paths))


def _table_schematics(items, text):
    """Resolve a source-declared observed/schematic pair within one native view."""
    cue = re.search(
        r"\bdata shown in Table (\d+(?:\.\d+)+)\b.*?"
        r"\bgeneral data table will look as shown in Table (\d+(?:\.\d+)+)\b",
        text,
        re.I | re.S,
    )
    if cue is None or cue[1] == cue[2]:
        return None
    selected = []
    for code in cue.groups():
        pointers = []
        for pointer, node in items.items():
            if node.get("label") != "table":
                continue
            for caption in node.get("captions", ()):
                title = items.get(caption.get("$ref"), {}).get("text", "")
                if re.match(rf"^Table\s+{re.escape(code)}(?=:|\s|$)", title, re.I):
                    pointers.append(pointer)
        if len(pointers) != 1:
            return None
        selected.append(pointers[0])
    return selected


def _scalar_procedure_readings(proposals, passages) -> Iterable[dict[str, Any]]:
    """Project compatible one-span procedure roles for existing structural readers."""
    for annotation, result in proposals:
        predicates = {
            p.predicate.tokens[0]: p.predicate for p in result.frames if p.predicate.tokens
        }
        for frame in result.frames:
            if frame.reading not in {"active", "passive"} or len(frame.predicate.extents) != 1:
                continue
            (action,) = frame.predicate.extents
            scopes = (
                ((annotation.block_start, annotation.block_end),)
                if passages is None
                else tuple((p.start, p.end) for p in passages)
            )
            local = tuple((a, b) for a, b in scopes if a <= action[0] < action[1] <= b)
            if not local:
                continue

            def exact(span, local=local):
                if len(span.extents) == 1:
                    ((start, end),) = span.extents
                    if any(a <= start < end <= b for a, b in local):
                        return ((start, end),)
                return ()

            roles = {
                name: tuple(
                    extent
                    for role in frame.roles
                    if role.name == name and role.status == "located"
                    for extent in exact(role.span)
                )
                for name in ("actor", "object")
            }
            qualifiers = {
                field: tuple(
                    extent
                    for cue in frame.cues
                    if cue.kind == kind and cue.status == "located"
                    for extent in exact(cue.span)
                )
                for field, kind in (
                    ("modality", "modality"),
                    ("conditions", "condition"),
                    ("exceptions", "exception"),
                )
            }
            orders = []
            for cue in frame.cues:
                if (
                    cue.kind != "order"
                    or cue.status != "located"
                    or cue.component not in predicates
                ):
                    continue
                subordinate = exact(predicates[cue.component])
                if subordinate:
                    if cue.variant == "before":
                        orders.append((action, subordinate[0]))
                    elif cue.variant == "after":
                        orders.append((subordinate[0], action))
            yield dict(
                action=action,
                **roles,
                **qualifiers,
                orders=tuple(orders),
                voice=frame.voice,
                polarity=frame.polarity,
                behavior=frame.interpretation,
                clause_role=frame.reading,
                dependency=annotation.dependency_digest,
                reading_key=f"{annotation.block_id}:{frame.variant}:{frame.predicate.tokens}",
            )


def discover_relations(
    frame,
    *,
    source_work=None,
    annotations=(),
    annotation_errors=(),
    annotation_origin_task_id=None,
    passages=None,
    formula_seconds=0.5,
    max_formula_chars=2048,
    predicate_version="2",
    inline_equations_enabled=False,
    witnessed_links_enabled=False,
):
    """Return participants and relation candidates against actual detached source pieces.

    Geometry determines candidates/containment, never independent semantic support. No
    materialized full-corpus graph or source-independent role reconstruction is used.
    """
    native = json.loads(frame.native_context)
    if not frame.text:
        raise ValueError("structural joins require a nonempty source projection")
    source_pieces = tuple(native["pieces"])
    context = NativeSourceContext(
        frame,
        (),
        (SourceSlice(frame.source_view_id, 0, len(frame.text)),),
        "native structural composition",
        "scoped-source-joins-1",
        "selected source",
        max_chars=max(1, len(frame.text)),
        max_pieces=max(1, len(source_pieces)),
    )
    pin = record_source_pin(frame)
    dependency = (
        "native:" + str(frame.native_product.task_id)
        if hasattr(frame, "native_product")
        else "native:" + str(pin["native_product_task_id"])
    )
    # The unchanged geometry/artifact operation has an independent identity.
    # Artifact cohort replay also reconstructs this identity from the source.
    op = operation_identity("structure.scoped_relations", "3", pin)
    products, coordinates, participants = [], {}, {}
    formula_diagnostics = []
    annotation_dependencies = tuple("annotation:" + a.dependency_digest for a in annotations)
    items = {item["self_ref"]: item for item in native["items"]}
    geometry = {
        pointer: _measure_table_geometry(node)
        for pointer, node in items.items()
        if node.get("label") == "table"
    }

    def participant(
        start,
        end,
        *,
        role,
        pointer,
        region,
        extra=None,
        dependencies=(),
        operation=op,
        reading_key=None,
    ):
        key = (start, end, role, pointer, operation, reading_key)
        if key in participants:
            return participants[key]
        if not 0 <= start < end <= len(frame.text):
            raise ValueError("structural participant lies outside source")
        anchors = []
        for piece in context.map_span(
            start, end, literal=frame.text[start:end], allow_multiple=True
        ):
            anchor, coordinate = evidence_anchor(context, piece, native=True)
            anchors.append(anchor)
            coordinates[canonical_bytes({k: v for k, v in coordinate.items() if k != "text"})] = (
                coordinate
            )
        row = dict(
            contract="RetainedContributionSemantics",
            kind="occurrence",
            semantic_type="structural.located_participant",
            operation_key=operation,
            item_key=f"{pointer}:{role}:{start}:{end}" + (f":{reading_key}" if reading_key else ""),
            pin=pin,
            anchors=tuple(anchors),
            occurrence_id=occurrence_identity(anchors),
            standing="retained_private",
            score_state="missing",
            disposition="located_proposal",
            computation_dependencies=tuple(dict.fromkeys((dependency, *dependencies))),
            value=source_value(
                dict(
                    role=role,
                    source_pointer=pointer,
                    region=region,
                    text=frame.text[start:end],
                    start=start,
                    end=end,
                    **(extra or {}),
                )
            ),
        )
        row["contribution_id"] = contribution_identity(row)
        products.append(row)
        participants[key] = row
        return row

    def relation(
        subject,
        target,
        kind,
        region,
        basis="native_geometry",
        state="unassessed",
        operation=op,
        *,
        witness=None,
        extra_witnesses=(),
        question=None,
    ):
        extra = tuple(row["contribution_id"] for row in extra_witnesses)
        if witness is not None:
            extra += (witness["contribution_id"],)
        deps = tuple(
            dict.fromkeys(
                (
                    subject["contribution_id"],
                    target["contribution_id"],
                    dependency,
                    *subject["computation_dependencies"],
                    *target["computation_dependencies"],
                    *extra,
                )
            )
        )
        row = dict(
            contract="RetainedContributionSemantics",
            kind="relation",
            semantic_type="structural.scoped_attachment",
            operation_key=operation,
            item_key=f"{kind}:{deps[0]}:{deps[1]}",
            pin=pin,
            anchors=(),
            endpoints=(
                dict(role="attachment", contribution_id=deps[0]),
                dict(role="target", contribution_id=deps[1]),
            ),
            members=deps[:2],
            disposition="scoped_proposal",
            standing="retained_private",
            score_state="missing",
            computation_dependencies=deps,
            component=dict(
                protocol="witnessed-component-1",
                kind="scoped_attachment",
                question=question
                or ("source_structural_relations" if operation == op else "source_procedure_roles"),
                question_version="1"
                if operation == op or question
                else PROCEDURE_OPERATION_VERSION,
                scope=region,
                interpretation=state,
                bases=(
                    dict(
                        kind=basis,
                        dependencies=tuple(
                            dict.fromkeys(
                                (
                                    *subject["computation_dependencies"],
                                    *target["computation_dependencies"],
                                    *extra,
                                )
                            )
                        ),
                    ),
                ),
                dependencies=deps,
                attachment_contribution_id=deps[0],
                target_contribution_id=deps[1],
                attachment_kind=kind,
            ),
            value=source_value(
                dict(
                    protocol="scoped-attachment-1",
                    subject_id=deps[0],
                    target_id=deps[1],
                    relation=kind,
                    region=region,
                    scope=region,
                    basis=basis,
                    interpretation=state,
                    dependencies=deps,
                    reason=(
                        "Located source relation candidate; "
                        "independent meaning/support remains unassessed."
                    ),
                )
            ),
        )
        row["contribution_id"] = contribution_identity(row)
        products.append(row)
        return row

    cell_rows = {}
    text_rows = []
    artifact_captions = {}
    artifact_mentions = []
    for piece in source_pieces:
        if piece.get("kind") != "native_text" or piece["start"] == piece["end"]:
            continue
        pointer = piece["item_ref"]
        node = items.get(pointer, {})
        if piece.get("source_field") in {"chart_title", "chart_cell_text"}:
            # Chart coordinates have a distinct field bridge from scalar PDF cells.
            continue
        if piece.get("source_field") == "cell_text":
            index = piece["cell_index"]
            cell = geometry.get(pointer, node).get("data", {}).get("table_cells", ())[index]
            role = (
                "header"
                if cell.get("column_header")
                else "row_label"
                if cell.get("row_header")
                else "cell"
            )
            cell_rows[(pointer, index)] = participant(
                piece["start"],
                piece["end"],
                role=role,
                pointer=pointer + "/data/table_cells/" + str(index),
                region=pointer,
                extra={
                    name: cell[name]
                    for name in (
                        "start_row_offset_idx",
                        "end_row_offset_idx",
                        "start_col_offset_idx",
                        "end_col_offset_idx",
                    )
                    if name in cell
                },
            )
        else:
            text = frame.text[piece["start"] : piece["end"]]
            text_rows.append((piece, node, text))
            for found in artifact_spans(text):
                if source_work is None or piece.get("cell_index") is not None:
                    continue
                start, end = piece["start"] + found["start"], piece["start"] + found["end"]
                item = participant(
                    start, end, role="artifact_reference", pointer=pointer, region=pointer
                )
                # Caption status comes from the original native label, not surface position.
                caption = node.get("label") == "caption"
                from corpus_structure.semantic.artifact_identity import source_alias_fields

                value = SourceArtifactOccurrence.model_validate(
                    dict(
                        artifact_kind=found["artifact_kind"],
                        source_work=source_work,
                        controlled_code=found["controlled_code"],
                        title=text[found["end"] :].strip(" .:\n") or None if caption else None,
                        **source_alias_fields(text, found["end"], pointer),
                        revision=None,
                        revision_state="unknown",
                        occurrence_role="caption" if caption else "reference",
                        scope=pointer,
                        source_pointer=pointer,
                        dependencies=(dependency,),
                    )
                ).model_dump(mode="json", exclude_none=True)
                artifact = {
                    **item,
                    "semantic_type": "structural.artifact",
                    "value": source_value(value),
                }
                artifact["contribution_id"] = contribution_identity(artifact)
                products.append(artifact)
                code = normalized_code(found["controlled_code"])
                if code is None or found["artifact_kind"] not in {"table", "figure"}:
                    continue
                key = (found["artifact_kind"], code)
                parent = (node.get("parent") or {}).get("$ref")
                expected_parent = "table" if found["artifact_kind"] == "table" else "picture"
                if caption and items.get(parent, {}).get("label") == expected_parent:
                    artifact_captions.setdefault(key, []).append(item)
                elif not caption and ARTIFACT_REFERENCE_CUE.search(text[: found["start"]]):
                    artifact_mentions.append((key, item, pointer))

    # Contextual nominations add source roles and explicit local caption custody.
    # This private edge does not authorize a canonical identity merge.
    for key, mention, region in artifact_mentions:
        targets = artifact_captions.get(key, ())
        if len(targets) == 1:
            relation(mention, targets[0], "artifact_reference_target", region, "matched_cue")

    for pointer, node in items.items():
        if node.get("label") != "table":
            continue
        table = geometry[pointer]
        cells = table.get("data", {}).get("table_cells", ())
        targets = native_table_geometry(table)
        for target in targets:
            subject = cell_rows.get((pointer, target.cell_index))
            if subject is None:
                continue
            for kind, indices in (("header", target.header_path), ("row_label", target.row_path)):
                for index in indices:
                    header = cell_rows.get((pointer, index))
                    if header is not None:
                        relation(subject, header, kind, pointer)
                        raw = node["data"]["table_cells"][index].get("text", "")
                        if re.search(
                            r"\b(?:mean|variance|probability|count|frequency|standard deviation)\b",
                            raw,
                            re.IGNORECASE,
                        ):
                            relation(subject, header, "value_role", pointer, "matched_cue")
                        if re.search(r"[%$€£]|\b(?:kg|USD|EUR|seconds|meters)\b", raw):
                            relation(subject, header, "unit", pointer, "matched_cue")
        # A native footnote pointer establishes the table association. Applicability
        # inside the table requires its own exact scope cue.
        for ref in node.get("footnotes", ()):
            target_pointer = ref.get("$ref") if isinstance(ref, dict) else None
            for piece, _note, note_text in text_rows:
                if piece["item_ref"] != target_pointer:
                    continue
                note_row = participant(
                    piece["start"],
                    piece["end"],
                    role="note",
                    pointer=target_pointer,
                    region=pointer,
                    extra={"table_association": pointer},
                )
                for target in _note_scope(note_text, cells, targets):
                    cell = cell_rows.get((pointer, target.cell_index))
                    if cell is not None:
                        relation(cell, note_row, "note", pointer, "matched_cue")

    # In an unlabeled marginal row/column, layout alone leaves an ordinary-count
    # reading viable. An explicitly identified schematic supplies the competing
    # source-conditioned role and the exact declaration behind it.
    role_patterns = (
        (r"\brow sums by (\w+) and (\w+)", "row_sum"),
        (r"\bcolumn sums by (\w+) and (\w+)", "column_sum"),
        (r"\bsize of the data set will be denoted by (\w+)", "sample_count"),
        (r"\bijth entry in the table will be denoted by (sij)\b", "observed_count"),
    )
    coordinate_fields = (
        "start_row_offset_idx",
        "end_row_offset_idx",
        "start_col_offset_idx",
        "end_col_offset_idx",
    )
    for piece, _node, source_text in text_rows:
        tables = _table_schematics(items, source_text)
        if tables is None:
            continue
        cues = [(re.search(pattern, source_text, re.I), role) for pattern, role in role_patterns]
        if not all(match is not None for match, _ in cues):
            continue
        observed, schematic = tables
        literals, occurrence_roles = {}, {}
        for match, role in cues:
            assert match is not None
            cue = participant(
                piece["start"] + match.start(),
                piece["start"] + match.end(),
                role="table_role_declaration",
                pointer=piece["item_ref"],
                region=observed,
                extra={"measure_role": role},
            )
            occurrence_roles[role] = cue
            for literal in match.groups():
                literals[literal.casefold()] = role
        cells = items[schematic]["data"]["table_cells"]
        by_extent = {
            tuple(cell.get(k) for k in coordinate_fields): (index, cell["text"].strip())
            for index, cell in enumerate(cells)
            if all(type(cell.get(k)) is int for k in coordinate_fields)
        }
        for index, cell in enumerate(items[observed]["data"]["table_cells"]):
            if not re.fullmatch(r"\d+", cell.get("text", "").strip()):
                continue
            counterpart = by_extent.get(tuple(cell.get(k) for k in coordinate_fields))
            if counterpart is None:
                continue
            other_index, symbol = counterpart
            role = literals.get("sij" if re.fullmatch(r"s\d+", symbol) else symbol.casefold())
            subject, target = (
                cell_rows.get((observed, index)),
                cell_rows.get((schematic, other_index)),
            )
            if role is None or subject is None or target is None:
                continue
            relation(
                subject,
                target,
                "value_role",
                observed,
                "matched_cue",
                witness=occurrence_roles[role],
            )
            if role != "observed_count":
                relation(
                    subject,
                    occurrence_roles["observed_count"],
                    "value_role",
                    observed,
                    "native_geometry",
                )

    # Symbol declaration is source local and explicitly cued. Each occurrence has
    # independent offsets, so repeated symbols never collapse into one identity.
    for text_index, (piece, node, text) in enumerate(text_rows):
        pointer = piece["item_ref"]
        for match in re.finditer(
            r"\b(?:where|let)\s+([A-Za-z][A-Za-z0-9_]*)\s+(?:denotes|is|be|represents)\s+([^.;\n]+)",
            text,
            re.IGNORECASE,
        ):
            symbol = participant(
                piece["start"] + match.start(1),
                piece["start"] + match.end(1),
                role="symbol",
                pointer=pointer,
                region=pointer,
            )
            declaration = participant(
                piece["start"] + match.start(2),
                piece["start"] + match.end(2),
                role="declaration",
                pointer=pointer,
                region=pointer,
            )
            relation(symbol, declaration, "declares", pointer, "matched_cue")
            # An explicit leading "where" scopes declarations to the immediately
            # preceding formula in the same native parent. Repeated symbols are
            # independently anchored occurrences, never global string identities.
            if (
                match[0].lower().startswith("where")
                and not text[: match.start()].strip()
                and text_index
            ):
                previous, formula_node, formula_text = text_rows[text_index - 1]
                if (
                    formula_node.get("label") == "formula"
                    and formula_node.get("parent") == node.get("parent")
                    and node.get("parent") is not None
                ):
                    from .structural_roles import captured_formula_symbols

                    if len(formula_text) > max_formula_chars:
                        formula_diagnostics.append(
                            dict(
                                pointer=previous["item_ref"],
                                outcome="limited",
                                reason="captured formula exceeds selected character limit",
                            )
                        )
                        continue
                    parsed, status = captured_formula_symbols(formula_text, seconds=formula_seconds)
                    formula_diagnostics.append(
                        dict(
                            pointer=previous["item_ref"],
                            outcome=status,
                            input_policy="captured_native_text",
                            mapping="unchanged_native_field",
                        )
                    )
                    for occurrence in parsed:
                        if occurrence["name"] != match[1]:
                            continue
                        used = participant(
                            previous["start"] + occurrence["start"],
                            previous["start"] + occurrence["end"],
                            role="formula_symbol",
                            pointer=previous["item_ref"],
                            region=pointer,
                            extra=dict(
                                syntax_parent=occurrence["syntax_parent"],
                                syntax_standing="syntax_only",
                                input_policy="captured_native_text",
                                mapping="exact_native_field",
                            ),
                        )
                        relation(used, declaration, "declares", pointer, "matched_cue")
        # Explicit Let declarations also scope an immediately following same-parent
        # formula; no search over another example/section is performed.
        if node.get("label") != "formula" and text_index + 1 < len(text_rows):
            following, formula_node, formula_text = text_rows[text_index + 1]
            declarations = tuple(
                re.finditer(
                    r"\blet\s+([A-Za-z][A-Za-z0-9_]*)\s+(?:denotes|is|be|represents)\s+([^.;\n]+)",
                    text,
                    re.IGNORECASE,
                )
            )
            if (
                declarations
                and formula_node.get("label") == "formula"
                and node.get("parent") is not None
                and node.get("parent") == formula_node.get("parent")
            ):
                from .structural_roles import captured_formula_symbols

                if len(formula_text) <= max_formula_chars:
                    parsed, status = captured_formula_symbols(formula_text, seconds=formula_seconds)
                    formula_diagnostics.append(
                        dict(
                            pointer=following["item_ref"],
                            outcome=status,
                            input_policy="captured_native_text",
                            mapping="unchanged_native_field",
                        )
                    )
                    for declaration_match in declarations:
                        declaration = participant(
                            piece["start"] + declaration_match.start(2),
                            piece["start"] + declaration_match.end(2),
                            role="declaration",
                            pointer=pointer,
                            region=pointer,
                        )
                        for occurrence in parsed:
                            if occurrence["name"] != declaration_match[1]:
                                continue
                            used = participant(
                                following["start"] + occurrence["start"],
                                following["start"] + occurrence["end"],
                                role="formula_symbol",
                                pointer=following["item_ref"],
                                region=pointer,
                                extra=dict(
                                    syntax_parent=occurrence["syntax_parent"],
                                    syntax_standing="syntax_only",
                                    input_policy="captured_native_text",
                                    mapping="exact_native_field",
                                ),
                            )
                            relation(used, declaration, "declares", pointer, "matched_cue")
    from corpus_structure.ingest.annotations import AnnotationProduct

    from .predicate_contributions import predicate_results, publish_predicate_evidence
    from .structural_roles import procedure_frames

    procedure_op = operation_identity(
        "source_procedure_roles",
        PROCEDURE_OPERATION_VERSION,
        pin,
        None if passages is None else tuple(p.passage_id for p in passages),
    )
    predicate_proposals = predicate_results(frame, annotations, source_pieces, items)
    readings: list[dict[str, Any]] = [
        *(
            dict(reading)
            for reading in procedure_frames(
                frame.text, tuple(a for a in annotations if not isinstance(a, AnnotationProduct))
            )
        ),
        *_scalar_procedure_readings(predicate_proposals, passages),
    ]
    for reading in readings:

        def located(extent, role, reading=reading):
            start, end = extent
            original = next(
                (
                    p
                    for p in source_pieces
                    if p.get("kind") == "native_text" and p["start"] <= start < end <= p["end"]
                ),
                None,
            )
            if original is None:
                return None
            action_reading = reading
            extra = {}
            if role == "procedure_action":
                extra = dict(
                    voice=action_reading["voice"],
                    polarity=action_reading["polarity"],
                    behavior=action_reading["behavior"],
                    clause_role=action_reading["clause_role"],
                    role_states={
                        name: "located_linguistic_proposal"
                        if action_reading[name]
                        else "not_located"
                        for name in (
                            "actor",
                            "object",
                            "modality",
                            "conditions",
                            "exceptions",
                            "orders",
                        )
                    },
                )
            return participant(
                start,
                end,
                role=role,
                pointer=original["item_ref"],
                region=original["item_ref"],
                extra=extra,
                dependencies=("annotation:" + action_reading["dependency"],),
                operation=procedure_op,
                reading_key=reading.get("reading_key") if role == "procedure_action" else None,
            )

        action = located(reading["action"], "procedure_action")
        if action is None:
            continue
        for role in ("actor", "object", "modality"):
            for extent in reading[role]:
                target = located(extent, "procedure_" + role)
                if target is not None:
                    relation(
                        action,
                        target,
                        role,
                        action["item_key"].split(":")[0],
                        "model_reading",
                        operation=procedure_op,
                    )
                    if role == "object":
                        for (a, b, r, _pointer, _operation, _reading_key), artifact in tuple(
                            participants.items()
                        ):
                            if r == "artifact_reference" and extent[0] <= a < b <= extent[1]:
                                relation(
                                    action,
                                    artifact,
                                    "uses_artifact",
                                    _pointer,
                                    "model_reading",
                                    operation=procedure_op,
                                )
        for field, kind, role in (
            ("conditions", "prerequisite", "precondition"),
            ("exceptions", "exception", "exception"),
        ):
            for extent in reading[field]:
                target = located(extent, role)
                if target is not None:
                    relation(
                        action,
                        target,
                        kind,
                        target["item_key"].split(":")[0],
                        "model_reading",
                        operation=procedure_op,
                    )
        for earlier, later in reading["orders"]:
            first = located(earlier, "procedure_action")
            second = located(later, "procedure_action")
            if first is not None and second is not None:
                relation(
                    first,
                    second,
                    "order",
                    first["item_key"].split(":")[0],
                    "model_reading",
                    operation=procedure_op,
                )
    # Diagnostics are retained independently of contribution count or solver success.
    available = any(
        {"DEP", "POS"} <= {x.attribute for x in a.availability if x.status == "complete"}
        for a in annotations
    )
    emitted = sum(p["operation_key"] == procedure_op for p in products)
    extra_operations = (
        dict(
            operation_key=procedure_op,
            question="source_procedure_roles",
            operation_version=PROCEDURE_OPERATION_VERSION,
            outcome=("limited" if emitted else "failed")
            if annotation_errors
            else (
                ("succeeded" if emitted else "empty")
                if available
                else ("unsupported" if annotations else "not_run")
            ),
            reason=(
                "Some retained annotation blocks failed; independently assess emitted roles."
                if annotation_errors
                else (
                    "Located linguistic role proposals remain independently unassessed."
                    if available
                    else "No complete retained DEP/POS product; no absence is inferred."
                )
            ),
            inspected_count=sum(len(a.tokens) for a in annotations),
            emitted_count=emitted,
            computation_dependencies=tuple(dict.fromkeys((dependency, *annotation_dependencies))),
        ),
    )
    predicate_operations = publish_predicate_evidence(
        frame,
        context,
        pin,
        dependency,
        predicate_proposals,
        annotation_errors,
        annotation_origin_task_id,
        passages,
        products,
        coordinates,
        version=predicate_version,
    )
    inline_operations = ()
    witnessed_operations = ()
    formula_uses = []
    inline_emitted = 0
    if inline_equations_enabled:
        from .inline_formula_occurrences import (
            INLINE_FORMULA_OCCURRENCE_FIELDS,
            INLINE_FORMULA_QUESTION,
            INLINE_FORMULA_VERSION,
            inline_equations,
            inline_symbols,
        )

        selection = (
            None
            if passages is None
            else tuple((p.passage_id, p.start, p.end, p.effective_version) for p in passages)
        )
        equations = tuple(
            inline_equations(
                frame.text, source_pieces, items, selection, max_chars=max_formula_chars
            )
        )
        if equations:
            inline_op = operation_identity(
                INLINE_FORMULA_QUESTION, INLINE_FORMULA_VERSION, pin, selection
            )
            prior_count = len(products)
            unavailable = False
            for equation in equations:
                symbols, outcome = inline_symbols(frame.text, equation, seconds=formula_seconds)
                formula_diagnostics.append(equation.diagnostic(outcome))
                unavailable |= outcome != "parsed"
                for symbol in symbols:
                    row = participant(
                        symbol.start,
                        symbol.end,
                        role="formula_symbol",
                        pointer=equation.pointer,
                        region=equation.pointer,
                        extra=INLINE_FORMULA_OCCURRENCE_FIELDS,
                        operation=inline_op,
                    )
                    formula_uses.append((equation.pointer, symbol.start, symbol.end, row))
            inline_emitted = len(products) - prior_count
            inline_operations = (
                dict(
                    operation_key=inline_op,
                    question=INLINE_FORMULA_QUESTION,
                    operation_version=INLINE_FORMULA_VERSION,
                    outcome=("limited" if inline_emitted else "unsupported")
                    if unavailable
                    else ("succeeded" if inline_emitted else "empty"),
                    inspected_count=len(equations),
                    emitted_count=inline_emitted,
                    computation_dependencies=(dependency,),
                    **(
                        {"reason": "Some selected inline equations lack mapped native syntax."}
                        if unavailable
                        else {}
                    ),
                ),
            )
    if witnessed_links_enabled:
        from .witnessed_source_links import (
            NAMED_QUESTION,
            QUESTION,
            VERSION,
            named_source_links,
            recapped_declarations,
        )

        selection = tuple(
            (p.passage_id, p.start, p.end, p.effective_version) for p in passages or ()
        )
        witness_op = operation_identity(QUESTION, VERSION, pin, selection)
        links = tuple(recapped_declarations(frame.text, source_pieces, items, passages))
        prior = len(products)
        for link in links:
            uses = [
                row
                for pointer, start, end, row in formula_uses
                if pointer == link.use_pointer
                and link.equation[0] <= start < end <= link.equation[1]
                and frame.text[start:end] == link.symbol
            ]
            declaration = participants.get(
                (*link.declaration, "declaration", link.declaration_pointer, op, None)
            )
            if declaration is None:
                continue
            declarations = [
                row
                for row in products
                if row["operation_key"] == op
                and row["item_key"].startswith("declares:")
                and row["members"][1] == declaration["contribution_id"]
            ]
            if len(declarations) != 1:
                continue
            if len(uses) != 1:
                continue
            cue = participant(
                *link.recap,
                role="declaration_recap",
                pointer=link.use_pointer,
                region=link.passage,
                operation=witness_op,
            )
            target = participant(
                *link.name,
                role="declared_name",
                pointer=link.declaration_pointer,
                region=link.passage,
                operation=witness_op,
            )
            relation(
                uses[0],
                target,
                "declares",
                link.scope,
                "matched_cue",
                operation=witness_op,
                extra_witnesses=(cue, declarations[0]),
                question=QUESTION,
            )
        if links:
            witnessed_operations = (
                dict(
                    operation_key=witness_op,
                    question=QUESTION,
                    operation_version=VERSION,
                    outcome="succeeded" if len(products) > prior else "empty",
                    inspected_count=len(links),
                    emitted_count=len(products) - prior,
                    computation_dependencies=(dependency,),
                ),
            )
        named = tuple(named_source_links(frame.text, source_pieces, items, passages))
        if named:
            named_op = operation_identity(NAMED_QUESTION, VERSION, pin, selection)
            first = len(products)
            limited = False
            for link in named:
                subject = participant(
                    *link.left,
                    role="named_link_subject",
                    pointer=link.pointer,
                    region=link.passage,
                    extra={"resolution": link.resolution} if link.resolution else None,
                    operation=named_op,
                )
                cue = participant(
                    *link.cue,
                    role="named_link_cue",
                    pointer=link.pointer,
                    region=link.passage,
                    operation=named_op,
                )
                if link.right is None or link.target_pointer is None:
                    limited = True
                    continue
                target = participant(
                    *link.right,
                    role="named_link_target",
                    pointer=link.target_pointer,
                    region=link.passage,
                    operation=named_op,
                )
                relation(
                    subject,
                    target,
                    link.kind,
                    link.scope,
                    "matched_cue",
                    operation=named_op,
                    witness=cue,
                    question=NAMED_QUESTION,
                )
            witnessed_operations += (
                dict(
                    operation_key=named_op,
                    question=NAMED_QUESTION,
                    operation_version=VERSION,
                    outcome="limited" if limited else "succeeded",
                    inspected_count=len(named),
                    emitted_count=len(products) - first,
                    computation_dependencies=(dependency,),
                    **(
                        {"reason": "Some explicit references lack a unique selected target."}
                        if limited
                        else {}
                    ),
                ),
            )
    return dict(
        contributions=tuple(products),
        coordinates=tuple(coordinates.values()),
        extra_operations=(
            *extra_operations,
            *predicate_operations,
            *inline_operations,
            *witnessed_operations,
        ),
        formula_diagnostics=tuple(formula_diagnostics),
        operation=dict(
            operation_key=op,
            question="source_structural_relations",
            operation_version="1",
            outcome="succeeded" if any(p["operation_key"] == op for p in products) else "empty",
            inspected_count=len(source_pieces),
            emitted_count=sum(p["operation_key"] == op for p in products),
            computation_dependencies=tuple(dict.fromkeys((dependency, *annotation_dependencies))),
        ),
    )


class ScopedRelationsMethod:
    name = "structure.scoped_relations"
    version = "6"
    family = MethodFamily.RESOLVE
    tier = MethodTier.DETERMINISTIC
    unit_type = TaskUnitType.SOURCE_VIEW
    confidence_source = None
    Config = ScopedRelationsConfig
    resources = Resources()

    def select(self, run, cfg):
        return tuple(
            UnitRef(TaskUnitType.SOURCE_VIEW, v.id, v.key) for v in run.reader.source_views()
        )

    def input_digest(self, unit, cfg):
        inputs = {"configuration": cfg.model_dump(mode="json")}
        if cfg.inputs is None:
            annotation = unit.run.reader.source_result(unit.ref.unit_id, "extract.m1_annotations")
            inputs["annotation"] = annotation
        return Digest(canonical_bytes(inputs))

    def run(self, units, cfg, ctx):
        results = []
        classifications = [
            (
                ref,
                StructuralProductReport.model_validate(
                    ctx.reader.retained_structural_report(ref)["report"]
                ),
            )
            for ref in cfg.classification_refs
        ]

        def resolve_frame(ref):
            retained = ctx.reader.retained_source_contribution(ref)
            (frame,) = [
                row
                for row in retained["contributions"]
                if row["contribution_id"] == ref.contribution_id
            ]
            return frame

        for unit in units:
            ctx.check_active()
            view = ctx.reader.source_view(unit.ref.unit_id)
            frame = native_source_frame(view, ())
            bindings = [
                b
                for b in cfg.work_bindings
                if b.native_content_digest == view.ref.native_product.content_digest
            ]
            if len(bindings) > 1:
                raise ValueError("source has ambiguous parent-work assignment")
            from corpus_structure.ingest.annotations import AnnotationProfile
            from corpus_structure.methods.m1_annotations import consume_annotations

            if cfg.inputs is not None:
                sources = [
                    source for source in cfg.inputs.sources if source.source_view_id == view.ref.id
                ]
                if len(sources) != 1:
                    raise ValueError(
                        "original annotations require exactly one selected source reference"
                    )
                original = sources[0]
                if (
                    original.native_task_id,
                    original.native_product_key,
                    original.native_content_digest,
                    original.projection_digest,
                    original.recipe_digest,
                ) != (
                    frame.native_product.task_id,
                    frame.native_product.product_key,
                    frame.native_product.content_digest,
                    frame.projection_digest,
                    frame.recipe_digest,
                ):
                    raise ValueError(
                        "original annotation reference differs from current native source"
                    )
                # This owned port authenticates the manifest and original source cut;
                # it detaches retained columns without running a linguistic pipeline.
                retained = ctx.reader.structural_source_annotations(
                    cfg.inputs, original.identity, AnnotationProfile(cfg.sentences)
                )
                if (
                    NativeSourcePin.from_source(retained.source)
                    != NativeSourcePin.from_source(frame)
                    or retained.source.text != frame.text
                ):
                    raise ValueError("retained annotations differ from current native projection")
                annotations, annotation_errors = retained.annotations, retained.errors
                annotation_origin_task_id = getattr(retained, "annotation_task_id", None)
                passages = tuple(
                    passage
                    for passage in cfg.inputs.passages
                    if passage.source_ref == original.identity
                )
            else:
                passages = None
                annotation_origin_task_id = None
                try:
                    annotations, annotation_errors, annotation_result = consume_annotations(
                        ctx.reader, view, AnnotationProfile(cfg.sentences)
                    )
                    annotation_origin_task_id = annotation_result.get("origin_task_id")
                except ValueError as error:
                    if (
                        str(error)
                        != "required upstream M1 annotation operation has no source result"
                    ):
                        raise
                    annotations = ()
                    annotation_errors = ()
            output = discover_relations(
                frame,
                source_work=bindings[0].source_work if bindings else None,
                annotations=annotations,
                annotation_errors=annotation_errors,
                annotation_origin_task_id=annotation_origin_task_id,
                passages=passages,
                formula_seconds=cfg.formula_seconds,
                max_formula_chars=cfg.max_formula_chars,
                predicate_version="3",
                inline_equations_enabled=True,
                witnessed_links_enabled=True,
            )
            from corpus_structure.methods.inline_formula_occurrences import INLINE_FORMULA_QUESTION
            from corpus_structure.methods.table_interpretation import table_policy_operations

            formula_keys = {
                o["operation_key"]
                for o in output["extra_operations"]
                if o["question"] == INLINE_FORMULA_QUESTION
            }
            table_inputs = tuple(
                row for row in output["contributions"] if row["operation_key"] not in formula_keys
            )
            interpretation = table_policy_operations(
                contributions=table_inputs,
                dependency_ids=tuple(
                    sorted(
                        {
                            dependency
                            for row in table_inputs
                            for dependency in row["computation_dependencies"]
                        }
                        | set(output["operation"]["computation_dependencies"])
                    )
                ),
                source_revision=frame.native_product.content_digest,
                mode=cfg.interpretation_mode,
                weight_scale=cfg.interpretation_weight_scale,
            )
            model_readings = []
            if classifications:
                from corpus_structure.methods.clause_classification import model_concordance

                for ref, report in classifications:
                    model_readings.extend(
                        model_concordance(
                            ref,
                            report,
                            view.ref.id,
                            output["contributions"],
                            resolve_frame,
                        )
                    )
            parse_detail: dict[str, JsonValue] = {
                "formula_syntax": list(output["formula_diagnostics"]),
                "annotation_errors": list(annotation_errors),
            }
            if model_readings:
                parse_detail["clause_model_concordance"] = cast(JsonValue, model_readings)
            results.append(
                UnitResult(
                    ref=unit.ref,
                    outcome=ObservationOutcome.PRODUCED
                    if output["contributions"]
                    else ObservationOutcome.EMPTY,
                    contributions=output["contributions"],
                    contribution_operations=(
                        output["operation"],
                        *output["extra_operations"],
                        *interpretation,
                    ),
                    parse_detail=parse_detail,
                    contribution_coordinate_texts=output["coordinates"],
                )
            )
        return tuple(results)
