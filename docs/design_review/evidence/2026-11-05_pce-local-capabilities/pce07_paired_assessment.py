"""Evidence-only retained baseline, exact-question paired grading and fresh output capture.

Commands execute only when explicitly invoked against the coordinator's final
runtime. Immutable 2026-11-05 source-only A/B/C artifacts remain in foundations.
No assessment labels enter a producer; raw tasks36/37 are the retained baseline.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict, deque
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from corpus_structure.evaluate import operation_assessment as assessment
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.runtime_bindings import installed_runtime_id
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
FOUNDATION = HERE.parent / "2026-11-05_pce-foundations"
FOUNDATION_DRIVER = FOUNDATION / "pce03_native_assessment_004.py"
PROJECT = "m1-source-grinstead-snell"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")


def read_local(name):
    path = Path(name)
    return json.loads((path if path.is_absolute() else RAW / path).read_bytes())


def artifact_path(name):
    path = Path(name)
    return path if path.is_absolute() else RAW / path


def foundation_driver():
    # The original source/author lookup owner stays unchanged. Only new writes
    # are redirected; absolute wrapper paths reuse its existing protected APIs.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("pce07_foundation004", FOUNDATION_DRIVER)
    if spec is None or spec.loader is None:
        raise RuntimeError("foundation driver import is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.write = lambda path, value: write(RAW / path.name, value)
    return module


def project_defaults(settings):
    with open_runtime_engine(settings, "pce07-assessment-defaults", purpose="evaluate") as engine, engine.connect() as conn:
        project = table("data.project")
        return dict(conn.execute(select(project).where(project.c.project_id == PROJECT)).mappings().one())


def run_context(conn, run_id):
    runs, completed = map(table, ("ops.run", "ops.completed_result"))
    run = dict(conn.execute(select(runs).where(runs.c.id == run_id,
        runs.c.project_id == PROJECT)).mappings().one())
    sealed = dict(conn.execute(select(completed).where(completed.c.run_id == run_id)).mappings().one())
    return run, sealed, open_release(conn, run["release_id"])


def operation_inventory(conn, *, run_id, source_view_id=None):
    run, completed, prepared = run_context(conn, run_id)
    inventory = read_source_contributions(conn, prepared=prepared, run_id=run_id,
        source_view_id=source_view_id, cut_id=completed["cut_id"], limit=10_000)
    if inventory.more:
        raise ValueError("selected operation inventory exceeds 10000 rows")
    return run, completed, prepared, inventory


def local_interpretation_inventory(conn, *, run_id):
    _, completed, prepared, inventory = operation_inventory(conn, run_id=run_id)
    reports = []
    for operation in inventory.operations:
        if operation["operation_version"] != "local-interpretation-1":
            continue
        details = read_source_contributions(conn, prepared=prepared, run_id=run_id,
            source_view_id=operation["source_view_id"], operation_key=operation["operation_key"],
            cut_id=completed["cut_id"], limit=10_000, include_details=True)
        if details.more or len(details.operations) != 1:
            raise ValueError("bounded local interpretation operation capture is incomplete")
        reports.append(dict(details.operations[0]))
    return dict(operations=reports,
        outcome_counts=dict(Counter(row["outcome"] for row in reports)),
        production_factor="unavailable" if reports and all(
            row["local_interpretation"]["outcome"] == "not_run"
            and not row["local_interpretation"]["coupling_enabled"]
            and "request" not in row["local_interpretation"] for row in reports)
            else "inspect_actual_retained_reports",
        scope="actual retained consumer questions; useful source products survive not_run solves")


def run_selected_retained(args, settings, old, retained_tasks):
    """Existing registered retained-only graph with explicit raw candidate tasks."""
    from corpus_structure.orchestrate.phase0 import bind_pdf_source

    product = old.retained_product()
    pack = old.DOMAINS / "statistics"
    with open_runtime_engine(settings, "pce07-selected-retained-operation", purpose="write") as engine:
        selected_before = old.selected_default(engine)
        with engine.connect() as conn:
            prepared = open_release(conn, args.release)
            realizations, documents = map(table, ("data.realization", "kb.document"))
            realization = conn.execute(select(realizations).where(
                realizations.c.realization_id == args.realization,
                realizations.c.project_id == PROJECT,
                realizations.c.release_id == args.release)).mappings().one()
            docs = [dict(row) for row in conn.execute(select(documents).where(
                documents.c.project_id == PROJECT)).mappings()]
            document = old.m1.retained_document(conn, product, prepared=prepared,
                project_id=PROJECT, documents=docs)
            corpus, _ = old.records([row for row in docs if row["id"] == document.id], {},
                slice=None, scope=None, corpus=None)
            binding = old.OperationBinding(args.release, args.realization,
                realization["data_revision"], canonical_bytes(dict(domain="statistics",
                    release=args.release, retained_source_tasks=retained_tasks)))
        registry = bind_pdf_source(old.m1.registry(pack), product, configuration="default",
            method_name="ingest.pdf_integrated", input_role="integrated")
        registry = old.m1.bind_retained_document(registry, document)
        allowed = {"ingest.pdf_integrated", "resolve.m1_readings"}
        configs = {key: dict(value) for key, value in registry.file.configs.items() if key in allowed}
        configs["resolve.m1_readings"]["default"] = dict(
            configs["resolve.m1_readings"]["default"], retained_source_tasks=retained_tasks)
        registry = old.MethodRegistry([method for method in registry.methods() if method.name in allowed],
            replace(registry.file, configs=configs), registry.sources, prepared=registry.prepared)
        selected = registry.resolve("resolve.m1_readings", "default").config
        if tuple(selected.retained_source_tasks) != retained_tasks or selected.source_dependencies != "retained_source_result":
            raise RuntimeError("retained resolver route would execute an upstream producer")
        source = old.m1.source_graph("source-only")
        graph = old.Graph((*source.stages, (old.Stage.ASSEMBLE, (
            old.Step("resolve.m1_readings/default", upstream=("ingest.pdf_integrated",)),))),
            policy_propose=False)
        if {step.config.partition("/")[0] for _, steps in graph.stages for step in steps} != allowed or graph.policy_propose:
            raise RuntimeError("selected retained graph contains an unauthorized producer")
        report = old.run_source_methods(engine, project_id=PROJECT, prepared=prepared,
            binding=binding, registry=registry, graph=graph,
            method_settings=old.method_settings(settings), domain="statistics",
            guideline=(pack / "m1-guideline.md").read_text(), corpus_record=corpus,
            extraction_policy="m1-candidate", extraction_policy_config=canonical_bytes(dict(
                route="selected-retained-reading-only-1", retained_source_tasks=retained_tasks,
                provider_execution=False, conversion=False, annotation_execution=False)).decode())
        inventory = old.method_inventory(engine, report.run_id, allowed)
        write(RAW / f"{args.receipt}-prediction-prepared.json", dict(report.model_dump(mode="json"),
            method_inventory=inventory, declared_graph=sorted(allowed)))
        completed = old.commands.finalize_bound_run(engine, report.run_id,
            f"{args.receipt}:prediction:{report.run_id}", analytics=settings.analytics)
        selected_after = old.selected_default(engine)
        if selected_before != selected_after:
            raise RuntimeError("retained reading finalization changed the selected result")
        return dict(prediction_run_id=int(report.run_id),
            selected_result_before=selected_before, selected_result_after=selected_after,
            source_ready_cut_id=int(report.cut_id), completed=asdict(completed),
            method_inventory=inventory, retained_source_tasks=list(retained_tasks),
            provider_execution=False, conversion=False, annotation_execution=False,
            persistent_default_changed=False)


def retained(args, settings, old):
    from corpus_structure.orchestrate import m1
    from corpus_structure.schema.pack import DOMAINS

    with open_runtime_engine(settings, "pce07-retained-runtime-pin", purpose="evaluate") as engine, engine.connect() as conn:
        if installed_runtime_id(open_release(conn, args.release)) != args.runtime:
            raise RuntimeError("installed runtime differs from the final coordinator pin")
    registered = m1.registry(DOMAINS / "statistics")
    if any(method.version != "3" for method in registered.methods() if method.name == "resolve.m1_readings"):
        raise RuntimeError("retained journey requires reading resolver version3")
    retained_tasks = tuple(args.retained_tasks)
    if not retained_tasks or len(set(retained_tasks)) != len(retained_tasks) or any(task < 1 for task in retained_tasks):
        raise ValueError("retained tasks must be distinct positive task IDs")
    result = run_selected_retained(args, settings, old, retained_tasks)
    with open_runtime_engine(settings, "pce07-retained-result-inventory", purpose="evaluate") as engine, engine.connect() as conn:
        run, completed, _, inventory = operation_inventory(conn, run_id=result["prediction_run_id"])
        if run["runtime_id"] != args.runtime or run["release_id"] != args.release:
            raise RuntimeError("actual retained run differs from the final runtime/release pin")
        local = local_interpretation_inventory(conn, run_id=run["id"])
        origins = {row["origin_task_id"] for row in inventory.reports
            if row["method"] == "resolve.m1_readings"}
        results = table("ops.task_result")
        raw_inputs = [dict(task_id=row["task_id"],
            retained_input=source_python(row["parse_detail"])["retained_input"])
            for row in conn.execute(select(results.c.task_id,
                results.c.body["parse_detail"].label("parse_detail"))
                .where(results.c.task_id.in_(origins))).mappings()]
        if {row["retained_input"]["selected_task_id"] for row in raw_inputs} != set(retained_tasks):
            raise RuntimeError("actual retained input task custody differs from the declared source tasks")
        by_operation = defaultdict(Counter)
        for contribution in inventory.contributions:
            by_operation[contribution["operation_key"]][contribution["kind"]] += 1
    return dict(result, outcome="passed", runtime_id=run["runtime_id"], release_id=run["release_id"],
        sealed_result=completed, operation_inventory=list(inventory.operations),
        contribution_counts=dict(Counter(row["kind"] for row in inventory.contributions)),
        semantic_type_counts=dict(Counter(row["semantic_type"] for row in inventory.contributions)),
        operation_contribution_counts={key: dict(counts) for key, counts in by_operation.items()},
        retained_input_custody=raw_inputs,
        pce08_local_consumer=local, producer_models_executed=False,
        scope="registered reading/attachment derivation over explicitly selected raw candidate tasks; no fresh extraction or gap-closure claim")


def body_wrappers(wrappers, old):
    """Drop only the unrelated header unit, preserving exact authored body cases."""
    result = dict(wrappers)
    keys = [key for key in result["frames"] if key.endswith(":unit2")]
    if set(keys) != {question + ":unit2" for question in old.VERSIONS}:
        raise ValueError("paired body assessment requires both frozen source-first questions")
    result["frames"] = {key: result["frames"][key] for key in keys}
    result["payloads"] = {key: result["payloads"][key] for key in keys}
    for key in keys:
        frame = assessment.decode_frame(result["frames"][key])
        if frame.direction != "source_first" or frame.operation_version != old.VERSIONS[frame.operation_question]:
            raise ValueError("body wrapper operation semantics differ from the original frozen question")
        for kind in "ABC":
            authored = result["payloads"][key][kind]["authored"]
            if any(not case["case_id"].startswith("unit2:") for case in authored["cases"]):
                raise ValueError("paired body wrapper contains an unrelated source unit")
            assessment.decode_authored(canonical_bytes(authored), frame)
    return result


def serialize(args, settings, old):
    source_path = FOUNDATION / "raw" / "source-only-unit-2-002.json"
    original = json.loads(source_path.read_bytes())["source_frame"]["source_views"][0]
    wrappers = body_wrappers(old.prepare_wrappers(args, settings), old)
    correspondence = []
    with open_runtime_engine(settings, "pce07-exact-source-correspondence", purpose="evaluate") as engine, engine.connect() as conn:
        run, completed, _ = run_context(conn, args.source_run)
        views = table("kb.source_view")
        for key, encoded in wrappers["frames"].items():
            frame = assessment.decode_frame(encoded)
            current = dict(conn.execute(select(*[column for column in views.c if column.name != "projection"])
                .where(views.c.id == frame.pin["source_view_id"])).mappings().one())
            fields = ("native_task_id", "native_product_key", "native_content_digest",
                "projection_digest", "recipe_digest", "section_pointer", "membership")
            if any(original[field] != current[field] for field in fields):
                raise ValueError("exact source correspondence requires identical retained product/projection/recipe/section/membership")
            correspondence.append(dict(frame_key=key, original_view=original["id"],
                current_view=current["id"], original_release=original["release_id"],
                current_release=run["release_id"], physical_identity={field: current[field] for field in fields},
                rule="identical native product, projection, recipe, section and membership; rebind source aliases only"))
    authors = {}
    for kind in "ABC":
        path = FOUNDATION / "raw" / f"author-{kind}-001.json"
        author = json.loads(path.read_bytes())
        if "20261105" not in author["actor"]:
            raise ValueError("source serialization requires today's independently authored cases")
        authors[kind] = dict(path=str(path), sha256=digest(path), actor=author["actor"])
    adjudicator = json.loads((FOUNDATION / "raw" / "author-C-001.json").read_bytes())
    actual_inputs = {entry["path"]: entry["sha256"] for entry in adjudicator["author_inputs"]}
    if any(actual_inputs[f"author-{kind}-001.json"] != authors[kind]["sha256"] for kind in "AB"):
        raise ValueError("adjudicator inputs differ from the retained independent author bytes")
    return dict(wrappers, protocol="pce07-exact-paired-source-wrappers-1", outcome="passed",
        runtime_id=run["runtime_id"], source_cut_id=completed["cut_id"],
        source_correspondence=correspondence, source_author_artifacts=authors,
        original_source_artifact=dict(path=str(source_path), sha256=digest(source_path)),
        original_translator=dict(path=str(FOUNDATION_DRIVER), sha256=digest(FOUNDATION_DRIVER)),
        serialized_case_counts={key: {kind: len(wrappers["payloads"][key][kind]["authored"]["cases"])
            for kind in "ABC"} for key in wrappers["frames"]},
        selected_scope="unchanged unit2 body cohort: four original text pointers and original16 selected table cells; header unit1 excluded",
        correspondence_limit="No historical whole-record labels or new interpretations; untranslated raw author qualifications remain authoritative.")


def register(args, settings, old):
    args.wrappers = str(artifact_path(args.wrappers).resolve())
    wrappers = read_local(args.wrappers)
    validated = body_wrappers(wrappers, old)
    if set(validated["frames"]) != set(wrappers["frames"]):
        raise ValueError("register requires the serialized body-only wrapper artifact")
    return dict(old.register(args, settings), outcome="passed")


def grade(args, settings, old):
    registration = read_local(args.registration)
    wrappers = read_local(registration["wrapper_artifact"])
    body_wrappers(wrappers, old)
    grades, inventories = {}, {}
    with open_runtime_engine(settings, "pce07-protected-paired-grade", purpose="evaluate") as engine, engine.begin() as conn:
        for label, run_id in (("baseline", args.baseline_run), ("revised", args.prediction_run)):
            run, completed, _, inventory = operation_inventory(conn, run_id=run_id)
            if run["release_id"] != wrappers["release_id"]:
                raise ValueError("paired grading requires both runs in the exact wrapper release")
            inventories[label] = dict(run_id=run_id, runtime_id=run["runtime_id"],
                completed=completed, reports=list(inventory.reports), operations=list(inventory.operations))
        for question, entry in registration["sets"].items():
            frame = assessment.decode_frame(wrappers["frames"][question + ":unit2"])
            availability = {}
            for label in ("baseline", "revised"):
                operations = [row for row in inventories[label]["operations"]
                    if row["source_view_id"] == frame.pin["source_view_id"] and row["question"] == question]
                availability[label] = dict(requested_version=frame.operation_version,
                    actual_versions=sorted({row["operation_version"] for row in operations}),
                    matching_operations=sum(row["operation_version"] == frame.operation_version for row in operations),
                    execution_outcomes=dict(Counter(row["outcome"] for row in operations)),
                    scope="operation population unavailable/not_requested" if not operations else "actual retained operation population",
                    source_first_denominator=len(wrappers["payloads"][question + ":unit2"]["C"]["authored"]["cases"]))
            mismatch = any(set(item["actual_versions"]) - {frame.operation_version} for item in availability.values())
            if mismatch:
                grades[question] = dict(outcome="incomparable", availability=availability,
                    reason="returned operation versions differ; no semantic correspondence or relabelling is supplied")
                continue
            before = assessment.reference_evaluate(conn, project_id=PROJECT,
                run_id=args.baseline_run, set_id=entry["set_id"])
            after = assessment.reference_evaluate(conn, project_id=PROJECT,
                run_id=args.prediction_run, set_id=entry["set_id"])
            comparison = assessment.compare_assessments(before.result, after.result)
            grades[question] = dict(outcome="passed", availability=availability,
                baseline=before.model_dump(mode="json"), revised=after.model_dump(mode="json"),
                comparison=comparison,
                comparison_counts={key: len(values) for key, values in comparison["changes"].items()},
                default_export=assessment.review_export(conn, project_id=PROJECT, set_id=entry["set_id"]))
        local = local_interpretation_inventory(conn, run_id=args.baseline_run)
    return dict(protocol="pce07-exact-paired-operation-assessment-1",
        outcome="partial" if any(item["outcome"] == "incomparable" for item in grades.values()) else "passed",
        grades=grades, run_inventories=inventories, pce08_retained_consumer=local,
        runtime_comparison_policy="Paired source/question/version/rubric matched; producer runtimes may differ and remain exactly attributed. No runtime-equivalence claim.",
        population_estimate="not_established", quality_benefit="not_established_by_bounded_case_comparison",
        causal_attribution="Missing captured outputs measure this source-first population only; no nomination, producer, retrieval, source-inspection or inspected-absence inference follows.")


OUTPUT_PRIORITY_TYPES = (
    "attribute.role", "entity.distribution", "entity.quantity", "entity.condition",
    "source_rule.definition_cue", "source_rule.condition_cue", "math.syntax",
    "table.header_path_attachment", "table.caption_attachment",
    "relation.approximated_by", "relation.arises_from", "relation.condition_for",
)


def output_stratum(row):
    return (row["kind"], row["semantic_type"], row["operation_question"], row["operation_version"])


def choose_outputs(pool, limit=24):
    """Metadata-only capability coverage before bounded kind/stratum fill."""
    ordered = sorted(pool, key=lambda identity: sha256(
        ("pce07-output-selection-2:" + identity).encode()).hexdigest())
    selected = []

    def take(predicate):
        if len(selected) < limit:
            identity = next((identity for identity in ordered
                if identity not in selected and predicate(pool[identity])), None)
            if identity is not None:
                selected.append(identity)

    # First cover available new semantic questions, regardless of how many
    # alphabetically earlier legacy proposal strata exist.
    for semantic_type in OUTPUT_PRIORITY_TYPES:
        take(lambda row, semantic_type=semantic_type: row["semantic_type"] == semantic_type)
    take(lambda row: row["semantic_type"] == "attribute.role")
    for marker in (".native_group", ".returned_group"):
        take(lambda row, marker=marker: row["kind"] == "composite" and row["semantic_type"].endswith(marker))
    for kind in ("occurrence", "diagnostic"):
        take(lambda row, kind=kind: row["kind"] == kind)
    for semantic_type in OUTPUT_PRIORITY_TYPES:
        for stratum in sorted({output_stratum(row) for row in pool.values()
            if row["semantic_type"] == semantic_type}):
            if not any(output_stratum(pool[identity]) == stratum for identity in selected):
                take(lambda row, stratum=stratum: output_stratum(row) == stratum)
    for group in sorted({(row["kind"], row["operation_question"], row["operation_version"])
        for row in pool.values()}):
        if not any((pool[identity]["kind"], pool[identity]["operation_question"],
            pool[identity]["operation_version"]) == group for identity in selected):
            take(lambda row, group=group: (row["kind"], row["operation_question"], row["operation_version"]) == group)
    strata = defaultdict(list)
    for identity, row in pool.items():
        if identity not in selected:
            strata[output_stratum(row)].append(identity)
    queues = defaultdict(deque)
    for stratum, identities in sorted(strata.items()):
        queues[stratum[0]].append(deque(sorted(identities,
            key=lambda identity: sha256(("pce07-output-selection-2:" + identity).encode()).hexdigest())))
    while any(queues.values()) and len(selected) < limit:
        for kind in sorted(queues):
            if not queues[kind] or len(selected) >= limit:
                continue
            stratum = queues[kind].popleft()
            selected.append(stratum.popleft())
            if stratum:
                queues[kind].append(stratum)
    return selected


OUTPUT_SOURCE_RUBRIC = {
    "literal_extent_fidelity": "Assess the exact retained source literal and its native extent only. Literal/location fidelity does not establish scientific entity type, contextual role, attachment, canonical identity or source completeness.",
    "entity_classification": "Independently classify the located mention as distribution, quantity or condition where source supports that class; no supported class, ambiguity and insufficient context are permitted. The producer's proposed entity label is withheld.",
    "conditional_role": "For this actually selected located mention, independently assess defined_term or mentioned_term if supported. Neither label is forced. Mention discovery, missing attributes and negative labels are different questions; this output-first question does not measure discovery recall.",
    "directional_source_association": "Independently identify source-supported endpoints for the declared predicate, preserving direction, endpoint roles and governing qualifiers. Locate the governing target from the source; the producer's proposed target and qualifiers are withheld. Correct subject/cue location does not establish attachment.",
    "source_grouping": "Independently assess only the selected grouping facet whose source question is specified. A composite can remain unassessed when source scope or the question is insufficient; do not infer correctness of a complete record from its pieces.",
    "captured_syntax": "Assess only the declared captured-native-text syntax question. Captured text and native-item placement do not establish original PDF glyph fidelity, successful recognition, symbol interpretation or scientific truth; preserve whole versus trimmed input and explicit failure/ambiguity.",
    "authoring": "Author one chosen applicable facet per interest for this initial bounded cohort. State selected_facet, independently permissible fields and exact native spans/pieces, source state, uncertainty and limits. Do not copy producer output values or scores: they are withheld. No forced label or target is required; use unassessed when necessary.",
}


def source_interest(row, closure, *, interest_id, frame_key, question, version):
    """Expose declared question locations, never proposed values, scores or targets."""
    primary = [endpoint for endpoint in row.get("endpoints", ())
        if endpoint["role"] in {"head", "subject", "term", "cell_value", "mention"}]
    subjects = [closure[endpoint["contribution_id"]] for endpoint in primary] if primary else [row]
    extents = {}
    for subject in subjects:
        for anchor in subject.get("anchors", ()):
            extent = dict(pin=dict(anchor["pin"]), pointer=anchor["pointer"],
                start=anchor.get("start"), end=anchor.get("end"), precision=anchor["precision"])
            extents[canonical_bytes(extent)] = extent
    source_extents = [extents[key] for key in sorted(extents)]
    pointers = sorted({extent["pointer"] for extent in source_extents})
    semantic_type = row["semantic_type"]
    facets = ["literal_extent_fidelity"] if row["kind"] == "occurrence" else (
        ["conditional_role"] if semantic_type == "attribute.role" else
        ["directional_source_association"] if row["kind"] == "relation" else
        ["source_grouping"] if row["kind"] == "composite" else
        ["captured_syntax"] if "syntax" in semantic_type or "syntax" in question else
        ["literal_extent_fidelity"])
    if semantic_type.startswith("entity."):
        facets.append("entity_classification")
    return dict(interest_id=interest_id, frame_key=frame_key,
        intended_question="located entity classification/literal fidelity" if semantic_type.startswith("entity.") else semantic_type,
        operation_question=question, operation_version=version, product_kind=row["kind"],
        declared_predicate=semantic_type if row["kind"] == "relation" else None,
        declared_endpoint_roles=[endpoint["role"] for endpoint in row.get("endpoints", ())],
        primary_endpoint_role=primary[0]["role"] if len(primary) == 1 else None,
        selected_facet=facets[0], available_facets=facets,
        source_item_pointers=pointers, source_extents=source_extents,
        context_item_pointers=sorted({pointer.split("/data/table_cells/", 1)[0] for pointer in pointers}),
        scope="The extents declare where this output-first question is inspected; they are not source-truth labels. Inspect complete named native items, full table nodes for cell pointers, ancestors and governing context. Independently author permissible source fields/spans for one selected facet.",
        limitations="No proposed output value, score, target, frozen contribution ID or prior judgment is supplied. A missing source subject or insufficient independent rubric remains unassessed.")


def output_prepare(args, settings, old):
    source = body_wrappers(read_local(args.wrappers), old)
    seed = assessment.decode_frame(next(iter(source["frames"].values())))
    with open_runtime_engine(settings, "pce07-fresh-output-selection", purpose="evaluate") as engine, read_snapshot(engine) as conn:
        run, completed, prepared, inventory = operation_inventory(conn, run_id=args.prediction_run,
            source_view_id=seed.pin["source_view_id"])
        if run["release_id"] != seed.release_id:
            raise ValueError("fresh output capture requires the exact current source-frame release")
        operations = {row["operation_key"]: row for row in inventory.operations if row["method"] == args.method}
        pool = {row["contribution_id"]: dict(row,
            operation_question=operations[row["operation_key"]]["question"],
            operation_version=operations[row["operation_key"]]["operation_version"])
            for row in inventory.contributions if row["operation_key"] in operations}
        selected = choose_outputs(pool)
        closure, pending = {}, set(selected)
        while pending:
            if len(closure) + len(pending) > 1000:
                raise ValueError("fresh selected output endpoint/member closure exceeds 1000 products")
            details = read_source_contributions(conn, prepared=prepared, run_id=args.prediction_run,
                source_view_id=seed.pin["source_view_id"], cut_id=completed["cut_id"],
                contribution_ids=tuple(sorted(pending)), limit=10_000, include_details=True,
                max_bytes=32_000_000)
            received = {row["contribution_id"]: dict(row) for row in details.contributions}
            if details.more or pending - received.keys():
                raise ValueError("fresh selected output endpoint/member capture is incomplete")
            closure.update(received)
            pending = {endpoint["contribution_id"] for row in closure.values() for endpoint in row.get("endpoints", ())}
            pending.update(member for row in closure.values() for member in row.get("members", ()))
            pending.difference_update(closure)
        by_operation = defaultdict(list)
        for identity in selected:
            by_operation[(pool[identity]["operation_question"], pool[identity]["operation_version"])].append(identity)
        frames, interests, captures = {}, [], []
        for index, ((question, version), identities) in enumerate(sorted(by_operation.items()), start=1):
            key = f"operation{index}:unit2"
            relevant, queue = set(), list(identities)
            while queue:
                identity = queue.pop()
                if identity in relevant:
                    continue
                relevant.add(identity)
                row = closure[identity]
                queue.extend(endpoint["contribution_id"] for endpoint in row.get("endpoints", ()))
                queue.extend(row.get("members", ()))
            anchors = {anchor["anchor_id"] for identity in relevant
                for anchor in closure[identity].get("anchors", ())}
            related_pins = {canonical_bytes(anchor["pin"]): anchor["pin"] for identity in relevant
                for anchor in closure[identity].get("anchors", ()) if anchor["pin"] != seed.pin}
            frame = replace(seed, guideline_version="pce07-fresh-output-source-1",
                rubric_version="pce07-output-local-1", context_policy="exact-native-source-output-question-1",
                operation_question=question, operation_version=version, direction="output_first",
                anchor_ids=tuple(sorted(anchors)), anchor_scopes=(),
                related_pins=tuple(related_pins[key] for key in sorted(related_pins)),
                contribution_ids=tuple(identities))
            frames[key] = assessment.encode_frame(frame)
            for identity in identities:
                row = closure[identity]
                interest_id = f"pce07-output-source-{len(interests) + 1:03d}"
                interests.append(source_interest(row, closure, interest_id=interest_id,
                    frame_key=key, question=question, version=version))
                captures.append(dict(interest_id=interest_id, frame_key=key, contribution=row))
        reader = BoundReader(conn, args.prediction_run, prepared, completed["cut_id"], analysis=False,
            read_budget=PublishedReadBudget(40000, 256 * 1024**2))
        view = reader.source_view(seed.pin["source_view_id"])
        related_ids = {pin["source_view_id"] for encoded in frames.values()
            for pin in assessment.decode_frame(encoded).related_pins}
        related_views = {identity: reader.source_view(identity) for identity in related_ids}
        source_packet = dict(protocol="pce07-fresh-output-source-authoring-1",
            source_scopes=[dict(frame_key=key, unit_ref=seed.unit, pin=dict(seed.pin),
                operation_question=assessment.decode_frame(encoded).operation_question,
                operation_version=assessment.decode_frame(encoded).operation_version,
                native_items=list(view.items), native_ancestors=list(view.ancestors),
                related_sources=[dict(pin=dict(pin),
                    native_items=list(related_views[pin["source_view_id"]].items),
                    native_ancestors=list(related_views[pin["source_view_id"]].ancestors))
                    for pin in assessment.decode_frame(encoded).related_pins]) for key, encoded in frames.items()],
            assessment_interests=interests,
            source_only_rubric=OUTPUT_SOURCE_RUBRIC, selected_method=args.method,
            instructions="Fresh independent source-only A/B/C authoring for exact selected operation questions. Producer values/scores and prior judgments are withheld. State inspected scope, exact native pointers/offsets, permitted alternatives, uncertainty and any rubric limitation.")
    write(RAW / f"{args.receipt}-author-source-packet.json", source_packet)
    write(RAW / f"{args.receipt}-selected-products.json", dict(selected_outputs=captures,
        endpoint_member_closure=list(closure.values())))
    return dict(protocol="pce07-frozen-output-frame-1", outcome="passed", source_run_id=args.prediction_run,
        source_cut_id=completed["cut_id"], release_id=prepared.release_id, runtime_id=run["runtime_id"],
        partition="feature_fit", selected_method=args.method, frames=frames,
        author_source_packet=f"{args.receipt}-author-source-packet.json",
        private_product_capture=f"{args.receipt}-selected-products.json",
        output_selection=dict(protocol="pce07-capability-priority-metadata-selection-2", limit=24,
            eligible=len(pool), selected=len(selected), contribution_ids=selected,
            priority_semantic_types=list(OUTPUT_PRIORITY_TYPES),
            available_priority_strata=[list(stratum) for stratum in sorted({output_stratum(row)
                for row in pool.values() if row["semantic_type"] in OUTPUT_PRIORITY_TYPES})],
            selected_strata=[list(stratum) for stratum in sorted({output_stratum(pool[identity])
                for identity in selected})],
            allocation="One per available priority semantic type; second conditional attribute; native/returned composites, literal and diagnostic representatives; uncovered priority and kind/question/version strata; remaining round robin kinds/type/question/version. Independent SHA256 identity order within every choice; no values, labels, scores or judgments consumed.",
            supersession_reason="Protocol2 supersedes protocol1's insufficient new-capability coverage, identified from metadata before any independent output judgments. Earlier frozen selections/receipts remain unchanged."),
        operation_inventory=list(inventory.operations),
        next_work="Fresh independent A/B/C output-specific source answers, exact wrappers and protected registration/grade remain not_run; do not reuse source-first answers as output-first labels.")


OUTPUT_ANSWER_PROTOCOL = "pce07-independent-output-answers-1"


def output_source_scopes(packet):
    scopes = {}
    for scope in packet["source_scopes"]:
        sources = (scope, *scope.get("related_sources", ()))
        scopes[scope["frame_key"]] = {
            source["pin"]["source_view_id"]: dict(pin=source["pin"], items={
                item.get("self_ref", item.get("pointer")): item
                for item in (*source["native_items"], *source["native_ancestors"])
            }) for source in sources
        }
    return scopes


def output_author_anchor(raw, *, frame, sources, old):
    if set(raw) - {"pointer", "precision", "start", "end", "text", "source_view_id", "field"}:
        raise ValueError("authored source piece contains unknown fields or generated identities")
    source = sources[raw.get("source_view_id", frame.pin["source_view_id"])]
    if raw.get("field", "text") != "text":
        raise ValueError("authored value pieces must cite native text, not orig or inferred fields")
    if raw["precision"] == "item":
        if any(raw.get(key) is not None for key in ("start", "end", "text")):
            raise ValueError("item-precision source anchor cannot acquire exact text/offset claims")
        return old.make_anchor(source["pin"], raw["pointer"], items=source["items"])
    if raw["precision"] != "exact" or not isinstance(raw.get("text"), str):
        raise ValueError("exact authored source piece requires its independently transcribed text")
    if type(raw.get("start")) is not int or type(raw.get("end")) is not int or not 0 <= raw["start"] < raw["end"]:
        raise ValueError("exact authored source piece requires nonempty half-open native offsets")
    return old.make_anchor(source["pin"], raw["pointer"], raw["text"], raw["start"], raw["end"], source["items"])


def output_expected_fields(fields, anchors):
    if not isinstance(fields, dict) or set(fields) - {
        "semantic_type", "value", "source_pieces", "source_field_state", "anchor_role"
    }:
        raise ValueError("expected fields must be declared source semantics, never output IDs or scores")
    result = dict(fields)
    if "value" in result:
        # Only the independent author's value is encoded. Producer values and
        # confidence never supply an expectation, even when they appear correct.
        result["value"] = source_value(result["value"])
    exact_pieces = [anchor["source_piece"] for anchor in anchors if anchor["precision"] == "exact"]
    if "source_pieces" in result and (
        len(exact_pieces) != len(anchors) or result["source_pieces"] != exact_pieces
    ):
        raise ValueError("expected source pieces differ from independently authored exact anchors")
    return result


def serialize_output_case(entry, interest, captured, *, frame, sources, provenance, old):
    if set(entry) - {"interest_id", "selected_facet", "source_state", "judgment", "inspected_scope",
        "primary", "alternatives", "anchor_endpoint_role", "explanation", "limitations"}:
        raise ValueError("independent output answer contains unknown fields")
    facet = entry["selected_facet"]
    if facet not in interest["available_facets"]:
        raise ValueError("author selected a facet outside the frozen source question")
    if not entry["inspected_scope"] or not entry["explanation"].strip():
        raise ValueError("independent output answer requires inspected scope and explanation")
    output = captured["contribution"]
    anchors, alternatives, primary_sets, supporting_evidence = {}, [], [], []
    independently_located = [option.get("primary", entry.get("primary", ()))
        for option in entry.get("alternatives", ())] or [entry.get("primary", ())]
    literal_unassessable = (facet == "literal_extent_fidelity" and entry["judgment"] == "supported"
        and not any(pieces and all(piece["precision"] == "exact" for piece in pieces)
            for pieces in independently_located))
    effective_judgment = "unassessed" if literal_unassessable else entry["judgment"]
    roles = {entry["anchor_endpoint_role"]} if entry.get("anchor_endpoint_role") else set()
    if facet == "conditional_role":
        roles.add("mention")
    authored_alternatives = () if literal_unassessable else entry.get("alternatives", ())
    if (not authored_alternatives and facet == "literal_extent_fidelity"
        and effective_judgment == "supported" and entry["source_state"] == "stated"
        and entry.get("primary") and all(piece["precision"] == "exact" for piece in entry["primary"])):
        # The source-only rubric permits exact independently transcribed primary
        # pieces to be the literal expectation; no producer field is consulted.
        authored_alternatives = ({"fields": {}},)
    for alternative in authored_alternatives:
        if set(alternative) - {"fields", "primary", "anchor_endpoint_role", "endpoints", "supporting_source_pieces"}:
            raise ValueError("permissible structure contains unknown fields or generated identities")
        own = [output_author_anchor(raw, frame=frame, sources=sources, old=old)
            for raw in alternative.get("primary", entry.get("primary", ()))]
        if not own:
            raise ValueError("available source expectation requires an independently located primary subject")
        primary_sets.append(tuple(anchor["anchor_id"] for anchor in own))
        anchors.update((anchor["anchor_id"], anchor) for anchor in own)
        supporting = [output_author_anchor(raw, frame=frame, sources=sources, old=old)
            for raw in alternative.get("supporting_source_pieces", ())]
        anchors.update((anchor["anchor_id"], anchor) for anchor in supporting)
        supporting_evidence.append(supporting)
        expected_fields = dict(alternative.get("fields", {}))
        if facet == "literal_extent_fidelity" and "value" in expected_fields:
            literal = expected_fields.pop("value")
            exact_pieces = [anchor["source_piece"] for anchor in own if anchor["precision"] == "exact"]
            if len(exact_pieces) != len(own) or not (
                isinstance(literal, str) and len(exact_pieces) == 1 and literal == exact_pieces[0]
                or isinstance(literal, list) and literal == exact_pieces
            ):
                raise ValueError("literal facet value differs from independently authored ordered exact pieces")
            # This facet measures source literals, not an arbitrary metadata/value payload.
            expected_fields.setdefault("source_pieces", exact_pieces)
        fields = output_expected_fields(expected_fields, own)
        if facet == "literal_extent_fidelity":
            fields["source_anchor_ids"] = [anchor["anchor_id"] for anchor in own]
            if all(anchor["precision"] == "exact" for anchor in own):
                fields.setdefault("source_pieces", [anchor["source_piece"] for anchor in own])
        if facet == "conditional_role" and alternative.get("fields", {}).get("value") not in (
            "defined_term", "mentioned_term"
        ):
            raise ValueError("conditional role expectation must independently select a declared label")
        if alternative.get("anchor_endpoint_role"):
            roles.add(alternative["anchor_endpoint_role"])
        endpoints = []
        for endpoint in alternative.get("endpoints", ()):
            if set(endpoint) - {"role", "anchors", "fields"} or not endpoint["role"].strip():
                raise ValueError("source association needs declared endpoint roles and independent anchors")
            pieces = [output_author_anchor(raw, frame=frame, sources=sources, old=old)
                for raw in endpoint["anchors"]]
            if not pieces:
                raise ValueError("source association endpoint lacks independently located pieces")
            anchors.update((anchor["anchor_id"], anchor) for anchor in pieces)
            endpoints.append(dict(role=endpoint["role"], anchor_ids=[anchor["anchor_id"] for anchor in pieces],
                fields=output_expected_fields(endpoint.get("fields", {}), pieces)))
        if endpoints:
            fields["endpoint_semantics"] = endpoints
        role = alternative.get("anchor_endpoint_role") or entry.get("anchor_endpoint_role")
        if facet == "directional_source_association" and (not role or len(endpoints) < 2):
            raise ValueError("directional source expectation requires its primary role and ordered endpoint semantics")
        if role and endpoints:
            primary = [endpoint for endpoint in endpoints if endpoint["role"] == role]
            if len(primary) != 1 or primary[0]["anchor_ids"] != list(primary_sets[-1]):
                raise ValueError("authored primary pieces differ from the declared source endpoint role")
        if not fields:
            raise ValueError("source expectation has no comparable independently authored field")
        alternatives.append(fields)
    if len(roles) > 1:
        raise ValueError("one output facet cannot silently switch its declared primary endpoint role")
    endpoint_role = next(iter(roles), None)
    if effective_judgment == "supported" and not alternatives:
        raise ValueError("available source answer lacks independent permissible structures")
    if not primary_sets:
        own = [output_author_anchor(raw, frame=frame, sources=sources, old=old)
            for raw in entry.get("primary", ())]
        anchors.update((anchor["anchor_id"], anchor) for anchor in own)
        # For an unassessed answer, these are only immutable population locations;
        # no expected literal, role or target is taken from the producer.
        if not own and entry["judgment"] == "unassessed":
            own = list(output.get("anchors", ()))
            anchors.update((anchor["anchor_id"], anchor) for anchor in own)
        primary_sets.append(tuple(anchor["anchor_id"] for anchor in own))
    case = assessment.OperationCase(case_id=entry["interest_id"], facet=facet,
        anchor_ids=primary_sets[0], permissible_anchor_sets=tuple(dict.fromkeys(primary_sets[1:])),
        inspected_scope=canonical_bytes(entry["inspected_scope"]).decode(), source_state=entry["source_state"],
        judgment=effective_judgment, alternatives=tuple(alternatives), explanation=entry["explanation"] + (
            " Wrapper applicability: exact literal fidelity is unassessed because only item-precision source inspection is independently supplied; the empty-source fact is preserved separately."
            if literal_unassessable else ""),
        assessor_provenance=dict(provenance, fresh_source_answer=entry,
            source_expectation_judgment=entry["judgment"],
            assessment_applicability="item-only source inspection cannot establish a nonempty exact literal extent"
                if literal_unassessable else "selected source facet applicable as authored",
            supporting_source_evidence=supporting_evidence,
            supporting_evidence_scope="Independent source justification and governing context; not a product-owned literal or a grade of captured qualifiers/full scientific statement",
            source_judgment_meaning="support/determinacy of the independently authored expectation, never correctness of hidden output"),
        contribution_kind=output["kind"], contribution_id=output["contribution_id"],
        anchor_endpoint_role=endpoint_role)
    return case, anchors


def output_serialize(args, settings, old):
    selection_path = artifact_path(args.selection)
    selection = read_local(args.selection)
    if selection["protocol"] != "pce07-frozen-output-frame-1":
        raise ValueError("fresh output answers require the current frozen output-selection protocol")
    packet_path = artifact_path(selection["author_source_packet"])
    packet = read_local(selection["author_source_packet"])
    private = read_local(selection["private_product_capture"])
    frames = {key: assessment.decode_frame(value) for key, value in selection["frames"].items()}
    interests = {item["interest_id"]: item for item in packet["assessment_interests"]}
    captures = {item["interest_id"]: item for item in private["selected_outputs"]}
    if len(interests) > 24 or len(interests) != len(packet["assessment_interests"]) or interests.keys() != captures.keys():
        raise ValueError("fresh output interests differ from their bounded frozen population")
    operations = {row["operation_key"]: row for row in selection["operation_inventory"]}
    for key, frame in frames.items():
        captured_ids = {item["contribution"]["contribution_id"] for item in captures.values() if item["frame_key"] == key}
        if frame.direction != "output_first" or frame.release_id != selection["release_id"] or captured_ids != set(frame.contribution_ids):
            raise ValueError("every frozen output must have exactly its retained private interest mapping")
    for identity, captured in captures.items():
        frame = frames[captured["frame_key"]]
        interest = interests[identity]
        if captured["contribution"]["contribution_id"] not in frame.contribution_ids or (
            interest["frame_key"], interest["operation_question"], interest["operation_version"]
        ) != (captured["frame_key"], frame.operation_question, frame.operation_version):
            raise ValueError("private output mapping differs from the exact frozen question/version/frame")
        operation = operations[captured["contribution"]["operation_key"]]
        if (operation["question"], operation["operation_version"]) != (frame.operation_question, frame.operation_version):
            raise ValueError("selected retained operation differs from the frozen semantic question/version")
    scopes = output_source_scopes(packet)
    if scopes.keys() != frames.keys() or any(
        scopes[key][frame.pin["source_view_id"]]["pin"] != frame.pin for key, frame in frames.items()
    ):
        raise ValueError("author source scopes differ from the exact frozen primary source pins")
    paths = {kind: artifact_path(getattr(args, "author_" + kind.lower())) for kind in "ABC"}
    authors = {kind: json.loads(path.read_bytes()) for kind, path in paths.items()}
    if len({author["actor"] for author in authors.values()}) != 3:
        raise ValueError("fresh output A/B/C actors must be independent")
    expected_inputs = {digest(paths[kind]) for kind in "AB"}
    if {item["sha256"] for item in authors["C"]["author_inputs"]} != expected_inputs or not authors["C"].get("adjudication_reasons"):
        raise ValueError("C requires the exact retained A/B inputs and explicit conflict/reason dispositions")
    cases = {key: {} for key in frames}
    anchor_maps = {key: {} for key in frames}
    for kind, author in authors.items():
        if author["protocol"] != OUTPUT_ANSWER_PROTOCOL or author["source_packet_sha256"] != digest(packet_path):
            raise ValueError("independent author protocol/source packet differs from the frozen source-only input")
        if kind in "AB" and author.get("author_inputs"):
            raise ValueError("A/B source-only answers cannot consume another author's answers")
        entries = {entry["interest_id"]: entry for entry in author["cases"]}
        if len(entries) != len(author["cases"]) or entries.keys() != interests.keys():
            raise ValueError("each independent author must answer every frozen interest exactly once")
        provenance = dict(actor=author["actor"], model=author.get("model"),
            source_artifact=str(paths[kind]), source_artifact_sha256=digest(paths[kind]),
            source_packet_sha256=digest(packet_path), serializer_sha256=digest(Path(__file__)),
            source_format_revision=author.get("source_format_revision"),
            assistance="fresh source-only independent output author; deterministic exact-question wrapper")
        for identity, entry in entries.items():
            captured = captures[identity]
            key = captured["frame_key"]
            case, anchors = serialize_output_case(entry, interests[identity], captured,
                frame=frames[key], sources=scopes[key], provenance=provenance, old=old)
            cases[key].setdefault(kind, []).append(case)
            anchor_maps[key].update(anchors)
    encoded, payloads = {}, {}
    for key, original in frames.items():
        frame = replace(original, anchor_ids=tuple(sorted(set(original.anchor_ids) | anchor_maps[key].keys())),
            anchor_scopes=tuple({name: value for name, value in anchor.items()
                if name not in {"anchor_id", "source_piece", "binding"}} for anchor in anchor_maps[key].values()))
        encoded[key] = assessment.encode_frame(frame)
        payloads[key] = {}
        for kind in "ABC":
            payload = dict(protocol=assessment.PROTOCOL, release_id=frame.release_id, unit_ref=frame.unit,
                guideline=frame.guideline_version, rubric_version=frame.rubric_version,
                context_policy=frame.context_policy, operation_question=frame.operation_question,
                operation_version=frame.operation_version, domain=frame.domain, direction="output_first",
                reason="Fresh independent source expectations for the exact frozen output interests; no producer-derived expected value.",
                adjudication_passes=[], cases=[asdict(case) for case in cases[key][kind]])
            assessment.decode_authored(canonical_bytes(payload), frame)
            payloads[key][kind] = dict(actor=authors[kind]["actor"], authored=payload)
    return dict(protocol="pce07-fresh-output-author-wrappers-1", outcome="passed",
        source_run_id=selection["source_run_id"], source_cut_id=selection["source_cut_id"],
        release_id=selection["release_id"], runtime_id=selection["runtime_id"], partition="feature_fit",
        frames=encoded, payloads=payloads, selection_artifact=str(selection_path), selection_sha256=digest(selection_path),
        source_author_packet=str(packet_path), source_cohort_sha256=digest(packet_path),
        source_author_artifacts={kind: dict(path=str(path), sha256=digest(path)) for kind, path in paths.items()},
        output_selection=selection["output_selection"],
        guideline_text="Independently authored source-only expectations for one selected facet per frozen output interest. Conditional roles require the actual located mention; mention discovery is separate. Ordered source endpoint semantics preserve direction. Misidentification and mislinking are observed comparison diagnoses, never inferred from confidence or missing output. Grouping/syntax without a sufficient independent rubric remain unassessed.",
        correspondence="Frozen output population, source cut, operation question/version, guideline and rubric unchanged; independently authored exact source anchors add permissible source targets only.",
        database_mutations=False)


def output_register(args, settings, old):
    wrappers_path = artifact_path(args.wrappers)
    wrappers = read_local(args.wrappers)
    if wrappers["protocol"] != "pce07-fresh-output-author-wrappers-1":
        raise ValueError("output registration requires fresh independently authored output wrappers")
    if digest(artifact_path(wrappers["selection_artifact"])) != wrappers["selection_sha256"]:
        raise ValueError("frozen output selection artifact changed after independent serialization")
    sets = {}
    with open_runtime_engine(settings, "pce07-fresh-output-registration", purpose="evaluate") as engine, engine.begin() as conn:
        for key, encoded in wrappers["frames"].items():
            frame = assessment.decode_frame(encoded)
            if frame.direction != "output_first":
                raise ValueError("fresh output registration cannot consume a source-first denominator")
            created = assessment.create_reference_set(conn, project_id=PROJECT,
                source_run_id=wrappers["source_run_id"], source_cut_id=wrappers["source_cut_id"],
                label=f"{args.receipt}:{key}", legacy_split="dev", guideline=frame.guideline_version,
                guideline_text=wrappers["guideline_text"], partition=wrappers["partition"], frames={frame.unit: frame},
                sampling=dict(seed=20261105, strata={frame.unit: "frozen-output-kind-type-question-version"},
                    inclusion_probabilities={frame.unit: 1}, cohort="pce07-fresh-independent-output24",
                    provenance=dict(wrapper_artifact=str(wrappers_path), wrapper_sha256=digest(wrappers_path),
                        source_packet_sha256=wrappers["source_cohort_sha256"], output_selection=wrappers["output_selection"],
                        inference="none; finite frozen semantic products only")))
            units = table("eval.reference_unit")
            unit = conn.scalar(select(units.c.id).where(units.c.set_id == created["set_id"], units.c.unit_key == frame.unit))
            identities, passes = [], {}
            for kind in "ABC":
                item = wrappers["payloads"][key][kind]
                identity = assessment.record_pass(conn, unit_id=unit, pass_kind=kind, actor=item["actor"],
                    authored=canonical_bytes(dict(item["authored"], adjudication_passes=identities if kind == "C" else [])), frame=frame)
                passes[kind] = identity
                if kind in "AB":
                    identities.append(identity)
            sets[key] = dict(set_id=created["set_id"], pass_ids=passes,
                operation_question=frame.operation_question, operation_version=frame.operation_version)
    return dict(protocol="pce07-fresh-output-registration-1", outcome="passed",
        source_run_id=wrappers["source_run_id"], sets=sets, partition=wrappers["partition"],
        wrapper_artifact=str(wrappers_path), wrapper_sha256=digest(wrappers_path))


def output_grade(args, settings, old):
    registration = read_local(args.registration)
    wrappers = read_local(registration["wrapper_artifact"])
    if registration["protocol"] != "pce07-fresh-output-registration-1" or (
        wrappers["protocol"] != "pce07-fresh-output-author-wrappers-1"
    ) or digest(artifact_path(registration["wrapper_artifact"])) != registration["wrapper_sha256"]:
        raise ValueError("output grading requires its unchanged protected output registration and wrappers")
    grades, diagnostics = {}, []
    with open_runtime_engine(settings, "pce07-protected-fresh-output-grade", purpose="evaluate") as engine, engine.begin() as conn:
        for key, item in registration["sets"].items():
            report = assessment.reference_evaluate(conn, project_id=PROJECT,
                run_id=registration["source_run_id"], set_id=item["set_id"])
            grades[key] = report.model_dump(mode="json")
            expected = {case["case_id"]: case for case in wrappers["payloads"][key]["C"]["authored"]["cases"]}
            for unit in report.result["units"]:
                for case in unit["cases"]:
                    author = expected[case["case_id"]]
                    status = case["judgment"]
                    if status == "unsupported" and author["judgment"] == "supported":
                        status = "mislinked" if case["facet"] == "directional_source_association" else (
                            "misidentified" if case["facet"] in {"literal_extent_fidelity", "entity_classification", "conditional_role"}
                            else "unsupported")
                    diagnostics.append(dict(interest_id=case["case_id"], frame_key=key, outcome=status,
                        protected_judgment=case["judgment"], comparison_error=case["error_category"],
                        source_judgment=author["assessor_provenance"].get("source_expectation_judgment", author["judgment"]),
                        reference_case_judgment=author["judgment"],
                        reason=case["explanation"], facet=case["facet"]))
    return dict(protocol="pce07-fresh-output-assessment-1", outcome="passed", grades=grades,
        diagnostics=diagnostics, diagnostic_counts=dict(Counter(item["outcome"] for item in diagnostics)),
        protected_judgment_counts=dict(Counter(item["protected_judgment"] for item in diagnostics)),
        source_run_id=registration["source_run_id"], population_estimate="not_established",
        scope="Frozen output-first selected facets only; separate from source-first coverage denominators.",
        causal_attribution="Misidentified/mislinked name mismatches with independent source expectations, not a hidden producer stage; missing capture and unavailable questions retain their protected error/outcome without causal attribution.")


def main():
    parser = argparse.ArgumentParser(__doc__)
    subcommands = parser.add_subparsers(dest="action", required=True)
    commands = {name: subcommands.add_parser(name) for name in
        ("retained", "serialize", "register", "grade", "output-prepare", "output-serialize", "output-register", "output-grade")}
    required = {"retained": ("release", "realization", "runtime"), "serialize": ("source-run",),
        "register": ("wrappers",), "grade": ("registration", "baseline-run", "prediction-run"),
        "output-prepare": ("wrappers", "prediction-run"),
        "output-serialize": ("selection", "author-a", "author-b", "author-c"),
        "output-register": ("wrappers",), "output-grade": ("registration",)}
    for action, command in commands.items():
        command.add_argument("--receipt", required=True)
        for name in required[action]:
            command.add_argument("--" + name, required=True, type=int if name.endswith("-run") else str)
    commands["retained"].add_argument("--retained-tasks", nargs="+", type=int, default=(36, 37))
    commands["output-prepare"].add_argument("--method",
        choices=("extract.m1_candidates", "resolve.m1_readings"), default="extract.m1_candidates")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", args.receipt):
        raise ValueError("receipt must be a simple immutable file prefix")
    for suffix in (".json", "-driver.py", "-failure.json", "-prediction-prepared.json",
        "-author-source-packet.json", "-selected-products.json"):
        if (RAW / (args.receipt + suffix)).exists():
            raise FileExistsError(RAW / (args.receipt + suffix))
    with (RAW / f"{args.receipt}-driver.py").open("xb") as stream:
        stream.write(Path(__file__).read_bytes())
    execution = dict(arguments=vars(args).copy(), driver_sha256=digest(Path(__file__)),
        foundation_helper_sha256=digest(FOUNDATION_DRIVER))
    try:
        settings = Settings()
        before = project_defaults(settings)
        old = foundation_driver()
        functions = {"retained": retained, "serialize": serialize, "register": register,
            "grade": grade, "output-prepare": output_prepare, "output-serialize": output_serialize,
            "output-register": output_register, "output-grade": output_grade}
        result = functions[args.action](args, settings, old)
        after = project_defaults(settings)
        if before != after:
            raise RuntimeError("assessment journey changed project defaults")
        result.update(project_defaults_preserved=True, project_defaults_before=before,
            project_defaults_after=after, execution=execution)
    except BaseException as error:
        write(RAW / f"{args.receipt}-failure.json", dict(execution, outcome="failed",
            error_type=type(error).__name__, error=str(error)))
        raise
    write(RAW / f"{args.receipt}.json", result)
    print(json.dumps(dict(outcome=result["outcome"], action=args.action,
        receipt=str(RAW / f"{args.receipt}.json"))), flush=True)


if __name__ == "__main__":
    main()
