"""Detached exact-source verification for named and formula navigation."""

from dataclasses import asdict

from corpus_structure.core.evidence import config_key
from corpus_structure.methods.inline_formula_occurrences import INLINE_FORMULA_QUESTION
from corpus_structure.methods.witnessed_source_links import (
    NAMED_QUESTION,
    NAMED_VERSION,
    QUESTION,
    VERSION,
    named_source_links,
    recapped_declarations,
)
from corpus_structure.semantic.contributions import operation_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python


def verify_witnessed_links(report, source, pin, inputs):
    body = report["body"]
    context, text = source["context"], source["text"]
    pieces = context["pieces"]
    selection = ()
    if inputs is not None:
        (ref,) = [r for r in inputs.sources if r.source_view_id == source["source_view_id"]]
        selection = tuple(p for p in inputs.passages if p.source_ref == ref.identity)
    expected = tuple(
        recapped_declarations(
            text,
            pieces,
            {i["self_ref"]: i for i in context["items"]},
            selection,
        )
    )
    operations = {o["operation_key"]: o for o in body["contribution_operations"]}
    link_ops = [o for o in operations.values() if o["question"] == QUESTION]
    if not expected and not link_ops:
        return
    operation = operation_identity(
        QUESTION,
        VERSION,
        pin,
        tuple((p.passage_id, p.start, p.end, p.effective_version) for p in selection),
    )
    if len(link_ops) != 1 or link_ops[0]["operation_key"] != operation:
        raise ValueError("witnessed links lack the exact selected operation binding")
    (op,) = link_ops
    rows = {r["contribution_id"]: r for r in body["contributions"]}
    selected = [r for r in rows.values() if r["operation_key"] == operation]
    formula = [
        r
        for r in rows.values()
        if operations[r["operation_key"]]["question"] == INLINE_FORMULA_QUESTION
    ]
    if (
        op["operation_version"] != VERSION
        or op["inspected_count"] != len(expected)
        or op["emitted_count"] != len(selected)
        or op["outcome"] != ("succeeded" if selected else "empty")
    ):
        raise ValueError("witnessed link outcome differs from exact selected source")

    def exact(row, role, pointer, extent):
        (piece,) = [
            p for p in pieces if p.get("item_ref") == pointer and p["kind"] == "native_text"
        ]
        start, end = extent
        anchors = row.get("anchors", ())
        value = source_python(row["value"])
        return (
            row["kind"] == "occurrence"
            and value["role"] == role
            and value["text"] == text[start:end]
            and (value["source_pointer"], value["start"], value["end"]) == (pointer, start, end)
            and len(anchors) == 1
            and anchors[0]["pointer"] == pointer
            and (anchors[0]["start"], anchors[0]["end"])
            == (start - piece["start"], end - piece["start"])
            and anchors[0]["source_piece"] == text[start:end]
        )

    verified = set()
    for link in expected:
        uses = [
            r
            for r in formula
            if (
                (v := source_python(r["value"]))["source_pointer"] == link.use_pointer
                and v["text"] == link.symbol
                and link.equation[0] <= v["start"] < v["end"] <= link.equation[1]
            )
        ]
        if len(uses) != 1:
            continue
        (use,) = uses
        targets = [
            r for r in selected if exact(r, "declared_name", link.declaration_pointer, link.name)
        ]
        cues = [r for r in selected if exact(r, "declaration_recap", link.use_pointer, link.recap)]
        antecedents = [
            r
            for r in rows.values()
            if r.get("component", {}).get("attachment_kind") == "declares"
            and r["operation_key"] != operation
            and exact(
                rows[r["members"][1]], "declaration", link.declaration_pointer, link.declaration
            )
            and source_python(rows[r["members"][0]]["value"]).get("text") == link.symbol
        ]
        if len(antecedents) != 1:
            continue
        if len(targets) != 1 or len(cues) != 1:
            raise ValueError("witnessed links lack the exact named target and recap")
        (target,), (cue,), (prior,) = targets, cues, antecedents
        endpoints = [
            {"role": "attachment", "contribution_id": use["contribution_id"]},
            {"role": "target", "contribution_id": target["contribution_id"]},
        ]
        relations = [
            r
            for r in selected
            if r.get("endpoints") == endpoints
            and r["kind"] == "relation"
            and r.get("component", {}).get("attachment_kind") == "declares"
            and r["component"]["scope"] == link.scope
            and {cue["contribution_id"], prior["contribution_id"]}
            <= set(r["computation_dependencies"])
        ]
        if len(relations) != 1:
            raise ValueError("witnessed links differ from declared direction or premises")
        verified.update(r["contribution_id"] for r in (target, cue, *relations))
    if verified != {r["contribution_id"] for r in selected}:
        raise ValueError("witnessed links contain unsupported rows")


