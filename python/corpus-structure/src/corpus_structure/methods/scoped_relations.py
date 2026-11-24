"""Bounded native structural joins. Retained proposals are not semantic admission."""

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, NotRequired, TypedDict

from corpus_structure.methods.scoped_inventory import ScopedInventory
from corpus_structure.semantic.artifact_identity import normalized_code
from corpus_structure.semantic.contributions import (
    contribution_identity,
    occurrence_identity,
    operation_identity,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    evidence_anchor,
    record_source_pin,
)

PROCEDURE_OPERATION_VERSION = "2"


SCOPED_VERSION = "17"


def artifact_spans(text, *, navigation, pointer, start):
    for record in (
        *navigation.select("artifact_mention", pointer),
        *navigation.select("artifact_reference", pointer),
    ):
        span = record.span("subject")
        if span is not None and start <= span[0] < span[1] <= start + len(text):
            yield dict(
                start=span[0] - start,
                end=span[1] - start,
                artifact_kind=record.payload["artifact_kind"],
                controlled_code=record.payload["designator"],
                reference=record.payload["kind"] == "artifact_reference",
                primary_node=record.reference.values(),
                primary_record=record,
            )


def _measure_table_geometry(node: Mapping[str, Any], *, navigation) -> Mapping[str, Any]:
    """Recognize nested sample-size bands without modifying the native annotations."""
    data = node.get("data", {})
    cells: list[dict[str, Any]] = data.get("table_cells", [])
    source_roles = {
        fact.payload["cell_index"]: fact.payload["geometry_role"]
        for fact in navigation.select("table_geometry", node["self_ref"])
    }
    cell_roles = {id(cell): source_roles.get(index) for index, cell in enumerate(cells)}
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
    labels = {"frequency", "relative_frequency"}
    measures = [
        c
        for c in cells
        if c.get("start_row_offset_idx") == 1
        and c.get("end_row_offset_idx") == 2
        and cell_roles[id(c)] in labels
    ]
    for band in bands:
        if {
            cell_roles[id(c)]
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
            and cell_roles[id(c)] == "row_key"
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


def _table_schematics(caption_tables, *, navigation, pointer):
    facts = navigation.select("table_schematic", pointer)
    if len(facts) != 1:
        return None
    selected = []
    for role in ("observed", "schematic"):
        pointers = caption_tables.get(facts[0].text(role), ())
        if len(pointers) != 1:
            return None
        selected.append(pointers[0])
    return selected


class ScalarProcedureReading(TypedDict):
    action: tuple[int, int]
    actor: Sequence[tuple[int, int]]
    object: Sequence[tuple[int, int]]
    modality: Sequence[tuple[int, int]]
    conditions: Sequence[tuple[int, int]]
    exceptions: Sequence[tuple[int, int]]
    orders: Sequence[tuple[tuple[int, int], tuple[int, int]]]
    voice: str
    polarity: str
    behavior: str
    clause_role: str
    dependency: str
    reading_key: NotRequired[str]
    predicate_token: NotRequired[int]
    block: NotRequired[str]


def retained_action_extents(contributions):
    positions = defaultdict(list)
    for row in contributions:
        component = row.get("component", {})
        if component.get("kind") != "predicate_frame":
            continue
        key = component["annotation"], component["block"], component["predicate_token"]
        for member in component["frame_members"]:
            if (
                member["role"] == "predicate"
                and member["outcome"] == "complete"
                and len(member["extents"]) == 1
            ):
                extent = member["extents"][0]
                positions[key].append((extent["start"], extent["end"]))
    return {key: rows[0] for key, rows in positions.items() if len(rows) == 1}


def retained_procedure_readings(contributions, passages) -> Iterable[ScalarProcedureReading]:
    """Project scalar procedure roles from already characterized predicate facts."""
    by_id = {row["contribution_id"]: row for row in contributions}
    frames = {
        identifier: row["component"]
        for identifier, row in by_id.items()
        if row.get("component", {}).get("kind") == "predicate_frame"
    }

    from corpus_structure.semantic.positioned_rows import PositionedRows

    frames_by_predicate = {}
    for frame in frames.values():
        frames_by_predicate.setdefault(
            (frame["annotation"], frame["block"], frame["predicate_token"]), []
        ).append(frame)
    readings_by_frame = {}
    qualifiers_by_frame = {}
    for row in contributions:
        component = row.get("component", {})
        if component.get("kind") == "predicate_reading":
            readings_by_frame.setdefault(component["frame"], []).append(component)
        elif component.get("kind") == "predicate_qualifier":
            qualifiers_by_frame.setdefault(component["host_contribution_id"], []).append(component)
    passage_regions = (
        PositionedRows.build(passages, lambda passage: (passage.start, passage.end))
        if passages is not None
        else None
    )

    def exact(member, local):
        if member.get("outcome") != "complete" or len(member["extents"]) != 1:
            return ()
        extent = member["extents"][0]
        a, b = extent["start"], extent["end"]
        return ((a, b),) if a < b and local.containing(a, b) else ()

    for identifier, frame in frames.items():
        if frame["grammatical_reading"] not in {"active", "passive"}:
            continue
        predicate = tuple(
            member for member in frame["frame_members"] if member["role"] == "predicate"
        )
        local = (
            passage_regions
            if passage_regions is not None
            else PositionedRows.build(
                (
                    extent
                    for member in frame["frame_members"]
                    if member["role"] == "focus"
                    for extent in member["extents"]
                ),
                lambda extent: (extent["start"], extent["end"]),
            )
        )
        action = exact(predicate[0], local) if len(predicate) == 1 else ()
        readings = readings_by_frame.get(identifier, ())
        if len(action) != 1 or len(readings) != 1:
            continue
        (reading,) = readings
        fields = {
            name: tuple(
                extent
                for member in frame["frame_members"]
                if member["role"] == name
                for extent in exact(member, local)
            )
            for name in ("actor", "object")
        }
        qualifiers = {name: [] for name in ("modality", "conditions", "exceptions")}
        orders = []
        for relation in qualifiers_by_frame.get(identifier, ()):
            cue = by_id[relation["qualifier_contribution_id"]]["component"]
            if cue.get("host_state") != "located" or len(cue["extents"]) != 1:
                continue
            extent = cue["extents"][0]
            span = (extent["start"], extent["end"])
            if not span[0] < span[1] or not local.containing(*span):
                continue
            name = {
                "modality": "modality",
                "condition": "conditions",
                "exception": "exceptions",
            }.get(relation["qualifier_kind"])
            if name is not None:
                qualifiers[name].append(span)
            if relation["qualifier_kind"] == "order" and cue.get("subordinate_token") is not None:
                subordinate = frames_by_predicate.get(
                    (frame["annotation"], frame["block"], cue["subordinate_token"]), ()
                )
                positions = tuple(
                    position
                    for other in subordinate
                    for member in other["frame_members"]
                    if member["role"] == "predicate"
                    for position in exact(member, local)
                )
                if len(positions) == 1 and cue["variant"] in {"before", "after"}:
                    orders.append(
                        (action[0], positions[0])
                        if cue["variant"] == "before"
                        else (positions[0], action[0])
                    )
        yield dict(
            action=action[0],
            actor=fields["actor"],
            object=fields["object"],
            modality=tuple(qualifiers["modality"]),
            conditions=tuple(qualifiers["conditions"]),
            exceptions=tuple(qualifiers["exceptions"]),
            orders=tuple(orders),
            voice=reading["voice"],
            polarity=reading["polarity"],
            behavior=reading["reading"],
            clause_role=frame["grammatical_reading"],
            dependency=frame["annotation"],
            predicate_token=frame["predicate_token"],
            block=frame["block"],
            reading_key=f"{frame['block']}:{frame['variant']}:{(frame['predicate_token'],)}",
        )


def located_participant(
    frame,
    context,
    pin,
    dependency,
    operation,
    start,
    end,
    *,
    role,
    pointer,
    region,
    extra=None,
    dependencies=(),
    reading_key=None,
):
    """Project one genuine original-relative participant for structural consumers."""
    if not 0 <= start < end <= len(frame.text):
        raise ValueError("structural participant lies outside source")
    anchors, mapped_coordinates = [], []
    for piece in context.map_span(start, end, literal=frame.text[start:end], allow_multiple=True):
        anchor, coordinate = evidence_anchor(context, piece, native=True)
        anchors.append(anchor)
        mapped_coordinates.append(coordinate)
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
    return row, tuple(mapped_coordinates)


def artifact_occurrence(
    item,
    found,
    node,
    source_work,
    dependency,
    field_start,
):
    """Project already characterized artifact facts, without unrelated structural work."""
    # Caption status comes from the original native label, not surface position.
    caption = node.get("label") == "caption"
    pointer = found["primary_record"].payload["pointer"]
    from .witnessed_source_links import retained_artifact_fields

    aliases, _, title = retained_artifact_fields(found["primary_record"], field_start)

    from corpus_structure.semantic.structural_products import DeclaredSourceArtifactOccurrence

    value = DeclaredSourceArtifactOccurrence.model_validate(
        dict(
            artifact_kind=found["artifact_kind"],
            source_work=source_work,
            controlled_code=found["controlled_code"],
            title=title if caption else None,
            **aliases,
            revision=None,
            revision_state="unknown",
            occurrence_role="caption" if caption else "reference",
            scope=pointer,
            source_pointer=pointer,
        )
    ).model_dump(mode="json", exclude_none=True)
    # Working evidence is separated by the report owner before publication.
    value["primary_node"] = found["primary_node"]
    artifact = {
        **item,
        "semantic_type": "structural.artifact",
        "value": source_value(value),
    }
    artifact["contribution_id"] = contribution_identity(artifact)
    return artifact


def discover_relations(
    frame,
    *,
    source_work=None,
    piece_schema=None,
    annotation_errors=(),
    passages=None,
    formula_seconds=0.5,
    max_formula_chars=2048,
    inline_equations_enabled=False,
    witnessed_links_enabled=False,
    ordered_formula_witness=None,
    qualifier_preflight=None,
    navigation=None,
    formal_layers=None,
    retained_predicates=None,
    retained_predicate_operations=(),
    retained_coordinate_texts=(),
):
    """Discover one source's relations with invocation-owned analytical inventories."""
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

    if not isinstance(frame, DeclaredNativeFrameSource):
        raise TypeError("scoped relations require the actual declared native source")
    from corpus_structure.semantic.declared_formal_readings import prepare_formal_layers

    native = frame.view.columns
    if formal_layers is not None:
        formal_layers = prepare_formal_layers(formal_layers)
    with ScopedInventory(native["pieces"], frame.selected_ranges, piece_schema=piece_schema) as inventory:
        return _discover_relations(
            frame,
            inventory=inventory,
            native=native,
            source_work=source_work,
            annotation_errors=annotation_errors,
            passages=passages,
            formula_seconds=formula_seconds,
            max_formula_chars=max_formula_chars,
            inline_equations_enabled=inline_equations_enabled,
            witnessed_links_enabled=witnessed_links_enabled,
            ordered_formula_witness=ordered_formula_witness,
            qualifier_preflight=qualifier_preflight,
            navigation=navigation,
            formal_layers=formal_layers,
            retained_predicates=retained_predicates,
            retained_predicate_operations=retained_predicate_operations,
            retained_coordinate_texts=retained_coordinate_texts,
        )


def _discover_relations(
    frame,
    *,
    inventory,
    native,
    source_work=None,
    annotation_errors=(),
    passages=None,
    formula_seconds=0.5,
    max_formula_chars=2048,
    inline_equations_enabled=False,
    witnessed_links_enabled=False,
    ordered_formula_witness=None,
    qualifier_preflight=None,
    navigation=None,
    formal_layers=None,
    retained_predicates=None,
    retained_predicate_operations=(),
    retained_coordinate_texts=(),
):
    """Return participants and relation candidates against actual detached source pieces.

    Geometry determines candidates/containment, never independent semantic support. No
    materialized full-corpus graph or source-independent role reconstruction is used.
    """
    from corpus_structure.semantic.constructions.navigation import NativeNavigationIndex
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.source_contexts import PreparedNativeSources, source_slice

    from .witnessed_source_links import symbol_declarations

    if not isinstance(frame, DeclaredNativeFrameSource):
        raise TypeError("scoped relations require the actual declared native source")
    if (
        not isinstance(navigation, NativeNavigationIndex)
        or formal_layers is None
        or retained_predicates is None
    ):
        raise ValueError(
            "declared scoped relations require actual navigation, formal and retained predicate inputs"
        )
    if not {"source_predicate_frames", "source_predicate_interpretation"} <= {
        operation["question"] for operation in retained_predicate_operations
    }:
        raise ValueError(
            "declared scoped relations require actual retained predicate inspection outcomes"
        )
    navigation.require()
    if not frame.text:
        raise ValueError("structural joins require a nonempty source projection")
    source_pieces = inventory.pieces
    context = NativeSourceContext(
        frame,
        (),
        (source_slice(frame, 0, len(frame.text)),),
        "native structural composition",
        "scoped-source-joins-1",
        "selected source",
        max_chars=max(1, len(frame.text)),
        max_pieces=max(1, len(source_pieces)),
        max_sources=1,
        version=2,
        preparation=PreparedNativeSources((frame,), max_sources=1),
    )
    pin = record_source_pin(frame)
    dependency = pin["source_product"]
    # The unchanged geometry/artifact operation has an independent identity.
    # Artifact cohort replay also reconstructs this identity from the source.
    op = operation_identity("structure.scoped_relations", "3", pin)
    products, coordinates, participants = [], {}, {}
    formula_diagnostics = []
    items = {item["self_ref"]: item for item in native["items"]}
    geometry = {
        pointer: _measure_table_geometry(node, navigation=navigation)
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
        row, mapped = located_participant(
            frame,
            context,
            pin,
            dependency,
            operation,
            start,
            end,
            role=role,
            pointer=pointer,
            region=region,
            extra=extra,
            dependencies=dependencies,
            reading_key=reading_key,
        )
        for coordinate in mapped:
            coordinates[canonical_bytes({k: v for k, v in coordinate.items() if k != "text"})] = (
                coordinate
            )
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
        question_version=None,
        effective_version=None,
        primary_node=None,
    ):
        if primary_node is None:
            for row in (subject, target, witness):
                if row is None:
                    continue
                primary_node = row.get("component", {}).get("primary_node")
                if primary_node is None and "value" in row:
                    value = source_python(row["value"])
                    primary_node = value.get("primary_node") or value.get("named_cue", {}).get(
                        "primary_node"
                    )
                if primary_node is not None:
                    break
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
                question_version=question_version
                or ("1" if operation == op or question else PROCEDURE_OPERATION_VERSION),
                scope=region,
                **(
                    {"effective_version": effective_version}
                    if effective_version is not None
                    else {}
                ),
                interpretation=state,
                **(
                    {"primary_node": primary_node, "primary_choices": ()}
                    if primary_node is not None
                    else {}
                ),
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

    table_targets = inventory.table_targets(geometry)
    geometry_basis = {
        pointer: tuple(fact.reference.values() for fact in navigation.select("table_geometry", pointer))
        for pointer, value in geometry.items()
        if value is not items[pointer]
    }
    artifact_records = {}
    for kind in ("artifact_mention", "artifact_reference"):
        for record in navigation.select(kind):
            if record.span("subject") is not None:
                artifact_records.setdefault(record.payload["pointer"], []).append(record)
    artifact_pieces = inventory.contained_pairs(
        [(piece["start"], piece["end"]) for piece in source_pieces],
        [record.span("subject") for records in artifact_records.values() for record in records],
    )
    all_artifacts = tuple(record for records in artifact_records.values() for record in records)
    cell_rows = {}
    text_rows = []
    artifact_captions = {}
    artifact_mentions = []
    for piece_index, piece in enumerate(source_pieces):
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
                    **(
                        {
                            "table_geometry_basis": geometry_basis[pointer]
                        }
                        if geometry.get(pointer, node) is not node
                        else {}
                    ),
                    **{
                        name: cell[name]
                        for name in (
                            "start_row_offset_idx",
                            "end_row_offset_idx",
                            "start_col_offset_idx",
                            "end_col_offset_idx",
                        )
                        if name in cell
                    },
                },
            )
        else:
            text = frame.text[piece["start"] : piece["end"]]
            text_rows.append((piece, node, text))
            for artifact_index in artifact_pieces.get(piece_index, ()):
                record = all_artifacts[artifact_index]
                if record.payload["pointer"] != pointer:
                    continue
                span = record.span("subject")
                found = dict(
                    start=span[0] - piece["start"], end=span[1] - piece["start"],
                    artifact_kind=record.payload["artifact_kind"],
                    controlled_code=record.payload["designator"],
                    reference=record.payload["kind"] == "artifact_reference",
                    primary_node=record.reference.values(), primary_record=record,
                )
                if source_work is None or piece.get("cell_index") is not None:
                    continue
                start, end = piece["start"] + found["start"], piece["start"] + found["end"]
                item = participant(
                    start,
                    end,
                    role="artifact_reference",
                    pointer=pointer,
                    region=pointer,
                    extra={"primary_node": found["primary_node"]},
                )
                artifact = artifact_occurrence(
                    item,
                    found,
                    node,
                    source_work,
                    dependency,
                    piece["start"],
                )
                caption = node.get("label") == "caption"
                products.append(artifact)
                code = normalized_code(found["controlled_code"])
                if code is None or found["artifact_kind"] not in {"table", "figure"}:
                    continue
                key = (found["artifact_kind"], code)
                parent = (node.get("parent") or {}).get("$ref")
                expected_parent = "table" if found["artifact_kind"] == "table" else "picture"
                if caption and items.get(parent, {}).get("label") == expected_parent:
                    artifact_captions.setdefault(key, []).append(item)
                elif not caption and found["reference"]:
                    artifact_mentions.append((key, item, pointer))

    # Contextual nominations add source roles and explicit local caption custody.
    # This private edge does not authorize a canonical identity merge.
    caption_rows = tuple(
        (key, item) for key, values in artifact_captions.items() for item in values
    )
    for mention_index, caption_index in inventory.unique_matches(
        [key for key, _, _ in artifact_mentions], [key for key, _ in caption_rows]
    ):
        _key, mention, region = artifact_mentions[mention_index]
        relation(
            mention,
            caption_rows[caption_index][1],
            "artifact_reference_target",
            region,
            "matched_cue",
        )

    text_by_pointer = defaultdict(list)
    for row in text_rows:
        text_by_pointer[row[0]["item_ref"]].append(row)
    table_roles = defaultdict(list)
    for fact in navigation.select("table_role"):
        table_roles[fact.payload["pointer"], fact.payload.get("cell_index")].append(fact)
    caption_tables = defaultdict(list)
    for table_pointer, node in items.items():
        if node.get("label") != "table":
            continue
        for caption in node.get("captions", ()):
            caption_pointer = caption.get("$ref")
            codes = {
                fact.payload.get("designator")
                for family in ("artifact_mention", "artifact_reference")
                for fact in navigation.select(family, caption_pointer)
                if fact.payload.get("artifact_kind") == "table"
            }
            for code in codes:
                caption_tables[code].append(table_pointer)
    for pointer, node in items.items():
        if node.get("label") != "table":
            continue
        table = geometry[pointer]
        cells = table.get("data", {}).get("table_cells", ())
        targets = table_targets[pointer]
        for target in targets:
            subject = cell_rows.get((pointer, target.cell_index))
            if subject is None:
                continue
            for kind, indices in (("header", target.header_path), ("row_label", target.row_path)):
                for index in indices:
                    header = cell_rows.get((pointer, index))
                    if header is not None:
                        relation(subject, header, kind, pointer)
                        for fact in table_roles[pointer, index]:
                            if fact.payload["measure_role"] in {"value_role", "unit"}:
                                relation(
                                    subject,
                                    header,
                                    fact.payload["measure_role"],
                                    pointer,
                                    "matched_cue",
                                    primary_node=fact.reference.values(),
                                )
        path_labels = defaultdict(set)
        targets_by_path = defaultdict(list)
        for target in targets:
            for axis, path in (("row", target.row_path), ("column", target.header_path)):
                for index in path:
                    path_labels[axis, cells[index].get("text", "").strip().casefold()].add(index)
                    targets_by_path[axis, index].append(target)
        # A native footnote pointer establishes the table association. Applicability
        # inside the table requires its own exact scope cue.
        for ref in node.get("footnotes", ()):
            target_pointer = ref.get("$ref") if isinstance(ref, dict) else None
            facts = navigation.select("note_scope", target_pointer)
            note_targets = ()
            if len(facts) == 1:
                axis = facts[0].payload["axis"]
                indices = path_labels[axis, facts[0].payload.get("label")]
                note_targets = (
                    targets
                    if axis == "all"
                    else targets_by_path[axis, next(iter(indices))]
                    if len(indices) == 1
                    else ()
                )
            for piece, _note, _note_text in text_by_pointer[target_pointer]:
                note_row = participant(
                    piece["start"],
                    piece["end"],
                    role="note",
                    pointer=target_pointer,
                    region=pointer,
                    extra={
                        "table_association": pointer,
                        **(
                            {"primary_node": facts[0].reference.values()} if len(facts) == 1 else {}
                        ),
                    },
                )
                for target in note_targets:
                    cell = cell_rows.get((pointer, target.cell_index))
                    if cell is not None:
                        relation(cell, note_row, "note", pointer, "matched_cue")

    # In an unlabeled marginal row/column, layout alone leaves an ordinary-count
    # reading viable. An explicitly identified schematic supplies the competing
    # source-conditioned role and the exact declaration behind it.
    schematics = {
        pointer: _table_schematics(caption_tables, navigation=navigation, pointer=pointer)
        for pointer in text_by_pointer
    }
    counterpart_pairs = inventory.table_counterparts(
        items, tuple(dict.fromkeys(tuple(pair) for pair in schematics.values() if pair is not None))
    )
    for piece, _node, _source_text in text_rows:
        tables = schematics[piece["item_ref"]]
        if tables is None:
            continue
        cues = [
            (record, record.payload["measure_role"])
            for record in table_roles[piece["item_ref"], None]
            if record.payload["measure_role"]
            in {"row_sum", "column_sum", "sample_count", "observed_count"}
        ]
        if {role for _, role in cues} != {
            "row_sum",
            "column_sum",
            "sample_count",
            "observed_count",
        }:
            continue
        observed, schematic = tables
        literals, occurrence_roles = {}, {}
        for match, role in cues:
            assert match is not None
            cue = participant(
                *match.span("cue"),
                role="table_role_declaration",
                pointer=piece["item_ref"],
                region=observed,
                extra={"measure_role": role, "primary_node": match.reference.values()},
            )
            occurrence_roles[role] = cue
            for literal in (
                match.text(binding["role"])
                for binding in match.payload["roles"]
                if binding["role"].startswith("symbol/")
            ):
                literals[literal.casefold()] = role
        for index, other_index, symbol in counterpart_pairs[observed, schematic]:
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

    # Prepare formula input and symbol questions once before the ordered emission seam.
    from .structural_roles import captured_formula_symbols

    declarations_by_piece = {
        index: tuple(symbol_declarations(navigation, piece["item_ref"], piece["start"], piece["end"]))
        for index, (piece, _node, _text) in enumerate(text_rows)
    }
    formula_inputs = {}
    formula_questions = []
    question_keys = []
    for index, (_piece, node, text) in enumerate(text_rows):
        for match in declarations_by_piece[index]:
            candidates = []
            if match.record.payload["introducer"] == "where" and not text[:match.start()].strip() and index:
                candidates.append(index - 1)
            if match.record.payload["introducer"] == "let" and node.get("label") != "formula" and index + 1 < len(text_rows):
                candidates.append(index + 1)
            for formula_index in candidates:
                formula_piece, formula_node, formula_text = text_rows[formula_index]
                if (formula_node.get("label") != "formula" or node.get("parent") is None
                    or formula_node.get("parent") != node.get("parent") or len(formula_text) > max_formula_chars):
                    continue
                if formula_index not in formula_inputs:
                    formula_inputs[formula_index] = captured_formula_symbols(
                        formula_text, seconds=formula_seconds, primary_layers=formal_layers,
                        projection=frame.projection_digest, source_start=formula_piece["start"],
                        native_pointer=formula_piece["item_ref"],
                    )
                question_keys.append((index, match.start(1), formula_index))
                formula_questions.append((formula_index, match[1]))
    formula_symbols = [
        (formula_index, symbol)
        for formula_index, (symbols, _status) in formula_inputs.items()
        for symbol in symbols
    ]
    matched_symbols = inventory.formula_matches(formula_questions, formula_symbols)
    formula_answers = {
        key: tuple(formula_symbols[index][1] for index in matched_symbols.get(ordinal, ()))
        for ordinal, key in enumerate(question_keys)
    }

    # Symbol declaration is source local and explicitly cued. Each occurrence has
    # independent offsets, so repeated symbols never collapse into one identity.
    for text_index, (piece, node, text) in enumerate(text_rows):
        pointer = piece["item_ref"]
        for match in declarations_by_piece[text_index]:
            symbol = participant(
                piece["start"] + match.start(1),
                piece["start"] + match.end(1),
                role="symbol",
                pointer=pointer,
                region=pointer,
                extra={"primary_node": match.primary_node},
            )
            declaration = participant(
                piece["start"] + match.start(2),
                piece["start"] + match.end(2),
                role="declaration",
                pointer=pointer,
                region=pointer,
                extra={"primary_node": match.primary_node},
            )
            relation(symbol, declaration, "declares", pointer, "matched_cue")
            # An explicit leading "where" scopes declarations to the immediately
            # preceding formula in the same native parent. Repeated symbols are
            # independently anchored occurrences, never global string identities.
            if (
                match.record.payload["introducer"] == "where"
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
                    parsed = formula_answers.get((text_index, match.start(1), text_index - 1), ())
                    status = formula_inputs[text_index - 1][1]
                    formula_diagnostics.append(
                        dict(
                            pointer=previous["item_ref"],
                            outcome=status,
                            input_policy="captured_native_text",
                            mapping="unchanged_native_field",
                        )
                    )
                    for occurrence in parsed:
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
                        relation(
                            used,
                            declaration,
                            "declares",
                            pointer,
                            "matched_cue",
                            primary_node=match.primary_node,
                        )
        # Explicit Let declarations also scope an immediately following same-parent
        # formula; no search over another example/section is performed.
        if node.get("label") != "formula" and text_index + 1 < len(text_rows):
            following, formula_node, formula_text = text_rows[text_index + 1]
            declarations = tuple(match for match in declarations_by_piece[text_index] if match.record.payload["introducer"] == "let")
            if (
                declarations
                and formula_node.get("label") == "formula"
                and node.get("parent") is not None
                and node.get("parent") == formula_node.get("parent")
            ):
                from .structural_roles import captured_formula_symbols

                if len(formula_text) <= max_formula_chars:
                    status = formula_inputs[text_index + 1][1]
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
                            extra={"primary_node": declaration_match.primary_node},
                        )
                        for occurrence in formula_answers.get((text_index, declaration_match.start(1), text_index + 1), ()):
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
                            relation(
                                used,
                                declaration,
                                "declares",
                                pointer,
                                "matched_cue",
                                primary_node=declaration_match.primary_node,
                            )
    procedure_op = operation_identity(
        "source_procedure_roles",
        PROCEDURE_OPERATION_VERSION,
        pin,
        None if passages is None else tuple(p.passage_id for p in passages),
    )
    readings: list[ScalarProcedureReading]
    assert retained_predicates is not None
    products.extend(retained_predicates)
    for coordinate in retained_coordinate_texts:
        coordinates[
            canonical_bytes({key: value for key, value in coordinate.items() if key != "text"})
        ] = coordinate
    readings = list(retained_procedure_readings(retained_predicates, passages))
    requested_extents = []
    object_extents = []
    for reading in readings:
        requested_extents.append(reading["action"])
        for field in ("actor", "object", "modality", "conditions", "exceptions"):
            requested_extents.extend(reading[field])
        for earlier, later in reading["orders"]:
            requested_extents.extend((earlier, later))
        object_extents.extend(reading["object"])
    located_pieces = inventory.containing_pieces(requested_extents)
    artifact_rows = tuple(
        (a, b, pointer, artifact)
        for (a, b, role, pointer, _operation, _reading_key), artifact in participants.items()
        if role == "artifact_reference"
    )
    distinct_objects = tuple(dict.fromkeys(object_extents))
    object_artifacts = inventory.contained_pairs(
        distinct_objects, [(a, b) for a, b, _, _ in artifact_rows]
    )
    artifacts_by_object = {
        extent: tuple(artifact_rows[index] for index in object_artifacts[i])
        for i, extent in enumerate(distinct_objects)
    }
    for reading in readings:

        def located(extent, role, reading=reading):
            start, end = extent
            original = located_pieces.get((start, end))
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
                    **(
                        {
                            "predicate_token": action_reading["predicate_token"],
                            "block": action_reading["block"],
                        }
                    ),
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
                dependencies=(action_reading["dependency"],),
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
                        for _a, _b, artifact_pointer, artifact in artifacts_by_object[extent]:
                            relation(
                                action,
                                artifact,
                                "uses_artifact",
                                artifact_pointer,
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
    available = all(
        operation["outcome"] in {"succeeded", "empty"}
        for operation in retained_predicate_operations
    )
    emitted = sum(p["operation_key"] == procedure_op for p in products)
    extra_operations = (
        dict(
            operation_key=procedure_op,
            question="source_procedure_roles",
            operation_version=PROCEDURE_OPERATION_VERSION,
            outcome=("limited" if emitted else "failed")
            if annotation_errors
            else (("succeeded" if emitted else "empty") if available else "not_run"),
            reason=(
                "Some retained annotation blocks failed; independently assess emitted roles."
                if annotation_errors
                else (
                    "Located linguistic role proposals remain independently unassessed."
                    if available
                    else "No complete retained DEP/POS product; no absence is inferred."
                )
            ),
            inspected_count=(
                sum(operation["inspected_count"] for operation in retained_predicate_operations)
            ),
            emitted_count=emitted,
            computation_dependencies=tuple(dict.fromkeys((dependency,))),
        ),
    )
    predicate_operations = retained_predicate_operations
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
                frame.text,
                source_pieces,
                items,
                selection,
                max_chars=max_formula_chars,
                primary_layers=formal_layers,
                projection=frame.projection_digest,
                inventory=inventory,
            )
        )
        if equations:
            inline_op = operation_identity(
                INLINE_FORMULA_QUESTION, INLINE_FORMULA_VERSION, pin, selection
            )
            prior_count = len(products)
            unavailable = False
            for equation in equations:
                symbols, outcome = inline_symbols(
                    frame.text,
                    equation,
                    seconds=formula_seconds,
                    primary_layers=formal_layers,
                    projection=frame.projection_digest,
                )
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
            INHERITANCE_QUESTION,
            NAMED_QUESTION,
            ORDERED_LIMIT_REASON,
            ORDERED_VERSION,
            QUESTION,
            VERSION,
            OrderedRecappedDeclaration,
            match_named_source_links,
            ordered_recapped_declarations,
            ordered_witness_selection,
            procedure_artifact_bindings,
            procedure_artifact_endpoint,
            qualified_inheritance,
            recapped_declarations,
        )

        selection = tuple(
            (p.passage_id, p.start, p.end, p.effective_version) for p in passages or ()
        )
        witness_version = VERSION
        if ordered_formula_witness is not None:
            if passages is None or len(passages) != 1:
                raise ValueError("ordered formula witness requires one original selected passage")
            (query,) = passages
            witness_source = frame.value
            inspected, links = ordered_recapped_declarations(
                frame.text,
                source_pieces,
                {
                    item["self_ref"]: item
                    for item in (*witness_source["ancestors"], *witness_source["items"])
                },
                ordered_formula_witness,
                query,
                navigation=navigation,
                inventory=inventory,
            )
            witness_version = ORDERED_VERSION
            witness_selection = ordered_witness_selection(query, ordered_formula_witness)
        else:
            links = tuple(
                recapped_declarations(
                    frame.text,
                    source_pieces,
                    items,
                    passages,
                    navigation=navigation,
                    inventory=inventory,
                )
            )
            inspected = len(links)
            witness_selection = selection
        witness_op = operation_identity(QUESTION, witness_version, pin, witness_selection)
        prior = len(products)
        linked = 0
        linked_uses = inventory.contained_pairs(
            [link.equation for link in links],
            [(start, end) for _pointer, start, end, _row in formula_uses],
        )
        declarations_by_target = defaultdict(list)
        declarations_by_pair = defaultdict(list)
        for row in products:
            if row["operation_key"] == op and row["item_key"].startswith("declares:"):
                declarations_by_target[row["members"][1]].append(row)
                declarations_by_pair[tuple(row["members"][:2])].append(row)
        for link_index, link in enumerate(links):
            uses = [
                row
                for index in linked_uses[link_index]
                for pointer, start, end, row in (formula_uses[index],)
                if pointer == link.use_pointer and frame.text[start:end] == link.symbol
            ]
            declaration = participants.get(
                (*link.declaration, "declaration", link.declaration_pointer, op, None)
            )
            if declaration is None:
                if isinstance(link, OrderedRecappedDeclaration):
                    raise ValueError("ordered formula witness lacks its exact prior declaration")
                continue
            declared_symbol = None
            if isinstance(link, OrderedRecappedDeclaration):
                declared_symbol = participants.get(
                    (*link.symbol_site, "symbol", link.declaration_pointer, op, None)
                )
                if declared_symbol is None:
                    raise ValueError("ordered formula witness lacks its exact prior symbol")
            declarations = (
                declarations_by_target[declaration["contribution_id"]]
                if declared_symbol is None
                else declarations_by_pair[
                    declared_symbol["contribution_id"], declaration["contribution_id"]
                ]
            )
            if len(declarations) != 1:
                if isinstance(link, OrderedRecappedDeclaration):
                    raise ValueError("ordered formula witness lacks one exact prior binding")
                continue
            if len(uses) != 1:
                continue
            cue = participant(
                *link.recap,
                role="declaration_recap",
                pointer=link.use_pointer,
                region=link.passage,
                extra={"primary_node": link.primary_node},
                operation=witness_op,
            )
            target = participant(
                *link.name,
                role="declared_name",
                pointer=(
                    link.name_pieces[0][0]
                    if isinstance(link, OrderedRecappedDeclaration)
                    else link.declaration_pointer
                ),
                region=link.passage,
                extra={"primary_node": link.declaration_node},
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
                question_version=witness_version,
                primary_node=link.primary_node,
                effective_version=link.effective_version
                if link.effective_version is not None
                else None,
            )
            linked += 1
        if links or ordered_formula_witness is not None:
            limited = ordered_formula_witness is not None and linked < inspected
            witnessed_operations = (
                dict(
                    operation_key=witness_op,
                    question=QUESTION,
                    operation_version=witness_version,
                    outcome="limited" if limited else "succeeded" if linked else "empty",
                    inspected_count=inspected,
                    emitted_count=len(products) - prior,
                    computation_dependencies=(dependency,),
                    **({"reason": ORDERED_LIMIT_REASON} if limited else {}),
                ),
            )
        if passages is not None:
            inspected, inherited = qualified_inheritance(products)
            inheritance_op = operation_identity(INHERITANCE_QUESTION, "1", pin, selection)
            for cue, host, qualification in inherited:
                component = qualification["component"]
                relation(
                    cue,
                    host,
                    "scope_inheritance",
                    component["scope"],
                    "matched_cue",
                    operation=inheritance_op,
                    extra_witnesses=(qualification,),
                    question=INHERITANCE_QUESTION,
                    effective_version=component.get("effective_version"),
                )
            if inherited:
                inheritance_outcome = "limited" if annotation_errors else "succeeded"
            else:
                inheritance_outcome = (
                    "unsupported" if annotation_errors or not available else "empty"
                )
            witnessed_operations += (
                dict(
                    operation_key=inheritance_op,
                    question=INHERITANCE_QUESTION,
                    operation_version="1",
                    outcome=inheritance_outcome,
                    inspected_count=inspected,
                    emitted_count=len(inherited),
                    computation_dependencies=tuple(dict.fromkeys((dependency,))),
                    **(
                        {"reason": "Some selected qualifier evidence is unavailable."}
                        if inheritance_outcome in {"limited", "unsupported"}
                        else {}
                    ),
                ),
            )
            inspection = match_named_source_links(
                frame.text,
                source_pieces,
                items,
                passages,
                annotation_errors=annotation_errors,
                version="4",
                navigation=navigation,
                inventory=inventory,
            )
            named_op = operation_identity(NAMED_QUESTION, "4", pin, selection)
            first = len(products)
            artifact_bindings = procedure_artifact_bindings(products)
            procedure_rows = {row["contribution_id"]: row for row in products}
            procedure_actions = defaultdict(list)
            for row in products:
                if row.get("semantic_type") != "structural.located_participant":
                    continue
                value = source_python(row["value"])
                if value.get("role") == "procedure_action":
                    for annotation in row["computation_dependencies"]:
                        procedure_actions[
                            value["source_pointer"], value["start"], value["end"], annotation
                        ].append(row)
            action_extents = retained_action_extents(retained_predicates)
            for link in inspection.matches:
                evidence = link.evidence()
                extra = dict(
                    resolution=link.resolution,
                    named_cue=evidence,
                    primary_node=link.witness.primary_node,
                )
                deps = (link.witness.annotation,)
                artifact_deps = (
                    artifact_bindings.get((link.pointer, link.left[0], link.left[1]), ())
                    if link.kind == "procedure_reference"
                    and link.resolution == "target_selection_required"
                    else ()
                )
                reading_key = operation_identity(evidence, link.passage)
                subject = participant(
                    *link.left,
                    role="named_link_subject",
                    pointer=link.pointer,
                    region=link.passage,
                    extra=extra,
                    dependencies=(*deps, *artifact_deps),
                    operation=named_op,
                    reading_key=reading_key,
                )
                cue = participant(
                    *link.cue,
                    role="named_link_cue",
                    pointer=link.pointer,
                    region=link.passage,
                    extra=extra,
                    dependencies=deps,
                    operation=named_op,
                    reading_key=reading_key,
                )
                if (
                    link.kind == "definition_reference"
                    and link.resolution == "target_selection_required"
                    and (concept := link.definition_subject) is not None
                ):
                    participant(
                        *concept[0],
                        role="named_link_definition_subject",
                        pointer=link.pointer,
                        region=link.passage,
                        extra={**extra, "definition_subject_kind": concept[1]},
                        dependencies=(
                            *deps,
                            subject["contribution_id"],
                            cue["contribution_id"],
                        ),
                        operation=named_op,
                        reading_key=reading_key,
                    )
                if artifact_deps:
                    binding = procedure_artifact_endpoint(
                        procedure_rows,
                        link,
                        (None),
                        artifact_deps[0],
                        verb_extent=action_extents.get(
                            (
                                link.witness.annotation,
                                link.witness.block,
                                link.witness.tokens["verb"],
                            )
                        ),
                        action_index=procedure_actions,
                    )
                    if binding is not None:
                        action, caption, artifact = binding
                        relation(
                            action,
                            caption,
                            "procedure_reference",
                            link.scope,
                            "matched_cue",
                            operation=named_op,
                            extra_witnesses=(subject, cue, artifact),
                            question=NAMED_QUESTION,
                            question_version="4",
                            effective_version=link.witness.effective_version,
                        )
                if link.right is None or link.target_pointer is None:
                    continue
                target = participant(
                    *link.right,
                    role="named_link_target",
                    pointer=link.target_pointer,
                    region=link.passage,
                    extra=extra,
                    dependencies=deps,
                    operation=named_op,
                    reading_key=reading_key,
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
                    question_version="4",
                    effective_version=link.witness.effective_version,
                )
            outcome = inspection.outcome()
            witnessed_operations += (
                dict(
                    operation_key=named_op,
                    question=NAMED_QUESTION,
                    operation_version="4",
                    outcome=outcome,
                    inspected_count=inspection.inspected_count,
                    emitted_count=len(products) - first,
                    computation_dependencies=tuple(dict.fromkeys((dependency,))),
                    **(
                        {"reason": "Some selected cue or target coverage remains unresolved."}
                        if outcome in {"limited", "unsupported"}
                        else {}
                    ),
                ),
            )
    return dict(
        contributions=tuple(products),
        coordinates=tuple(coordinates.values()),
        extra_operations=tuple(
            (*extra_operations, *predicate_operations, *inline_operations, *witnessed_operations)
        ),
        formula_diagnostics=tuple(formula_diagnostics),
        operation=dict(
            operation_key=op,
            question="source_structural_relations",
            operation_version="1",
            outcome="succeeded" if any(p["operation_key"] == op for p in products) else "empty",
            inspected_count=len(source_pieces),
            emitted_count=sum(p["operation_key"] == op for p in products),
            computation_dependencies=tuple(dict.fromkeys((dependency,))),
        ),
    )
