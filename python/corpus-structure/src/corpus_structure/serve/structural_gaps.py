"""Bounded gap reports over exact selected producers and authorized support."""

import json
from hashlib import sha256
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
from sqlalchemy import func, select, text

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import bind_completed_result
from corpus_structure.semantic.refusals import InvalidContinuation, SemanticRefusal

GapKind = Literal[
    "unresolved_binding", "unknown_applicability_premise", "unconnected_supported_comparison"
]
Positive = Annotated[int, Field(strict=True, gt=0)]
SUCCESS = {"succeeded", "empty", "produced"}
METHODS = {
    "unresolved_binding": "retrieve.contextual",
    "unknown_applicability_premise": "structure.definitions",
    "unconnected_supported_comparison": "structure.compare",
}


class GapTask(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    task_id: Positive
    run_id: Positive
    cut_id: Positive | None = None


class GapParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    task_id: Positive
    cut_id: Positive | None = None
    source_view_id: Positive | None = None
    scope: str | None = Field(default=None, min_length=1)
    occurrence_id: str | None = Field(default=None, min_length=1)
    operation_key: str | None = Field(default=None, min_length=1)
    binding_task: GapTask | None = None
    limit: int = Field(default=20, strict=True, ge=1, le=100)
    max_bytes: int = Field(default=1_000_000, strict=True, ge=1, le=8_000_000)


class GapRequest(GapParams):
    run_id: Positive
    report: GapKind
    cursor: str | None = None

    @model_validator(mode="after")
    def selectors(self):
        if self.report != "unresolved_binding" and (self.occurrence_id or self.operation_key):
            raise ValueError("occurrence and operation selectors require the binding gap")
        if self.report != "unconnected_supported_comparison" and self.binding_task is not None:
            raise ValueError("binding producer selector requires the supported comparison gap")
        return self


class GapRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    row_id: str
    status: Literal["actionable", "unavailable"]
    reason: str
    operation: str
    outcome: str
    evidence: dict[str, JsonValue]


class GapPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["structural-gap-1"] = "structural-gap-1"
    report: GapKind
    selection: dict[str, JsonValue]
    producer: dict[str, JsonValue]
    binding_producer: dict[str, JsonValue] | None = None
    status: Literal["actionable", "empty", "unavailable", "mixed"]
    rows: tuple[GapRow, ...]
    next_cursor: str | None = None


def _task(conn, task: GapTask, expected_method: str):
    session = bind_completed_result(conn, task.run_id)
    cut_id = session.completed_cut_id
    if cut_id is None or (task.cut_id is not None and task.cut_id != cut_id):
        raise SemanticRefusal("gap selection requires its exact completed cut")
    selected, origin = table("ops.task"), table("ops.task").alias("gap_origin")
    membership, run = table("ops.cut_task"), table("ops.run")
    origin_run = run.alias("gap_origin_run")
    config, method, result = (
        table("ops.method_config"),
        table("ops.method"),
        table("ops.task_result"),
    )
    row = (
        conn.execute(
            select(
                selected.c.id.label("selected_task_id"),
                origin.c.id.label("origin_task_id"),
                run.c.project_id,
                origin_run.c.runtime_id.label("runtime_fingerprint"),
                method.c.name.label("method"),
                method.c.version.label("operation_version"),
                selected.c.status.label("task_status"),
                selected.c.unit_type,
                selected.c.unit_id,
                membership.c.task_id.is_not(None).label("cut_member"),
                result.c.body["outcome"].astext.label("operation_outcome"),
                func.left(
                    func.coalesce(
                        selected.c.error["reason"].astext, selected.c.error["message"].astext
                    ),
                    768,
                ).label("operation_reason"),
            )
            .select_from(selected)
            .join(run, run.c.id == selected.c.run_id)
            .join(origin, origin.c.id == func.coalesce(selected.c.reused_task_id, selected.c.id))
            .join(origin_run, origin_run.c.id == origin.c.run_id)
            .join(config, config.c.id == origin.c.method_config_id)
            .join(method, method.c.id == config.c.method_id)
            .outerjoin(result, result.c.task_id == origin.c.id)
            .outerjoin(
                membership,
                (membership.c.task_id == selected.c.id)
                & (membership.c.origin_task_id == origin.c.id)
                & (membership.c.cut_id == cut_id),
            )
            .where(
                selected.c.run_id == task.run_id,
                selected.c.id == task.task_id,
                selected.c.release_id == session.binding.release_id,
                origin.c.release_id == session.binding.release_id,
                method.c.name == expected_method,
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise SemanticRefusal("gap producer is outside the selected run or operation")
    return session, dict(
        **row,
        run_id=task.run_id,
        cut_id=cut_id,
        release_id=session.binding.release_id,
        result_revision=session.binding.data_revision,
    )


_BINDING_PAYLOAD = """
SELECT jsonb_build_object(
 'operations',COALESCE((SELECT jsonb_agg(
  (o-ARRAY['contextual_enrichment','computation_dependencies'])||
  jsonb_strip_nulls(jsonb_build_object(
   'dependencies',CASE WHEN o->>'question'=
    'contextual relationship selection for located occurrence'
    THEN o->'computation_dependencies' END,
   'contextual',CASE WHEN o ? 'contextual_enrichment' THEN jsonb_build_object(
    'candidate_lists',COALESCE((SELECT jsonb_agg(jsonb_build_object(
      'occurrence_id',c->'occurrence_id','list_id',c->'list_id',
      'eligible_target_count',c->'eligible_target_count',
      'candidates',jsonb_path_query_array(c,'$.candidates[*].target_id')))
     FROM jsonb_array_elements(o->'contextual_enrichment'->'candidate_lists') c
     WHERE CAST(:occurrence_id AS text) IS NULL OR c->>'occurrence_id'=:occurrence_id),'[]'),
    'decisions',COALESCE((SELECT jsonb_agg(jsonb_build_object(
      'occurrence_id',d->'occurrence_id','decision_id',d->'decision_id','scope',d->'scope',
      'outcome',d->'outcome','reason',d->'reason','exclusions',d->'exclusions',
      'unresolved_constraints',d->'unresolved_constraints'))
     FROM jsonb_array_elements(o->'contextual_enrichment'->'relationship_decisions') d
     WHERE CAST(:occurrence_id AS text) IS NULL OR d->>'occurrence_id'=:occurrence_id),'[]'),
    'section_resolutions',COALESCE((SELECT jsonb_agg(s)
     FROM jsonb_array_elements(o->'contextual_enrichment'->'section_resolutions') s
     WHERE CAST(:occurrence_id AS text) IS NULL OR s->>'occurrence_id'=:occurrence_id),'[]')
   ) END))
  ORDER BY operation.position)
  FROM kb.source_contribution_operation operation
  CROSS JOIN LATERAL (
   SELECT result.body->'contribution_operations'->(operation.position::integer) o
  ) raw
  WHERE operation.task_id=result.task_id AND (o ? 'contextual_enrichment' OR (
   operation.question='contextual relationship selection for located occurrence' AND
   (CAST(:operation_key AS text) IS NULL OR operation.operation_key=:operation_key)))),'[]'),
 'occurrences',COALESCE((SELECT jsonb_agg(jsonb_build_object(
  'id',contribution.contribution_id,'occurrence_id',contribution.occurrence_id,
  'anchors',result.body->'contributions'->(contribution.position::integer)->'anchors')
  ORDER BY contribution.position)
  FROM kb.source_contribution contribution WHERE contribution.task_id=result.task_id
  AND contribution.semantic_type='contextual.located_mention'
  AND (CAST(:occurrence_id AS text) IS NULL OR contribution.occurrence_id=:occurrence_id)),'[]')
) AS payload FROM ops.task_result result WHERE result.task_id=:origin
"""


def gap_payload_from_report(body, request, *, binding=False):
    """Reconstruct a bounded gap projection from the original producer result."""
    if binding:
        from corpus_structure.semantic.structural_products import StructuralProductReport

        product = body.get("structural_product")
        if not product or product.get("kind") != "dossier":
            return None
        dossier = product["dossier"]
        bound_sides = {
            canonical_bytes(
                {
                    "reference": member["comparison_binding"]["comparison_ref"],
                    "side": member["comparison_binding"]["side"],
                }
            )
            for member in dossier["members"]
            if member.get("comparison_binding") is not None
        }
        return {
            "product_id": StructuralProductReport.model_validate(product).product_id,
            "root": dossier.get("root_component"),
            "predecessors": dossier["predecessors"],
            "bound_sides": [json.loads(row) for row in sorted(bound_sides)],
        }
    if request.report != "unresolved_binding":
        return body.get("structural_product")
    operations = []
    for raw in body.get("contribution_operations") or ():
        operation = {
            key: value
            for key, value in raw.items()
            if key not in {"contextual_enrichment", "computation_dependencies"}
        }
        if contextual := raw.get("contextual_enrichment"):

            def selected(rows):
                return [
                    row
                    for row in rows
                    if request.occurrence_id is None
                    or row["occurrence_id"] == request.occurrence_id
                ]

            operation["contextual"] = {
                "candidate_lists": [
                    {
                        **{
                            k: c.get(k)
                            for k in ("occurrence_id", "list_id", "eligible_target_count")
                        },
                        "candidates": [candidate["target_id"] for candidate in c["candidates"]],
                    }
                    for c in selected(contextual["candidate_lists"])
                ],
                "decisions": [
                    {
                        key: row[key]
                        for key in (
                            "occurrence_id",
                            "decision_id",
                            "scope",
                            "outcome",
                            "reason",
                            "exclusions",
                            "unresolved_constraints",
                        )
                        if row.get(key) is not None
                    }
                    for row in selected(contextual["relationship_decisions"])
                ],
                "section_resolutions": selected(contextual.get("section_resolutions", ())),
            }
        elif (
            raw["question"] == "contextual relationship selection for located occurrence"
            and request.operation_key in (None, raw["operation_key"])
        ):
            operation["dependencies"] = raw["computation_dependencies"]
        else:
            continue
        operations.append(operation)
    return {
        "operations": operations,
        "occurrences": [
            {
                "id": row["contribution_id"],
                "occurrence_id": row["occurrence_id"],
                "anchors": row["anchors"],
            }
            for row in body.get("contributions") or ()
            if row["semantic_type"] == "contextual.located_mention"
            and request.occurrence_id in (None, row["occurrence_id"])
        ],
    }


def _read_payload(conn, producer, request, *, binding=False):
    if not producer["cut_member"] or producer["task_status"] not in {"done", "reused", "empty"}:
        return None
    if request.report == "unresolved_binding" and not binding:
        parameters = dict(
            origin=producer["origin_task_id"],
            occurrence_id=request.occurrence_id,
            operation_key=request.operation_key,
        )
        source = _BINDING_PAYLOAD
    else:
        parameters = dict(origin=producer["origin_task_id"])
        source = (
            "SELECT body->'structural_product' AS payload "
            "FROM ops.task_result WHERE task_id=:origin"
        )
        if binding:
            source = """
            SELECT jsonb_build_object(
              'product_id','structural:'||encode(sha256(convert_to(data.canonical_json(report-'retrieval_report'),'UTF8')),'hex'),
              'root',report->'dossier'->'root_component',
              'predecessors',report->'dossier'->'predecessors',
              'bound_sides',COALESCE((SELECT
                 jsonb_agg(DISTINCT jsonb_build_object(
                  'reference',member->'comparison_binding'->'comparison_ref',
                  'side',member->'comparison_binding'->'side'))
                 FROM jsonb_array_elements(report->'dossier'->'members') member
                 WHERE jsonb_typeof(member->'comparison_binding')='object'),'[]')) AS payload
            FROM (SELECT body->'structural_product' report
                 FROM ops.task_result WHERE task_id=:origin) retained
            WHERE report->>'kind'='dossier'
            """
    length = conn.scalar(
        text(f"SELECT octet_length(payload::text) FROM ({source}) gap"), parameters
    )
    if length is None:
        return None
    if length > request.max_bytes:
        raise SemanticRefusal("gap evidence exceeds byte budget; narrow the selection")
    return conn.scalar(text(source), parameters)


def _gap(status, reason, operation, outcome, **evidence):
    value = dict(
        status=status, reason=reason, operation=operation, outcome=outcome, evidence=evidence
    )
    return GapRow(row_id=sha256(canonical_bytes(value)).hexdigest(), **value)


def _unresolved(payload, request):
    phases = {}
    by_digest = {}
    by_dependency = {}
    contextual = []
    for operation in payload["operations"]:
        if operation.get("contextual") is not None:
            contextual.append(operation["contextual"])
        elif operation["question"] == "contextual relationship selection for located occurrence":
            key = operation["operation_key"]
            phases[key] = operation
            if digest := operation.get("report_digest"):
                by_digest.setdefault(digest, set()).add(key)
            for dependency in operation.get("dependencies", ()):
                by_dependency.setdefault(dependency, set()).add(key)
    chosen: dict[tuple[str, ...], GapRow] = {}
    selected_operation_matches = False
    for product in contextual:
        decisions = {d["occurrence_id"]: d for d in product["decisions"]}
        candidates = {c["occurrence_id"]: c for c in product["candidate_lists"]}
        resolutions = {r["occurrence_id"]: r for r in product["section_resolutions"]}
        for occurrence in payload["occurrences"]:
            key = occurrence["occurrence_id"]
            decision, candidate, resolution = (
                decisions.get(key),
                candidates.get(key),
                resolutions.get(key),
            )
            if decision and request.scope is not None and decision["scope"] != request.scope:
                continue
            matching = set(by_dependency.get(occurrence["id"], ()))
            if candidate:
                matching.update(by_dependency.get(candidate["list_id"], ()))
            if decision:
                matching.update(by_digest.get(decision["decision_id"].rsplit(":", 1)[-1], ()))
            if request.operation_key is not None:
                matching.intersection_update({request.operation_key})
                selected_operation_matches |= bool(matching)
            if not matching:
                if request.operation_key is None:
                    chosen[(key, occurrence["id"])] = _gap(
                        "unavailable",
                        "binding_operation_unavailable",
                        "relationship_selection",
                        "not_run",
                        occurrence_id=key,
                        cue=occurrence["anchors"],
                    )
                continue
            for operation in matching:
                phase = phases[operation]
                evidence = dict(
                    occurrence_id=key,
                    cue=occurrence["anchors"],
                    candidates=candidate["candidates"] if candidate else [],
                    eligible_target_count=candidate["eligible_target_count"] if candidate else None,
                    exclusions=decision.get("exclusions", []) if decision else [],
                )
                outcome = phase["outcome"]
                if outcome not in SUCCESS or decision is None:
                    row = _gap(
                        "unavailable",
                        "binding_operation_unavailable",
                        operation,
                        outcome,
                        **evidence,
                        operation_reason=phase.get("reason"),
                    )
                elif decision["outcome"] == "selected":
                    continue
                else:
                    result = decision["outcome"]
                    route = resolution.get("outcome") if resolution else None
                    if route == "unavailable_representation":
                        reason = "missing_representation"
                    elif result == "ambiguous" or route == "ambiguous":
                        reason = "ambiguous_candidates"
                    elif route == "no_compatible_candidate" or (
                        candidate is not None and candidate["eligible_target_count"] == 0
                    ):
                        reason = "no_eligible_target"
                    else:
                        reason = "insufficient_evidence"
                    row = _gap(
                        "unavailable" if route == "unavailable_representation" else "actionable",
                        reason,
                        operation,
                        result,
                        **evidence,
                        decision_id=decision["decision_id"],
                        decision_reason=decision.get("reason"),
                        route_outcome=route,
                        unresolved_constraints=decision.get("unresolved_constraints", []),
                    )
                chosen[(key, occurrence["id"], operation)] = row
    if request.operation_key is not None and request.operation_key not in phases:
        raise SemanticRefusal("binding operation is outside the selected producer")
    if (
        request.operation_key is not None
        and request.occurrence_id is not None
        and phases[request.operation_key]["outcome"] in SUCCESS
        and not selected_operation_matches
    ):
        raise SemanticRefusal("binding operation did not inspect the selected occurrence")
    if (
        request.operation_key is not None
        and not chosen
        and phases[request.operation_key]["outcome"] not in SUCCESS
    ):
        phase = phases[request.operation_key]
        return [
            _gap(
                "unavailable",
                "binding_operation_unavailable",
                request.operation_key,
                phase["outcome"],
                operation_reason=phase.get("reason"),
            )
        ]
    if not contextual:
        return [
            _gap(
                "unavailable", "contextual_product_unavailable", "relationship_selection", "not_run"
            )
        ]
    if request.occurrence_id is not None and not payload["occurrences"]:
        raise SemanticRefusal("binding occurrence is outside the selected producer")
    return list(chosen.values())


def _structural_source(report, request):
    if request.source_view_id is not None and not any(
        source.source_view_id == request.source_view_id for source in report.inputs.sources
    ):
        raise SemanticRefusal("gap source is outside the selected structural inputs")
    if request.scope is not None and request.scope != report.inputs.scope:
        raise SemanticRefusal("gap scope differs from the selected structural inputs")


def _unknown(report, producer, request):
    definition = report.definition
    if definition is None:
        return [
            _gap("unavailable", "applicability_product_unavailable", producer["method"], "not_run")
        ]
    passage = next(p for p in report.inputs.passages if p.passage_id == definition.usage_id)
    source = next(s for s in report.inputs.sources if s.identity == passage.source_ref)
    if request.source_view_id is not None and request.source_view_id != source.source_view_id:
        raise SemanticRefusal("gap source differs from the selected usage occurrence")
    passages = {p.passage_id: p.model_dump(mode="json") for p in report.inputs.passages}
    return [
        _gap(
            "actionable",
            premise.reason,
            producer["method"],
            reading.outcome,
            dimension=premise.dimension,
            state=premise.state,
            source=source.model_dump(mode="json"),
            usage=passages[definition.usage_id],
            cited_passages=[passages[key] for key in premise.evidence],
            component_ref=reading.component_ref.model_dump(mode="json"),
            relationship_ref=reading.link_ref.model_dump(mode="json"),
        )
        for reading in definition.readings
        for premise in reading.premises
        if premise.state in {"unknown", "incompatible"}
    ]


def _supported_comparison(report, producer, binding, binding_producer, support, request):
    def unavailable(reason, outcome):
        return [_gap("unavailable", reason, producer["method"], outcome)]

    if not support:
        return unavailable("authorized_comparison_support_unavailable", "not_available")
    comparison = report.comparison
    reference = dict(
        product_id=report.product_id,
        **{
            key: producer[key]
            for key in (
                "project_id",
                "run_id",
                "cut_id",
                "release_id",
                "result_revision",
                "selected_task_id",
                "origin_task_id",
                "runtime_fingerprint",
            )
        },
    )
    if binding is None:
        if (
            binding_producer is not None
            and binding_producer.get("comparison_binding_available") is False
        ):
            return unavailable("binding_production_unavailable", "unsupported_release")
        return unavailable(
            "binding_production_unavailable",
            binding_producer["task_status"] if binding_producer else "not_run",
        )
    if reference not in binding["predecessors"]:
        return unavailable("comparison_outside_binding_selection", "not_inspected")
    bound_sides = {
        entry["side"] for entry in binding.get("bound_sides", ()) if entry["reference"] == reference
    }
    # Older captured projections recorded comparison-level membership only.
    if comparison is None:
        raise ValueError("selected supported product lacks comparison")
    passages = {p.passage_id: p for p in report.inputs.passages}
    sources = {s.identity: s for s in report.inputs.sources}
    selected_sides = {}
    for side, passage_id, reading in (
        ("left", comparison.left_id, comparison.left_reading),
        ("right", comparison.right_id, comparison.right_reading),
    ):
        passage = passages[passage_id]
        source = sources[passage.source_ref]
        if request.source_view_id not in (None, source.source_view_id):
            continue
        selected_sides[side] = dict(
            passage=passage.model_dump(mode="json"),
            source=source.model_dump(mode="json"),
            reading=reading.model_dump(mode="json") if reading else None,
        )
    if not selected_sides:
        raise SemanticRefusal("gap source does not identify a selected comparison side")
    sides = {side: row for side, row in selected_sides.items() if side not in bound_sides}
    if reference in binding.get("bound", ()) or not sides:
        return []
    return [
        _gap(
            "actionable",
            "no_qualifying_root_binding",
            producer["method"],
            "produced",
            comparison=reference,
            sides=sides,
            support=support,
            root=binding["root"],
            binding_product_id=binding["product_id"],
            binding_status="inspected_no_binding",
        )
    ]


def gap_rows(request, producer, payload, binding_producer, binding_payload, support):
    """Replay a selected gap from the producer projection captured by the ordinary reader."""
    from corpus_structure.semantic.structural_products import StructuralProductReport

    if (
        request.report == "unconnected_supported_comparison"
        and payload is None
        and producer.get("support_unavailable")
    ):
        return [
            _gap(
                "unavailable",
                "authorized_comparison_support_unavailable",
                producer["method"],
                "not_available",
            )
        ]
    if payload is None:
        return [
            _gap(
                "unavailable",
                "selected_operation_unavailable",
                producer["method"],
                producer["operation_outcome"] or producer["task_status"],
                operation_reason=producer.get("operation_reason"),
            )
        ]
    if request.report == "unresolved_binding":
        return _unresolved(payload, request)
    report = StructuralProductReport.model_validate(payload)
    _structural_source(report, request)
    if request.report == "unknown_applicability_premise":
        return _unknown(report, producer, request)
    return _supported_comparison(
        report, producer, binding_payload, binding_producer, support, request
    )


def gap_capture(conn, request):
    session, producer = _task(
        conn,
        GapTask(run_id=request.run_id, cut_id=request.cut_id, task_id=request.task_id),
        METHODS[request.report],
    )
    if (
        producer["unit_type"] == "source_view"
        and request.source_view_id is not None
        and producer["unit_id"] != request.source_view_id
    ):
        raise SemanticRefusal("gap source differs from the selected producer")
    payload = _read_payload(conn, producer, request)
    if (
        payload
        and request.report != "unresolved_binding"
        and payload.get("version") != "structural-product-3"
    ):
        payload = None
        producer["operation_outcome"] = "unsupported_release"
        producer["operation_reason"] = "retained structural report uses an earlier contract"
    binding_producer = binding_payload = None
    support = []
    if request.report == "unconnected_supported_comparison" and payload:
        from corpus_structure.semantic.structural_admission import (
            read_structural_assertions,
            structural_claim_id,
            structural_statement,
        )
        from corpus_structure.semantic.structural_products import StructuralProductReport

        report = StructuralProductReport.model_validate(payload)
        _structural_source(report, request)
        if "StructuralPublicationPolicy" in session.prepared.index.definitions:
            claim_id = structural_claim_id(structural_statement(report))
            support = [
                dict(assertion_id=row["assertion_id"], claim_id=row["claim_id"])
                for row in read_structural_assertions(
                    conn,
                    release_id=session.binding.release_id,
                    realization_id=session.binding.realization_id,
                    product_ids=(report.product_id,),
                    max_bytes=request.max_bytes,
                )
                if row["cut_id"] == producer["cut_id"]
                and row["selected_task_id"] == producer["selected_task_id"]
                and row["origin_task_id"] == producer["origin_task_id"]
                and row["claim_id"] == claim_id
            ]
        if not support:
            payload = None
            producer["support_unavailable"] = True
    if request.binding_task is not None:
        binding_session, binding_producer = _task(conn, request.binding_task, "structure.dossier")
        binding_capable = "DossierComparisonBinding" in binding_session.prepared.index.definitions
        binding_producer["comparison_binding_available"] = binding_capable
        if support and binding_capable:
            binding_payload = _read_payload(conn, binding_producer, request, binding=True)
    return dict(
        producer=producer,
        payload=payload,
        binding_producer=binding_producer,
        binding_payload=binding_payload,
        support=support,
    )


_CUSTODY_FIELDS = (
    "run_id",
    "cut_id",
    "project_id",
    "release_id",
    "result_revision",
    "selected_task_id",
    "origin_task_id",
    "runtime_fingerprint",
    "method",
)


def gap_review_custody(conn, captured, budget):
    """Export original producer records and only the authorized assertion statement."""
    from corpus_structure.semantic.structural_admission import read_structural_assertions
    from corpus_structure.semantic.structural_products import StructuralProductReport

    results = table("ops.task_result")
    raw = {}
    bindings = {}
    for name, producer in (
        ("producer", captured["producer"]),
        ("binding", captured["binding_producer"]),
    ):
        body = None
        bindings[name] = None
        if producer:
            _, bound = _task(
                conn,
                GapTask(
                    run_id=producer["run_id"],
                    cut_id=producer["cut_id"],
                    task_id=producer["selected_task_id"],
                ),
                producer["method"],
            )
            bindings[name] = {key: bound[key] for key in _CUSTODY_FIELDS}
        if (
            producer
            and producer["cut_member"]
            and producer["task_status"] in {"done", "reused", "empty"}
        ):
            query = select(results.c.body).where(results.c.task_id == producer["origin_task_id"])
            budget.preflight(conn, query)
            body = conn.scalar(query)
        raw[name] = body
    assertions = []
    if captured["support"]:
        producer = captured["producer"]
        session = bind_completed_result(conn, producer["run_id"])
        product = StructuralProductReport.model_validate(captured["payload"])
        ids = {row["assertion_id"] for row in captured["support"]}
        assertions = [
            {key: row[key] for key in ("assertion_id", "claim_id", "statement")}
            for row in read_structural_assertions(
                conn,
                release_id=session.binding.release_id,
                realization_id=session.binding.realization_id,
                product_ids=(product.product_id,),
                support=True,
            )
            if row["assertion_id"] in ids
            and row["cut_id"] == producer["cut_id"]
            and row["selected_task_id"] == producer["selected_task_id"]
            and row["origin_task_id"] == producer["origin_task_id"]
        ]
    return {"bodies": raw, "bindings": bindings, "assertions": assertions}


def gap_review_source_ids(custody):
    selected = set()
    for body in custody["bodies"].values():
        if not body:
            continue
        product = body.get("structural_product") or {}
        selected.update(
            row["source_view_id"] for row in product.get("inputs", {}).get("sources", ())
        )
        selected.update(
            row["pin"]["source_view_id"]
            for row in body.get("contributions") or ()
            if row.get("pin", {}).get("source_view_id") is not None
        )
    return selected


def _verify_gap_source_pins(bodies, sources):
    for body in bodies.values():
        if not body:
            continue
        product = body.get("structural_product") or {}
        inputs = product.get("inputs", {})
        by_identity = {}
        for pin in inputs.get("sources", ()):
            source = sources[pin["source_view_id"]]
            ref = source["ref"]
            if (ref["projection_digest"], ref["recipe_digest"], ref["native_product"]) != (
                pin["projection_digest"],
                pin["recipe_digest"],
                {
                    "task_id": pin["native_task_id"],
                    "product_key": pin["native_product_key"],
                    "content_digest": pin["native_content_digest"],
                },
            ):
                raise ValueError("detached gap source differs from the original structural pin")
            by_identity[sha256(canonical_bytes(pin)).hexdigest()] = source["text"]
        for passage in inputs.get("passages", ()):
            text = by_identity.get(passage["source_ref"])
            if text is None or text[passage["start"] : passage["end"]] != passage["text"]:
                raise ValueError("detached gap passage differs from the original projected text")
        for row in body.get("contributions") or ():
            pin = row.get("pin", {})
            if (view_id := pin.get("source_view_id")) is None:
                continue
            ref = sources[view_id]["ref"]
            if (ref["projection_digest"], ref["recipe_digest"], ref["native_product"]) != (
                pin["projection_digest"],
                pin["recipe_digest"],
                {
                    "task_id": pin["native_product_task_id"],
                    "product_key": pin["product_key"],
                    "content_digest": pin["product_digest"],
                },
            ):
                raise ValueError("detached gap occurrence differs from the original source pin")


def verify_gap_review_custody(captured, custody, request, sources=None):
    from corpus_structure.semantic.structural_admission import (
        structural_claim_id,
        structural_statement,
    )
    from corpus_structure.semantic.structural_products import StructuralProductReport

    bodies = custody["bodies"]
    if "bindings" in custody:
        if sources is None or not gap_review_source_ids(custody) <= sources.keys():
            raise ValueError("detached gap is missing its original source views")
        _verify_gap_source_pins(bodies, sources)
        for name, producer in (
            ("producer", captured["producer"]),
            ("binding", captured["binding_producer"]),
        ):
            expected_binding = {key: producer[key] for key in _CUSTODY_FIELDS} if producer else None
            if custody["bindings"][name] != expected_binding:
                raise ValueError("detached gap origin differs from the selected cut")
            if bodies[name] is not None and (
                producer is None or bodies[name].get("method") != producer["method"]
            ):
                raise ValueError("detached gap report differs from its selected producer method")
    body = bodies["producer"]
    expected = gap_payload_from_report(body, request) if body is not None else None
    missing_support = (
        request.report == "unconnected_supported_comparison" and not custody["assertions"]
    )
    if (
        request.report != "unresolved_binding"
        and expected is not None
        and (expected.get("version") != "structural-product-3" or missing_support)
    ):
        expected = None
    if expected != captured["payload"]:
        raise ValueError("detached gap payload differs from the original producer report")
    expected_support = []
    if custody["assertions"]:
        statement = structural_statement(StructuralProductReport.model_validate(expected))
        claim = structural_claim_id(statement)
        for row in custody["assertions"]:
            if row["statement"] != statement or row["claim_id"] != claim:
                raise ValueError("detached gap support differs from the original comparison")
            expected_support.append({"assertion_id": row["assertion_id"], "claim_id": claim})
    if expected_support != captured["support"]:
        raise ValueError("detached gap support differs from the authorized assertion projection")
    expected_binding = None
    if (
        bodies["binding"] is not None
        and expected_support
        and (captured["binding_producer"]["comparison_binding_available"])
    ):
        expected_binding = gap_payload_from_report(bodies["binding"], request, binding=True)
    binding = captured["binding_payload"]
    if expected_binding is not None and binding is not None:
        expected_binding["bound_sides"] = sorted(
            expected_binding["bound_sides"], key=canonical_bytes
        )
        binding = {**binding, "bound_sides": sorted(binding["bound_sides"], key=canonical_bytes)}
    if expected_binding != binding:
        raise ValueError("detached gap binding differs from the original dossier report")


def gap_page(request: GapRequest, captured) -> GapPage:
    rows = sorted(gap_rows(request, **captured), key=lambda row: row.row_id)
    selection = request.model_dump(mode="json", exclude={"cursor", "limit", "max_bytes"})
    producer, binding = captured["producer"], captured["binding_producer"]
    digest = sha256(
        canonical_bytes(dict(selection=selection, producer=producer, binding=binding))
    ).hexdigest()
    after = None
    if request.cursor is not None:
        prefix, _, after = request.cursor.partition(".")
        if prefix != digest or after not in {row.row_id for row in rows}:
            raise InvalidContinuation(
                "gap continuation differs from exact selected report and scope"
            )
    remaining = [row for row in rows if after is None or row.row_id > after]
    chosen = remaining[: request.limit]
    statuses = {row.status for row in rows}
    page = GapPage(
        report=request.report,
        selection=selection,
        producer=producer,
        binding_producer=binding,
        status="empty" if not statuses else next(iter(statuses)) if len(statuses) == 1 else "mixed",
        rows=tuple(chosen),
        next_cursor=f"{digest}.{chosen[-1].row_id}" if len(remaining) > request.limit else None,
    )
    if len(canonical_bytes(page.model_dump(mode="json"))) > request.max_bytes:
        raise SemanticRefusal("gap response exceeds byte budget; narrow the page")
    return page


def serve_structural_gap(conn, request: GapRequest) -> GapPage:
    return gap_page(request, gap_capture(conn, request))
