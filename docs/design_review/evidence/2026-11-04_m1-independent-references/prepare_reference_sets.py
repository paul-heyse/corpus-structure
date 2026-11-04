"""Freeze source-only M1 reference sets/author packets on explicitly final source runs.

This script never reads predictions, passes, fitted products or grades. Running it
uses existing protected evaluator operations; preparation itself runs no providers.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from corpus_structure.evaluate.record_alignment import RecordEvaluationFrame
from corpus_structure.evaluate.record_references import (
    PARTITIONS,
    assign_origin,
    author_packet,
    create_reference_set,
    source_binding,
    source_units,
)
from corpus_structure.evaluate.semantic import split_documents
from corpus_structure.evaluate.split import SplitConfig
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings
from sqlalchemy import select, text

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
GUIDELINE = ROOT / "domains/statistics/m1-reference-guideline.md"
GUIDELINE_ID = "statistics-m1-reference-3"
REFERENCE_POLICY = "statistics-reference-reading-3"
PREDICTION_POLICY = "m1-grouped-reading-logistic-1"


def retain(path, value):
    content = canonical_bytes(value)
    with path.open("xb") as stream:
        stream.write(content)
    return dict(path=path.name, sha256=sha256(content).hexdigest(), bytes=len(content))


def source_pin(row, source):
    return dict(
        source=source,
        native_product_task_id=row["native_task_id"],
        product_key=row["native_product_key"],
        product_digest=row["native_content_digest"],
        projection_digest=row["projection_digest"],
        recipe_digest=row["recipe_digest"],
        source_view_id=row["id"],
    )


def anchor_scopes(view, pin):
    """Real native extents and genuine projection pieces, including empty item scopes."""
    scopes = []
    for item in (*view.items, *view.ancestors):
        pointer = item["self_ref"]
        nodes = [(pointer, item)]
        if pointer.startswith("#/tables/"):
            nodes.extend(
                (f"{pointer}/data/table_cells/{index}", cell)
                for index, cell in enumerate(item.get("data", {}).get("table_cells", ()))
            )
        for location, node in nodes:
            if not isinstance(node, dict):
                raise ValueError(f"native item/cell is not an object: {location}")
            for precision in ("item", "coarse"):
                scopes.append(dict(pin=pin, space="native", pointer=location, precision=precision))
            literal = node.get("text")
            if isinstance(literal, str) and literal:
                scopes.append(dict(pin=pin, space="native", pointer=location,
                                   precision="exact", start=0, end=len(literal)))
    for piece in view.pieces:
        if piece["kind"] != "native_text":
            continue
        pointer = piece["item_ref"]
        source_field = piece.get("source_field", "text")
        if source_field == "cell_text":
            pointer += f"/data/table_cells/{piece['cell_index']}"
        elif source_field in {"chart_title", "chart_cell_text"}:
            # The full source frame retains these real pieces. Current canonical
            # record admission does not support their alternate native fields;
            # a chart cell must not acquire an invented table-cell address.
            continue
        elif source_field not in {"text", "orig"}:
            raise ValueError(f"unsupported genuine projection field: {source_field}")
        start, end = piece["start"], piece["end"]
        if not 0 <= start <= end <= len(view.text):
            raise ValueError("retained projection piece exceeds its source text")
        if start < end:
            scopes.append(dict(pin=pin, space="selected_projection", pointer=pointer,
                               precision="exact", start=start, end=end))
    # Overlapping primary/ancestor projections may repeat a real item. Deduplicate
    # scopes only, never source units or eligible reference occurrences.
    return tuple({canonical_bytes(scope): scope for scope in scopes}.values())


def same_product(left, right):
    names = ("native_task_id", "native_product_key", "native_content_digest",
             "native_build_id", "native_revision_id")
    return all(left[name] == right[name] for name in names)


def related_views(primary, view, by_id, declared):
    """Freeze explicit native link custody; this does not decide note applicability."""
    local = {item["self_ref"] for item in (*view.items, *view.ancestors)}
    targets = {
        link["$ref"]
        for item in view.items
        for field in ("captions", "footnotes", "references")
        for link in item.get(field, ())
        if isinstance(link, dict) and isinstance(link.get("$ref"), str)
    } - local
    selected = {}
    unresolved = []
    for pointer in sorted(targets):
        candidates = [row for row in by_id.values()
                      if row["id"] != primary["id"] and same_product(primary, row)
                      and pointer in row["projection"]["items"]]
        if not candidates:
            unresolved.append(pointer)
            continue
        # Smallest selected projection contains the explicit target without
        # unnecessarily widening the authoring closure; identity breaks ties.
        chosen = min(candidates, key=lambda row: (len(row["projection"]["items"]), row["id"]))
        selected[chosen["id"]] = chosen
    for entry in declared:
        if not isinstance(entry.get("needed_reason"), str) or not entry["needed_reason"].strip():
            raise ValueError("explicit related context requires its source-only need reason")
        chosen = by_id[entry["source_view_id"]]
        if chosen["id"] == primary["id"] or not same_product(primary, chosen):
            raise ValueError("related context must be selected and in the same native product")
        selected[chosen["id"]] = chosen
    return tuple(selected[key] for key in sorted(selected)), unresolved


def prepare_origin(reader, evaluator, entry, release_id, guideline_text, output, mapping_digest):
    run_id, cut_id = entry["source_run_id"], entry["source_cut_id"]
    run, cut = table("ops.run"), table("ops.input_cut")
    selected_run = reader.execute(select(run).where(run.c.id == run_id)).mappings().one()
    if (selected_run["release_id"], selected_run["project_id"]) != (release_id, entry["project_id"]):
        raise ValueError("source run differs from the explicit final release/project mapping")
    if reader.execute(select(cut.c.id).where(
        cut.c.id == cut_id, cut.c.run_id == run_id, cut.c.release_id == release_id
    )).scalar_one_or_none() is None:
        raise ValueError("explicit source cut is not sealed on that final-release run")
    prepared = open_release(reader, release_id)
    units = source_units(reader, run_id)
    if not units or len({unit["unit_key"] for unit in units}) != len(units):
        raise ValueError("source census must contain unique units, including empty/unreadable ones")
    views = table("kb.source_view")
    by_id = {row["id"]: dict(row) for row in reader.execute(select(views).where(
        views.c.id.in_([unit["source_view_id"] for unit in units])
    )).mappings()}
    if any(row["release_id"] != release_id for row in by_id.values()):
        raise ValueError("old intake-release projections cannot proxy final-release source views")
    docs = table("kb.document")
    documents = [dict(row) for row in reader.execute(select(docs).where(
        docs.c.id.in_({row["document_id"] for row in by_id.values()})
    )).mappings()]
    uris = sorted({row["source_uri"] for row in documents})
    assign_origin(evaluator, project_id=entry["project_id"], origin_group=entry["origin_group"],
                  partition=entry["partition"], source_uris=uris, provenance=entry["origin_provenance"])
    split = split_documents(evaluator, entry["project_id"], SplitConfig(forced_dev={
        uri: "M1 source-only census; historical dev split is separate from origin partition"
        for uri in uris
    }), release_id=release_id)
    source_reader = BoundReader(reader, run_id, prepared, cut_id=cut_id, analysis=False)
    cache = {}

    def hydrate(identity):
        if identity not in cache:
            cache[identity] = source_reader.source_view(identity)
        return cache[identity]

    frames, captured, source_receipts = {}, {}, []
    for unit in units:
        identity, key = unit["source_view_id"], unit["unit_key"]
        primary = by_id[identity]
        view = hydrate(identity)
        pin = source_pin(primary, source_binding(evaluator, source_run_id=run_id,
                                                source_view_id=identity, source_cut_id=cut_id))
        related, unresolved_links = related_views(primary, view, by_id,
            entry.get("related_contexts", {}).get(str(identity), []))
        pins = (pin, *(source_pin(row, row["key"]) for row in related))
        scopes = list(anchor_scopes(view, pin))
        for row, related_pin in zip(related, pins[1:], strict=True):
            scopes.extend(anchor_scopes(hydrate(row["id"]), related_pin))
        coordinates = []
        for capture in entry.get("captured_coordinates", {}).get(str(identity), []):
            if not capture.get("needed_reason", "").strip():
                raise ValueError("captured recognition needs an explicit source-only need reason")
            captured_pin = next(p for p in pins if p["source_view_id"] == capture["source_view_id"])
            address = capture["recognition"]
            literal = reader.scalar(text("SELECT ops.record_captured_recognition_text(:t,:k,:d,:p,CAST(:a AS jsonb))"),
                dict(t=captured_pin["native_product_task_id"], k=captured_pin["product_key"],
                     d=captured_pin["product_digest"], p=capture["pointer"],
                     a=canonical_bytes(address).decode()))
            coordinate = dict(pin=captured_pin, space="captured_recognition", pointer=capture["pointer"],
                              recognition=address, text=literal)
            coordinates.append(coordinate)
            if literal:
                scopes.append({key: value for key, value in coordinate.items() if key != "text"} |
                              dict(precision="exact", start=0, end=len(literal)))
        frames[key] = RecordEvaluationFrame(key, release_id, GUIDELINE_ID, REFERENCE_POLICY,
                                           PREDICTION_POLICY, pin, frozenset(), tuple(pins[1:]), tuple(scopes))
        captured[key] = coordinates
        source_receipts.append(dict(source_view_id=identity, unit_key=key,
            projection_digest=primary["projection_digest"], analysis_eligible=primary["analysis_eligible"],
            source_health=view.health, text_characters=len(view.text), native_items=len(view.items),
            unresolved_native_context_targets=unresolved_links, related_source_view_ids=[r["id"] for r in related],
            unsupported_record_projection_pieces=[dict(piece) for piece in view.pieces
                if piece["kind"] == "native_text" and piece.get("source_field") in {"chart_title", "chart_cell_text"}],
            unsupported_piece_disposition="Retained in the complete source frame and census; no exact released record anchor scope. Authors report eligible unrepresentable content as limitations, never absence."))
    created = create_reference_set(evaluator, project_id=entry["project_id"], source_run_id=run_id,
        source_cut_id=cut_id, label=entry["label"], legacy_split="dev", guideline=GUIDELINE_ID,
        guideline_text=guideline_text, partition=entry["partition"], unit_keys=tuple(frames), frames=frames,
        reference_policy_version=REFERENCE_POLICY, prediction_policy_version=PREDICTION_POLICY,
        captured_coordinates=captured, sampling=dict(seed=entry.get("seed", 20261104),
            strata={unit["unit_key"]: "all_selected_source_units" for unit in units},
            inclusion_probabilities={unit["unit_key"]: 1 for unit in units}, cohort=entry["cohort"],
            provenance=dict(selection="source-only census; no prediction/label selection", mapping_sha256=mapping_digest,
                            origin=entry["origin_provenance"])))
    sets, stored_units = table("eval.reference_set"), table("eval.reference_unit")
    definition = evaluator.execute(select(sets).where(sets.c.id == created["set_id"])).mappings().one()
    retain(output / "frozen-sampling.json", definition["sampling"])
    retain(output / "source-census.json", dict(documents=documents, units=source_receipts, split=split))
    packets = []
    for unit in evaluator.execute(select(stored_units).where(
        stored_units.c.set_id == created["set_id"]
    ).order_by(stored_units.c.id)).mappings():
        packet = author_packet(evaluator, unit["id"])
        receipt = retain(output / f"unit-{unit['id']}.json", packet)
        packets.append(dict(unit_id=unit["id"], unit_key=unit["unit_key"],
                            source_view_id=unit["source_view_id"], projection_digest=unit["projection_digest"],
                            source_frame_sha256=sha256(canonical_bytes(packet["source_frame"])).hexdigest(), **receipt))
    sampling_digest = evaluator.scalar(text(
        "SELECT encode(sha256(convert_to(sampling::text,'UTF8')),'hex') "
        "FROM eval.reference_set WHERE id=:s"
    ), dict(s=created["set_id"]))
    return dict(set_id=created["set_id"], release_id=release_id, project_id=entry["project_id"],
                source_run_id=run_id, source_cut_id=cut_id, origin_group=entry["origin_group"],
                partition=entry["partition"], cohort=entry["cohort"], units=packets,
                sampling_digest=sampling_digest,
                frozen_sampling_sha256=sha256(canonical_bytes(definition["sampling"])).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    mapping_bytes = args.mapping.read_bytes()
    mapping = json.loads(mapping_bytes)
    release_id = mapping["release_id"]
    entries = mapping["origins"]
    if not isinstance(release_id, str) or not release_id.strip() or not entries:
        raise ValueError("explicit final release and origin/run/cut mappings are required")
    for entry in entries:
        if entry["partition"] not in PARTITIONS or not entry["origin_provenance"]:
            raise ValueError("each origin requires a declared partition and credible provenance")
        for name in ("source_run_id", "source_cut_id"):
            if type(entry[name]) is not int or entry[name] <= 0:
                raise ValueError(f"explicit positive {name} is required")
    guideline_bytes = GUIDELINE.read_bytes()
    guideline_text = guideline_bytes.decode("utf-8")
    if GUIDELINE_ID not in guideline_text or guideline_text.encode("utf-8") != guideline_bytes:
        raise ValueError("domain guideline exact UTF-8 bytes/version differ")
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "guideline.md").write_bytes(guideline_bytes)
    (args.out / "input-mapping.json").write_bytes(mapping_bytes)
    completed = []
    artifacts = []
    try:
        settings = Settings()
        with open_runtime_engine(settings, "m1-reference-source-only", purpose="read") as reader_engine, \
             open_runtime_engine(settings, "m1-reference-freeze", purpose="evaluate") as evaluator_engine:
            with reader_engine.connect() as reader:
                reader.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
                prepared = open_release(reader, release_id)
                for kind in ("record_projection.json", "json_schema/ReferenceRecordBatch"):
                    artifact = next(item for item in prepared.artifacts if item.kind == kind)
                    name = "record-contract.json" if kind == "record_projection.json" else "authored-schema.json"
                    (args.out / name).write_bytes(artifact.content)
                    artifacts.append(dict(artifact_name=kind, path=name,
                                          sha256=sha256(artifact.content).hexdigest()))
                family_schemas = args.out / "family-schemas"
                family_schemas.mkdir()
                for definition in prepared.definitions:
                    if "SemanticRecordFields" not in definition.ancestors:
                        continue
                    kind = "json_schema/" + definition.name
                    artifact = next(item for item in prepared.artifacts if item.kind == kind)
                    name = "family-schemas/" + definition.name + ".json"
                    (args.out / name).write_bytes(artifact.content)
                    artifacts.append(dict(artifact_name=kind, path=name,
                                          sha256=sha256(artifact.content).hexdigest()))
                for index, entry in enumerate(entries):
                    output = args.out / f"origin-{index:02d}"
                    output.mkdir()
                    with evaluator_engine.begin() as evaluator:
                        result = prepare_origin(reader, evaluator, entry, release_id,
                            guideline_text, output, sha256(mapping_bytes).hexdigest())
                    result["directory"] = output.name
                    completed.append(result)
                    retain(output / "set-manifest.json", result)
        retain(args.out / "manifest.json", dict(outcome="passed", prepared_at=datetime.now(UTC).isoformat(),
            release_id=release_id, guideline_id=GUIDELINE_ID,
            guideline_sha256=sha256(guideline_bytes).hexdigest(), reference_policy_version=REFERENCE_POLICY,
            prediction_policy_version=PREDICTION_POLICY, mapping_sha256=sha256(mapping_bytes).hexdigest(),
            artifacts=artifacts, sets=completed, reference_passes="not_run", prediction_read="not_run",
            quality_claim="not_established"))
    except BaseException as error:
        retain(args.out / "failure.json", dict(outcome="failed", error_type=type(error).__name__,
            error=str(error), completed_sets=completed,
            note="Listed sets have observed commits. Other retained packets may belong to rolled-back or interrupted work; reconcile their native IDs before reuse."))
        raise


if __name__ == "__main__":
    main()
