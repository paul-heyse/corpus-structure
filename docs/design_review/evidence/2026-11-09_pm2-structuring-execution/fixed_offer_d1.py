"""Run a private fixed-offer d1 rendering screen without publishing grades or results."""

import json
import sys
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import select

from corpus_structure.methods.pm2_worker import open_pm2_worker, preflight_pm2_runtime
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import declared_families
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parents[4]
ASSETS = ROOT / "build/models/pm2"
WORKER = ROOT / "python/corpus-structure/src/corpus_structure/methods/pm2_native.py"
PROJECT = "nce-grinstead-snell-full-book"
VERSION = "fixed-offer-rendering-screen-1"
CASES = {
    "probability": (431, 531, 2128, "quantity"),
    "roulette": (431, 531, 2129, "quantity"),
    "host": (431, 531, 2130, "qualification_host"),
    "referent": (431, 531, 2131, "local_referent"),
    "exponential": (464, 572, 2198, "concept_link"),
    "no_match": (464, 572, 2199, "concept_link"),
}
DECISIONS = {
    "qualification_host": "Read the marked qualifier and the candidate predicate evidence in the source. Choose the predicate whose event or assertion is governed by that qualifier. Distinguish an adjacent predicate from the one the qualifier governs.",
    "local_referent": "Identify the entity denoted by the focal mention. Compare the exact offered mentions with that mention in context. Choose only an earlier offered mention that denotes the same entity, not merely a nearby participant.",
    "concept_link": "Identify the concept expressed by the focal use in this source. Compare each offered definition's exact term and defining content. Choose only an offered definition of that same concept, not a related, broader or similarly named concept.",
}


def digest(value):
    return sha256(canonical_bytes(value)).hexdigest()


def retained(conn, run, cut, task, question):
    session = bind_completed_result(conn, run)
    if session.completed_cut_id != cut:
        raise ValueError("historical d1 cut differs")
    tasks, cuts, results, configs, runs = map(
        table, ("ops.task", "ops.cut_task", "ops.task_result", "ops.method_config", "ops.run")
    )
    query = (
        select(
            results.c.body,
            tasks.c.unit_id,
            tasks.c.unit_key,
            tasks.c.input_hash,
            configs.c.config_hash,
            configs.c.params,
            runs.c.project_id,
        )
        .select_from(cuts)
        .join(tasks, tasks.c.id == cuts.c.task_id)
        .join(results, results.c.task_id == cuts.c.origin_task_id)
        .join(configs, configs.c.id == tasks.c.method_config_id)
        .join(runs, runs.c.id == tasks.c.run_id)
        .where(cuts.c.cut_id == cut, tasks.c.id == task, tasks.c.run_id == run)
    )
    budget = PublishedReadBudget(16, 4 * 1024 * 1024)
    budget.preflight(conn, query)
    body, view_id, unit, input_hash, config_hash, params, project = conn.execute(query).one()
    budget.value(body)
    detail = source_python(body["parse_detail"])["pm2_native"]
    request = detail["request"]
    view = BoundReader(conn, run, session.prepared, cut, analysis=False).source_view_ref(view_id)
    (operation,) = body["contribution_operations"]
    assessed = request["interpretation"]["assessed_scope"]
    if (
        project != PROJECT
        or body["release_id"] != session.prepared.release_id
        or body["source"] != view.key
        or body["method"] != "extract.pm2_d1"
        or body["unit_key"] != unit
        or body["input_hash"] != input_hash
        or body["configuration_hash"] != config_hash
        or operation["report_digest"] != digest(detail)
        or operation["operation_version"] != "2"
        or set(request["questions"]) != {question}
        or assessed["pin"]["source_view_id"] != view_id
        or assessed["pin"]["projection_digest"] != view.projection_digest
        or detail["authorized_source_path"] != "/source"
    ):
        raise ValueError(f"retained d1 task {task} does not match its exact run/source binding")
    pin = dict(
        run=run, cut=cut, task=task, configuration=config_hash, input_hash=input_hash,
        report_digest=operation["report_digest"], source=assessed,
        declaration_digest=request["interpretation"]["declaration_digest"],
        candidate_population=request["interpretation"]["candidates"],
    )
    # JSONB object order is not prompt order. Recover the exact state order from
    # the worker's retained serialization and the criteria order from the release.
    rendered = json.loads(detail["native"]["rendered_state"])
    family = declared_families(session.prepared.registry_rows)[operation["question"]]
    (declaration,) = (item for item in family.questions if item.key == question)
    native_question = declaration.native(rendered.get("candidates", []))
    if (
        rendered != request["state"]
        or family.digest != pin["declaration_digest"]
        or native_question != request["questions"][question]
    ):
        raise ValueError("retained d1 request differs from its released rendering")
    request = {**request, "state": rendered, "questions": {question: native_question}}
    return pin, request, detail["native"], params["startup"]


def native_input(request):
    return {key: deepcopy(request[key]) for key in ("state", "questions")}


def challenger(request, key):
    if key in DECISIONS:
        # Keep the authenticated state and all choices verbatim. Change only task wording.
        request["questions"][key]["instructions"] = (
            request["questions"][key]["instructions"] + " " + DECISIONS[key]
        )
    return request


def reverse_options(request, key):
    request["state"]["candidates"].reverse()
    criteria = request["questions"][key]["criteria"]
    # Reverse the candidate ordering without moving the released non-candidate options.
    offered = {candidate["key"] for candidate in request["state"]["candidates"]}
    reversed_pairs = iter(reversed([(key, value) for key, value in criteria.items() if key in offered]))
    request["questions"][key]["criteria"] = dict(
        next(reversed_pairs) if key in offered else (key, value) for key, value in criteria.items()
    )
    return request


