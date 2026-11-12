"""BEP09 retained consumers over an explicit final pin; never starts NLP or selects results."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
from itertools import islice
import json
from pathlib import Path
import subprocess

from fastmcp import Client
from sqlalchemy import select

from corpus_structure.intervene.semantic_server import SemanticProjectSession, build_semantic_server
from corpus_structure.semantic.characterization_store import read_layer_manifest, read_view
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import selected_source_views
from corpus_structure.serve.characterization import CharacterizationRequest, inspect_characterization
from corpus_structure.serve.characterization_replay import (
    CharacterizationReviewSelection,
    inspect_characterization_review,
    verify_characterization_review,
)
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
PRODUCERS = {
    "text.native_evidence", "text.formal_evidence", "text.constructions",
    "text.contextual_characterization", "text.model_characterization", "text.evaluate_context",
}
ORIGINAL = ProductReference(1627, "integrated", "35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb")
LIMIT = "Retained execution/consumer fidelity only; no accuracy, recognition completeness or speed claim."


def write(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def digest(value):
    return sha256(canonical_bytes(value)).hexdigest()


def binding(path):
    value = json.loads(path.read_bytes())
    pin = ProductReference(**value["view"])
    if type(value["run_id"]) is not int or value["run_id"] < 1:
        raise ValueError("binding requires an exact positive final run_id")
    if value["project"] != "nce-grinstead-snell-full-book":
        raise ValueError("binding is outside the declared whole-book project")
    if (value["source_run_id"], value["source_cut_id"], value["source_view_count"], value["native_pages"]) != (496, 614, 316, 518):
        raise ValueError("binding differs from retained capture496/cut614/316 views/518 pages")
    if ProductReference(**value["base_document"]) != ORIGINAL:
        raise ValueError("binding changes the original native product")
    return value, pin


def native_facts(conn, bound, pin):
    runs, tasks, completed = map(table, ("ops.run", "ops.task", "ops.completed_result"))
    selected_run = conn.execute(select(runs).where(runs.c.id == bound["run_id"])).mappings().one()
    origin = conn.execute(select(runs).where(runs.c.id == bound["source_run_id"])).mappings().one()
    cut = conn.scalar(select(completed.c.cut_id).where(completed.c.run_id == bound["source_run_id"]))
    if selected_run["project_id"] != bound["project"] or origin["project_id"] != bound["project"] or cut != bound["source_cut_id"]:
        raise ValueError("explicit run/project/source-cut binding differs")
    if origin["status"] != "finished" or not origin["sealed"]:
        raise ValueError("original capture is not completed")
    view = read_view(conn, pin, run_id=bound["run_id"]).payload
    captured = selected_source_views(conn, bound["source_run_id"])
    source_ids = {source.id for source in captured}
    if len(source_ids) != 316 or set(view["source_scope"]["source_view_ids"]) != source_ids:
        raise ValueError("final view does not preserve exactly all316 original source IDs")
    if ProductReference(**view["base_document"]) != ORIGINAL or any(source.native_product != ORIGINAL for source in captured):
        raise ValueError("final/captured source pin differs from native1627")
    native = published_record_reader(conn, ORIGINAL, projection_context=open_release(conn, origin["release_id"]))
    if native is None:
        raise ValueError("original native product is unavailable")
    with closing(native.iter_rows("companion", {"family": "health"}, batch_size=3)) as rows:
        health = [native.decode_companion_row(row) for row in islice(rows, 3)]
    selected_health = [row for row in health if "source_scope" in row]
    if len(selected_health) != 1 or len(health) > 2:
        raise ValueError("original native health is unavailable or ambiguous")
    health = selected_health[0]
    page_start, page_end = health.get("page_start"), health.get("page_end")
    pages_known = type(page_start) is int and type(page_end) is int
    if pages_known and page_end - page_start + 1 != 518:
        raise ValueError("original native health differs from the declared518-page range")
    active = [ProductReference(**value) for value in view.get("active_layers", view["layers"])]
    matrix = {identity: Counter() for identity in source_ids}
    accounting, manifests = {}, []
    for reference in active:
        body = read_layer_manifest(conn, reference, run_id=bound["run_id"]).payload
        producer = body["operation"]["key"]
        if producer not in PRODUCERS or ProductReference(**body["base_document"]) != ORIGINAL:
            raise ValueError("active layer has an unexpected producer/base document")
        for identity in body["source_scope"]["source_view_ids"]:
            if identity not in matrix:
                raise ValueError("layer includes a source outside original capture")
            matrix[identity][producer] += 1
        for row in body["coverage"]:
            key = (producer, row["family"], row["outcome"], row["availability"])
            counts = accounting.setdefault(key, Counter())
            counts["rows"] += 1
            for field in ("eligible", "examined", "unexamined"):
                counts[field + "_selectors"] += len(row.get(field, ()))
        manifests.append({"reference": reference.values(), "operation": body["operation"],
                          "source_view_ids": body["source_scope"]["source_view_ids"], "coverage": body["coverage"]})
    retained_coverage = Counter(canonical_bytes(row) for manifest in manifests for row in manifest["coverage"])
    if retained_coverage != Counter(canonical_bytes(row) for row in view["coverage"]):
        raise ValueError("final view coverage differs from exact active-layer coverage")
    if any(set(counts) != PRODUCERS or any(count != 1 for count in counts.values()) for counts in matrix.values()):
        raise ValueError("every original source must have exactly one active layer from each of the six producers")
    facts = dict(
        acquired_at=datetime.now(timezone.utc).isoformat(), binding=bound,
        release_id=selected_run["release_id"], producing_run_id=conn.scalar(select(tasks.c.run_id).where(tasks.c.id == pin.task_id)),
        source_view_ids=sorted(source_ids), active_layer_count=len(active), closure_layer_count=len(view["layers"]),
        coverage_rows=sum(retained_coverage.values()), final_coverage_equals_active_layers=True,
        source_producers={str(identity): dict(counts) for identity, counts in sorted(matrix.items())},
        family_outcomes=[dict(operation=key[0], family=key[1], outcome=key[2], availability=key[3], **counts) for key, counts in sorted(accounting.items())],
        original_native_health=health,
        native_page_context=dict(expected_pages=518, page_start=page_start, page_end=page_end,
                                 outcome="passed" if pages_known else "blocked",
                                 prerequisite=None if pages_known else "native health has no exact page range"),
        scope_limit="Selector counts are recorded coverage scope, not tokens/pages/accuracy. Original native health remains independent of analytical coverage.",
    )
    return facts, manifests, active


def prepare(settings, bound, pin, root, export_bytes):
    if (root / "consumer-requests.json").exists():
        raise ValueError("prepare output already exists; select a new --output to preserve it")
    common = dict(run_id=bound["run_id"], **pin.values(), limit=3, max_bytes=8_388_608)
    requests = {
        "summary": CharacterizationRequest(**common, view="summary"),
        "coverage": CharacterizationRequest(**{**common, "limit": 1000}, view="coverage"),
        "native-annotations": CharacterizationRequest(**common, view="annotations", family="spacy.tokens"),
        "formal-annotations": CharacterizationRequest(**common, view="annotations", family="formal.math"),
    }
    discovery = {}
    with open_runtime_engine(settings, "bep09-consumer-prepare", purpose="read") as engine, read_snapshot(engine) as conn:
        facts, manifests, active = native_facts(conn, bound, pin)
        for producer, kind in (("text.native_evidence", "membership"), ("text.constructions", "terms")):
            selected = [row["reference"] for row in manifests if row["operation"]["key"] == producer][:8]
            found_term = found_reading = found_membership = False
            for layer in selected:
                query = CharacterizationRequest(**{**common, "limit": 8}, view="annotations" if kind == "membership" else "terms", layer_key=layer["product_key"], **({"kind": "native.block"} if kind == "membership" else {}))
                response = inspect_characterization(conn, query)
                for item in response.items:
                    if kind == "membership" and not found_membership:
                        pages = [extent["page"] for occurrence in item["occurrences"] for extent in occurrence["extents"] if type(extent.get("page")) is int]
                        if not pages:
                            continue
                        page = 1 if pages[0] != 1 else 2
                        member = CharacterizationRequest(**common, view="membership", layer_key=layer["product_key"], annotation_id=item["annotation"]["local_id"], page=page)
                        actual = inspect_characterization(conn, member)
                        if actual.items and any(row.get("outside_selection") is True for row in actual.items):
                            requests["off-page-membership"] = member
                            found_membership = True
                    elif kind == "terms":
                        term = item["term"]["local_id"]
                        if not found_term:
                            requests["exact-term"] = CharacterizationRequest(**common, view="terms", layer_key=layer["product_key"], annotation_id=term)
                            found_term = True
                        if item.get("choices") and not found_reading:
                            requests["packed-reading"] = CharacterizationRequest(**common, view="reading", layer_key=layer["product_key"], annotation_id=term)
                            found_reading = True
                if (kind == "membership" and found_membership) or (kind == "terms" and found_term and found_reading):
                    break
            for name, found in (("off-page-membership", found_membership),) if kind == "membership" else (("exact-term", found_term), ("packed-reading", found_reading)):
                discovery[name] = dict(outcome="prepared" if found else "not_run", scope="First8 active layers for this producer, first8 matching nodes per layer; no absence claim beyond this bounded discovery.")
    write(root, "native-facts.json", facts)
    write(root, "active-layer-manifests.json", manifests)
    write(root, "consumer-requests.json", dict(binding=bound, binding_sha256=digest(bound), discovery=discovery, requests={name: request.model_dump(mode="json") for name, request in requests.items()}))
    selection = CharacterizationReviewSelection(run_id=bound["run_id"], **pin.values(), max_bytes=export_bytes, max_source_rows=316)
    write(root, "review-selection.json", selection.model_dump(mode="json"))
    print(json.dumps(dict(outcome="prepared", requests=list(requests), export_max_bytes=export_bytes, output=str(root))))


def command(request):
    args = ["uv", "run", "ci", "source", "enriched", str(request.run_id), "--producing-task", str(request.task_id), "--product", request.product_key, "--digest", request.content_digest, "--view", request.view, "--limit", str(request.limit), "--max-bytes", str(request.max_bytes), "--json"]
    for field, option in (("layer_key", "--layer"), ("annotation_id", "--annotation"), ("family", "--family"), ("kind", "--kind"), ("page", "--page"), ("cursor", "--cursor")):
        value = getattr(request, field)
        if value is not None:
            args.extend([option, str(value)])
    for choice in request.choices:
        args.extend(["--choice", choice])
    return args


async def live(settings, bound, root, max_coverage_pages):
    prepared = json.loads((root / "consumer-requests.json").read_bytes())
    if prepared["binding_sha256"] != digest(bound) or prepared["binding"] != bound:
        raise ValueError("prepared consumer requests differ from explicit binding")
    if (root / "consumer-cases.json").exists() or (root / "raw").exists():
        raise ValueError("live output already exists; prepare a new --output for a fresh attempt")
    cases, outcomes = [], {}
    with open_runtime_engine(settings, "bep09-consumer-live", purpose="read") as engine:
        server = build_semantic_server(SemanticProjectSession(engine, bound["project"]), read_engine=engine)
        async with Client(server) as client:
            for name, body in prepared["requests"].items():
                request = CharacterizationRequest.model_validate(body)
                page, rows, seen = 0, 0, set()
                while True:
                    key = f"{name}-{page:04d}"
                    with read_snapshot(engine) as conn:
                        native = inspect_characterization(conn, request).model_dump(mode="json")
                    write(root, f"raw/{key}-native.json", native)
                    invocation = command(request)
                    called = subprocess.run(invocation, capture_output=True, text=True, check=False, timeout=180)
                    write(root, f"raw/{key}-cli-receipt.json", dict(command=invocation, exit_code=called.returncode, stderr=called.stderr[-8000:]))
                    cli = json.loads(called.stdout) if called.returncode == 0 else None
                    write(root, f"raw/{key}-cli.json", cli)
                    result = await client.call_tool("inspect_enriched_document", {"request": request.model_dump(mode="json")})
                    mcp = result.structured_content
                    write(root, f"raw/{key}-mcp.json", dict(is_error=result.is_error, response=mcp))
                    passed = called.returncode == 0 and not result.is_error and canonical_bytes(native) == canonical_bytes(cli) == canonical_bytes(mcp)
                    outcomes[key] = dict(outcome="passed" if passed else "failed", cli_exit_code=called.returncode, mcp_error=result.is_error, native_sha256=digest(native))
                    cases.append(dict(name=key, request=request.model_dump(mode="json"), native_sha256=digest(native)))
                    write(root, "consumer-cases.json", dict(binding_sha256=digest(bound), cases=cases))
                    if name != "coverage":
                        break
                    rows += len(native["items"])
                    cursor = native["continuation"]
                    if cursor is None:
                        if rows != native["coverage_total"]:
                            raise ValueError("coverage pagination did not account for every retained row")
                        outcomes["coverage-accounting"] = dict(outcome="passed", rows=rows, coverage_total=native["coverage_total"], pages=page + 1)
                        break
                    if cursor in seen or page + 1 >= max_coverage_pages:
                        raise ValueError("coverage cursor repeated or explicit page bound exhausted")
                    seen.add(cursor)
                    request = request.model_copy(update={"cursor": cursor})
                    page += 1
    report = dict(outcome="passed" if all(row["outcome"] == "passed" for row in outcomes.values()) else "failed", acquired_at=datetime.now(timezone.utc).isoformat(), binding=bound, outcomes=outcomes, discovery=prepared["discovery"], qualification_limit=LIMIT)
    write(root, "consumer-live.json", report)
    print(json.dumps(report))
    return report["outcome"] == "passed"


def replay(bound, root, bundle, manifest_sha256, names):
    cases = json.loads((root / "consumer-cases.json").read_bytes())
    if cases["binding_sha256"] != digest(bound):
        raise ValueError("live consumer cases differ from explicit binding")
    manifest = verify_characterization_review(bundle, manifest_digest=manifest_sha256)
    selection = CharacterizationReviewSelection.model_validate(manifest["selection"])
    if selection.run_id != bound["run_id"] or selection.reference() != ProductReference(**bound["view"]):
        raise ValueError("detached closure differs from explicit final run/pin")
    replay_root = root / "detached" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    outcomes = {}
    for case in cases["cases"]:
        if names and not any(case["name"].startswith(name + "-") for name in names):
            continue
        response = inspect_characterization_review(bundle, CharacterizationRequest.model_validate(case["request"]), manifest_digest=manifest_sha256).model_dump(mode="json")
        write(replay_root, f"raw/{case['name']}-detached.json", response)
        outcomes[case["name"]] = dict(outcome="passed" if digest(response) == case["native_sha256"] else "failed", detached_sha256=digest(response))
    if not outcomes:
        raise ValueError("no saved live cases matched detached selection")
    report = dict(outcome="passed" if all(row["outcome"] == "passed" for row in outcomes.values()) else "failed", acquired_at=datetime.now(timezone.utc).isoformat(), binding=bound, manifest_sha256=manifest_sha256, closure_verification="passed", completeness=manifest["completeness"], original_source_completeness=manifest["original_source_completeness"], outcomes=outcomes, qualification_limit=LIMIT)
    write(replay_root, "consumer-detached.json", report)
    print(json.dumps(report))
    return report["outcome"] == "passed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "live", "replay"))
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "consumers")
    parser.add_argument("--export-max-bytes", type=int, default=8 * 1024**3)
    parser.add_argument("--max-coverage-pages", type=int, default=1000)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--request-name", action="append")
    args = parser.parse_args()
    bound, pin = binding(args.binding)
    if args.action == "prepare":
        prepare(Settings(), bound, pin, args.output, args.export_max_bytes)
        return True
    if args.action == "live":
        return asyncio.run(live(Settings(), bound, args.output, args.max_coverage_pages))
    if args.bundle is None or not args.manifest_sha256:
        parser.error("replay requires --bundle and separately retained --manifest-sha256")
    return replay(bound, args.output, args.bundle, args.manifest_sha256, args.request_name)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
