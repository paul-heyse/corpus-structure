"""Enumerate typed shadow differences for independent source adjudication."""

import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

from archive_study import scoped_entries, validate_overlay
from sqlalchemy import func, select

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.visual_requests import (
    MAX_VISUAL_GROUP,
    VisualSelection,
    _load_visual_source,
    _selection_region,
    _visual_run,
)
from corpus_structure.semantic.visual_routing import _matches, _page_items
from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source
from corpus_structure.serve.pdf_visual_evidence import (
    VisualEvidencePin,
    visual_observation_manifest,
)
from corpus_structure.settings import Settings

_STRUCTURES = {"picture", "table", "caption", "caption_candidate", "formula"}
_ARMS = ("incumbent_only", "explicit", "selective", "all_page_shadow")
_CELL_FIELDS = (
    "start_row_offset_idx",
    "end_row_offset_idx",
    "start_col_offset_idx",
    "end_col_offset_idx",
    "column_header",
    "row_header",
    "text",
)


def signature(item):
    def text(value):
        return " ".join((value or "").split())

    data = item.get("data", item)
    cells = data.get("table_cells", data.get("cells"))
    if cells is not None:
        return (
            data["num_rows"],
            data["num_cols"],
            sorted(
                tuple(
                    text(cell.get(key))
                    if key == "text"
                    else cell.get(key, False)
                    for key in _CELL_FIELDS
                )
                for cell in cells
            ),
        )
    literal = item.get("text")
    return text(literal), text(item.get("orig", item.get("original_text", literal)))


def differences(member, observation, regions, incumbent_item, entries=()):
    overlay_by_id = {entry["id"]: entry for entry in entries}
    replaced = [entry.get("archive_address") for entry in entries]
    regions = [part for part in regions if part.crop.model_dump() not in replaced]
    for item in observation.items:
        row = item.model_dump(mode="json", exclude_none=True)
        kind = row["kind"]
        region = item.source_region
        pointer = None
        overlay_id = None
        reason = "additional_typed_field"
        if kind in _STRUCTURES:
            label = "caption" if kind == "caption_candidate" else kind
            if region is None or region.enclosing_occurrence_id is not None:
                reason = "independent_location_missing"
            else:
                box = (region.left, region.top, region.right, region.bottom)
                matches = {
                    (part.crop.pointer, None)
                    for part in regions
                    if part.kind == label and _matches(box, part.box)
                } | {
                    ((entry.get("archive_address") or {}).get("pointer"), entry["id"])
                    for entry in entries
                    if entry["kind"] == label and _matches(box, tuple(entry["box"]))
                }
                if len(matches) != 1:
                    reason = "no_unique_incumbent_location"
                else:
                    ((pointer, overlay_id),) = matches
                    selected = (
                        overlay_by_id[overlay_id]["reading"]
                        if overlay_id is not None
                        else incumbent_item(pointer)
                    )
                    if kind == "picture":
                        reason = "picture_metadata_differs"
                        if row.get("metadata") == selected.get("meta"):
                            continue
                    elif signature(row) == signature(selected):
                        if kind not in {"caption", "caption_candidate"} or not (
                            row.get("parser_attachment_occurrence_ids")
                            or row.get("associated_picture_occurrence_ids")
                        ):
                            continue
                        reason = "caption_association_requires_witness"
                    else:
                        reason = "typed_reading_differs"
        yield {
            "selection": member["selection"],
            "evidence": member["mapped"],
            "incumbent_pointer": pointer,
            "reason": reason,
            "candidate": row,
            "standing": observation.standing,
            "disposition": "source_review_pending",
            **({"incumbent_overlay": overlay_id} if overlay_id is not None else {}),
        }


def _scopes(source, rows):
    result = {}
    for row in rows:
        selection = VisualSelection.model_validate({"source": source, **row})
        if selection.source != source:
            raise ValueError("frozen request belongs to another source")
        key = canonical_bytes(selection.scope())
        if key in result:
            raise ValueError("frozen arm repeats a request")
        result[key] = selection
    return result


