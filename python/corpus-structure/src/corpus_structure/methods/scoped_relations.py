"""Bounded native structural joins. Retained proposals are not semantic admission."""

import json
import re
from typing import Literal

from pydantic import Field

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.methods.source_preparation import native_table_geometry
from corpus_structure.semantic.artifact_identity import SourceArtifactOccurrence
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
    SourceSlice,
    evidence_anchor,
    record_source_pin,
)
from corpus_structure.semantic.structural_products import StructuralValue


class SourceWorkBinding(StructuralValue):
    native_content_digest: str = Field(pattern="^[0-9a-f]{64}$")
    source_work: str = Field(min_length=1)
    provenance: str = Field(min_length=1)


class ScopedRelationsConfig(StructuralValue):
    work_bindings: tuple[SourceWorkBinding, ...] = ()
    interpretation_mode: Literal["feasibility", "independent", "coupled"] = "coupled"


def artifact_spans(text):
    """Locate numbered mentions; never copy nearby captions into references."""
    pattern = re.compile(
        r"\b(Table|Figure|Theorem|Section)\s+([A-Z]?\d+(?:\.\d+)*[A-Za-z]?)", re.IGNORECASE
    )
    for match in pattern.finditer(text):
        yield dict(
            start=match.start(),
            end=match.end(),
            artifact_kind=match[1].lower(),
            controlled_code=match[2],
        )


