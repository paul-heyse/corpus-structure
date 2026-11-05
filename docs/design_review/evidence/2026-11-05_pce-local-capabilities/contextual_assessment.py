"""Freeze fresh source-only A/B/C into the existing protected operation assessor.

The serializer consumes independently authored source answers and curator inputs, never
predictions. A separate grade command consumes completed runs after reference registration.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from corpus_structure.evaluate import operation_assessment as assessment
from corpus_structure.evaluate.record_references import source_binding
from corpus_structure.semantic.contextual_registry import RegistryTarget, registry_input
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.record_contracts import anchor_identity
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
PROJECT = "m1-source-grinstead-snell"
QUESTION = "contextual denotation selection for supplied occurrence"
GUIDELINE = "contextual-independent-source-1"
RUBRIC = "contextual-denotation-1"
CONTEXT = "declared-native-source-and-curated-targets-1"


def load(name):
    return json.loads((RAW / name).read_bytes())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (RAW / name).open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")


def serialize(args):
    packet_name = "contextual-source-author-packet-001.json"
    packet = load(packet_name)
    _, targets = registry_input(tuple(RegistryTarget(**item) for item in packet["inventory"]))
    targets = {target.target_id: target for target in targets}
    with open_runtime_engine(Settings(), "pce-contextual-source-freeze", purpose="evaluate") as engine, engine.connect() as conn:
        views, members, cuts, runs = map(table, ("kb.source_view", "ops.run_source_view", "ops.input_cut", "ops.run"))
        cut = conn.scalar(select(cuts.c.id).where(cuts.c.run_id == args.source_run, cuts.c.final))
        if cut is None:
            raise ValueError("reference source must have a final sealed cut")
        view = conn.execute(select(views).join(members, members.c.source_view_id == views.c.id).where(
            members.c.run_id == args.source_run,
            views.c.native_content_digest == packet["physical_pin"]["product_digest"],
            views.c.projection_digest == packet["physical_pin"]["projection_digest"])).mappings().one()
        release = conn.scalar(select(runs.c.release_id).where(runs.c.id == args.source_run))
        pin = dict(source=source_binding(conn, source_run_id=args.source_run, source_view_id=view["id"], source_cut_id=cut),
                   native_product_task_id=view["native_task_id"], product_key=view["native_product_key"],
                   product_digest=view["native_content_digest"], projection_digest=view["projection_digest"],
                   recipe_digest=view["recipe_digest"], source_view_id=view["id"])
        origins, groups, documents = map(table, ("eval.reference_origin_source", "eval.reference_origin_group", "kb.document"))
        partition = conn.scalar(select(groups.c.partition).join(origins,
            (origins.c.project_id == groups.c.project_id) & (origins.c.origin_group == groups.c.origin_group)).join(
                documents, (documents.c.project_id == origins.c.project_id) & (documents.c.source_uri == origins.c.source_uri)).where(
                    documents.c.id == view["document_id"], groups.c.project_id == PROJECT))
        if partition not in {"development", "feature_fit"}:
            raise ValueError("declared development study must preserve a development-use origin partition")
    anchors = []
    cases_by_id = {case["case_id"]: case for case in packet["cases"]}
    for case in packet["cases"]:
        if case["text"][case["start"]:case["end"]] != case["mention"]:
            raise ValueError("source packet extent changed")
        anchor = dict(pin=pin, space="native", pointer=case["pointer"], precision="exact",
                      start=case["start"], end=case["end"], source_piece=case["mention"])
        anchor["anchor_id"] = anchor_identity(anchor)
        anchors.append(anchor)
    anchors_by_id = dict(zip(cases_by_id, anchors, strict=True))
    frame = assessment.OperationEvaluationFrame(unit=pin["source"], release_id=release,
        guideline_version=GUIDELINE, rubric_version=RUBRIC, context_policy=CONTEXT,
        operation_question=QUESTION, operation_version="1", domain="statistics", direction="source_first",
        pin=pin, anchor_ids=tuple(anchor["anchor_id"] for anchor in anchors),
        anchor_scopes=tuple({key: value for key, value in anchor.items() if key not in {"anchor_id", "source_piece"}} for anchor in anchors))
    payloads = {}
    for kind in "ABC":
        name = f"contextual-author-{kind}-001.json"
        author = load(name)
        if author["packet_sha256"] != digest(RAW / packet_name):
            raise ValueError("independent author refers to different source packet")
        if {case["case_id"] for case in author["cases"]} != set(cases_by_id):
            raise ValueError("author omitted or added a selected source case")
        cases = []
        for raw in author["cases"]:
            selected = cases_by_id[raw["case_id"]]
            anchor = anchors_by_id[raw["case_id"]]
            if raw["source_pointer"] != selected["pointer"]:
                raise ValueError("independent author source pointer differs")
            extent = raw.get("declared_mention", dict(text=raw.get("mention"), start=raw.get("start"), end=raw.get("end")))
            if extent != dict(text=selected["mention"], start=selected["start"], end=selected["end"]):
                raise ValueError("independent author selected extent differs")
            alternatives = []
            for target_id in raw["permissible_target_ids"]:
                target = targets[target_id]
                alternatives.append(dict(semantic_type="contextual.denotation", value=source_value(dict(
                    target_id=target_id, target_source_binding=target.source_binding,
                    relation="denotes", scope="statistics.chapter5", effective_version=None))))
            cases.append(assessment.OperationCase(case_id=raw["case_id"], facet="denotation",
                anchor_ids=(anchor["anchor_id"],), inspected_scope=selected["pointer"],
                source_state="stated", judgment="supported" if alternatives else "unassessed",
                alternatives=tuple(alternatives), explanation=raw["denotation_reason"],
                assessor_provenance=dict(model="gpt-6.1-sol", reasoning_effort="high", pass_kind=kind,
                    author_artifact=name, author_sha256=digest(RAW / name),
                    packet_sha256=digest(RAW / packet_name), serializer_sha256=digest(Path(__file__)),
                    semantic_authorship="fresh model-assisted source-only author; C sees source and A/B",
                    scope_limits="curated concept denotation only; no canonical identity, discovery or population claim"),
                contribution_kind="proposal", candidate_selector=dict(semantic_type="contextual.denotation")))
        payload = dict(protocol=assessment.PROTOCOL, release_id=release, unit_ref=frame.unit,
            guideline=GUIDELINE, rubric_version=RUBRIC, context_policy=CONTEXT,
            operation_question=QUESTION, operation_version="1", domain=frame.domain,
            direction="source_first", reason="Exact semantic serialization of fresh source-only answers; generated lineage is excluded from the independently assessable statement.",
            cases=[asdict(case) for case in cases], adjudication_passes=[])
        assessment.decode_authored(canonical_bytes(payload), frame)
        payloads[kind] = payload
    result = dict(protocol="pce-contextual-reference-wrappers-1", source_run_id=args.source_run,
        source_cut_id=cut, frame=assessment.encode_frame(frame), payloads=payloads,
        packet_sha256=digest(RAW / packet_name), serializer_sha256=digest(Path(__file__)),
        source_correspondence="Exact immutable native product/projection; current source pin only; no prediction inputs",
        partition=partition, limits="17 selected development-study mentions in eight passages; immutable native origin partition preserved; source C retains richer relationships outside this denotation question")
    with (RAW / (args.receipt + "-serializer.py")).open("xb") as stream:
        stream.write(Path(__file__).read_bytes())
    write(args.receipt + ".json", result)
    print(json.dumps(dict(outcome="passed", artifact=args.receipt + ".json", cases=17, release_id=release)))


def register(args):
    wrappers = load(args.wrappers)
    frame = assessment.decode_frame(wrappers["frame"])
    with open_runtime_engine(Settings(), "pce-contextual-reference-register", purpose="evaluate") as engine, engine.begin() as conn:
        created = assessment.create_reference_set(conn, project_id=PROJECT,
            source_run_id=wrappers["source_run_id"], source_cut_id=wrappers["source_cut_id"],
            label=args.receipt, legacy_split="dev", guideline=GUIDELINE,
            guideline_text="Assess exact selected source usages against independently curated target inputs. Full semantic value equality; no canonical identity or source fact inferred from target descriptions. Source selection predates predictions; passage qualifiers remain in immutable author artifacts.",
            partition=wrappers["partition"], sampling=dict(cohort="17-source-selected-contextual-mentions-1", seed=20261105,
                strata={frame.unit: "declared-seventeen-reference-mentions"},
                inclusion_probabilities={frame.unit: 1},
                provenance=dict(wrappers_sha256=digest(RAW / args.wrappers),
                    selection="Fixed purposive mention frame; all declared cases, no corpus probability sampling"),
                population="declared supplied mentions only", inference="none", wrappers_sha256=digest(RAW / args.wrappers)),
            frames={frame.unit: frame})
        units = table("eval.reference_unit")
        unit = conn.scalar(select(units.c.id).where(units.c.set_id == created["set_id"]))
        pass_ids = {}
        for kind in "ABC":
            payload = dict(wrappers["payloads"][kind], adjudication_passes=list(pass_ids.values()) if kind == "C" else [])
            pass_ids[kind] = assessment.record_pass(conn, unit_id=unit, pass_kind=kind,
                actor=f"fresh-contextual-source-{kind}:gpt-6.1-sol:high", authored=canonical_bytes(payload), frame=frame)
    result = dict(outcome="passed", source_run_id=wrappers["source_run_id"], set_id=created["set_id"],
                  unit_id=unit, pass_ids=pass_ids, wrappers=args.wrappers, wrappers_sha256=digest(RAW / args.wrappers))
    write(args.receipt + ".json", result)
    print(json.dumps(result))


def grade(args):
    registration = load(args.registration)
    with open_runtime_engine(Settings(), "pce-contextual-protected-grade", purpose="evaluate") as engine, engine.begin() as conn:
        report = assessment.reference_evaluate(conn, project_id=PROJECT, run_id=args.run, set_id=registration["set_id"])
        evaluations = table("eval.reference_evaluation")
        content_digest = conn.scalar(select(evaluations.c.content_digest).where(evaluations.c.id == report.id))
    result = dict(outcome="passed", evaluation_id=report.id, content_digest=content_digest,
                  run_id=args.run, report=report.model_dump(mode="json"), registration=args.registration)
    write(args.receipt + ".json", result)
    print(json.dumps(dict(outcome="passed", evaluation_id=report.id, content_digest=content_digest,
                         run_id=args.run, units=report.result["units"])))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    serialize_parser = sub.add_parser("serialize")
    serialize_parser.add_argument("--source-run", type=int, required=True)
    register_parser = sub.add_parser("register")
    register_parser.add_argument("--wrappers", required=True)
    grade_parser = sub.add_parser("grade")
    grade_parser.add_argument("--registration", required=True)
    grade_parser.add_argument("--run", type=int, required=True)
    for child in (serialize_parser, register_parser, grade_parser):
        child.add_argument("--receipt", required=True)
    args = parser.parse_args()
    {"serialize": serialize, "register": register, "grade": grade}[args.command](args)
