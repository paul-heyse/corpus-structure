"""Fresh output references and evidence-only identity checks for 24 frozen questions.

No production compatibility/projection API is added. Author artifacts are immutable.
Read phases capture bounded sealed products; registration remains with the coordinator.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

sys.dont_write_bytecode = True

from sqlalchemy import Integer, cast, select, func

from corpus_structure.evaluate import operation_assessment as assessment
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

from pce03_native_assessment_001 import RAW, digest, make_anchor, node, read, write

SIDECARS = {"selected_task_id", "origin_task_id", "source", "method", "cut_member", "task_status", "source_view_id", "task_id", "position"}


def bounded_json(conn, statement, *, rows=10000, max_bytes=8_000_000):
    budget = PublishedReadBudget(rows, max_bytes)
    budget.preflight(conn, statement)
    output = []
    for row in conn.execute(statement).mappings():
        value = dict(row)
        budget.value(value)
        output.append(value)
    return output


def capture_closure(conn, *, task_id, selected_ids):
    """Read indexed selected roots and complete endpoint/member closure before JSON hydration."""
    contributions, results = table("kb.source_contribution"), table("ops.task_result")
    found, pending = {}, set(selected_ids)
    while pending:
        if len(found) + len(pending) > 1000:
            raise ValueError("fixed-question endpoint/member closure exceeds the bounded capture")
        statement = select(contributions.c.contribution_id, results.c.body["contributions"][cast(contributions.c.position,Integer)].label("payload")).join(
            results, results.c.task_id == contributions.c.task_id).where(
                contributions.c.task_id == task_id, contributions.c.contribution_id.in_(tuple(sorted(pending))))
        rows = bounded_json(conn, statement, rows=1000)
        received = {row["contribution_id"] for row in rows}
        if pending - received:
            raise ValueError(f"sealed product closure is missing {sorted(pending-received)}")
        pending = set()
        for row in rows:
            value = row["payload"]
            if value["contribution_id"] != row["contribution_id"]:
                raise ValueError("selected contribution index differs from immutable report position")
            from corpus_structure.semantic.contributions import contribution_identity
            if contribution_identity(value) != value["contribution_id"]:
                raise ValueError("sealed semantic contribution identity differs from exact payload")
            found[value["contribution_id"]] = value
        for value in found.values():
            pending.update(endpoint["contribution_id"] for endpoint in value.get("endpoints", ()))
            pending.update(value.get("members", ()))
        pending.difference_update(found)
    operations = table("kb.source_contribution_operation")
    keys = {value["operation_key"] for value in found.values()}
    statement = select(operations.c.operation_key, results.c.body["contribution_operations"][cast(operations.c.position,Integer)].label("payload")).join(
        results, results.c.task_id == operations.c.task_id).where(operations.c.task_id == task_id,
                                                               operations.c.operation_key.in_(tuple(sorted(keys))))
    op_rows = bounded_json(conn, statement, rows=1000)
    op_map = {row["operation_key"]: row["payload"] for row in op_rows}
    if keys - op_map.keys():
        raise ValueError("sealed operation closure is incomplete")
    return found, op_map


def physical_sources(conn, roots):
    """Capture physical ownership metadata and authenticate the retained native products."""
    ids = {value["pin"]["source_view_id"] for value in roots.values()}
    ids.update(anchor["pin"]["source_view_id"] for value in roots.values() for anchor in value.get("anchors", ()))
    views, artifacts, documents = table("kb.source_view"), table("kb.source_artifact"), table("kb.document")
    output = {}
    for identity in sorted(ids):
        # No ops.run select-star: the pre-transition database has no runtime_id column.
        row = conn.execute(select(views).where(views.c.id == identity)).mappings().one()
        data = dict(row)
        recipe = conn.execute(select(artifacts.c.content).where(artifacts.c.artifact_digest == data["recipe_digest"])).scalar_one()
        if sha256(bytes(recipe)).hexdigest() != data["recipe_digest"] or sha256(canonical_bytes(data["projection"])).hexdigest() != data["projection_digest"]:
            raise ValueError("physical source recipe/projection bytes differ from their immutable digests")
        document = conn.execute(select(documents.c.content_hash, documents.c.source_uri).where(documents.c.id == data["document_id"])).mappings().one()
        from corpus_structure.semantic.pdf_record_reader import published_record_reader
        from corpus_structure.semantic.product_reference import ProductReference
        from corpus_structure.semantic.published_document import PublishedDocumentBinding
        from corpus_structure.semantic.releases import open_release
        owner = published_record_reader(conn, ProductReference(data["native_task_id"], data["native_product_key"], data["native_content_digest"]),
            projection_context=open_release(conn, data["release_id"]), read_budget=PublishedReadBudget(40000,256*1024**2))
        if owner is None:
            raise ValueError("source product is not natively published")
        PublishedDocumentBinding.from_revision(owner.reference, owner.revision).require_placement(data)
        descriptor = {key: value for key,value in data.items() if key not in {"id", "key", "release_id"}}
        descriptor.update(source_uri=document["source_uri"], document_content_hash=document["content_hash"], recipe_bytes_sha256=sha256(bytes(recipe)).hexdigest())
        output[str(identity)] = dict(view_id=identity, source_key=data["key"], release_id=data["release_id"],
            physical_descriptor=descriptor, physical_sha256=sha256(canonical_bytes(descriptor)).hexdigest())
    return output


def normalized_capture(capture):
    """Evidence-only exact comparison; only authenticated view aliases are replaced."""
    from corpus_structure.semantic.contributions import occurrence_identity
    from corpus_structure.semantic.record_contracts import anchor_identity

    sources=capture["physical_sources"];roots=capture["roots"];operations=capture["operations"]
    def source(identity, key):
        physical=sources[str(identity)]
        if physical["source_key"]!=key:raise ValueError("source alias does not match its authenticated physical owner")
        return physical["physical_sha256"]
    def pin(value):
        return {**{k:v for k,v in value.items() if k not in {"source","source_view_id"}},
                "physical_source":source(value["source_view_id"],value["source"])}
    def anchor(value):
        if anchor_identity(value)!=value["anchor_id"]:raise ValueError("anchor identity differs from exact coordinates")
        return {**{k:v for k,v in value.items() if k not in {"anchor_id","pin"}},"pin":pin(value["pin"])}
    def bindings(op):
        return [{**{k:v for k,v in row.items() if k not in {"current_source","current_source_view_id"}},
                 "physical_current_source":source(row["current_source_view_id"],row["current_source"])} for row in op["retained_source_bindings"]]
    def dependencies(values,op):
        expected="retained-source-map:"+sha256(canonical_bytes(op["retained_source_bindings"])).hexdigest()
        actual=[value for value in values if value.startswith("retained-source-map:")]
        if actual!=[expected]:raise ValueError("retained-source-map does not authenticate complete actual source bindings")
        substitute="authenticated-physical-source-map:"+sha256(canonical_bytes(bindings(op))).hexdigest()
        return sorted(substitute if value==expected else value for value in values)
    op_cache={}
    def operation(key):
        if key not in op_cache:
            value=operations[key]
            op_cache[key]={**{k:v for k,v in value.items() if k not in {"operation_key","retained_source_bindings","computation_dependencies"}},
                           "retained_source_bindings":bindings(value),"computation_dependencies":dependencies(value["computation_dependencies"],value)}
        return op_cache[key]
    cache={};active=set()
    def product(identity):
        if identity in cache:return cache[identity]
        if identity in active:raise ValueError("cyclic contribution closure")
        active.add(identity);value=roots[identity];op=operations[value["operation_key"]]
        if value.get("occurrence_id") is not None and occurrence_identity(value["anchors"])!=value["occurrence_id"]:
            raise ValueError("occurrence identity differs from physical source coordinates")
        normalized={k:v for k,v in value.items() if k not in SIDECARS|{"contribution_id","operation_key","pin","anchors","members","endpoints","computation_dependencies"}}
        normalized.update(pin=pin(value["pin"]),anchors=[anchor(a) for a in value["anchors"]],
            operation=operation(value["operation_key"]),computation_dependencies=dependencies(value["computation_dependencies"],op),
            members=[product(member) for member in value.get("members",())],
            endpoints=[{**{k:v for k,v in endpoint.items() if k!="contribution_id"},"product":product(endpoint["contribution_id"])} for endpoint in value.get("endpoints",())])
        active.remove(identity);cache[identity]=normalized
        return normalized
    return {identity:product(identity) for identity in roots}


def reidentify(args):
    old=read(args.old_capture);selection=read(args.selection)
    old_all={identity:product for cap in old["captures"].values() for identity,product in cap["roots"].items()}
    frozen={row["interest_id"]:row for row in old["selected_outputs"]}
    old_norm={identity:product for cap in old["captures"].values() for identity,product in normalized_capture(cap).items()}
    settings=Settings();captures={}
    with open_runtime_engine(settings,"pce-fixed-output-reidentify",purpose="read") as engine,engine.begin() as conn:
        completed,cut_tasks,contributions,results=map(table,("ops.completed_result","ops.cut_task","kb.source_contribution","ops.task_result"))
        cut=conn.scalar(select(completed.c.cut_id).where(completed.c.run_id==args.prediction_run))
        if cut is None:raise ValueError("new prediction run lacks completed custody")
        task_ids=conn.scalars(select(cut_tasks.c.origin_task_id).where(cut_tasks.c.cut_id==cut)).all()
        candidate_tasks=conn.scalars(select(contributions.c.task_id).where(contributions.c.task_id.in_(task_ids)).distinct()).all()
        from sqlalchemy import Text
        from corpus_structure.semantic.contributions import contribution_identity
        for task_id in candidate_tasks:
            # The report is the immutable custody unit. Bound its actual byte size
            # before one hydration; avoid repeated TOAST decompression per root.
            size=conn.scalar(select(func.octet_length(cast(results.c.body,Text))).where(results.c.task_id==task_id))
            if size is None or size>64*1024**2:raise ValueError("fixed-question sealed report exceeds explicit 64MiB evidence capture budget")
            body=conn.scalar(select(results.c.body).where(results.c.task_id==task_id))
            products={value["contribution_id"]:value for value in body["contributions"]}
            ids=[]
            for row in frozen.values():
                original=old_all[row["contribution"]["contribution_id"]]
                lineage=[item for item in original["computation_dependencies"] if item.startswith("predecessor-contribution:")]
                if len(lineage)!=1:raise ValueError("fixed output lacks unique exact returned-item predecessor lineage")
                ids.extend(identity for identity,value in products.items() if value["item_key"]==original["item_key"]
                           and value["kind"]==original["kind"] and value["semantic_type"]==original["semantic_type"]
                           and lineage[0] in value["computation_dependencies"])
            roots={};pending=set(ids)
            while pending:
                if len(roots)+len(pending)>1000:raise ValueError("fixed-question recursive closure exceeds 1000 products")
                identity=pending.pop();value=products[identity]
                if contribution_identity(value)!=identity:raise ValueError("new product identity differs from immutable contents")
                roots[identity]=value
                pending.update(e["contribution_id"] for e in value.get("endpoints",()))
                pending.update(value.get("members",()));pending.difference_update(roots)
            operations={value["operation_key"]:value for value in body["contribution_operations"] if value["operation_key"] in {root["operation_key"] for root in roots.values()}}
            if not roots:continue
            captures[str(task_id)]=dict(roots=roots,operations=operations,physical_sources=physical_sources(conn,roots))
        runs=table("ops.run")
        run=dict(conn.execute(select(runs.c.release_id,runs.c.runtime_id).where(runs.c.id==args.prediction_run)).mappings().one())
    new_norm={identity:product for cap in captures.values() for identity,product in normalized_capture(cap).items()}
    new_all={identity:product for cap in captures.values() for identity,product in cap["roots"].items()}
    mapping={};proof=[]
    for interest,row in frozen.items():
        old_id=row["contribution"]["contribution_id"];value=old_norm[old_id]
        matches=[identity for identity,candidate in new_norm.items() if candidate==value]
        if len(matches)!=1:raise ValueError(f"fixed question {interest} has {len(matches)} exact complete physical/semantic matches; refuse reselection")
        mapping[old_id]=matches[0]
        proof.append(dict(interest_id=interest,old_contribution_id=old_id,new_contribution_id=matches[0],normalized_complete_question_sha256=sha256(canonical_bytes(value)).hexdigest()))
    # Map every reachable anchor by exact normalized coordinates, never by its label alone.
    old_sources={key:value for cap in old["captures"].values() for key,value in cap["physical_sources"].items()}
    new_sources={key:value for cap in captures.values() for key,value in cap["physical_sources"].items()}
    aliases={old_id:next((new_id for new_id,new_source in new_sources.items() if new_source["physical_descriptor"]==old_source["physical_descriptor"]),None) for old_id,old_source in old_sources.items()}
    if None in aliases.values():raise ValueError("frozen source frame lacks exact authenticated physical alias")
    return dict(protocol="pce-fixed-output-reidentification-1",source_run_id=args.prediction_run,source_cut_id=cut,**run,
        frozen_selection=args.selection,frozen_selection_sha256=digest(RAW/args.selection),old_capture=args.old_capture,
        old_capture_sha256=digest(RAW/args.old_capture),mapping=mapping,proof=proof,source_aliases=aliases,captures=captures,
        selected_outputs=[{**row,"contribution":new_all[mapping[row["contribution"]["contribution_id"]]]} for row in frozen.values()],
        claim="Same frozen 24 fresh scientific questions after exact complete recursive semantic and authenticated physical equality; no new sampling or historical-reference migration",database_mutations=False)


def capture_old(args):
    selected = read(args.selection)
    private = read(selected["private_product_capture"])
    grouped = {}
    for row in private["selected_outputs"]:
        value = row["contribution"]
        grouped.setdefault(value["origin_task_id"], []).append(value["contribution_id"])
    captures = {}
    settings = Settings()
    with open_runtime_engine(settings,"pce-fixed-output-old-closure",purpose="read") as engine, engine.begin() as conn:
        tasks, completed, cut_tasks = table("ops.task"),table("ops.completed_result"),table("ops.cut_task")
        cut = conn.scalar(select(completed.c.cut_id).where(completed.c.run_id == selected["source_run_id"]))
        if cut != selected["source_cut_id"]:
            raise ValueError("old output selection differs from its immutable completed cut")
        for task_id, ids in grouped.items():
            task = conn.execute(select(tasks.c.id,tasks.c.run_id,tasks.c.release_id,tasks.c.status,tasks.c.unit_id).where(tasks.c.id==task_id)).mappings().one()
            if task["status"] not in {"done","empty"} or not conn.scalar(select(cut_tasks.c.task_id).where(cut_tasks.c.cut_id==cut,cut_tasks.c.origin_task_id==task_id).limit(1)):
                raise ValueError("old product origin lacks sealed completed-cut custody")
            roots, operations = capture_closure(conn,task_id=task_id,selected_ids=ids)
            captures[str(task_id)] = dict(task=dict(task),roots=roots,operations=operations,physical_sources=physical_sources(conn,roots))
    return dict(protocol="pce-fixed-output-closure-1",selection=args.selection,selection_sha256=digest(RAW/args.selection),
                selected_outputs=private["selected_outputs"],captures=captures, database_mutations=False)


def source_items(packet):
    scopes = {}
    for scope in packet["source_scopes"]:
        values = {item.get("self_ref",item.get("pointer")):item for item in (*scope["native_items"],*scope["native_ancestors"])}
        scopes[scope["frame_key"]] = values
    return scopes


def author_anchor(raw, *, pin, items):
    if raw.get("field", "text") != "text":
        raise ValueError("an orig/other-field inspection is context, not a native text value anchor")
    if raw["precision"] == "item":
        return make_anchor(pin, raw["native_pointer"], items=items)
    return make_anchor(pin, raw["native_pointer"], raw["text"], raw["start"], raw["end"], items)


def inside_subject(anchors, subjects):
    """Only scope selection: a declared whole native item can contain an exact inspected piece."""
    if not anchors:
        return False
    for actual in anchors:
        matching = [subject for subject in subjects if subject["pointer"]==actual["pointer"] and subject["pin"]==actual["pin"]]
        if not any(subject["precision"]=="item" or (
            subject["precision"]==actual["precision"]=="exact" and subject["start"]<=actual["start"]<actual["end"]<=subject["end"]
        ) for subject in matching):
            return False
    return True


def serialize_one(entry, interest, output, closure, frame, items, provenance):
    """Serialize one fresh source answer without promoting contextual labels to literal truth."""
    observed = assessment._comparison_product(output,closure)
    structures = [*entry.get("expected_structures",()),*entry.get("permissible_structures",())]
    anchors, choices, exclusions = {}, [], []
    primary_sets = []
    endpoint_role = None
    facet = "literal_source_support"
    for structure in structures:
        kind = structure["kind"]
        own = [author_anchor(raw,pin=frame.pin,items=items) for raw in structure.get("anchors",())]
        for anchor in own:
            anchors[anchor["anchor_id"]]=anchor
        if entry["judgment"]=="unassessed":
            continue
        if kind=="literal" and output["kind"] in {"occurrence","proposal"} and interest["intended_question"]=="source_occurrence":
            if not own or any(anchor["precision"]!="exact" for anchor in own):
                raise ValueError("literal answer lacks exact independently authored native pieces")
            ids=tuple(anchor["anchor_id"] for anchor in own)
            primary_sets.append(ids)
            choices.append(dict(source_anchor_ids=list(ids),source_pieces=[anchor["source_piece"] for anchor in own]))
        elif kind=="field_state" and structure.get("semantic_type")==interest["intended_question"]:
            facet="source_field_state"
            if output["kind"]=="relation":
                endpoint_role="term" if interest["intended_question"].startswith("definition.") else "cell_value"
                subjects=[endpoint for endpoint in output["endpoints"] if endpoint["role"]==endpoint_role]
                actual_anchors=closure[subjects[0]["contribution_id"]]["anchors"] if len(subjects)==1 else []
            else:
                actual_anchors=output.get("anchors",())
            if not inside_subject(actual_anchors,own):
                raise ValueError("frozen output subject is outside the independently inspected field-state item")
            # These IDs select the frozen output's source subject only; the expected
            # state comes exclusively from the fresh independent source answer.
            primary_sets.append(tuple(anchor["anchor_id"] for anchor in actual_anchors))
            for anchor in actual_anchors:
                anchors[anchor["anchor_id"]]=anchor
            choices.append(dict(source_field_state=structure["source_field_state"],anchor_role="inspection_subject"))
        elif kind=="attachment" and output["kind"]=="relation" and structure.get("semantic_type")==interest["intended_question"]:
            facet="source_attachment_item_scope"
            endpoint_role="term" if interest["intended_question"].startswith("definition.") else "cell_value"
            endpoints=structure.get("endpoints",())
            term=[endpoint for endpoint in endpoints if endpoint["role"] in {"defined_term","governing_target"}]
            if len(term)!=1 or not interest["intended_question"].startswith("definition."):
                raise ValueError("fresh attachment answer needs an explicit declared binary-role translation")
            term_anchors=[author_anchor(raw,pin=frame.pin,items=items) for raw in term[0]["anchors"]]
            text_subject=[endpoint for endpoint in endpoints if endpoint["role"] in {"primary","defining_text"}]
            text_anchors=[author_anchor(raw,pin=frame.pin,items=items) for raw in (text_subject[0]["anchors"] if len(text_subject)==1 else structure.get("anchors",()))]
            actual_text=[endpoint for endpoint in output["endpoints"] if endpoint["role"]=="defining_text"]
            actual_text_anchors=closure[actual_text[0]["contribution_id"]]["anchors"] if len(actual_text)==1 else []
            if not inside_subject(actual_text_anchors,text_anchors):
                # The answer remains valid; this frozen association will be unsupported.
                selected_text=text_anchors
            else:
                selected_text=actual_text_anchors
            primary_sets.append(tuple(anchor["anchor_id"] for anchor in term_anchors))
            for anchor in (*term_anchors,*text_anchors,*selected_text):
                anchors[anchor["anchor_id"]]=anchor
            choices.append(dict(semantic_type=interest["intended_question"],endpoint_semantics=[
                dict(role="term",anchor_ids=[anchor["anchor_id"] for anchor in term_anchors],fields={}),
                dict(role="defining_text",anchor_ids=[anchor["anchor_id"] for anchor in selected_text],fields={}),
            ]))
        else:
            exclusions.append(dict(structure=structure,reason="Different semantic question/grain; retained as source context, not substituted for the frozen event."))
    if entry["judgment"]=="unassessed":
        facet="unassessed_output_event"
        primary=tuple(anchor["anchor_id"] for anchor in output.get("anchors",()))
        for anchor in output.get("anchors",()):
            anchors[anchor["anchor_id"]]=anchor
    else:
        if not primary_sets or not choices:
            raise ValueError(f"fresh available question {entry['interest_id']} has no faithful representable expectation")
        primary=primary_sets[0]
    case=assessment.OperationCase(case_id=entry["interest_id"],facet=facet,anchor_ids=primary,
        inspected_scope=canonical_bytes(entry["inspected_scope"]).decode(),source_state=entry["source_state"],judgment=entry["judgment"],
        alternatives=tuple(choices),explanation=entry["explanation"],assessor_provenance=dict(provenance,
            interest_id=entry["interest_id"],fresh_answer=entry,excluded_different_questions=exclusions,
            qualification_scope="literal fidelity, explicit source field state, or declared binary item association only; scientific/contextual roles are not inferred from source location"),
        contribution_kind=output["kind"],contribution_id=output["contribution_id"],
        permissible_anchor_sets=tuple(dict.fromkeys(primary_sets[1:])),anchor_endpoint_role=endpoint_role)
    return case,anchors


def serialize_old(args):
    selection=read(args.selection)
    packet=read(selection["author_source_packet"])
    private=read(selection["private_product_capture"])
    reidentification=read(args.reidentification) if args.reidentification else None
    if reidentification:
        if reidentification["frozen_selection_sha256"]!=digest(RAW/args.selection):raise ValueError("reidentification belongs to a different frozen selection")
        private=dict(selected_outputs=reidentification["selected_outputs"],endpoint_closures={
            key:[value for cap in reidentification["captures"].values() for value in cap["roots"].values()] for key in selection["frames"]})
    scopes=source_items(packet)
    interests={item["interest_id"]:item for item in packet["assessment_interests"]}
    captures={item["interest_id"]:item for item in private["selected_outputs"]}
    authors={kind:read(f"output-author-{kind}-001.json") for kind in "ABC"}
    frames={key:assessment.decode_frame(value) for key,value in selection["frames"].items()}
    if reidentification:
        for key,frame in list(frames.items()):
            values=[row["contribution"] for row in private["selected_outputs"] if row["frame_key"]==key]
            pins={canonical_bytes(value["pin"]) for value in values}
            if len(pins)!=1:raise ValueError("fixed output frame crosses physical source aliases")
            pin=values[0]["pin"]
            all_anchors=[a for value in private["endpoint_closures"][key] for a in value.get("anchors",())]
            frames[key]=replace(frame,release_id=reidentification["release_id"],unit=pin["source"],pin=pin,
                contribution_ids=tuple(reidentification["mapping"][identity] for identity in frame.contribution_ids),
                anchor_ids=tuple(sorted({a["anchor_id"] for a in all_anchors})),anchor_scopes=())
    cases={key:{} for key in frames};anchor_map={key:{} for key in frames}
    for kind,author in authors.items():
        artifact=RAW/f"output-author-{kind}-001.json"
        if {entry["interest_id"] for entry in author["cases"]}!=interests.keys():
            raise ValueError("fresh author did not answer every frozen output interest")
        for entry in author["cases"]:
            captured=captures[entry["interest_id"]];key=captured["frame_key"]
            closure={value["contribution_id"]:value for value in private["endpoint_closures"][key]}
            case,anchors=serialize_one(entry,interests[entry["interest_id"]],captured["contribution"],closure,frames[key],scopes[key],
                dict(actor=author["actor"],model=author["model"],source_artifact=artifact.name,source_artifact_sha256=digest(artifact),
                     serializer=Path(__file__).name,serializer_sha256=digest(Path(__file__)),assistance="fresh independent source-only output author; mechanical question-specific wrapper"))
            cases[key].setdefault(kind,[]).append(case);anchor_map[key].update(anchors)
    output_frames={};payloads={}
    for key,frame in frames.items():
        ids=tuple(sorted(set(frame.anchor_ids)|anchor_map[key].keys()))
        scope_rows=tuple({k:v for k,v in anchor.items() if k not in {"anchor_id","source_piece","binding"}} for anchor in anchor_map[key].values())
        frame=replace(frame,anchor_ids=ids,anchor_scopes=scope_rows,guideline_version="pce-fresh-output-guideline-1",rubric_version="pce-fresh-output-1")
        output_frames[key]=assessment.encode_frame(frame);payloads[key]={}
        for kind in "ABC":
            payload=dict(protocol=assessment.PROTOCOL,release_id=frame.release_id,unit_ref=frame.unit,guideline=frame.guideline_version,
                rubric_version=frame.rubric_version,context_policy=frame.context_policy,operation_question=frame.operation_question,
                operation_version=frame.operation_version,domain=frame.domain,direction="output_first",reason="Fresh blinded independent source answers for these exact frozen output questions; no historical-reference reuse.",
                adjudication_passes=[],cases=[asdict(value) for value in cases[key][kind]])
            assessment.decode_authored(canonical_bytes(payload),frame)
            payloads[key][kind]=dict(actor=authors[kind]["actor"],authored=payload)
    selected_scope=reidentification or selection
    return dict(protocol="pce-fresh-output-author-wrappers-1",source_run_id=selected_scope["source_run_id"],source_cut_id=selected_scope["source_cut_id"],
        release_id=selected_scope["release_id"],partition="feature_fit",frames=output_frames,payloads=payloads,
        guideline_text="Exact fresh output questions: literal source fidelity remains separate from contextual scientific roles; explicit unstated fields require inspected structural subjects; association item scope preserves actual endpoint roles. Ambiguous and unassessed source answers remain so. No inference from model confidence or retention.",
        source_cohort_sha256=digest(RAW/selection["author_source_packet"]),output_selection=dict(selection["output_selection"],
            contribution_ids=list(reidentification["mapping"].values()) if reidentification else selection["output_selection"]["contribution_ids"]),
        fixed_question_reidentification=args.reidentification,reidentification_sha256=digest(RAW/args.reidentification) if reidentification else None,
        selection_artifact=args.selection,selection_sha256=digest(RAW/args.selection),database_mutations=False)


def register_output(args):
    from pce03_native_assessment_001 import PROJECT,VERSIONS
    wrappers=read(args.wrappers);sets={}
    with open_runtime_engine(Settings(),"pce-fresh-output-register",purpose="evaluate") as engine,engine.begin() as conn:
        for question in VERSIONS:
            keys=[key for key in wrappers["frames"] if key.startswith(question+":")]
            frames={assessment.decode_frame(wrappers["frames"][key]).unit:assessment.decode_frame(wrappers["frames"][key]) for key in keys}
            if not frames:continue
            guidelines={frame.guideline_version for frame in frames.values()}
            if len(guidelines)!=1:raise ValueError("output guideline differs between frozen frames")
            created=assessment.create_reference_set(conn,project_id=PROJECT,source_run_id=wrappers["source_run_id"],source_cut_id=wrappers["source_cut_id"],
                label=f"{args.receipt}:{question}",legacy_split="dev",guideline=guidelines.pop(),guideline_text=wrappers["guideline_text"],partition="feature_fit",frames=frames,
                sampling=dict(seed=20261105,strata={unit:"frozen-output-kind-semantic-question-strata" for unit in frames},
                    inclusion_probabilities={unit:1 for unit in frames},cohort="fixed24-fresh-independent-output-questions",
                    provenance=dict(wrapper_artifact=args.wrappers,wrapper_sha256=digest(RAW/args.wrappers),selection=wrappers["output_selection"],
                        reidentification=wrappers["fixed_question_reidentification"],inference="none; finite selected semantic products only")))
            units=table("eval.reference_unit")
            unit_ids={row["unit_key"]:row["id"] for row in conn.execute(select(units).where(units.c.set_id==created["set_id"])).mappings()}
            passes={}
            for key in keys:
                frame=assessment.decode_frame(wrappers["frames"][key]);ids=[]
                for kind in "ABC":
                    item=wrappers["payloads"][key][kind]
                    identity=assessment.record_pass(conn,unit_id=unit_ids[frame.unit],pass_kind=kind,actor=item["actor"],
                        authored=canonical_bytes(dict(item["authored"],adjudication_passes=ids if kind=="C" else [])),frame=frame)
                    if kind in "AB":ids.append(identity)
                    passes[f"{key}:{kind}"]=identity
            sets[question]=dict(set_id=created["set_id"],pass_ids=passes)
    return dict(source_run_id=wrappers["source_run_id"],sets=sets,partition="feature_fit",wrapper_artifact=args.wrappers,wrapper_sha256=digest(RAW/args.wrappers))


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument("action",choices=("capture-old","serialize-old","reidentify","register-output"));p.add_argument("--receipt",required=True)
    p.add_argument("--old-capture",default="pce03-fixed-output-old-closure-002.json");p.add_argument("--prediction-run",type=int)
    p.add_argument("--reidentification");p.add_argument("--wrappers")
    p.add_argument("--selection",default="pce03-fresh-output-selection-001.json");args=p.parse_args()
    target=RAW/f"{args.receipt}.json"
    if target.exists():raise FileExistsError(target)
    snapshot=RAW/f"{args.receipt}-script.py"
    if snapshot.exists():raise FileExistsError(snapshot)
    snapshot.write_bytes(Path(__file__).read_bytes())
    try:result={"capture-old":capture_old,"serialize-old":serialize_old,"reidentify":reidentify,"register-output":register_output}[args.action](args)
    except BaseException as error:
        write(RAW/f"{args.receipt}-failure.json",dict(outcome="failed",error_type=type(error).__name__,error=str(error),serializer_sha256=digest(Path(__file__))))
        raise
    write(target,dict(result,serializer_sha256=digest(Path(__file__))))
    print(json.dumps(dict(outcome="passed",receipt=str(target))))


if __name__=="__main__":main()
