"""Model-bound explanations, declared impact and located existing-validator reports.

Report construction validates against the trusted report model. These read-only observations
never authorize effects or establish equivalence of arbitrary implementation behavior.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, JsonValue

from corpus_structure.model.compiled import model_projection, model_source
from corpus_structure.semantic.database_failures import DATABASE_ERRORS

from .identity import canonical_bytes
from .refusal_types import SemanticRefusal
from .refusals import trusted_operation_model_id
from .types import Diagnostic, PreparedRelease

if TYPE_CHECKING:
    from .data_operation_runtime import RuntimeBinding
    from .demand_queries import DemandQueryRequest

_REPORT_VERSIONS = {
    "OperationExplanation": 3,
    "LocatedValidationReport": 5,
    "SemanticImpactReport": 5,
    "ContractInspection": 3,
}
_SCHEMA_NAMES = tuple(_REPORT_VERSIONS)
_SCHEMA_PATH = "model/semantic/operation-report-schemas.json"


class _ReportSchemaProduct(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    profile: Literal["operation-report-schema-2"]
    source_id: str
    schemas: dict[str, dict[str, JsonValue]]


def _report_schema_source_id() -> str:
    from .types import BOUNDARY_ABI_VERSION, SEMANTIC_COMPILER_VERSION

    return sha256(
        canonical_bytes(
            dict(
                sources={source.name: source.digest for source in _report_sources().sources},
                compiler=SEMANTIC_COMPILER_VERSION,
                boundary=BOUNDARY_ABI_VERSION,
                pydantic=version("pydantic"),
                linkml_runtime=version("linkml-runtime"),
            )
        )
    ).hexdigest()


@model_projection
def _report_schemas() -> _ReportSchemaProduct:
    from pydantic import ValidationError

    try:
        product = _ReportSchemaProduct.model_validate_json(
            model_source("operation-report-schemas.json")
        )
    except (OSError, ValidationError) as exc:
        raise SemanticRefusal(
            "Report schema product unavailable; run "
            "python -m corpus_structure.semantic.operation_reporting"
        ) from exc
    if product.source_id != _report_schema_source_id() or set(product.schemas) != set(
        _SCHEMA_NAMES
    ):
        raise SemanticRefusal(
            "Report schema product differs from its source; run "
            "python -m corpus_structure.semantic.operation_reporting"
        )
    return product


if TYPE_CHECKING:
    from sqlalchemy import Connection

    from .ontology import GraphValidation
    from .types import SourceBundle


@model_projection
def _report_sources() -> SourceBundle:
    """Registration and invocation share one immutable process-owned source closure."""
    from .data_product_reference import reference_inputs
    from .types import SourceArtifact, SourceBundle

    modules = ("operation-reports", "pdf-products", "observations", "characterization", "core")
    bundle = SourceBundle(
        "report_root",
        (
            *(
                SourceArtifact(name.replace("-", "_"), model_source(name + ".yaml"))
                for name in modules
            ),
            SourceArtifact(
                "pdf-observation-vocabulary",
                model_source("pdf-observation-vocabulary.yaml"),
            ),
            SourceArtifact(
                "report_root",
                b"id: urn:corpus:report-boundary\nname: report_boundary\nimports: [operation_reports, pdf_products, observations, characterization, core]\n",
            ),
        ),
    )

    return reference_inputs(bundle)


@model_projection
def _report_model() -> tuple[PreparedRelease, str]:
    from .prepare import prepare_release

    boundary = prepare_release(_report_sources())
    return boundary, boundary.release_id


def _report(name: str, data: dict) -> BaseModel:
    boundary, digest = _report_model()

    def supplied(value):
        if isinstance(value, dict):
            return {key: supplied(item) for key, item in value.items() if item is not None}
        if isinstance(value, (tuple, list)):
            return [supplied(item) for item in value]
        return value

    return boundary.validate_json(
        name,
        canonical_bytes(
            supplied(
                dict(
                    report_version=_REPORT_VERSIONS[name],
                    report_schema_digest=digest,
                    **data,
                )
            )
        ),
    )


def explain_operation(
    prepared: PreparedRelease,
    operation: str,
    *,
    connection: Connection | None = None,
    observation: DemandQueryRequest | None = None,
) -> BaseModel:
    """Explain the captured DDO definition and optional actual selected frontier.

    Binding reasons come from the owning native/planner result. This projection
    neither reruns a competing applicability classifier nor authorizes execution.
    """
    from .data_operation_admission import bound_data_operation_model
    from .data_operation_json import json_bytes
    from .demand_queries import serve_demand_query
    from .native_definition_projection import read_native_definition_projection

    model = bound_data_operation_model(prepared)
    try:
        found = model.operation(operation)
    except StopIteration as exc:
        raise SemanticRefusal(
            "operation is not declared by this current release: " + operation
        ) from exc
    projection = read_native_definition_projection(prepared, model=model)
    native = next(row for row in projection["operations"] if row["operation_id"] == operation)
    selected = None
    if observation is not None:
        if (
            connection is None
            or observation.view != "operations"
            or observation.operation_id != operation
        ):
            raise ValueError(
                "operation observation requires its exact selected native operation query"
            )
        selected = serve_demand_query(connection, observation)
        if selected["cut"]["release_id"] != prepared.release_id:
            raise ValueError("operation observation belongs to another release")
    return _report(
        "OperationExplanation",
        dict(
            release_id=prepared.release_id,
            model_digest=projection["model_digest"],
            operation=operation,
            profile=found.profile,
            subject_definition=found.subject,
            definition=native["definition"],
            recipe=native["recipe"],
            eligibility=native["eligibility"],
            implementation_revision=native["implementation_revision"],
            declaration_json=found.definition.decode(),
            eligibility_json=found.eligibility.decode(),
            binding_json=canonical_bytes(native["binding"]).decode(),
            support_json=canonical_bytes(native["support_contract"]).decode(),
            precision_description=found.precision_description,
            coverage_description=found.coverage.description,
            observation_status="not_requested" if selected is None else "observed",
            observation_json=None if selected is None else json_bytes(selected).decode(),
            complete=selected is None or selected["page_complete"],
            authority="declaration_and_observation_only",
        ),
    )


def unavailable_validation_evidence(report, reason: str):
    """Project unavailable optional custody without changing validation meaning or disclosure."""
    fields = report.model_dump(mode="json", exclude={"report_version", "report_schema_digest"})
    evidence = fields.get("evidence") or {}
    fields["evidence"] = dict(
        kind="marker",
        engine=evidence.get("engine", "boundary"),
        media_type=evidence.get("media_type", "application/json"),
        sensitivity=evidence.get("sensitivity", "safe"),
        reason=reason,
    )
    limits = fields["presentation"]
    return _validation_presentation(
        fields,
        detail="correction_detail" in fields,
        max_errors=limits["max_errors"],
        max_depth=limits["max_depth"],
        max_bytes=limits["max_bytes"],
    )


def _validation_presentation(data, *, detail=False, max_errors=100, max_depth=8, max_bytes=262144):
    """Bound the complete report, preserving assessment independently of rendering."""
    from pydantic import MISSING

    from .correction_detail import _detail_limits

    _detail_limits(max_errors, max_depth, max_bytes)
    data = deepcopy(data)
    observations = data["observations"]
    original_count = len(observations)
    categories = {item["category"] for item in observations}
    data.setdefault(
        "validation_outcome",
        (
            "invalid_shape"
            if "invalid_shape" in categories
            else "execution_failure"
            if "validator_failure" in categories
            else "nonconformant"
            if categories & {"invalid_input", "state_violation"}
            else "unassessed"
            if "unassessed" in categories
            else "conformant"
        ),
    )
    correction = data.get("correction_detail")
    coverage = data.get("presentation") or dict(
        examined_count=correction["examined_count"] if correction else len(observations),
        inventory_complete=correction["inventory_complete"] if correction else True,
        render_complete=correction["render_complete"] if correction else True,
        coverage_note="Examined counts captured/yielded facts, not internal validator work.",
    )
    nodes = correction["nodes"] if correction else []
    # Native/schema captures supply the ordered forest. Observations mirror its roots.
    if nodes:
        roots = sum(node.get("parent") is None for node in nodes)
        observations[:] = observations[:roots]
    else:
        observations[:] = observations[:max_errors]
    if len(data["observations"]) < original_count:
        coverage["render_complete"] = False
    if correction and not nodes and coverage["examined_count"]:
        observations.clear()
        coverage["render_complete"] = False
    if len(observations) < coverage["examined_count"] and not nodes:
        coverage["render_complete"] = False
    coverage.update(max_errors=max_errors, max_depth=max_depth, max_bytes=max_bytes)
    data["presentation"] = coverage
    if not detail:
        data.pop("correction_detail", None)
    if correction:
        correction["render_complete"] = coverage["render_complete"]
    # Normalize once through the trusted declaration. Every later candidate is a
    # typed subset of these validated facts, so serialization (including generated
    # defaults and omission rules) stays owned by the actual boundary model.
    report: Any = _report("LocatedValidationReport", data)

    def fits(candidate):
        return (
            len(canonical_bytes(candidate.model_dump(mode="json", exclude_none=True))) <= max_bytes
        )

    if fits(report):
        return report
    evidence = getattr(report, "evidence", None)
    evidence = None if evidence is MISSING else evidence
    marker = evidence
    if evidence is not None and getattr(evidence, "content", MISSING) is not MISSING:
        marker = evidence.model_copy(
            update=dict(
                kind="marker",
                content=MISSING,
                reason="Inline evidence exceeds presentation budget.",
            )
        )
    selected_detail = getattr(report, "correction_detail", None)
    selected_detail = None if selected_detail is MISSING else selected_detail
    selected_nodes = selected_detail.nodes if selected_detail is not None else ()
    selected_observations = report.observations
    # A preorder prefix is parent-closed. The root index couples observations to
    # exactly the retained roots without rescanning the forest for each probe.
    root_counts = [0]
    for node in selected_nodes:
        root_counts.append(root_counts[-1] + (getattr(node, "parent", MISSING) is MISSING))
    total = len(selected_nodes) if detail and selected_nodes else len(selected_observations)

    def prefix(count):
        roots = root_counts[count] if detail and selected_nodes else count
        updates = dict(
            observations=selected_observations[:roots],
            presentation=report.presentation.model_copy(update=dict(render_complete=False)),
        )
        if marker is not None:
            updates["evidence"] = marker
        if selected_detail is not None:
            updates["correction_detail"] = selected_detail.model_copy(
                update=dict(
                    nodes=selected_nodes[:count],
                    render_complete=False,
                )
            )
        return report.model_copy(update=updates)

    # Evidence removal may suffice. Otherwise only serialized facts participate
    # in the search: compact views never step through hidden child nodes.
    whole = prefix(total)
    if fits(whole):
        return whole
    best = prefix(0)
    if not fits(best):
        error = SemanticRefusal("validation presentation binding exceeds requested byte limit")
        error.__dict__["validation_outcome"] = data["validation_outcome"]
        raise error
    low, high = 0, total
    while low + 1 < high:
        middle = (low + high) // 2
        candidate = prefix(middle)
        if fits(candidate):
            low, best = middle, candidate
        else:
            high = middle
    return best


def validation_report(
    diagnostics: tuple[Diagnostic, ...],
    *,
    prepared: PreparedRelease | None = None,
    operation: str | None = None,
    raw_evidence: bool = False,
    projection_dependencies: dict[str, Any] | None = None,
    detail: bool = False,
    max_errors: int = 100,
    max_depth: int = 8,
    max_bytes: int = 262144,
) -> BaseModel:
    categories = {
        "invalid": "invalid_input",
        "unsupported": "unassessed",
        "unresolved": "unassessed",
        "unchecked": "unassessed",
        "advisory": "unassessed",
    }
    from .correction_detail import preparation_diagnostic

    observations = [
        dict(
            category=categories[item.outcome],
            code=item.code,
            model_path=item.contract_id or item.location,
            input_path=item.location,
            operation=operation or item.consumer,
            scope="preparation",
            message=preparation_diagnostic(item, raw_evidence=raw_evidence)["message"],
            expected=item.expected if raw_evidence else None,
            actual=item.actual if raw_evidence else None,
            remedy=item.remedy,
        )
        for item in diagnostics
    ]
    return _validation_presentation(
        dict(
            release_id=prepared.release_id if prepared else None,
            model_id=trusted_operation_model_id(prepared) if prepared else None,
            observations=observations,
            evidence=dict(
                kind="marker",
                engine="preparation",
                media_type="application/json",
                sensitivity="raw" if raw_evidence else "safe",
                reason="Located model diagnostics; no managed raw evidence is established.",
            ),
            projection_dependencies=projection_dependencies,
            complete=all(
                item.outcome not in {"unsupported", "unresolved", "unchecked", "advisory"}
                for item in diagnostics
            ),
        ),
        detail=detail,
        max_errors=max_errors,
        max_depth=max_depth,
        max_bytes=max_bytes,
    )


_NO_MEMBER = object()


def _changed_members(before: Any, after: Any, model_path: str) -> list[dict[str, Any]]:
    """Compare normalized facts; named model members retain their declared identity."""
    from .observations import source_value

    def part(value: str) -> str:
        return value.replace("~", "~0").replace("/", "~1")

    def named(values, key):
        if not all(
            isinstance(value, Mapping) and isinstance(value.get(key), str) for value in values
        ):
            return None
        result = {value[key]: value for value in values}
        return result if len(result) == len(values) else None

    def visit(left, right, path):
        if left is not _NO_MEMBER and right is not _NO_MEMBER and left == right:
            return []
        if isinstance(left, Mapping) and isinstance(right, Mapping):
            return [
                change
                for key in sorted(left.keys() | right.keys())
                for change in visit(
                    left.get(key, _NO_MEMBER), right.get(key, _NO_MEMBER), path + "/" + part(key)
                )
            ]
        # Named collections follow the normalized compiler product's identities.
        # Other collections remain ordered values, with multiplicity preserved.
        member_key = {
            "properties": "name",
            "attributes": "name",
            "result_dimensions": "id",
            "calls": "id",
            "parameters": "name",
            "result_fields": "name",
            "records": "name",
            "fields": "name",
            "endpoints": "role",
            "dimensions": "id",
            "states": "id",
            "demands": "id",
            "ownership": "id",
        }.get(path.rsplit("/", 1)[-1])
        if member_key and isinstance(left, (tuple, list)) and isinstance(right, (tuple, list)):
            old, new = named(left, member_key), named(right, member_key)
            if old is not None and new is not None and tuple(old) == tuple(new):
                return [
                    change
                    for key in sorted(old.keys() | new.keys())
                    for change in visit(
                        old.get(key, _NO_MEMBER), new.get(key, _NO_MEMBER), path + "/" + part(key)
                    )
                ]
            # Membership changes carry position too: [a] -> [b,a] differs
            # from [a] -> [a,b], even though surviving members keep order.
            # Retain the actual sequence rather than inventing position facts.
        value: dict[str, Any] = dict(
            kind="added" if left is _NO_MEMBER else "removed" if right is _NO_MEMBER else "changed",
            model_path=path,
        )
        if left is not _NO_MEMBER:
            value["before"] = source_value(left)
        if right is not _NO_MEMBER:
            value["after"] = source_value(right)
        return [value]

    return visit(before, after, model_path)


def compare_semantic_releases(
    before: PreparedRelease,
    after: PreparedRelease,
    *,
    before_runtime: RuntimeBinding | None = None,
    after_runtime: RuntimeBinding | None = None,
    dependency_detail: bool = False,
) -> BaseModel:
    """Compare current captured meaning, keeping source, runtime and use limits explicit."""
    from .alias_policy import released_alias_product
    from .data_operation_admission import bound_data_operation_model
    from .data_operation_runtime import validate_data_operation_runtime
    from .model_comparison import compare_declared_models
    from .projection_analysis_products import compare_retained_projection_analysis
    from .vocabulary_impact import append_vocabulary_impact

    models = (bound_data_operation_model(before), bound_data_operation_model(after))
    compared = compare_declared_models(
        *models, before_release=before.release_id, after_release=after.release_id
    )
    changes: list[dict[str, Any]] = [
        dict(
            kind=change.kind,
            model_ref=change.model_ref,
            aspect=change.aspect,
            consumers=change.consumers,
            reason="Captured declared model meaning differs; output change is unassessed.",
            members=_changed_members(
                change.before if change.before is not None else _NO_MEMBER,
                change.after if change.after is not None else _NO_MEMBER,
                change.model_ref,
            ),
        )
        for change in compared.changes
    ]
    unknowns = set(compared.unknowns)
    try:
        policies = (released_alias_product(before), released_alias_product(after))
    except (ValueError, TypeError, KeyError) as error:
        unknowns.add("Released alias policy unassessed: " + str(error))
    else:
        for group, aspect in (("classes", "alias_normalization"), ("origins", "alias_origin")):
            old, new = (policy[group] for policy in policies)
            for iri in sorted(old.keys() | new.keys()):
                left, right = old.get(iri, _NO_MEMBER), new.get(iri, _NO_MEMBER)
                if left == right:
                    continue
                consumers = set()
                if group == "classes":
                    for model in models:
                        graph = model.projection_graph("semantic-reference")
                        roots = [
                            kind.semantic_id for kind in model.kinds if kind.semantic_id == iri
                        ]
                        if roots:
                            operations = {operation.semantic_id for operation in model.operations}
                            consumers.update(
                                set(graph.closure(roots, direction="dependents")) & operations
                            )
                    unknowns.add("Dynamic alias-policy consumer closure is unassessed for " + iri)
                changes.append(
                    dict(
                        kind="added"
                        if left is _NO_MEMBER
                        else "removed"
                        if right is _NO_MEMBER
                        else "changed",
                        model_ref="alias_policy:" + iri,
                        aspect=aspect,
                        consumers=sorted(consumers),
                        reason="Released normalization differs."
                        if group == "classes"
                        else "Alias source origin differs; normalization is separate.",
                        members=_changed_members(left, right, "alias_policy:" + iri + "/" + group),
                    )
                )
    query_analysis = compare_retained_projection_analysis(before, after)
    unknowns.update(query_analysis.unknowns)
    for change in query_analysis.changes:
        changes.append(
            dict(
                kind="added"
                if change.before is None
                else "removed"
                if change.after is None
                else "changed",
                model_ref=change.model_ref,
                aspect="query-" + change.aspect,
                consumers=change.consumers,
                reason="Captured query analysis differs; current source and retained data impact are separate.",
                members=_changed_members(
                    change.before if change.before is not None else _NO_MEMBER,
                    change.after if change.after is not None else _NO_MEMBER,
                    change.model_ref,
                ),
            )
        )
    append_vocabulary_impact(before, after, changes, unknowns, _changed_members, _NO_MEMBER)
    for prepared, runtime in ((before, before_runtime), (after, after_runtime)):
        if runtime is not None:
            if runtime.release_id != prepared.release_id:
                raise ValueError("runtime binding belongs to another semantic release")
            validate_data_operation_runtime(runtime, prepared)
    if (before_runtime is None) != (after_runtime is None):
        unknowns.add("Runtime change is unassessed: supply both runtime bindings.")
    elif (
        before_runtime is not None
        and after_runtime is not None
        and (
            before_runtime.implementation_digests != after_runtime.implementation_digests
            or json.loads(before_runtime.manifest)["python_version"]
            != json.loads(after_runtime.manifest)["python_version"]
        )
    ):
        unknowns.add(
            "Executable runtime changed independently of semantic release meaning; behavior equivalence is unassessed."
        )
    return _report(
        "SemanticImpactReport",
        dict(
            before_release=before.release_id,
            after_release=after.release_id,
            changes=changes,
            unknowns=sorted(unknowns),
            complete=not unknowns,
            projection_dependencies=_dependency_page((("before", before), ("after", after)))
            if dependency_detail
            else None,
        ),
    )


def _dependency_page(
    contexts, *, family=None, output=None, occurrence=None, after=0, limit=100, operation=None
):
    """Page retained occurrence facts without reconstructing unavailable analysis."""
    from .projection_analysis_products import read_projection_analysis

    if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 1000:
        raise SemanticRefusal("invalid dependency detail bounds")
    entries, complete = [], True
    for side, prepared in contexts:
        product = read_projection_analysis(prepared)
        if product is None:
            entries.append(
                dict(
                    side=side,
                    family=family or "*",
                    status="unavailable",
                    reason="Retained projection analysis unavailable.",
                )
            )
            complete = False
            continue
        complete = complete and product.complete
        for entry in sorted(product.projections, key=lambda row: row.family):
            if family is not None and entry.family != family:
                continue
            analysis = entry.analysis
            if operation is not None and operation not in analysis.consumers:
                continue
            complete = complete and not analysis.unknowns
            if analysis.detail_status != "available":
                entries.append(
                    dict(
                        side=side,
                        family=entry.family,
                        status="unavailable",
                        reason="Archived analysis does not retain occurrence detail.",
                    )
                )
                complete = False
                continue
            selected = [
                item
                for item in analysis.occurrences
                if (output is None or item.output == output)
                and (occurrence is None or item.identity == occurrence)
            ]
            entries.extend(
                dict(side=side, family=entry.family, status="available", occurrence=asdict(item))
                for item in sorted(selected, key=lambda item: item.structural_path)
            )
    if after > len(entries):
        raise SemanticRefusal("dependency detail position exceeds selected population")
    end = min(after + limit, len(entries))
    result = dict(
        items=entries[after:end],
        total=len(entries),
        after=after,
        next_after=end if end < len(entries) else None,
        paging_complete=end == len(entries),
        coverage_complete=complete,
    )
    if len(canonical_bytes(result)) > 1_000_000:
        raise SemanticRefusal("dependency detail exceeds byte bound; narrow the selection")
    return result


def projection_dependency_detail(
    prepared, *, family=None, output=None, occurrence=None, after=0, limit=100, operation=None
):
    """Bounded current-side view of the archived dependency authority."""
    return _dependency_page(
        (("current", prepared),),
        family=family,
        output=output,
        occurrence=occurrence,
        after=after,
        limit=limit,
        operation=operation,
    )


def projection_validation_report(
    prepared: PreparedRelease,
    *,
    dependency_detail: bool = False,
    dependency_family: str | None = None,
    dependency_output: str | None = None,
    dependency_occurrence: str | None = None,
    dependency_after: int = 0,
    dependency_limit: int = 100,
    detail: bool = False,
    max_errors: int = 100,
    max_depth: int = 8,
    max_bytes: int = 262144,
) -> BaseModel:
    """Expose retained coverage and optionally its bounded occurrence detail."""
    from .projection_analysis_products import read_projection_analysis

    product = read_projection_analysis(prepared)
    diagnostics = []
    if product is None:
        diagnostics.append(
            Diagnostic(
                "projection_analysis_unavailable",
                "projection",
                "Retained projection analysis unavailable.",
                outcome="unchecked",
            )
        )
    else:
        diagnostics.extend(
            Diagnostic(
                "projection_analysis_incomplete",
                "projection",
                message,
                outcome="unchecked",
            )
            for message in product.unknowns
        )
        for entry in product.projections:
            diagnostics.extend(
                Diagnostic(
                    "projection_analysis_incomplete",
                    "projection:" + entry.family,
                    message,
                    outcome="unchecked",
                )
                for message in entry.analysis.unknowns
            )
        if not product.complete and not diagnostics:
            diagnostics.append(
                Diagnostic(
                    "projection_analysis_incomplete",
                    "projection",
                    "Retained dependency coverage is incomplete.",
                    outcome="unchecked",
                )
            )
    return validation_report(
        tuple(diagnostics),
        detail=detail,
        max_errors=max_errors,
        max_depth=max_depth,
        max_bytes=max_bytes,
        prepared=prepared,
        projection_dependencies=(
            projection_dependency_detail(
                prepared,
                family=dependency_family,
                output=dependency_output,
                occurrence=dependency_occurrence,
                after=dependency_after,
                limit=dependency_limit,
            )
            if dependency_detail
            else None
        ),
    )


def report_schema(name: str) -> dict[str, object]:
    if name not in _SCHEMA_NAMES:
        raise SemanticRefusal("unknown operation report contract")
    return dict(deepcopy(_report_schemas().schemas[name]))


def write_report_schemas(destination: Path) -> None:
    """Generate registration metadata through the same authoritative prepared adapters."""
    from .schema_validation import prepared_schema_validator

    boundary, _digest = _report_model()
    schemas = {name: boundary.json_schema(name, mode="serialization") for name in _SCHEMA_NAMES}
    for schema in schemas.values():
        prepared_schema_validator(
            canonical_bytes({"$schema": "https://json-schema.org/draft/2020-12/schema", **schema})
        )
    content = canonical_bytes(
        dict(
            profile="operation-report-schema-2",
            source_id=_report_schema_source_id(),
            schemas=schemas,
        )
    )
    _ReportSchemaProduct.model_validate_json(content)
    destination.write_bytes(content)


def validation_failure_report(
    error: BaseException,
    *,
    prepared: PreparedRelease | None = None,
    operation: str | None = None,
    scope: str = "boundary",
    release_id: str | None = None,
    model_id: str | None = None,
    detail: bool = False,
    raw_evidence: bool = False,
    max_errors: int = 100,
    max_depth: int = 8,
    max_bytes: int = 262144,
) -> BaseModel:
    """Project known validator/native facts; callers retain the original exception/report."""
    from jsonschema.exceptions import SchemaError
    from jsonschema.exceptions import ValidationError as JsonValidationError
    from pydantic import ValidationError

    from corpus_structure.core.db.store import DatabaseCause, operation_failure

    from .invariant_failures import InvariantViolation
    from .ontology import GraphExecutionError, GraphShapeError
    from .operation_value_types import NativeResultViolation
    from .projection_analysis import ProjectionAnalysisUnavailable
    from .releases import ArchiveDecodeError
    from .types import PreparationError

    if isinstance(error, (PreparationError, ArchiveDecodeError)):
        return validation_report(
            error.diagnostics,
            prepared=prepared,
            operation=operation,
            raw_evidence=raw_evidence,
            detail=detail,
            max_errors=max_errors,
            max_depth=max_depth,
            max_bytes=max_bytes,
        )

    if prepared is not None:
        actual_model_id = trusted_operation_model_id(prepared)
        if release_id not in {None, prepared.release_id} or model_id not in {
            None,
            actual_model_id,
        }:
            raise SemanticRefusal(
                "validation report context differs from trusted release"
            ) from error
        release_id, model_id = prepared.release_id, actual_model_id

    def owner_release(observed: str | None) -> str | None:
        if observed is not None and release_id is not None and observed != release_id:
            raise SemanticRefusal(
                "native diagnostic release differs from supplied report context"
            ) from error
        return observed or release_id

    def pointer(path):
        return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in path)

    observations = []
    if isinstance(error, NativeResultViolation):
        details = (
            error.original.errors(include_url=False, include_input=False, include_context=False)
            if isinstance(error.original, ValidationError)
            else []
        )
        observations = [
            dict(
                category="validator_failure",
                code="native_result_contract",
                model_path=error.result_class,
                input_path=pointer(location),
                operation=error.operation,
                scope="native_result",
                message=str(error)
                if raw_evidence
                else "Boundary validation failed: " + type(error).__name__,
                expected=error.expected,
                actual="null" if error.actual is None else "type:" + type(error.actual).__name__,
                original_report=(
                    canonical_bytes(details).decode()
                    if details
                    else (
                        "exception:" + type(error.original).__name__
                        if error.original is not None
                        else "native-required-field:" + error.result_class + "/" + error.field
                    )
                ),
            )
            for location in error.locations
        ]
    elif (
        getattr(error, "boundary_diagnostic", None) is not None
        and getattr(error, "validation_capture", None) is None
    ):
        fact = error.boundary_diagnostic
        observations = [
            dict(
                category=fact.category,
                code=fact.code,
                model_path=fact.schema_path or "boundary",
                input_path=fact.pointer,
                record_locator=fact.locator,
                operation=operation,
                scope=scope,
                message=fact.message,
            )
        ]
    elif getattr(error, "validation_capture", None) is not None:
        observations = [
            dict(
                category="invalid_input",
                code="jsonschema",
                model_path="boundary",
                input_path=pointer(item.absolute_path),
                operation=operation,
                scope=scope,
                message=item.message
                if raw_evidence
                else "JSON Schema constraint failed: " + str(item.validator),
            )
            for item in error.validation_capture.errors
        ]
    elif isinstance(error, ValidationError):
        observations = [
            dict(
                category="invalid_input",
                code=item["type"],
                model_path=error.title,
                input_path=pointer(item["loc"]),
                operation=operation,
                scope=scope,
                message=item["msg"]
                if raw_evidence
                else "Validation constraint failed: " + item["type"],
                original_report="pydantic:" + error.title,
            )
            for item in error.errors(include_url=False, include_input=False)
        ]
    elif isinstance(error, (SchemaError, JsonValidationError)):
        observations = [
            dict(
                category="invalid_shape" if isinstance(error, SchemaError) else "invalid_input",
                code=type(error).__name__,
                model_path=pointer(error.absolute_schema_path),
                input_path=pointer(error.absolute_path),
                operation=operation,
                scope=scope,
                message=error.message
                if raw_evidence
                else "JSON Schema constraint failed: " + str(error.validator),
                original_report="jsonschema:" + type(error).__name__,
            )
        ]
    elif isinstance(error, InvariantViolation):
        failure = error.failure
        release_id = owner_release(failure.native.release_id)
        if model_id is not None and model_id != failure.model_id:
            raise SemanticRefusal(
                "native diagnostic model differs from supplied report context"
            ) from error
        model_id = failure.model_id
        native = failure.native.failure
        observations = [
            dict(
                category="state_violation",
                code=failure.code,
                model_path="invariants/" + failure.invariant,
                operation=failure.operation,
                scope=failure.scope,
                message="Admitted native invariant refused the operation.",
                native_sqlstate=native.sqlstate,
                native_constraint=native.constraint,
                original_report=canonical_bytes(asdict(failure.native)).decode(),
            )
        ]
    elif isinstance(error, DATABASE_ERRORS):
        native = operation_failure(error)
        release_id = owner_release(native.release_id)
        violation = native.failure.cause in {DatabaseCause.CONSTRAINT, DatabaseCause.FENCING}
        observations = [
            dict(
                category="state_violation" if violation else "validator_failure",
                code="database_" + native.failure.cause.value,
                model_path="native/operation",
                operation=operation or native.operation_id,
                scope=scope,
                message=(
                    "Native failure retained; no domain invariant is inferred from its message."
                ),
                native_sqlstate=native.failure.sqlstate,
                native_constraint=native.failure.constraint,
                original_report=canonical_bytes(asdict(native)).decode(),
            )
        ]
    elif isinstance(error, (GraphExecutionError, GraphShapeError)):
        observations = [
            dict(
                category="invalid_shape"
                if isinstance(error, GraphShapeError)
                else "validator_failure",
                code=error.outcome,
                model_path="graph/shapes"
                if isinstance(error, GraphShapeError)
                else "graph/validator",
                operation=operation or "graph_validate",
                scope=scope,
                message=str(error)
                if raw_evidence
                else "Boundary validation failed: " + type(error).__name__,
                original_report="exception:" + type(error).__name__,
            )
        ]
    elif isinstance(error, ProjectionAnalysisUnavailable):
        observations = [
            dict(
                category="unassessed",
                code="projection_analysis_unavailable",
                model_path=error.model_path,
                operation=operation,
                scope="projection_analysis",
                message=str(error)
                if raw_evidence
                else "Boundary validation failed: " + type(error).__name__,
                original_report="exception:" + type(error).__name__,
            )
        ]
    elif isinstance(error, SemanticRefusal):
        observations = [
            dict(
                category="unassessed",
                code=getattr(error, "reason", type(error).__name__),
                model_path="operation/compatibility",
                operation=operation,
                scope=scope,
                message=str(error)
                if raw_evidence
                else "Boundary validation failed: " + type(error).__name__,
                original_report=(
                    canonical_bytes(asdict(error.semantic_reason)).decode()
                    if getattr(error, "semantic_reason", None) is not None
                    else "refusal:" + type(error).__name__
                ),
            )
        ]
    elif isinstance(error, ValueError):
        observations = [
            dict(
                category="invalid_input",
                code=type(error).__name__,
                model_path="boundary",
                operation=operation,
                scope=scope,
                message=str(error)
                if raw_evidence
                else "Boundary validation failed: " + type(error).__name__,
                original_report="exception:" + type(error).__name__,
            )
        ]
    else:
        observations = [
            dict(
                category="validator_failure",
                code=type(error).__name__,
                model_path="validator",
                operation=operation,
                scope=scope,
                message=str(error)
                if raw_evidence
                else "Boundary validation failed: " + type(error).__name__,
                original_report="exception:" + type(error).__name__,
            )
        ]
    from .correction_detail import error_detail

    correction, evidence = error_detail(
        error,
        raw_evidence=raw_evidence,
        max_errors=max_errors,
        max_depth=max_depth,
        max_bytes=max_bytes,
        defer_bytes=True,
    )
    for observation in observations:
        observation.pop("original_report", None)
    return _validation_presentation(
        dict(
            release_id=release_id,
            model_id=model_id,
            observations=observations,
            correction_detail=correction,
            evidence=evidence,
            complete=all(item["category"] != "unassessed" for item in observations),
        ),
        detail=detail,
        max_errors=max_errors,
        max_depth=max_depth,
        max_bytes=max_bytes,
    )


def graph_validation_report(
    validation: GraphValidation,
    *,
    prepared: PreparedRelease,
    scope: str,
    detail: bool = False,
    raw_evidence: bool = False,
    max_errors: int = 100,
    max_depth: int = 8,
    max_bytes: int = 262144,
) -> BaseModel:
    """Keep graph locations and original report custody; completeness is relative to scope."""
    from hashlib import sha256

    reference = "sha256:" + sha256(validation.report).hexdigest()
    release_id, model_id = prepared.release_id, trusted_operation_model_id(prepared)
    observations = [
        dict(
            category="state_violation",
            code=item.constraint or "graph_nonconformance",
            model_path=item.source_shape or "graph/shape",
            input_path=item.focus_node
            if raw_evidence
            else "graph/focus/" + sha256(item.focus_node.encode()).hexdigest(),
            operation="graph_validate",
            scope=scope,
            message=item.message if raw_evidence else "Graph constraint failed.",
            actual=canonical_bytes(dict(path=item.path, severity=item.severity)).decode(),
            original_report=reference,
        )
        for item in validation.diagnostics
    ]
    if not validation.conforms and not observations:
        observations.append(
            dict(
                category="unassessed",
                code="graph_nonconformance_unlocated",
                model_path="graph",
                scope=scope,
                message=validation.message
                if raw_evidence
                else "Graph nonconformance has no located detail.",
                original_report=reference,
            )
        )
    from .correction_detail import graph_detail

    correction, evidence = graph_detail(
        validation,
        raw_evidence=raw_evidence,
        max_errors=max_errors,
        max_depth=max_depth,
        max_bytes=max_bytes,
        defer_bytes=True,
    )
    if correction["nodes"]:
        observations = []
        for node in correction["nodes"]:
            if node.get("parent") is not None:
                continue
            facts = json.loads(node["rdf_json"])
            observations.append(
                dict(
                    category="state_violation",
                    code=node["keyword"],
                    model_path=facts["source_shape"].get("value") or "graph/shape",
                    input_path=facts["focus_location"],
                    operation="graph_validate",
                    scope=scope,
                    message=node["message"],
                    actual=node["rdf_json"],
                )
            )
    for observation in observations:
        observation.pop("original_report", None)
    return _validation_presentation(
        dict(
            release_id=release_id,
            model_id=model_id,
            observations=observations,
            correction_detail=correction,
            evidence=evidence,
            complete=validation.conforms or bool(validation.diagnostics),
            validation_outcome="conformant" if validation.conforms else "nonconformant",
        ),
        detail=detail,
        max_errors=max_errors,
        max_depth=max_depth,
        max_bytes=max_bytes,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate model-owned MCP report schemas.")
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).resolve().parents[1] / _SCHEMA_PATH
    )
    write_report_schemas(parser.parse_args().out)