def verify_named_links(report, source, pin, inputs):
    body = report["body"]
    context, text = source["context"], source["text"]
    pieces = context["pieces"]
    passages = ()
    if inputs is not None:
        (ref,) = [r for r in inputs.sources if r.source_view_id == source["source_view_id"]]
        passages = tuple(p for p in inputs.passages if p.source_ref == ref.identity)
    expected = tuple(
        named_source_links(
            text,
            pieces,
            {i["self_ref"]: i for i in context["items"]},
            passages,
        )
    )
    operations = [o for o in body["contribution_operations"] if o["question"] == NAMED_QUESTION]
    if not expected and not operations:
        return
    _verify_named_population(
        body,
        source,
        pin,
        passages,
        operations,
        expected,
        version=VERSION,
        inspected_count=len(expected),
        outcome="limited" if any(link.right is None for link in expected) else "succeeded",
    )


def _verify_named_population(
    body,
    source,
    pin,
    passages,
    operations,
    expected,
    *,
    version,
    inspected_count,
    outcome,
    annotation_origin_task_id=None,
):
    text, pieces = source["text"], source["context"]["pieces"]
    key = operation_identity(
        NAMED_QUESTION,
        version,
        pin,
        tuple((p.passage_id, p.start, p.end, p.effective_version) for p in passages),
    )
    if len(operations) != 1 or operations[0]["operation_key"] != key:
        raise ValueError("named links lack the exact selected operation binding")
    (op,) = operations
    selected = [r for r in body["contributions"] if r["operation_key"] == key]
    if (
        op["operation_version"] != version
        or op["inspected_count"] != inspected_count
        or op["emitted_count"] != len(selected)
        or op["outcome"] != outcome
        or op.get("annotation_origin_task_id") != annotation_origin_task_id
    ):
        raise ValueError("named link outcome differs from exact selected source")
    verified = set()
    artifact_bindings = {}
    if version == NAMED_VERSION:
        from corpus_structure.methods.witnessed_source_links import procedure_artifact_bindings

        artifact_bindings = procedure_artifact_bindings(body["contributions"])

    def require(role, pointer, extent, passage, details, dependencies=None):
        (piece,) = [
            p for p in pieces if p.get("item_ref") == pointer and p["kind"] == "native_text"
        ]
        start, end = extent
        candidates = []
        for row in selected:
            if row["kind"] != "occurrence" or len(row.get("anchors", ())) != 1:
                continue
            (anchor,) = row["anchors"]
            if (
                (anchor["pointer"], anchor["start"], anchor["end"], anchor["source_piece"])
                == (
                    pointer,
                    start - piece["start"],
                    end - piece["start"],
                    text[start:end],
                )
                and canonical_bytes(source_python(row["value"]))
                == canonical_bytes(
                    dict(
                        role=role,
                        source_pointer=pointer,
                        region=passage,
                        text=text[start:end],
                        start=start,
                        end=end,
                        **details,
                    )
                )
                and (dependencies is None or row["computation_dependencies"] == dependencies)
            ):
                candidates.append(row["contribution_id"])
        if len(candidates) != 1:
            raise ValueError("named link lacks its exact located source role")
        (candidate,) = candidates
        verified.add(candidate)
        return candidate

    for link in expected:
        details = {"resolution": link.resolution} if link.resolution else {}
        versioned = {}
        dependencies = None
        subject_dependencies = None
        if version == NAMED_VERSION:
            versioned = details | {"named_cue": link.evidence()}
            dependencies = [f"native:{pin['native_product_task_id']}", link.witness.annotation]
            artifacts = (
                artifact_bindings.get((link.pointer, *link.left), ())
                if link.kind == "procedure_reference"
                and link.resolution == "target_selection_required"
                else ()
            )
            subject_dependencies = [*dependencies, *artifacts]
        subject = require(
            "named_link_subject",
            link.pointer,
            link.left,
            link.passage,
            details | versioned,
            subject_dependencies,
        )
        cue = require(
            "named_link_cue", link.pointer, link.cue, link.passage, versioned, dependencies
        )
        if link.right is None or link.target_pointer is None:
            continue
        target = require(
            "named_link_target",
            link.target_pointer,
            link.right,
            link.passage,
            versioned,
            dependencies,
        )
        endpoints = [
            {"role": "attachment", "contribution_id": subject},
            {"role": "target", "contribution_id": target},
        ]
        matches = [
            r
            for r in selected
            if r.get("endpoints") == endpoints
            and r["kind"] == "relation"
            and r.get("component", {}).get("attachment_kind") == link.kind
            and r["component"]["scope"] == link.scope
            and (
                version != NAMED_VERSION
                or (
                    r["component"]["question_version"] == version
                    and r["component"].get("effective_version") == link.witness.effective_version
                )
            )
            and cue in r["computation_dependencies"]
        ]
        if len(matches) != 1:
            raise ValueError("named link differs from its exact cue or direction")
        (matched,) = matches
        if version == NAMED_VERSION and matched["computation_dependencies"] != [
            subject,
            target,
            f"native:{pin['native_product_task_id']}",
            link.witness.annotation,
            cue,
        ]:
            raise ValueError("named link lacks exact released witness dependencies")
        verified.add(matched["contribution_id"])
    if verified != {r["contribution_id"] for r in selected}:
        raise ValueError("named links contain unsupported rows")


