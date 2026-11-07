"""Detached exact-source verification for witnessed formula navigation."""

from corpus_structure.methods.inline_formula_occurrences import INLINE_FORMULA_QUESTION
from corpus_structure.methods.witnessed_source_links import (
    NAMED_QUESTION,
    QUESTION,
    VERSION,
    named_source_links,
    recapped_declarations,
)
from corpus_structure.semantic.contributions import operation_identity
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
    key = operation_identity(
        NAMED_QUESTION,
        VERSION,
        pin,
        tuple((p.passage_id, p.start, p.end, p.effective_version) for p in passages),
    )
    if len(operations) != 1 or operations[0]["operation_key"] != key:
        raise ValueError("named links lack the exact selected operation binding")
    (op,) = operations
    selected = [r for r in body["contributions"] if r["operation_key"] == key]
    outcome = "limited" if any(link.right is None for link in expected) else "succeeded"
    if (
        op["operation_version"] != VERSION
        or op["inspected_count"] != len(expected)
        or op["emitted_count"] != len(selected)
        or op["outcome"] != outcome
    ):
        raise ValueError("named link outcome differs from exact selected source")
    verified = set()

    def require(role, pointer, extent, passage, resolution=None):
        (piece,) = [
            p for p in pieces if p.get("item_ref") == pointer and p["kind"] == "native_text"
        ]
        start, end = extent
        candidates = []
        for row in selected:
            if row["kind"] != "occurrence" or len(row.get("anchors", ())) != 1:
                continue
            (anchor,) = row["anchors"]
            if (anchor["pointer"], anchor["start"], anchor["end"], anchor["source_piece"]) == (
                pointer,
                start - piece["start"],
                end - piece["start"],
                text[start:end],
            ) and source_python(row["value"]) == dict(
                role=role,
                source_pointer=pointer,
                region=passage,
                text=text[start:end],
                start=start,
                end=end,
                **({"resolution": resolution} if resolution else {}),
            ):
                candidates.append(row["contribution_id"])
        if len(candidates) != 1:
            raise ValueError("named link lacks its exact located source role")
        (candidate,) = candidates
        verified.add(candidate)
        return candidate

    for link in expected:
        subject = require(
            "named_link_subject", link.pointer, link.left, link.passage, link.resolution
        )
        cue = require("named_link_cue", link.pointer, link.cue, link.passage)
        if link.right is None or link.target_pointer is None:
            continue
        target = require("named_link_target", link.target_pointer, link.right, link.passage)
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
            and cue in r["computation_dependencies"]
        ]
        if len(matches) != 1:
            raise ValueError("named link differs from its exact cue or direction")
        verified.add(matches[0]["contribution_id"])
    if verified != {r["contribution_id"] for r in selected}:
        raise ValueError("named links contain unsupported rows")
