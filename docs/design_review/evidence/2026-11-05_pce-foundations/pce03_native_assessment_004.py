"""Bounded PCE03 native journey, using independent source answers and retained tasks.

Run phases explicitly after the coordinator installs the final native candidate.
No model/provider/PDF conversion runs. Each phase writes a new immutable receipt.
Raw independent A/B/C artifacts are read as data and retained unchanged.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.evaluate import operation_assessment as assessment
from corpus_structure.evaluate.record_references import source_binding
from corpus_structure.orchestrate import commands, m1
from corpus_structure.orchestrate.registry import MethodRegistry
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.orchestrate.slices import records
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.record_contracts import anchor_identity
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
PROJECT = "m1-source-grinstead-snell"
QUESTION = "recover_returned_local_contributions"
ATTACHMENT = "propose_returned_role_attachments"
VERSIONS = {QUESTION: "retained-native-contributions-1", ATTACHMENT: "retained-group-attachments-1"}
GUIDELINE = "pce-independent-source-assessment-2"
RUBRIC = "pce-independent-local-2"


def read(name):
    return json.loads((RAW / name).read_bytes())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")


def method_settings(settings):
    return MethodSettings(data_dir=settings.paths.data_dir, model_cache=settings.paths.model_cache,
        nemotron_endpoint=settings.nemotron.endpoint, nemotron_python=settings.nemotron.python,
        nemotron_worker=settings.nemotron.worker, nemotron_receipts=settings.nemotron.receipts,
        nemotron_timeout_seconds=settings.nemotron.timeout_seconds)


def retained_product():
    pin = read("source-only-unit-2-002.json")["source_frame"]["evaluation_frame"]["pin"]
    return ProductReference(pin["native_product_task_id"], pin["product_key"], pin["product_digest"])


def selected_default(engine):
    project = table("data.project")
    with engine.connect() as conn:
        return conn.execute(select(project.c.selected_result_run_id).where(project.c.project_id == PROJECT)).scalar_one()


def method_inventory(engine, run_id, allowed):
    tasks, configs, methods = map(table, ("ops.task", "ops.method_config", "ops.method"))
    with engine.connect() as conn:
        rows = [dict(row) for row in conn.execute(select(tasks.c.id, tasks.c.status, methods.c.name,
            configs.c.params).join(configs, configs.c.id == tasks.c.method_config_id)
            .join(methods, methods.c.id == configs.c.method_id).where(tasks.c.run_id == run_id)).mappings()]
    if {row["name"] for row in rows} - set(allowed):
        raise RuntimeError("retained-only run attempted an unauthorized producer method")
    return rows


def run_source(args, settings):
    graph = m1.source_graph("source-only")
    declared = {step.config for _, steps in graph.stages for step in steps}
    if declared != {"ingest.pdf_integrated/default"} or graph.policy_propose:
        raise RuntimeError("source-only graph contains a forbidden producer or proposal stage")
    with open_runtime_engine(settings, "pce03-source-only", purpose="write") as engine:
        selected_before = selected_default(engine)
        report = commands.start_bound_run(engine, release_id=args.release,
            realization_id=args.realization, project_id=PROJECT, domain="statistics",
            method_settings=method_settings(settings), extraction_policy="m1-candidate",
            m1_configuration="source-only", integrated_product=retained_product())
        inventory = method_inventory(engine, report.run_id, {"ingest.pdf_integrated"})
        write(RAW / f"{args.receipt}-source-prepared.json", dict(report.model_dump(mode="json"), method_inventory=inventory, declared_graph=sorted(declared)))
        completed = commands.finalize_bound_run(engine, report.run_id,
            args.output_realization or f"{args.receipt}:source:{report.run_id}", analytics=settings.analytics)
        selected_after = selected_default(engine)
        if selected_before != selected_after:
            raise RuntimeError("source finalization changed the persistent selected result")
        return dict(source_run_id=int(report.run_id), selected_result_before=selected_before, selected_result_after=selected_after, source_ready_cut_id=int(report.cut_id),
                    completed=asdict(completed), method_inventory=inventory, operation="ci run m1-candidate/source-only then ci run finalize",
                    provider_execution=False, conversion=False, persistent_default_changed=False)


def run_predictions(args, settings):
    from corpus_structure.orchestrate.phase0 import bind_pdf_source

    product = retained_product()
    pack = DOMAINS / "statistics"
    with open_runtime_engine(settings, "pce03-retained-operation", purpose="write") as engine:
        selected_before = selected_default(engine)
        with engine.connect() as conn:
            prepared = open_release(conn, args.release)
            realizations, documents = table("data.realization"), table("kb.document")
            realization = conn.execute(select(realizations).where(realizations.c.realization_id == args.realization,
                realizations.c.project_id == PROJECT, realizations.c.release_id == args.release)).mappings().one()
            docs = [dict(row) for row in conn.execute(select(documents).where(documents.c.project_id == PROJECT)).mappings()]
            document = m1.retained_document(conn, product, prepared=prepared, project_id=PROJECT, documents=docs)
            corpus, _ = records([d for d in docs if d["id"] == document.id], {}, slice=None, scope=None, corpus=None)
            binding = OperationBinding(args.release, args.realization, realization["data_revision"],
                                       canonical_bytes(dict(domain="statistics", release=args.release)))
        registry = bind_pdf_source(m1.registry(pack), product, configuration="default",
                                   method_name="ingest.pdf_integrated", input_role="integrated")
        registry = m1.bind_retained_document(registry, document)
        allowed = {"ingest.pdf_integrated", "resolve.m1_readings"}
        configs = {key: value for key, value in registry.file.configs.items() if key in allowed}
        cfgs = dict(configs["resolve.m1_readings"])
        cfgs["default"] = dict(cfgs["default"], retained_source_tasks=(36, 37))
        configs["resolve.m1_readings"] = cfgs
        registry = MethodRegistry([method for method in registry.methods() if method.name in allowed],
                                  replace(registry.file, configs=configs), registry.sources, prepared=registry.prepared)
        selected_config = registry.resolve("resolve.m1_readings", "default").config
        if tuple(selected_config.retained_source_tasks) != (36, 37) or selected_config.source_dependencies != "retained_source_result":
            raise RuntimeError("prediction route would execute an upstream producer")
        source = m1.source_graph("source-only")
        graph = Graph((*source.stages, (Stage.ASSEMBLE, (Step("resolve.m1_readings/default",
                       upstream=("ingest.pdf_integrated",)),))), policy_propose=False)
        if {step.config.partition("/")[0] for _, steps in graph.stages for step in steps} != allowed or graph.policy_propose:
            raise RuntimeError("retained operation graph contains unauthorized methods")
        report = run_source_methods(engine, project_id=PROJECT, prepared=prepared, binding=binding,
            registry=registry, graph=graph, method_settings=method_settings(settings), domain="statistics",
            guideline=(pack / "m1-guideline.md").read_text(), corpus_record=corpus,
            extraction_policy="m1-candidate", extraction_policy_config=canonical_bytes(dict(
                route="retained-operation-only", retained_source_tasks=[36, 37], provider_execution=False)).decode())
        inventory = method_inventory(engine, report.run_id, allowed)
        write(RAW / f"{args.receipt}-prediction-prepared.json", dict(report.model_dump(mode="json"), method_inventory=inventory, declared_graph=sorted(allowed)))
        completed = commands.finalize_bound_run(engine, report.run_id,
            args.output_realization or f"{args.receipt}:prediction:{report.run_id}", analytics=settings.analytics)
        selected_after = selected_default(engine)
        if selected_before != selected_after:
            raise RuntimeError("retained operation finalization changed the persistent selected result")
        return dict(prediction_run_id=int(report.run_id), selected_result_before=selected_before, selected_result_after=selected_after, source_ready_cut_id=int(report.cut_id),
                    completed=asdict(completed), method_inventory=inventory, retained_source_tasks=[36, 37],
                    provider_execution=False, conversion=False, persistent_default_changed=False)


def source_items():
    result = {}
    for unit in (1, 2):
        packet = read(f"source-only-unit-{unit}-002.json")
        result[unit] = packet["native_contexts"][0]["native_items"]
    return result


def node(items, pointer):
    pointer = pointer.removesuffix("/text")
    if "/data/table_cells/" in pointer:
        table_pointer, index = pointer.split("/data/table_cells/")
        return items[table_pointer]["data"]["table_cells"][int(index)]
    return items[pointer]


def make_anchor(pin, pointer, text=None, start=None, end=None, items=None):
    pointer = pointer.removesuffix("/text")
    row = dict(pin=pin, space="native", pointer=pointer, precision="item")
    actual = node(items, pointer).get("text") if items is not None else None
    if text is not None and text != "":
        if start is None:
            if text != actual:
                raise ValueError(f"author excerpt without exact offsets cannot be relocated: {pointer} {text!r}")
            start, end = 0, len(text)
        if actual is None or actual[start:end] != text:
            raise ValueError(f"independent author source excerpt differs: {pointer}")
        row.update(precision="exact", start=start, end=end, source_piece=text)
    row["anchor_id"] = anchor_identity(row)
    return row


def authored_piece(piece, pin, items):
    evidence = piece["evidence"]
    if isinstance(evidence, list):
        evidence = evidence[0]
    return make_anchor(pin, evidence["native_pointer"], piece["text"],
                       evidence.get("start"), evidence.get("end"), items)


def field_anchor(field, pin, items):
    evidence = next(e for e in field["evidence"] if e["native_pointer"].removesuffix("/text").startswith(("#/texts/", "#/tables/"))
                    and e.get("field", "text") == "text")
    pointer = evidence["native_pointer"].removesuffix("/text")
    text = node(items, pointer).get("text")
    return make_anchor(pin, pointer, text, items=items)


def translate_author(author, pins, items_by_unit, artifact):
    """Only exact source answers become local expectations; prose roles stay unassessed."""
    buckets = {}
    anchors_by_unit = {unit: {} for unit in pins}
    base_provenance = dict(actor=author["actor"], model=author.get("model"), source_artifact=artifact.name,
        source_artifact_sha256=digest(artifact), serializer=Path(__file__).name,
        serializer_sha256=digest(Path(__file__)), assistance="source-only independent author; deterministic wrapper")

    def add(unit, question, raw_case, facet, anchors, *, state="stated", judgment="supported",
            alternatives=(), explanation, kind="proposal", selector=None, endpoint_role=None, suffix=""):
        for anchor in anchors:
            anchors_by_unit[unit][anchor["anchor_id"]] = anchor
        case = assessment.OperationCase(case_id=raw_case["case_id"] + ":" + facet + suffix, facet=facet,
            anchor_ids=tuple(anchor["anchor_id"] for anchor in anchors), inspected_scope=raw_case["case_id"],
            source_state=state, judgment=judgment, alternatives=tuple(alternatives), explanation=explanation,
            assessor_provenance=dict(base_provenance, source_case=raw_case["case_id"], source_facet=facet),
            contribution_kind=kind, candidate_selector=selector or {}, anchor_endpoint_role=endpoint_role)
        buckets.setdefault((question, unit), []).append(case)

    for raw_case in author["cases"]:
        unit = int(raw_case["case_id"].split(":", 1)[0].removeprefix("unit"))
        pin, items = pins[unit], items_by_unit[unit]
        pointer = raw_case.get("native_pointer") or raw_case["case_id"].split(":", 1)[1]
        if raw_case.get("table_cells"):
            for cell in raw_case["table_cells"]:
                primary_pointer = cell.get("native_pointer") or pointer + f"/data/table_cells/{cell['index']}"
                text = node(items, primary_pointer)["text"]
                primary = make_anchor(pin, primary_pointer, text, items=items)
                value = cell["cell_value"]
                raw_cell = dict(raw_case, case_id=raw_case["case_id"] + f":cell{cell['index']}")
                stated = value["state"] == "stated"
                add(unit, QUESTION, raw_cell, "cell_literal", [primary], state=value["state"],
                    kind="occurrence" if stated else "proposal",
                    alternatives=[{"source_pieces": [text]}] if stated else [{"source_field_state": "unstated", "anchor_role": "inspection_subject"}],
                    selector={} if stated else {"semantic_type": "table.cell_value"}, explanation=value["explanation"])
                for role in ("header_path", "row_label", "unit", "note"):
                    expected = cell[role]
                    options = []
                    if expected["state"] == "stated":
                        variants = []
                        if expected.get("pieces"):
                            variants.append([authored_piece(piece, pin, items) for piece in expected["pieces"]])
                        else:
                            variants.append([field_anchor(expected, pin, items)])
                        for alternative in expected.get("permissible_alternatives", ()):
                            if not isinstance(alternative, dict):
                                continue
                            if alternative.get("pieces"):
                                variants.append([authored_piece(piece, pin, items) for piece in alternative["pieces"]])
                            elif isinstance(alternative.get("value"), list) and len(alternative["value"]) == 1:
                                full = field_anchor(expected, pin, items)
                                if alternative["value"] == [full.get("source_piece")]:
                                    variants.append([full])
                        for targets in variants:
                            for anchor in targets:
                                anchors_by_unit[unit][anchor["anchor_id"]] = anchor
                            options.append(dict(semantic_type=f"table.{role}_attachment", endpoint_semantics=[
                                dict(role="cell_value", anchor_ids=[primary["anchor_id"]], fields={"source_pieces": [text]} if text else {}),
                                dict(role=role, anchor_ids=[anchor["anchor_id"] for anchor in targets],
                                     fields={"source_pieces": [anchor["source_piece"] for anchor in targets]}),
                            ]))
                    else:
                        options = [{"source_field_state": "unstated", "anchor_role": "inspection_subject"}]
                    add(unit, ATTACHMENT, raw_cell, role + "_attachment", [primary], state=expected["state"],
                        alternatives=options, explanation=expected["explanation"], kind="relation",
                        selector={"semantic_type": f"table.{role}_attachment"}, endpoint_role="cell_value")
        else:
            complete = node(items, pointer)["text"]
            region = make_anchor(pin, pointer, complete, items=items)
            anchors_by_unit[unit][region["anchor_id"]] = region
            for index, term in enumerate(raw_case.get("text_terms", ())):
                anchor = make_anchor(pin, pointer, term["text"], term["start"], term["end"], items)
                add(unit, QUESTION, raw_case, "literal_occurrence", [anchor], kind="occurrence",
                    alternatives=[{"source_pieces": [term["text"]]}], explanation="Exact independently cited literal only. " + term["explanation"], suffix=f":{index}")
                add(unit, QUESTION, raw_case, "contextual_role", [anchor], judgment="unassessed",
                    alternatives=[], explanation="Independent role retained: " + term["role"] +
                    ". No comparable declared contextual-role prediction event; a literal or formula.symbol does not certify this prose role.", suffix=f":{index}")
            add(unit, QUESTION, raw_case, "explicit_definition_or_alias_state", [region], state="unstated",
                alternatives=[{"source_field_state": "unstated", "anchor_role": "inspection_subject"}], selector={"semantic_type": "definition.explicit_cue_state"},
                explanation="State capture question on the inspected complete text item. Independent answer has no explicit definition/alias cue; zero output does not capture that field state.")
    return buckets, anchors_by_unit


def prepare_wrappers(args, settings):
    source_cohort = read("source-cohort-001.json")
    originals = {unit: read(f"source-only-unit-{unit}-002.json")["source_frame"]["source_views"][0] for unit in (1, 2)}
    with open_runtime_engine(settings, "pce03-source-reference-frame", purpose="evaluate") as engine, engine.begin() as conn:
        runs, cuts, views, membership = map(table, ("ops.run", "ops.input_cut", "kb.source_view", "ops.run_source_view"))
        release_id = conn.scalar(select(runs.c.release_id).where(runs.c.id == args.source_run, runs.c.project_id == PROJECT))
        cut = conn.execute(select(cuts.c.id).where(cuts.c.run_id == args.source_run, cuts.c.final)).scalar_one()
        current = [dict(row) for row in conn.execute(select(views).join(membership, membership.c.source_view_id == views.c.id)
            .where(membership.c.run_id == args.source_run)).mappings()]
        pins, correspondence = {}, []
        for unit, old in originals.items():
            matches = [view for view in current if all(view[key] == old[key] for key in (
                "native_task_id", "native_product_key", "native_content_digest", "section_pointer", "membership"))]
            if len(matches) != 1:
                raise ValueError("independent source frame requires exact retained native section correspondence")
            view = matches[0]
            pins[unit] = dict(source=source_binding(conn, source_run_id=args.source_run, source_view_id=view["id"], source_cut_id=cut),
                native_product_task_id=view["native_task_id"], product_key=view["native_product_key"], product_digest=view["native_content_digest"],
                projection_digest=view["projection_digest"], recipe_digest=view["recipe_digest"], source_view_id=view["id"])
            correspondence.append(dict(original_view=old["id"], current_view=view["id"], original_release=old["release_id"],
                current_release=release_id, rule="same retained native product, section pointer and membership"))
    authors, union = {}, {unit: {} for unit in pins}
    for kind in "ABC":
        artifact = RAW / f"author-{kind}-001.json"
        cases, anchors = translate_author(read(artifact.name), pins, source_items(), artifact)
        authors[kind] = cases
        for unit, values in anchors.items():
            union[unit].update(values)
    frames, payloads = {}, {}
    for question, unit in sorted(authors["C"]):
        key = f"{question}:unit{unit}"
        frame = assessment.OperationEvaluationFrame(unit=pins[unit]["source"], release_id=release_id,
            guideline_version=GUIDELINE, rubric_version=RUBRIC, context_policy="exact-native-selected-source-and-authored-context-1",
            operation_question=question, operation_version=VERSIONS[question], domain="scientific-source", direction="source_first",
            pin=pins[unit], anchor_ids=tuple(sorted(union[unit])), anchor_scopes=tuple(
                {key: value for key, value in anchor.items() if key not in {"anchor_id", "source_piece", "binding"}}
                for anchor in union[unit].values()))
        frames[key] = assessment.encode_frame(frame)
        payloads[key] = {}
        for kind in "ABC":
            source = read(f"author-{kind}-001.json")
            cases = authors[kind].get((question, unit), [])
            payload = dict(protocol=assessment.PROTOCOL, release_id=release_id, unit_ref=frame.unit,
                guideline=GUIDELINE, rubric_version=RUBRIC, context_policy=frame.context_policy,
                operation_question=question, operation_version=VERSIONS[question], domain=frame.domain, direction=frame.direction,
                reason=f"Deterministic exact-question serialization of immutable independent source-only author {kind}; no production outputs consulted.",
                adjudication_passes=[], cases=[asdict(case) for case in cases])
            assessment.decode_authored(canonical_bytes(payload), frame)
            payloads[key][kind] = dict(actor=source["actor"], authored=payload)
    return dict(protocol="pce-independent-reference-wrappers-2", source_run_id=args.source_run, source_cut_id=cut,
        release_id=release_id, partition=source_cohort["partition"], source_correspondence=correspondence,
        source_cohort_sha256=digest(RAW / "source-cohort-001.json"), serializer_sha256=digest(Path(__file__)),
        guideline_text="Independent source-selected literal and field-state questions. Attachment requires the named primary cell and target source pieces. Contextual prose roles without a comparable prediction event remain unassessed. Source-first misses describe coverage of selected retained outputs, without attributing a missing source occurrence to a producer mechanism. No population estimate. The note question means applicable qualification or footnote, excluding a general table-caption description; the raw caption-as-general-note alternative retains its different scope.",
        frames=frames, payloads=payloads, limits="Finite purposive feature-fit cohort only; original documents/page images uninspected; raw author artifacts remain authoritative for contextual qualifications and untranslated permissible alternatives.")


def register(args, settings):
    wrappers = read(args.wrappers)
    sets = {}
    with open_runtime_engine(settings, "pce03-independent-reference-registration", purpose="evaluate") as engine, engine.begin() as conn:
        for question in VERSIONS:
            keys = [key for key in wrappers["frames"] if key.startswith(question + ":")]
            if not keys:
                continue
            frames = {assessment.decode_frame(wrappers["frames"][key]).unit: assessment.decode_frame(wrappers["frames"][key]) for key in keys}
            created = assessment.create_reference_set(conn, project_id=PROJECT, source_run_id=wrappers["source_run_id"],
                source_cut_id=wrappers["source_cut_id"], label=f"{args.receipt}:{question}", legacy_split="dev", guideline=GUIDELINE,
                guideline_text=wrappers["guideline_text"], partition=wrappers["partition"], frames=frames,
                sampling=dict(seed=20261105, strata={unit: "source-selected-native-region" for unit in frames},
                    inclusion_probabilities={unit: 1 for unit in frames}, cohort="bounded-independent-source-selection",
                    provenance=dict(wrapper_artifact=args.wrappers, wrapper_sha256=digest(RAW / args.wrappers),
                        source_cohort_sha256=wrappers["source_cohort_sha256"], inference="none; purposive declared cases only")))
            units = table("eval.reference_unit")
            units_by_key = {row["unit_key"]: row["id"] for row in conn.execute(select(units).where(units.c.set_id == created["set_id"])).mappings()}
            pass_ids = {}
            for key in keys:
                frame = assessment.decode_frame(wrappers["frames"][key])
                ids = []
                for kind in "ABC":
                    item = wrappers["payloads"][key][kind]
                    payload = dict(item["authored"], adjudication_passes=ids if kind == "C" else [])
                    identity = assessment.record_pass(conn, unit_id=units_by_key[frame.unit], pass_kind=kind,
                        actor=item["actor"], authored=canonical_bytes(payload), frame=frame)
                    if kind in {"A", "B"}:
                        ids.append(identity)
                    pass_ids[f"{key}:{kind}"] = identity
            sets[question] = dict(set_id=created["set_id"], pass_ids=pass_ids)
    return dict(source_run_id=wrappers["source_run_id"], sets=sets, partition=wrappers["partition"],
                wrapper_artifact=args.wrappers, wrapper_sha256=digest(RAW / args.wrappers))


def grade(args, settings):
    registration = read(args.registration)
    grades = {}
    with open_runtime_engine(settings, "pce03-protected-operation-grade", purpose="evaluate") as engine, engine.begin() as conn:
        for question, entry in registration["sets"].items():
            before = assessment.reference_evaluate(conn, project_id=PROJECT, run_id=registration["source_run_id"], set_id=entry["set_id"])
            after = assessment.reference_evaluate(conn, project_id=PROJECT, run_id=args.prediction_run, set_id=entry["set_id"])
            grades[question] = dict(baseline=before.model_dump(mode="json"), revised=after.model_dump(mode="json"),
                comparison=assessment.compare_assessments(before.result, after.result),
                default_export=assessment.review_export(conn, project_id=PROJECT, set_id=entry["set_id"]))
    return dict(protocol="pce-bounded-operation-assessment-2", grades=grades,
        population_estimate="not_established", source_quality_scope="selected retained-output coverage on independently authored source cases",
        causal_attribution="missing source matches do not identify nomination, retrieval, adapter or source-inspection failure without corresponding returned-item evidence")


def prepare_output(args, settings):
    """Freeze <=24 stratified outputs for fresh question-specific independent source authoring."""
    from collections import defaultdict, deque
    from corpus_structure.semantic.contribution_queries import read_source_contributions

    source = read(args.wrappers)
    pool = {}
    closures = {}
    with open_runtime_engine(settings, "pce03-output-selection", purpose="evaluate") as engine, engine.begin() as conn:
        completed_table = table("ops.completed_result")
        completed = conn.execute(select(completed_table).where(completed_table.c.run_id == args.prediction_run)).mappings().one()
        prepared = open_release(conn, completed["release_id"])
        if prepared.release_id != source["release_id"]:
            raise ValueError("output selection requires the same source/rubric release")
        for key, encoded in source["frames"].items():
            frame = assessment.decode_frame(encoded)
            summary = read_source_contributions(conn, prepared=prepared, run_id=args.prediction_run,
                source_view_id=frame.pin["source_view_id"], cut_id=completed["cut_id"], limit=10000)
            keys = tuple(op["operation_key"] for op in summary.operations if op["question"] == frame.operation_question
                         and op["operation_version"] == frame.operation_version)
            if summary.more:
                raise ValueError("bounded output summary population capture incomplete")
            for row in summary.contributions:
                if row["operation_key"] in keys:
                    pool[row["contribution_id"]] = (key, row)
    strata = defaultdict(list)
    for identity, (key, row) in pool.items():
        strata[(row["kind"], row["semantic_type"], assessment.decode_frame(source["frames"][key]).operation_question)].append(identity)
    queues = defaultdict(deque)
    for stratum, values in sorted(strata.items()):
        queues[stratum[0]].append(deque(sorted(values, key=lambda identity: sha256(("pce-output-selection-1:" + identity).encode()).hexdigest())))
    selected = []
    while any(queues.values()) and len(selected) < 24:
        for kind in sorted(queues):
            if not queues[kind] or len(selected) >= 24:
                continue
            stratum_queue = queues[kind].popleft()
            selected.append(stratum_queue.popleft())
            if stratum_queue:
                queues[kind].append(stratum_queue)
    by_frame = defaultdict(list)
    for identity in selected:
        by_frame[pool[identity][0]].append(pool[identity][1])
    # Hydrate only the selected semantic products and their endpoint closure.
    with open_runtime_engine(settings, "pce03-selected-output-capture", purpose="evaluate") as engine, engine.begin() as conn:
        for key, selected_summaries in list(by_frame.items()):
            frame = assessment.decode_frame(source["frames"][key])
            ids = tuple(row["contribution_id"] for row in selected_summaries)
            details = read_source_contributions(conn, prepared=prepared, run_id=args.prediction_run,
                source_view_id=frame.pin["source_view_id"], cut_id=completed["cut_id"], limit=10000,
                contribution_ids=ids, include_details=True)
            endpoint_ids = tuple(sorted({e["contribution_id"] for row in details.contributions for e in row.get("endpoints", ())}))
            endpoints = read_source_contributions(conn, prepared=prepared, run_id=args.prediction_run,
                source_view_id=frame.pin["source_view_id"], cut_id=completed["cut_id"], limit=10000,
                contribution_ids=endpoint_ids, include_details=True) if endpoint_ids else None
            if details.more or (endpoints is not None and endpoints.more) or set(ids) - {row["contribution_id"] for row in details.contributions}:
                raise ValueError("bounded selected output/endpoint capture incomplete")
            closures[key] = {row["contribution_id"]: row for row in (*details.contributions, *(endpoints.contributions if endpoints else ()))}
            by_frame[key] = list({row["contribution_id"]: row for row in details.contributions}.values())
    frames, selected_outputs, source_scopes, interests = {}, [], [], []
    with open_runtime_engine(settings, "pce03-output-source-packet", purpose="read") as engine, engine.begin() as conn:
        from corpus_structure.semantic.operations import BoundReader
        from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
        reader = BoundReader(conn, args.prediction_run, prepared, analysis=False,
                             read_budget=PublishedReadBudget(40000, 256 * 1024**2))
        for key, outputs in by_frame.items():
            original = assessment.decode_frame(source["frames"][key])
            anchor_ids = set(original.anchor_ids)
            for output in outputs:
                anchor_ids.update(a["anchor_id"] for a in output.get("anchors", ()))
            frame = replace(original, direction="output_first", anchor_ids=tuple(sorted(anchor_ids)),
                            contribution_ids=tuple(output["contribution_id"] for output in outputs))
            frames[key] = assessment.encode_frame(frame)
            view = reader.source_view(frame.pin["source_view_id"])
            source_scopes.append(dict(frame_key=key, unit_ref=frame.unit, pin=dict(frame.pin),
                operation_question=frame.operation_question, operation_version=frame.operation_version,
                native_items=list(view.items), native_ancestors=list(view.ancestors),
                question="Author fresh exact source structures, roles, field states and source associations within the declared inspected scope; do not infer correctness from a returned product."))
            for output in outputs:
                interest = f"output-source-{len(interests)+1:03d}"
                subject = output
                if output["kind"] == "relation":
                    primary = [endpoint for endpoint in output.get("endpoints", ()) if endpoint["role"] in {"cell_value", "term"}]
                    subject = closures[key].get(primary[0]["contribution_id"], {}) if len(primary) == 1 else {}
                pointers = sorted({anchor["pointer"] for anchor in subject.get("anchors", ())})
                interests.append(dict(interest_id=interest, frame_key=key,
                    intended_question=output["semantic_type"], product_kind=output["kind"], source_item_pointers=pointers,
                    scope="Inspect the complete named native items and necessary governing context, not a producer-supplied substring. For associations, independently identify governing targets from the primary source subject; proposed targets are withheld.",
                    limitations="A missing source subject or an event without an independent source rubric remains unassessed. Literal/location support does not establish a scientific term, contextual role or association."))
                selected_outputs.append(dict(interest_id=interest, frame_key=key, contribution=dict(output)))
    author_packet = dict(protocol="pce-fresh-output-source-authoring-1", source_scopes=source_scopes, assessment_interests=interests,
        instructions="Fresh independent source authoring for the current operation contracts. No historical reference projections or production candidate values/scores are supplied. State exact native pointers and offsets, inspected scope, expected structures, permissible alternatives and limitations. Unavailable questions remain unassessed.")
    write(RAW / f"{args.receipt}-author-source-packet.json", author_packet)
    write(RAW / f"{args.receipt}-selected-products.json", dict(selected_outputs=selected_outputs,
        endpoint_closures={key: list(values.values()) for key, values in closures.items()}))
    return dict(protocol="pce-fresh-output-selection-1", source_run_id=args.prediction_run,
        source_cut_id=completed["cut_id"], release_id=prepared.release_id, partition="feature_fit", frames=frames,
        author_source_packet=f"{args.receipt}-author-source-packet.json",
        private_product_capture=f"{args.receipt}-selected-products.json",
        output_selection=dict(protocol="pce-stratified-output-selection-1", limit=24, selected=len(selected),
            allocation="round robin contribution kinds, then semantic type/question strata; SHA-256 order inside each stratum",
            eligible_scope="all retained contribution products in the two selected source views and declared operations",
            contribution_ids=selected),
        next_work="Fresh independent A/B/C operation-case answers and faithful wrapper serialization are required before native output registration/grade; earlier source answers are not forced into this frame.")


def grade_output(args, settings):
    registration = read(args.registration)
    with open_runtime_engine(settings, "pce03-protected-output-grade", purpose="evaluate") as engine, engine.begin() as conn:
        grades = {question: assessment.reference_evaluate(conn, project_id=PROJECT,
            run_id=registration["source_run_id"], set_id=entry["set_id"]).model_dump(mode="json") for question, entry in registration["sets"].items()}
    return dict(protocol="pce-bounded-output-assessment-2", grades=grades, population_estimate="not_established",
                scope="separate frozen output frame; no pooling with source-first denominators")


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("action", choices=("source-run", "prediction-run", "prepare", "register", "grade", "output-prepare", "output-grade"))
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--release")
    parser.add_argument("--realization")
    parser.add_argument("--output-realization")
    parser.add_argument("--source-run", type=int)
    parser.add_argument("--prediction-run", type=int)
    parser.add_argument("--wrappers")
    parser.add_argument("--registration")
    args = parser.parse_args()
    target = RAW / f"{args.receipt}.json"
    if target.exists():
        raise FileExistsError(target)
    source_copy = RAW / f"{args.receipt}-driver.py"
    with source_copy.open("xb") as stream:
        stream.write(Path(__file__).read_bytes())
    functions = {"source-run": run_source, "prediction-run": run_predictions,
                 "prepare": prepare_wrappers, "register": register, "grade": grade,
                 "output-prepare": prepare_output, "output-grade": grade_output}
    try:
        settings = Settings()
        result = functions[args.action](args, settings)
    except BaseException as error:
        write(RAW / f"{args.receipt}-failure.json", dict(action=args.action, outcome="failed", error_type=type(error).__name__, error=str(error),
            serializer_sha256=digest(Path(__file__))))
        raise
    result = dict(result, execution_driver=source_copy.name, execution_driver_sha256=digest(source_copy), arguments=vars(args))
    write(target, result)
    print(json.dumps(dict(outcome="passed", action=args.action, receipt=str(target))))


if __name__ == "__main__":
    main()