def quantity_parts(request):
    request["questions"] = {
        "magnitude": {
            "type": "number",
            "instructions": "Read the exact positive numeric magnitude stated for the amount at stake in the focal clause. Copy its original numeric literal from the source.",
        },
        "written_unit": {
            "type": "text",
            "instructions": "Copy only the exact written unit for that stated amount. If no unit is written, return no span.",
        },
        "role": {
            "type": "choice",
            "instructions": "Classify how the focal clause uses the stated amount; use not_stated if the role is unavailable.",
            "criteria": {
                "loss": "The amount is lost, surrendered or paid out by the focal actor.",
                "gain": "The amount is won, received or credited to the focal actor.",
                "not_stated": "Neither a loss nor a gain for the focal actor is established.",
            },
            "multiple": False,
        },
    }
    return request


def compact(reply, request, aliases):
    result = {key: value for key, value in reply.items() if key in {"outcome", "reason", "row_tokens"}}
    if reply["outcome"] not in {"succeeded", "empty"}:
        return result
    state = json.loads(reply["rendered_state"])
    if state != request["state"] or set(reply["native"]["answers"]) != set(request["questions"]):
        raise ValueError("native reply does not match the supplied request")
    answers = {}
    for key, answer in reply["native"]["answers"].items():
        shape = request["questions"][key]
        if answer["type"] != shape["type"]:
            raise ValueError("native reply differs from the declared question type")
        if answer["type"] == "choice":
            if answer["choice"] not in shape["criteria"] or set(answer["probabilities"]) != set(shape["criteria"]):
                raise ValueError("native reply differs from the offered option population")
            answers[key] = {**answer, "durable_choice": aliases.get(answer["choice"], answer["choice"])}
        else:
            answers[key] = answer
            if answer.get("span") is not None:
                (start, end), = ((a, b) for a, b, p in reply["state_fields"] if p == "/source")
                a, b = answer["span"]
                rendered = reply["rendered_state"]
                if (
                    answer.get("path") != "/source"
                    or not start <= a < b <= end
                    or json.loads('"' + rendered[a:b] + '"') != answer["text"]
                    or json.loads(rendered[:start] + rendered[end:])["source"] != ""
                ):
                    raise ValueError("native read did not locate the literal in the authorized source field")
    return {**result, "answers": answers}


def main():
    settings = Settings()
    with (
        open_runtime_engine(settings, "pm2-fixed-offer-screen", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        pinned = {name: retained(conn, *selection) for name, selection in CASES.items()}
    native_python = Path(sys.executable)
    preflight = preflight_pm2_runtime(
        python=native_python, script=WORKER, project=ROOT, provider="d1", assets=ASSETS
    )
    runtime = preflight["runtime_identity"]
    work = []
    for name, (_run, _cut, _task, key) in CASES.items():
        pin, request, historic_reply, _startup = pinned[name]
        aliases = request["interpretation"].get("option_aliases", {})
        base = native_input(request)
        work.append((name, "incumbent", base, aliases))
        if key in DECISIONS:
            work.append((name, "task_wording", challenger(native_input(request), key), aliases))
            if len(request["state"]["candidates"]) > 1:
                reordered = reverse_options(challenger(native_input(request), key), key)
                work.append((name, "task_wording_reordered", reordered, aliases))
        else:
            work.append((name, "separate_quantity_facets", quantity_parts(native_input(request)), {}))
        pinned[name] = (
            pin, request, compact(historic_reply, base, aliases), _startup
        )
    with TemporaryDirectory(prefix="pm2-fixed-offer-") as temporary:
        profile = Path(temporary) / "profile.json"
        profile.write_bytes(canonical_bytes({
            "provider": "d1", "device": "cuda", "assets": str(ASSETS), "runtime_identity": runtime,
        }))
        with open_pm2_worker(
            python=native_python, script=WORKER, profile=profile, device="cuda",
            nemotron_endpoint=settings.nemotron.endpoint,
        ) as worker:
            for _, _, _, expected_startup in pinned.values():
                if any(
                    worker.startup.get(key) != value
                    for key, value in expected_startup.items()
                    if key != "runtime_identity"
                ):
                    raise ValueError("model/device policy differs from the retained incumbent")
            rows = []
            for offset in range(0, len(work), 8):
                batch = work[offset:offset + 8]
                replies = worker.infer({"batch": [row[2] for row in batch]})["batch"]
                for (name, arm, request, aliases), reply in zip(batch, replies, strict=True):
                    rows.append({
                        "case": name, "arm": arm,
                        "ordered_request_digest": sha256(json.dumps(
                            request, ensure_ascii=False, separators=(",", ":"), allow_nan=False
                        ).encode()).hexdigest(),
                        "question": request["questions"], "result": compact(reply, request, aliases),
                    })
    output = {
        "protocol": VERSION,
        "scope": "private worker screen; no managed inference run, new grade, or selection",
        "runtime_digest": digest(runtime),
        "sources": {
            name: {
                **pin,
                "candidate_display": request["state"].get("candidates", []),
                "historical_incumbent": historical,
            }
            for name, (pin, request, historical, _) in pinned.items()
        },
        "rows": rows,
    }
    print(canonical_bytes(output).decode())


if __name__ == "__main__":
    main()