def verify_annotated_named_links(report, source, producers):
    from corpus_structure.ingest.annotations import AnnotationProfile, restore_annotations
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.witnessed_source_links import match_named_source_links
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import NativeSourcePin, record_source_pin
    from corpus_structure.semantic.structural_products import StructuralInput

    from .review_bundle import _retained_review_source_view

    body, cfg = report["body"], report["configuration"]
    if cfg.get("inputs") is None:
        return
    if body["operation_version"] not in {"7", "8"} or body["configuration_hash"] != config_key(
        "structure.scoped_relations", body["operation_version"], cfg
    ):
        raise ValueError("named links differ from their retained configuration")
    inputs = StructuralInput.model_validate(cfg["inputs"])
    view = _retained_review_source_view(source)
    (ref,) = [r for r in inputs.sources if r.source_view_id == view.ref.id]
    passages = tuple(p for p in inputs.passages if p.source_ref == ref.identity)
    operations = [op for op in body["contribution_operations"] if op["question"] == NAMED_QUESTION]
    (operation,) = operations
    origin_id = operation.get("annotation_origin_task_id")
    frame = native_source_frame(view, ())
    if origin_id is None:
        annotations, errors = (), ("retained annotation origin unavailable",)
    else:
        origin = producers[origin_id]
        original = origin["body"] or {}
        if (
            origin["method"] != "extract.m1_annotations"
            or origin["origin_unit_id"] != ref.source_view_id
            or origin["project_id"] != ref.project_id
            or original.get("release_id") != ref.release_id
            or original.get("source") != frame.unit_ref
            or original.get("operation_version") != "2"
            or original.get("input_hash") != origin.get("input_hash")
            or original.get("configuration_hash") != origin.get("config_hash")
        ):
            raise ValueError("named links lack their exact retained annotation producer")
        detail = source_python(original["parse_detail"])
        if detail.get("recipe") != "m1-owned-linguistic-product-1" or canonical_bytes(
            detail.get("source_pin")
        ) != canonical_bytes(asdict(NativeSourcePin.from_source(frame))):
            raise ValueError("named link annotation pin differs from its retained source")
        annotations = restore_annotations(
            detail["annotations"],
            source=frame,
            profile=AnnotationProfile(SentenceConfig.model_validate(cfg.get("sentences", {}))),
        )
        errors = tuple(detail.get("annotation_errors", ()))
        if original.get("outcome") == "failed" and not errors:
            errors = ("original annotation operation failed",)
    expected = match_named_source_links(
        view.text,
        view.pieces,
        {item["self_ref"]: item for item in view.items},
        passages,
        annotations,
        annotation_errors=errors,
    )
    _verify_named_population(
        body,
        source,
        record_source_pin(frame),
        passages,
        operations,
        expected.matches,
        version=NAMED_VERSION,
        inspected_count=expected.inspected_count,
        outcome=expected.outcome(),
        annotation_origin_task_id=origin_id,
    )
    _verify_inheritance(
        body,
        record_source_pin(frame),
        passages,
        annotation_available=bool(annotations),
        annotation_errors=bool(errors),
    )


def _verify_inheritance(body, pin, passages, *, annotation_available, annotation_errors):
    from corpus_structure.methods.witnessed_source_links import (
        INHERITANCE_QUESTION,
        qualified_inheritance,
    )

    (op,) = [op for op in body["contribution_operations"] if op["question"] == INHERITANCE_QUESTION]
    key = operation_identity(
        INHERITANCE_QUESTION,
        "1",
        pin,
        tuple((p.passage_id, p.start, p.end, p.effective_version) for p in passages),
    )
    rows = [row for row in body["contributions"] if row["operation_key"] == key]
    inspected, inherited = qualified_inheritance(body["contributions"])
    if annotation_errors:
        outcome = "limited" if inherited else "unsupported"
    elif annotation_available:
        outcome = "succeeded" if inherited else "empty"
    else:
        outcome = "unsupported"
    if (
        op["operation_key"] != key
        or op["operation_version"] != "1"
        or op["inspected_count"] != inspected
        or op["emitted_count"] != len(rows)
        or len(rows) != len(inherited)
        or op["outcome"] != outcome
    ):
        raise ValueError("scope inheritance differs from the admitted qualifier population")
    actual = set()
    for cue, host, qualifier in inherited:
        component = qualifier["component"]
        (edge,) = [
            row
            for row in rows
            if row["kind"] == "relation"
            and row["component"]["attachment_kind"] == "scope_inheritance"
            and row["component"]["scope"] == component["scope"]
            and row["component"].get("effective_version") == component.get("effective_version")
            and row["endpoints"]
            == [
                {"role": "attachment", "contribution_id": cue["contribution_id"]},
                {"role": "target", "contribution_id": host["contribution_id"]},
            ]
            and qualifier["contribution_id"] in row["computation_dependencies"]
        ]
        actual.add(edge["contribution_id"])
    if actual != {row["contribution_id"] for row in rows}:
        raise ValueError("scope inheritance has an unsupported direction or host")
