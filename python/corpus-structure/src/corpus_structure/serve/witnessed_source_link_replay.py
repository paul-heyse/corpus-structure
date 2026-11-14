"""Detached exact-source verification for named and formula navigation."""

import base64
import json
from dataclasses import asdict
from hashlib import sha256

from corpus_structure.core.evidence import config_key
from corpus_structure.methods.inline_formula_occurrences import INLINE_FORMULA_QUESTION
from corpus_structure.methods.witnessed_source_links import (
    NAMED_NATIVE_PIECES_INPUT,
    NAMED_PIECE_VERSION,
    NAMED_QUESTION,
    ORDERED_LIMIT_REASON,
    ORDERED_VERSION,
    QUESTION,
    VERSION,
    OrderedRecappedDeclaration,
    match_named_source_links,
    ordered_recapped_declarations,
    ordered_witness_selection,
    procedure_artifact_bindings,
    procedure_artifact_endpoint,
    recapped_declarations,
)
from corpus_structure.semantic.contributions import operation_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.structural_products import legacy_structural_sources


def verify_witnessed_links(
    report, source, pin, inputs, ordered_formula_witness=None, *, primary_layers=None
):
    from corpus_structure.methods.scoped_relations import SCOPED_VERSION

    body = report["body"]
    context, text = source["context"], source["text"]
    pieces = context["pieces"]
    selection = ()
    if inputs is not None:
        (ref,) = [
            r
            for r in legacy_structural_sources(inputs)
            if r.source_view_id == source["source_view_id"]
        ]
        selection = tuple(p for p in inputs.passages if p.source_ref == ref.identity)
    if ordered_formula_witness is not None:
        if body["operation_version"] != SCOPED_VERSION:
            raise ValueError("ordered formula witness requires the current scoped producer")
        (query,) = selection
        inspected, expected = ordered_recapped_declarations(
            text,
            pieces,
            {i["self_ref"]: i for i in (*context.get("ancestors", ()), *context["items"])},
            ordered_formula_witness,
            query,
            primary_layers=primary_layers,
            projection=pin["projection_digest"],
            source_view_id=pin["source_view_id"],
        )
        version = ORDERED_VERSION
        witness_selection = ordered_witness_selection(query, ordered_formula_witness)
    else:
        expected = tuple(
            recapped_declarations(
                text,
                pieces,
                {i["self_ref"]: i for i in context["items"]},
                selection,
                primary_layers=primary_layers,
                projection=pin["projection_digest"],
                source_view_id=pin["source_view_id"],
            )
        )
        inspected = len(expected)
        version = VERSION
        witness_selection = tuple(
            (p.passage_id, p.start, p.end, p.effective_version) for p in selection
        )
    operations = {o["operation_key"]: o for o in body["contribution_operations"]}
    link_ops = [o for o in operations.values() if o["question"] == QUESTION]
    if version == VERSION and not expected and not link_ops:
        return
    operation = operation_identity(
        QUESTION,
        version,
        pin,
        witness_selection,
    )
    if len(link_ops) != 1 or link_ops[0]["operation_key"] != operation:
        raise ValueError("witnessed links lack the exact selected operation binding")
    (op,) = link_ops
    if {canonical_bytes(value) for value in op.get("primary_layers", ())} != {
        canonical_bytes(ref.values()) for ref in (primary_layers or {})
    }:
        raise ValueError("witnessed links require their exact exported primary closure")
    rows = {r["contribution_id"]: r for r in body["contributions"]}
    selected = [r for r in rows.values() if r["operation_key"] == operation]
    formula = [
        r
        for r in rows.values()
        if operations[r["operation_key"]]["question"] == INLINE_FORMULA_QUESTION
    ]
    if (
        op["operation_version"] != version
        or op["inspected_count"] != inspected
        or op["emitted_count"] != len(selected)
    ):
        raise ValueError("witnessed link outcome differs from exact selected source")
    dependency = f"native:{pin['native_product_task_id']}"
    if version == ORDERED_VERSION and op["computation_dependencies"] != [dependency]:
        raise ValueError("witnessed link operation lacks the exact native dependency")

    offsets = (
        {
            p["item_ref"]: p["start"]
            for p in pieces
            if p["kind"] == "native_text"
            and p.get("source_field", "text") == "text"
            and "cell_index" not in p
            and ordered_formula_witness.start
            <= p["start"]
            < p["end"]
            <= ordered_formula_witness.end
        }
        if ordered_formula_witness is not None
        else {}
    )

    def exact(row, role, pointer, extent, name_pieces=None, region=None):
        start, end = extent
        value = source_python(row["value"])
        if row["kind"] != "occurrence" or value["role"] != role:
            return False
        if region is not None and value["region"] != region:
            return False
        if version == ORDERED_VERSION:
            if name_pieces is None:
                left = offsets[pointer]
                name_pieces = ((pointer, start - left, end - left),)
            expected_anchors = tuple(
                (ptr, lo, hi, text[offsets[ptr] + lo : offsets[ptr] + hi])
                for ptr, lo, hi in name_pieces
            )
            if (
                row["semantic_type"] != "structural.located_participant"
                or row["computation_dependencies"] != [dependency]
                or row["pin"] != pin
                or any(
                    anchor["space"] != "native"
                    or anchor["precision"] != "exact"
                    or anchor["pin"] != pin
                    for anchor in row.get("anchors", ())
                )
            ):
                return False
        else:
            (piece,) = [
                p for p in pieces if p.get("item_ref") == pointer and p["kind"] == "native_text"
            ]
            expected_anchors = (
                (pointer, start - piece["start"], end - piece["start"], text[start:end]),
            )
        return (
            value["text"] == text[start:end]
            and (value["source_pointer"], value["start"], value["end"]) == (pointer, start, end)
            and tuple(
                (a["pointer"], a["start"], a["end"], a["source_piece"])
                for a in row.get("anchors", ())
            )
            == expected_anchors
        )

    verified = set()
    linked = 0
    for link in expected:
        is_ordered = isinstance(link, OrderedRecappedDeclaration)
        uses = [
            r
            for r in formula
            if (
                (v := source_python(r["value"]))["source_pointer"] == link.use_pointer
                and v["text"] == link.symbol
                and link.equation[0] <= v["start"] < v["end"] <= link.equation[1]
            )
        ]
        if not is_ordered and len(uses) != 1:
            continue
        name_pieces = link.name_pieces if is_ordered else None
        region = link.passage if is_ordered else None
        targets = [
            r
            for r in selected
            if exact(
                r,
                "declared_name",
                name_pieces[0][0] if name_pieces else link.declaration_pointer,
                link.name,
                name_pieces,
                region,
            )
        ]
        cues = [
            r
            for r in selected
            if exact(r, "declaration_recap", link.use_pointer, link.recap, region=region)
        ]
        antecedents = [
            r
            for r in rows.values()
            if r.get("component", {}).get("attachment_kind") == "declares"
            and r["operation_key"] != operation
            and (
                not is_ordered
                or operations[r["operation_key"]]["question"] == "source_structural_relations"
            )
            and exact(
                rows[r["members"][1]],
                "declaration",
                link.declaration_pointer,
                link.declaration,
                region=link.declaration_pointer if is_ordered else None,
            )
            and (
                exact(
                    rows[r["members"][0]],
                    "symbol",
                    link.declaration_pointer,
                    link.symbol_site,
                    region=link.declaration_pointer,
                )
                if isinstance(link, OrderedRecappedDeclaration)
                else source_python(rows[r["members"][0]]["value"]).get("text") == link.symbol
            )
        ]
        if len(antecedents) != 1:
            if is_ordered:
                raise ValueError("witnessed links lack one exact prior binding")
            continue
        if len(uses) != 1:
            continue
        (use,) = uses
        if len(targets) != 1 or len(cues) != 1:
            raise ValueError("witnessed links lack the exact named target and recap")
        (target,), (cue,), (prior,) = targets, cues, antecedents
        if (
            source_python(target["value"]).get("primary_node") != link.declaration_node
            or source_python(cue["value"]).get("primary_node") != link.primary_node
        ):
            raise ValueError("witnessed link source roles lose their exact primary references")
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
            and (
                not is_ordered
                or (
                    r["component"]["question"] == QUESTION
                    and r["component"]["question_version"] == ORDERED_VERSION
                    and r["semantic_type"] == "structural.scoped_attachment"
                    and r["pin"] == pin
                    and r["members"] == [use["contribution_id"], target["contribution_id"]]
                    and r["computation_dependencies"]
                    == [
                        use["contribution_id"],
                        target["contribution_id"],
                        dependency,
                        cue["contribution_id"],
                        prior["contribution_id"],
                    ]
                )
            )
            and r["component"].get("primary_node") == link.primary_node
            and r["component"]["scope"] == link.scope
            and (r["component"].get("effective_version") == link.effective_version)
            and {cue["contribution_id"], prior["contribution_id"]}
            <= set(r["computation_dependencies"])
        ]
        if len(relations) != 1:
            raise ValueError("witnessed links differ from declared direction or premises")
        verified.update(r["contribution_id"] for r in (target, cue, *relations))
        linked += 1
    if verified != {r["contribution_id"] for r in selected}:
        raise ValueError("witnessed links contain unsupported rows")
    limited = version == ORDERED_VERSION and linked < inspected
    if op["outcome"] != ("limited" if limited else "succeeded" if selected else "empty") or (
        version == ORDERED_VERSION
        and op.get("reason") != (ORDERED_LIMIT_REASON if limited else None)
    ):
        raise ValueError("witnessed link outcome differs from exact selected source")