def _arm_scopes(manifest, source):
    if set(manifest["arms"]) != set(_ARMS):
        raise ValueError("the frozen comparison requires all four arms")
    scopes = {arm: _scopes(source, manifest["arms"][arm]) for arm in _ARMS}
    selections = _scopes(source, manifest["selections"])
    if scopes["incumbent_only"] or set(selections) != set().union(*scopes.values()):
        raise ValueError("managed work differs from the exact union of recognition arms")
    if (
        manifest.get("manifest_version") == "chandra-book-shadow-v2"
        and len(manifest.get("study_routes", ())) != 518
    ):
        raise ValueError("the frozen book comparison requires all 518 physical routes")
    if routes := manifest.get("study_routes"):
        numbers = [row["page_no"] for row in routes]
        if numbers != list(range(1, len(routes) + 1)) or any(
            selection.pointer is not None
            for selection in scopes["all_page_shadow"].values()
        ) or set(numbers) != {
            selection.page_no for selection in scopes["all_page_shadow"].values()
        }:
            raise ValueError("all-page coverage differs from the frozen physical route census")
    return scopes


def _require_campaign_group(conn, manifest, manifest_digest, source, path, group):
    index = int(path.name.split(".")[0].removeprefix("group-"))
    first = (index - 1) * MAX_VISUAL_GROUP
    ordered = manifest["selections"][first : first + MAX_VISUAL_GROUP]
    expected = [selection.scope() for selection in _scopes(source, ordered).values()]
    actual = [
        VisualSelection.model_validate(member["selection"]).scope()
        for member in group["members"]
    ]
    key = sha256(canonical_bytes({"manifest": manifest_digest, "first_selection": first})).hexdigest()
    retained = _visual_run(conn, group["run_id"])
    if (
        index < 1
        or not expected
        or actual != expected
        or group.get("campaign_group") != key
        or retained is None
        or retained.options.get("visual_campaign_group") != key
        or retained.options["visual_group"]["selections"] != expected
        or retained.release_id != manifest["semantic_release"]
        or retained.input_realization_id != manifest["realization"]
    ):
        raise ValueError("group receipt differs from its frozen campaign and managed run binding")


def _require_retained_member(conn, selection, member):
    mapped = VisualEvidencePin.model_validate(member["mapped"]) if member["mapped"] else None
    raw = VisualEvidencePin.model_validate(member["raw"]) if member["raw"] else None
    pin = mapped or raw
    if pin is None:
        return None
    manifest = visual_observation_manifest(
        conn,
        selection.source,
        page_no=selection.page_no,
        after_task=pin.task_id - 1,
        limit=1,
    )
    entry = next(iter(manifest.observations), None)
    if (
        entry is None
        or entry.mapped != mapped
        or entry.raw != raw
        or (entry.pointer, entry.region_index, entry.rotation or 0)
        != (selection.pointer, selection.region_index, selection.rotation or 0)
    ):
        raise ValueError("retained evidence pins or scope differ from the protected observation")
    return entry


def _require_recipe(conn, manifest, selection, entry, observation):
    if not (frozen := manifest.get("recipe")):
        return
    # The Reader's JSONB descriptor normalizes -0.0. Recompute identity from the
    # admitted raw payload bytes so equivalent geometry cannot hide a recipe change.
    bodies = table("ops.pdf_product_body")
    raw = entry.raw
    payload = conn.scalar(select(bodies.c.payload).where(
        bodies.c.task_id == raw.task_id,
        bodies.c.product_key == raw.product_key,
        func.octet_length(bodies.c.payload) <= 1024 * 1024,
    ))
    if payload is None or sha256(bytes(payload)).hexdigest() != raw.content_digest:
        raise ValueError("frozen comparison lacks the exact raw observation payload")
    raw_body = json.loads(bytes(payload))
    raw_observation = raw_body["observation"]
    image = raw_observation["image"]
    recipe = {
        "version": "chandra-inference-v1",
        "selection": selection.scope(),
        "runtime": frozen["runtime"],
        "original_digest": manifest["original_sha256"],
        "submitted_png_digest": image["artifact_digest"],
        "transform": image["transform"],
        "render_policy": frozen["render_policy"],
        "crop_policy": frozen["crop_policy"],
    }
    provenance = json.loads(raw_observation["binding"]["decoding_json"])
    expected = sha256(canonical_bytes(recipe)).hexdigest()
    if (
        provenance["inference_recipe_digest"] != expected
        or raw_body["recipe_digest"] != expected
        or raw_observation["raw_response_digest"] != observation["raw_response_digest"]
        or image["artifact_digest"] != observation["image"]["artifact_digest"]
    ):
        raise ValueError("retained recognition recipe differs from the frozen serial recipe")
    runs = table("ops.run")
    runtime_id = conn.scalar(select(runs.c.runtime_id).where(runs.c.id == entry.mapped.run_id))
    mapping = {
        "version": "chandra-mapping-v2",
        "selection": selection.scope(),
        "raw": raw.model_dump(mode="json"),
        "parser": frozen["parser"],
        "runtime_id": runtime_id,
    }
    if runtime_id is None or observation["recipe_digest"] != sha256(canonical_bytes(mapping)).hexdigest():
        raise ValueError("retained mapping recipe differs from the frozen parser and raw observation")


