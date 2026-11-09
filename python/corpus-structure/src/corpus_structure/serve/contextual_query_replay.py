"""Replay detached query signals over authenticated original parser and source custody."""

from corpus_structure.core.evidence import config_key
from corpus_structure.methods.contextual_candidates import ContextualQueryConfig
from corpus_structure.methods.contextual_embeddings import (
    E5,
    QWEN,
    ContextInput,
    RenderedInput,
    identity,
    validate_vector,
    verify_retained_rendering,
)
from corpus_structure.methods.contextual_query import QueryContextSelection, resolve_query_contexts
from corpus_structure.semantic.contributions import (
    contribution_identity,
    occurrence_identity,
    operation_identity,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.record_contracts import anchor_identity

_PARSER_METHOD = {
    "located-frame-1": "extract.pm2_hanlp",
    "located-referent-1": "extract.pm2_maverick",
    "located-discourse-neighbor-1": "extract.pm2_dipo",
}
_QUESTION = "retained producer occurrence roles and contextual encoder products"


def retained_query_selection(method, version, configuration):
    if method != "retrieve.contextual":
        return None
    raw = configuration.get("query_context")
    if version == "11":
        if raw is not None:
            return QueryContextSelection.model_validate(raw)
        ContextualQueryConfig.model_validate(configuration)
        return None
    if raw is not None:
        raise ValueError("retained query context differs from contextual operation 11")
    return None


def query_context_dependency(origin, reference):
    return {
        "required_by": f"origin-task:{origin}",
        "reason": "declared_query_context",
        "reference": reference.model_dump(mode="json"),
    }


def _focal_inputs(body, selection, operation, nodes, pin):
    occurrences = {binding.occurrence_id for binding in selection.bindings}
    carriers = {}
    contexts = {}
    for row in body.get("contributions", ()):
        occurrence = row.get("occurrence_id")
        if (
            row.get("semantic_type") != "contextual.located_mention"
            or occurrence not in occurrences
        ):
            continue
        anchors = row.get("anchors", ())
        if (
            not anchors
            or row["kind"] != "occurrence"
            or row["pin"] != pin
            or row["operation_key"] != operation["operation_key"]
            or row["contribution_id"] != contribution_identity(row)
            or occurrence != occurrence_identity(anchors)
            or len({anchor["pointer"] for anchor in anchors}) != 1
        ):
            raise ValueError("detached query context has a foreign focal carrier")
        text = nodes.get(anchors[0]["pointer"], {}).get("text", "")
        for anchor in anchors:
            start, end = anchor.get("start"), anchor.get("end")
            if (
                anchor["pin"] != pin
                or anchor["precision"] != "exact"
                or anchor["space"] != "native"
                or type(start) is not int
                or type(end) is not int
                or not 0 <= start < end <= len(text)
                or text[start:end] != anchor["source_piece"]
                or anchor["anchor_id"] != anchor_identity(anchor)
            ):
                raise ValueError("detached query carrier differs from its exact native source")
        if occurrence in carriers and anchors != carriers[occurrence]["anchors"]:
            raise ValueError("detached query context has conflicting focal carriers")
        carriers[occurrence] = row
        contexts[occurrence] = (
            text,
            min(a["start"] for a in anchors),
            max(a["end"] for a in anchors),
        )
    if carriers.keys() != occurrences:
        raise ValueError("detached query context is missing an exact focal carrier")
    return tuple(carriers.values()), contexts


def _receipt_outcome(occurrence, signal, operation, phases, rendered, vector):
    if rendered is not None and vector is not None:
        return "rendered" if signal.signals else "unavailable"
    if rendered is not None or vector is not None or operation.get("outcome") != "limited":
        raise ValueError("detached query context differs from its encoder outcome")
    retrieval = phases.get(
        f"contextual candidate retrieval for located occurrence {occurrence}", {}
    )
    reason = retrieval.get("reason", "").removeprefix("Exploratory retrieval unavailable. ")
    if retrieval.get("outcome") == "limited" and reason.startswith("ContextCoreLimited: "):
        return "limited"
    if operation.get("reason") == "configured contextual encoder unavailable for this selection":
        return "encoder_unavailable" if signal.signals else "unavailable"
    raise ValueError("detached query context lacks its retained encoder refusal")


def _verify_receipts(retained, selection, payloads, nodes, pin):
    body, config = retained["body"], retained["configuration"]
    cfg = ContextualQueryConfig.model_validate(config)
    profile = E5 if cfg.profile == "e5" else QWEN
    operations = body.get("contribution_operations", ())
    matches = [operation for operation in operations if "contextual_enrichment" in operation]
    key = operation_identity("retrieve.contextual", "11", cfg.model_dump(mode="json"), pin)
    if (
        len(matches) != 1
        or body.get("source") != pin["source"]
        or body.get("configuration_hash") != config_key("retrieve.contextual", "11", config)
        or matches[0].get("operation_key") != key
        or matches[0].get("operation_version") != "11"
        or matches[0].get("question") != _QUESTION
    ):
        raise ValueError("detached query context differs from its contextual producer")
    (operation,) = matches
    if any(
        binding.evidence.contribution_id not in operation["computation_dependencies"]
        for binding in selection.bindings
    ):
        raise ValueError("detached query context is missing a declared parser dependency")
    carriers, contexts = _focal_inputs(body, selection, operation, nodes, pin)
    expected = resolve_query_contexts(selection, payloads, carriers, nodes, pin)
    detail = source_python(body["parse_detail"])
    receipts = detail.get("query_context", {})
    if receipts.keys() != expected.keys():
        raise ValueError("detached query context receipt population differs from configuration")
    inputs, vectors = {}, {}
    for rows, collected in (
        (detail.get("encoder_inputs", ()), inputs),
        (operation["contextual_enrichment"]["vectors"], vectors),
    ):
        for row in rows:
            occurrence = row["object_id"]
            if occurrence in expected:
                if occurrence in collected:
                    raise ValueError("detached query context repeats an encoder result")
                collected[occurrence] = row
    phases = {op["question"]: op for op in operations if op is not operation}
    for occurrence, signal in expected.items():
        rendered, vector = inputs.get(occurrence), vectors.get(occurrence)
        outcome = _receipt_outcome(occurrence, signal, operation, phases, rendered, vector)
        if canonical_bytes(receipts[occurrence]) != canonical_bytes(
            dict(signal.report(), outcome=outcome)
        ):
            raise ValueError("detached query context receipt differs from original parser evidence")
        if rendered is None or vector is None:
            continue
        text, start, end = contexts[occurrence]
        item = ContextInput(
            occurrence,
            pin["source"],
            "query",
            text[start:end],
            text,
            start,
            end,
            representation_digest=signal.representation_digest,
            query_context=signal.rendered if signal.signals else None,
        )
        verify_retained_rendering(item, profile, RenderedInput(**rendered))
        binding = [
            occurrence,
            item.source_binding,
            profile.profile_id,
            rendered["final_input_digest"],
            item.representation_digest,
        ]
        if [
            vector[key]
            for key in (
                "object_id",
                "source_binding",
                "profile_id",
                "input_digest",
                "representation_digest",
            )
        ] != binding or vector["vector_id"] != identity("context-vector", binding):
            raise ValueError(
                "detached query context vector differs from the retained encoder input"
            )
        validate_vector(vector["values"], profile.dimension)


def verify_contextual_query_closure(root, manifest, scopes, inventory, report_inventory):
    from .review_bundle import _detached_relation, _retained_contribution_payloads

    reports, duplicates = {}, set()
    for row in _detached_relation(root, manifest, "reports"):
        origin = row["origin_task_id"]
        if origin in reports:
            duplicates.add(origin)
        reports[origin] = row
    enriched = []
    for origin, row in reports.items():
        body = row.get("body") or {}
        if not body and row.get("task_status") in {"failed", "skipped", "cancelled"}:
            continue
        config = row.get("configuration") or {}
        selection = retained_query_selection(
            row.get("method"), body.get("operation_version"), config
        )
        if row.get("method") == "retrieve.contextual" and body.get("operation_version") == "11":
            expected = set(config.get("required_occurrence_ids", ()))
            actual = {
                c.get("occurrence_id")
                for c in body.get("contributions", ())
                if c.get("semantic_type") == "contextual.located_mention"
            }
            if expected and expected != actual:
                raise ValueError("detached report differs from its exact carrier population")
            detail = body.get("parse_detail")
            if (
                selection is None
                and detail is not None
                and "query_context" in source_python(detail)
            ):
                raise ValueError("detached literal-only control contains a parser signal")
        if selection is not None:
            enriched.append((origin, row, selection))
    if not enriched:
        return set()

    sources = {row["source_view_id"]: row for row in _detached_relation(root, manifest, "sources")}
    references = tuple(dict.fromkeys(b.evidence for _, _, sel in enriched for b in sel.bindings))
    selected_origins = {origin for origin, _, _ in enriched} | {
        ref.origin_task_id for ref in references
    }
    if duplicates & selected_origins:
        raise ValueError("detached query context repeats an original report")
    payloads = dict(
        zip(
            references,
            _retained_contribution_payloads(
                root,
                manifest,
                [(None, ref) for ref in references],
                scopes,
                inventory,
                origin_sources=True,
                require_cut_member=True,
                origin_reports=reports,
            ),
            strict=True,
        )
    )
    selected = {}
    for (index, task, origin), report in report_inventory.items():
        if report.get("cut_member") is True and type(task) is int and index in scopes:
            selected.setdefault(origin, []).append((scopes[index], report))
    reasons = set()
    for origin, row, selection in enriched:
        source_id = row["origin_unit_id"]
        source = sources.get(source_id)
        if source is None or row.get("unit_type") != "source_view":
            raise ValueError("detached query context lacks the selected source view")
        if not any(
            scope.get("project_id") == row["project_id"]
            and scope.get("binding", {}).get("release_id") == row["body"]["release_id"]
            and member.get("origin_project_id") == row["project_id"]
            and member.get("origin_run_id") == row["origin_run_id"]
            and member.get("source_view_id") == source_id
            and member.get("runtime_fingerprint") == row["runtime_fingerprint"]
            for scope, member in selected.get(origin, ())
        ):
            raise ValueError("detached query context lacks the selected contextual report")
        ref = source["ref"]
        native = ref["native_product"]
        pin = dict(
            source=ref["key"],
            native_product_task_id=native["task_id"],
            product_key=native["product_key"],
            product_digest=native["content_digest"],
            projection_digest=ref["projection_digest"],
            recipe_digest=ref["recipe_digest"],
            source_view_id=source_id,
        )
        nodes = {node["self_ref"]: node for node in source["context"]["items"]}
        for pointer, node in tuple(nodes.items()):
            for index, cell in enumerate(node.get("data", {}).get("table_cells", ())):
                nodes[f"{pointer}/data/table_cells/{index}"] = cell
        for binding in selection.bindings:
            ref = binding.evidence
            parser = reports[ref.origin_task_id]
            if (
                (ref.project_id, ref.release_id) != (row["project_id"], row["body"]["release_id"])
                or parser["method"] != _PARSER_METHOD[selection.recipe]
                or parser["project_id"] != ref.project_id
                or parser["origin_unit_id"] != source_id
                or parser["body"].get("source") != pin["source"]
            ):
                raise ValueError("detached query context has a foreign parser origin")
            reasons.add(canonical_bytes(query_context_dependency(origin, ref)))
        _verify_receipts(
            row, selection, tuple(payloads[b.evidence] for b in selection.bindings), nodes, pin
        )
    return reasons