def verify_named_links(report, source, pin, inputs, *, primary_layers=None):
    return verify_annotated_named_links(report, source, {}, primary_layers=primary_layers)


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
    annotations=(),
):
    if version != NAMED_PIECE_VERSION:
        raise ValueError("named replay requires the current retained primary projection")
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
    rows = {row["contribution_id"]: row for row in body["contributions"]}
    annotation_by_dependency = {
        "annotation:" + annotation.dependency_digest: annotation for annotation in annotations
    }
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
        artifacts = ()
        versioned = details | {
            "named_cue": link.evidence(),
            "primary_node": link.witness.primary_node,
        }
        dependencies = [f"native:{pin['native_product_task_id']}", link.witness.annotation]
        artifacts = (
            artifact_bindings.get((link.pointer, *link.left), ())
            if link.kind == "procedure_reference" and link.resolution == "target_selection_required"
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
        if (
            link.kind == "definition_reference"
            and link.resolution == "target_selection_required"
            and (concept := link.definition_subject) is not None
        ):
            assert dependencies is not None
            require(
                "named_link_definition_subject",
                link.pointer,
                concept[0],
                link.passage,
                {**versioned, "definition_subject_kind": concept[1]},
                [*dependencies, subject, cue],
            )
        if artifacts:
            binding = procedure_artifact_endpoint(
                rows, link, annotation_by_dependency[link.witness.annotation], artifacts[0]
            )
            if binding is not None:
                action, caption, artifact = (row["contribution_id"] for row in binding)
                matches = [
                    row
                    for row in selected
                    if row["kind"] == "relation"
                    and row.get("component", {}).get("attachment_kind") == "procedure_reference"
                    and row["component"]["scope"] == link.scope
                    and row["component"].get("effective_version") == link.witness.effective_version
                    and row.get("members") == [action, caption]
                    and row.get("endpoints")
                    == [
                        {"role": "attachment", "contribution_id": action},
                        {"role": "target", "contribution_id": caption},
                    ]
                    and {subject, cue, artifact} <= set(row["computation_dependencies"])
                ]
                if len(matches) != 1:
                    raise ValueError(
                        "named procedure reference differs from exact action and caption"
                    )
                verified.add(matches[0]["contribution_id"])
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
            and r["component"]["question_version"] == version
            and r["component"].get("effective_version") == link.witness.effective_version
            and r["component"].get("primary_node") == link.witness.primary_node
            and cue in r["computation_dependencies"]
        ]
        if len(matches) != 1:
            raise ValueError("named link differs from its exact cue or direction")
        (matched,) = matches
        if matched["computation_dependencies"] != [
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


NAMED_LINK_NATIVE_PIECES_FIELD = "named_link_native_pieces"


def archived_named_link_native_pieces(contract):
    """Check the selected release's retained bytes before replaying piece ownership."""
    try:
        archived = contract[NAMED_LINK_NATIVE_PIECES_FIELD]
        manifest = base64.b64decode(archived["manifest_base64"], validate=True)
        policy = base64.b64decode(archived["input_base64"], validate=True)
        expected = dict(json.loads(manifest)["dependencies"])[NAMED_NATIVE_PIECES_INPUT]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("joined named links lack their archived native-piece policy") from error
    if (
        "release:" + sha256(manifest).hexdigest() != contract["release_id"]
        or sha256(policy).hexdigest() != expected
    ):
        raise ValueError("joined named-link native-piece policy is not bound to its release")
    return policy


def verify_annotated_named_links(
    report, source, producers, *, native_piece_policy=None, primary_layers=None
):
    """Verify current source-role projections from exported primary closure, without NLP."""
    from corpus_structure.methods.native_evidence_layers import (
        retained_annotation_products,
        retained_annotation_profile,
    )
    from corpus_structure.methods.scoped_relations import SCOPED_VERSION
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import NativeSourcePin, record_source_pin
    from corpus_structure.semantic.structural_products import StructuralInput

    from .review_bundle import _retained_review_source_view

    body, cfg = report["body"], report["configuration"]
    if body["operation_version"] != SCOPED_VERSION or body["configuration_hash"] != config_key(
        "structure.scoped_relations", SCOPED_VERSION, cfg
    ):
        raise ValueError("named links require their current exact retained configuration")
    if cfg.get("inputs") is None:
        return
    inputs = StructuralInput.model_validate(cfg["inputs"])
    view = _retained_review_source_view(source)
    (ref,) = [r for r in legacy_structural_sources(inputs) if r.source_view_id == view.ref.id]
    passages = tuple(p for p in inputs.passages if p.source_ref == ref.identity)
    operations = [op for op in body["contribution_operations"] if op["question"] == NAMED_QUESTION]
    if len(operations) != 1:
        raise ValueError("named links lack their exact selected operation")
    (operation,) = operations
    selected = [pin.values() for pin in (primary_layers or {})]
    if (
        not selected
        or any(pin not in cfg.get("characterization_layers", ()) for pin in selected)
        or {canonical_bytes(pin) for pin in operation.get("primary_layers", ())}
        != {canonical_bytes(pin) for pin in selected}
    ):
        raise ValueError("named link replay requires the exact exported frozen primary closure")
    frame = native_source_frame(view, ())
    origin_id = operation.get("annotation_origin_task_id")
    if origin_id is not None:
        origin = producers[origin_id]
        original = origin["body"] or {}
        if (
            origin["method"] != "extract.m1_annotations"
            or original.get("operation_version") != "3"
            or original.get("source") != frame.unit_ref
            or original.get("input_hash") != origin.get("input_hash")
            or original.get("configuration_hash") != origin.get("config_hash")
        ):
            raise ValueError("named links lack their exact retained M1 summary")
        detail = source_python(original["parse_detail"])
        if detail.get("recipe") != "m1-owned-linguistic-product-1" or canonical_bytes(
            detail.get("source_pin")
        ) != canonical_bytes(asdict(NativeSourcePin.from_source(frame))):
            raise ValueError("named link summary differs from retained native source")
    annotations = []
    for pin, layer in (primary_layers or {}).items():
        for run in layer.payload.get("native_runs", ()):
            if run["provider"] == "spacy":
                profile = retained_annotation_profile(run)
                annotations.extend(retained_annotation_products({pin: layer}, view, profile))
    expected = match_named_source_links(
        view.text,
        view.pieces,
        {item["self_ref"]: item for item in view.items},
        passages,
        annotations,
        version=NAMED_PIECE_VERSION,
        primary_layers=primary_layers,
        projection=view.ref.projection_digest,
        source_view_id=view.ref.id,
    )
    _verify_named_population(
        body,
        source,
        record_source_pin(frame),
        passages,
        operations,
        expected.matches,
        version=NAMED_PIECE_VERSION,
        inspected_count=expected.inspected_count,
        outcome=expected.outcome(),
        annotation_origin_task_id=origin_id,
        annotations=annotations,
    )