def _write(body):
    print(json.dumps(body, ensure_ascii=False))


def _page_coverage(manifest, scopes, results):
    keys_by_page = {arm: {} for arm in _ARMS}
    for arm, selections in scopes.items():
        for key, selection in selections.items():
            keys_by_page[arm].setdefault(selection.page_no, []).append(key)
    for route in manifest.get("study_routes", ()):
        page = route["page_no"]
        work = {}
        for arm in _ARMS[1:]:
            keys = keys_by_page[arm].get(page, ())
            work[arm] = (
                dict(Counter(results.get(key, ("unassessed", None))[0] for key in keys))
                if keys
                else {"no_request": 1}
            )
        _write({
            "outcome": "page_route",
            "page_no": page,
            "router_action": route["action"],
            "reasons": route["reasons"],
            "incumbent_only": (
                "repair_nominated"
                if any(reason["code"] == "incumbent_structure" for reason in route["reasons"])
                else "baseline_present"
            ),
            "recognition": work,
        })


def _compare_member(conn, manifest, selection, member, arms, overlay, reader):
    membership = {"selection": member["selection"], "arms": arms}
    entry = _require_retained_member(conn, selection, member)
    if member["status"] != "source_ready" or member["mapped"] is None:
        execution = entry.execution_outcome if entry else None
        if execution in {None, "failed"}:
            outcome = "failed"
        else:
            outcome = "mapping_unavailable"
        _write({
            **membership,
            "outcome": outcome,
            "observation_outcome": execution,
            "error": member.get("error"),
            "raw": member["raw"],
            "mapped": member["mapped"],
        })
        return outcome, execution
    if entry is None or entry.mapping_availability != "available":
        raise ValueError("source-ready member lacks an exact available mapping")

    page = selection.page_no
    by_page, _ = _page_items(conn, selection.source, page, page)
    incumbent = {}

    def incumbent_item(pointer):
        if pointer not in incumbent:
            incumbent[pointer] = reader.native_items((pointer,))[pointer]
        return incumbent[pointer]

    entries = scoped_entries(overlay, member["selection"])
    # The manifest and selected region above have already checked crop custody. A
    # pointer filter here would suppress unlocated hallucinations inside the crop.
    request = NativeSourceRequest(
        **selection.source.model_dump(),
        page_no=page,
        evidence=member["mapped"],
        view="visual_evidence",
        max_bytes=8 * 1024 * 1024,
        limit=1000,
    )
    count = 0
    while True:
        response = inspect_native_source(conn, request)
        observation = response.visual_evidence
        if observation is None or observation.mapping_availability != "available":
            _write({**membership, "outcome": "reader_unavailable", "reader_outcome": response.outcome})
            return "reader_unavailable", entry.execution_outcome
        if (
            observation.original_artifact_digest != manifest["original_sha256"]
            or observation.page_no != page
        ):
            raise ValueError("retained evidence differs from the frozen original or physical page")
        if request.cursor is None:
            _require_recipe(conn, manifest, selection, entry, observation.observation)
        for row in differences(member, observation, by_page.get(page, ()), incumbent_item, entries):
            _write({**row, "arms": arms})
            count += 1
        if response.next_cursor is None:
            _write({
                **membership,
                "outcome": "compared",
                "raw": member["raw"],
                "mapped": member["mapped"],
                "nominated_differences": count,
                "observation_outcome": observation.observation["outcome"],
                "finish_reason": observation.observation.get("finish_reason"),
                "mapping_health": observation.observation_health,
                "standing": observation.standing,
                "source_adjudication": "unassessed",
            })
            return "compared", entry.execution_outcome
        request = request.model_copy(update={"cursor": response.next_cursor})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument(
        "--retained-group",
        type=Path,
        action="append",
        help="Compare an exact previously settled group without starting a provider run.",
    )
    parser.add_argument(
        "--require-complete", action="store_true",
        help="Fail if any frozen request lacks a readable retained comparison.",
    )
    args = parser.parse_args()
    bound = args.campaign / "manifest.json"
    manifest_bytes = (args.manifest or bound).read_bytes()
    if bound.exists() and bound.read_bytes() != manifest_bytes:
        raise ValueError("comparison manifest differs from the retained campaign")
    manifest = json.loads(manifest_bytes)
    manifest_digest = sha256(manifest_bytes).hexdigest()
    source = VisualEvidencePin.model_validate(manifest["source"])
    scopes = _arm_scopes(manifest, source)
    results = {}
    paths = args.retained_group or sorted(args.campaign.glob("group-*.result.json"))
    with open_runtime_engine(Settings(), "chandra-shadow-comparison", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            _, _, original, reader = _load_visual_source(conn, source)
            source_release = reader.revision["release_id"]
            if (
                sha256(original).hexdigest() != manifest["original_sha256"]
                or source_release != manifest.get("source_release", source_release)
            ):
                raise ValueError("frozen comparison differs from the original or producer release")
            overlay = (
                validate_overlay(conn, source, manifest["archive_study"])
                if "archive_study" in manifest else None
            )
            release = open_release(conn, source_release)
        reference = ProductReference(source.task_id, source.product_key, source.content_digest)
        if overlay is not None:
            for arm in scopes:
                _write({
                    "arm": arm,
                    "outcome": "incumbent_repairs",
                    "overlay_digest": overlay["digest"],
                    "entries": [entry["id"] for entry in overlay["entries"]],
                })
        for path in paths:
            group = json.loads(path.read_bytes())
            if VisualEvidencePin.model_validate(group["source"]) != source:
                raise ValueError("group product differs from the frozen comparison")
            with read_snapshot(engine) as conn:
                if not args.retained_group and manifest.get("recipe") is not None:
                    _require_campaign_group(conn, manifest, manifest_digest, source, path, group)
                reader = published_record_reader(conn, reference, projection_context=release)
                if reader is None or reader.revision["release_id"] != source_release:
                    raise ValueError("frozen comparator is not readable")
                for member in group["members"]:
                    selection = VisualSelection.model_validate(member["selection"])
                    if selection.source != source or member["run_id"] != group["run_id"]:
                        raise ValueError("group member differs from the frozen source or managed run")
                    key = canonical_bytes(selection.scope())
                    arms = [arm for arm, allowed in scopes.items() if key in allowed]
                    if key in results or not arms:
                        raise ValueError("retained group repeats or lies outside a frozen study scope")
                    if selection.pointer is not None:
                        _selection_region(reader, selection)
                    results[key] = _compare_member(
                        conn, manifest, selection, member, arms, overlay, reader
                    )
    _page_coverage(manifest, scopes, results)
    complete = True
    for arm, allowed in scopes.items():
        statuses = Counter(results.get(key, ("unassessed", None))[0] for key in allowed)
        execution = Counter(
            results[key][1] for key in allowed if key in results and results[key][1] is not None
        )
        missing = statuses["unassessed"]
        compared = statuses["compared"]
        unavailable = len(allowed) - missing - compared
        complete &= not (missing or unavailable)
        _write({
            "arm": arm,
            "outcome": "recognition_coverage",
            "baseline_pages": len(manifest.get("study_routes", ())),
            "selected": len(allowed),
            "selected_physical_pages": len({selection.page_no for selection in allowed.values()}),
            "compared": compared,
            "attempted_unavailable": unavailable,
            "unassessed": missing,
            "statuses": dict(sorted(statuses.items())),
            "provider_outcomes": dict(sorted(execution.items())),
        })
    if args.require_complete and not complete:
        raise SystemExit("one or more frozen requests lack a readable retained comparison")


if __name__ == "__main__":
    main()