def discover_relations(frame, *, source_work=None):
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
    op = operation_identity("structure.scoped_relations", "1", pin)
    products, coordinates, participants = [], {}, {}
    items = {item["self_ref"]: item for item in native["items"]}

    def participant(start, end, *, role, pointer, region, extra=None):
        key = (start, end, role, pointer)
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
            operation_key=op,
            item_key=f"{pointer}:{role}:{start}:{end}",
            pin=pin,
            anchors=tuple(anchors),
            occurrence_id=occurrence_identity(anchors),
            standing="retained_private",
            score_state="missing",
            disposition="located_proposal",
            computation_dependencies=(dependency,),
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

    def relation(subject, target, kind, region, basis="native_geometry", state="unassessed"):
        deps = (subject["contribution_id"], target["contribution_id"], dependency)
        row = dict(
            contract="RetainedContributionSemantics",
            kind="relation",
            semantic_type="structural.scoped_attachment",
            operation_key=op,
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
                question="source_structural_relations",
                question_version="1",
                scope=region,
                interpretation=state,
                bases=(dict(kind=basis, dependencies=(dependency,)),),
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

    cell_rows = {}
    text_rows = []
    for piece in source_pieces:
        if piece.get("kind") != "native_text" or piece["start"] == piece["end"]:
            continue
        pointer = piece["item_ref"]
        node = items.get(pointer, {})
        if piece.get("cell_index") is not None:
            index = piece["cell_index"]
            cell = node.get("data", {}).get("table_cells", ())[index]
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
                if source_work is None:
                    continue
                start, end = piece["start"] + found["start"], piece["start"] + found["end"]
                item = participant(
                    start, end, role="artifact_reference", pointer=pointer, region=pointer
                )
                # Caption status comes from the original native label, not surface position.
                caption = node.get("label") == "caption"
                value = SourceArtifactOccurrence.model_validate(
                    dict(
                        artifact_kind=found["artifact_kind"],
                        source_work=source_work,
                        controlled_code=found["controlled_code"],
                        title=text[found["end"] :].strip(" .:\n") or None if caption else None,
                        aliases=(),
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

    for pointer, node in items.items():
        if node.get("label") != "table":
            continue
        for target in native_table_geometry(node):
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
                            r"\b(?:mean|variance|probability|count|standard deviation)\b",
                            raw,
                            re.IGNORECASE,
                        ):
                            relation(subject, header, "value_role", pointer, "matched_cue")
                        if re.search(r"[%$€£]|\b(?:kg|USD|EUR|seconds|meters)\b", raw):
                            relation(subject, header, "unit", pointer, "matched_cue")
        # Native note references carry attachment scope. Nearby note prose alone
        # does not license a table-wide join.
        for ref in node.get("footnotes", ()):
            target_pointer = ref.get("$ref") if isinstance(ref, dict) else None
            for piece, _note, _text in text_rows:
                if piece["item_ref"] != target_pointer:
                    continue
                note_row = participant(
                    piece["start"],
                    piece["end"],
                    role="note",
                    pointer=target_pointer,
                    region=pointer,
                )
                for (table_pointer, _index), cell in cell_rows.items():
                    if table_pointer == pointer:
                        relation(cell, note_row, "note", pointer)

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
                    for occurrence in re.finditer(
                        r"\b" + re.escape(match[1]) + r"\b", formula_text
                    ):
                        used = participant(
                            previous["start"] + occurrence.start(),
                            previous["start"] + occurrence.end(),
                            role="formula_symbol",
                            pointer=previous["item_ref"],
                            region=pointer,
                        )
                        relation(used, declaration, "declares", pointer, "matched_cue")
        for match in re.finditer(
            r"\bif\s+([^.;\n]+?),\s*(?:then\s+)([^.;\n]+)", text, re.IGNORECASE
        ):
            condition = participant(
                piece["start"] + match.start(1),
                piece["start"] + match.end(1),
                role="precondition",
                pointer=pointer,
                region=pointer,
            )
            action = participant(
                piece["start"] + match.start(2),
                piece["start"] + match.end(2),
                role="procedure_action",
                pointer=pointer,
                region=pointer,
            )
            relation(action, condition, "prerequisite", pointer, "matched_cue")
        # Explicit before/after statements supply the ordering cue and exact
        # endpoint role spans; this does not infer order from document position.
        for match in re.finditer(
            r"\b([A-Za-z][A-Za-z ]{0,60}?)\s+(before|after)\s+"
            r"([A-Za-z][A-Za-z ]{0,60})(?=[.;\n]|$)",
            text,
            re.IGNORECASE,
        ):
            a = participant(
                piece["start"] + match.start(1),
                piece["start"] + match.end(1),
                role="procedure_step",
                pointer=pointer,
                region=pointer,
            )
            b = participant(
                piece["start"] + match.start(3),
                piece["start"] + match.end(3),
                role="procedure_step",
                pointer=pointer,
                region=pointer,
            )
            relation(
                a if match[2].lower() == "before" else b,
                b if match[2].lower() == "before" else a,
                "order",
                pointer,
                "matched_cue",
            )
    return dict(
        contributions=tuple(products),
        coordinates=tuple(coordinates.values()),
        operation=dict(
            operation_key=op,
            question="source_structural_relations",
            operation_version="1",
            outcome="succeeded" if products else "empty",
            inspected_count=len(source_pieces),
            emitted_count=len(products),
            computation_dependencies=(dependency,),
        ),
    )


class ScopedRelationsMethod:
    name = "structure.scoped_relations"
    version = "1"
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
        return Digest(canonical_bytes(cfg.model_dump(mode="json")))

    def run(self, units, cfg, ctx):
        results = []
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
            output = discover_relations(
                frame, source_work=bindings[0].source_work if bindings else None
            )
            from corpus_structure.methods.table_interpretation import table_policy_operations

            interpretation = table_policy_operations(
                contributions=output["contributions"],
                dependency_ids=tuple(
                    sorted(
                        {
                            dependency
                            for row in output["contributions"]
                            for dependency in row["computation_dependencies"]
                        }
                        | set(output["operation"]["computation_dependencies"])
                    )
                ),
                source_revision=frame.native_product.content_digest,
                mode=cfg.interpretation_mode,
            )
            results.append(
                UnitResult(
                    ref=unit.ref,
                    outcome=ObservationOutcome.PRODUCED,
                    contributions=output["contributions"],
                    contribution_operations=(output["operation"], *interpretation),
                    contribution_coordinate_texts=output["coordinates"],
                )
            )
        return tuple(results)
