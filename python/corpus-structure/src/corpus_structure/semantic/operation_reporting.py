"""Model-bound explanations, declared impact and located existing-validator reports.

Report construction validates against the trusted report model. These read-only observations
never authorize effects or establish equivalence of arbitrary implementation behavior.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import lru_cache
from hashlib import sha256
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, JsonValue

from .contracts import bound_execution_model
from .identity import canonical_bytes
from .refusals import DATABASE_ERRORS, SemanticRefusal
from .types import Diagnostic, PreparedRelease

if TYPE_CHECKING:
    from .runtime_bindings import RuntimeBinding

_REPORT_VERSIONS = {
    "OperationExplanation": 2,
    "LocatedValidationReport": 5,
    "SemanticImpactReport": 4,
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


@lru_cache(maxsize=1)
def _report_schemas() -> _ReportSchemaProduct:
    from pydantic import ValidationError

    try:
        product = _ReportSchemaProduct.model_validate_json(
            files("corpus_structure").joinpath(_SCHEMA_PATH).read_bytes()
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

    from .contracts import OperationContract
    from .ontology import GraphProjectionBinding, GraphValidation
    from .pdf_record_reader import PublishedPdfReader
    from .product_reference import ProductReference
    from .query import SnapshotBinding
    from .types import SourceBundle


@dataclass(frozen=True)
class PublishedDocumentSubject:
    reference: ProductReference
    run_id: int | None = None
    section_pointer: str | None = None
    pointer: str | None = None
    region_index: int | None = None


@lru_cache(maxsize=1)
def _report_sources() -> SourceBundle:
    """Registration and invocation share one immutable process-owned source closure."""
    from .contracts import trusted_execution_schema

    return trusted_execution_schema()


@lru_cache(maxsize=1)
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


def _subject_family(
    operation: OperationContract,
) -> Literal["snapshot", "published_document"] | None:
    """Select qualified observers from this release's declared context concepts."""
    snapshot = "SnapshotBinding" in operation.inputs
    concepts = (*operation.inputs, *operation.results)
    document = "SourceView" in concepts or (
        "published_document_address" in operation.applicability and "SourceArtifact" in concepts
    )
    if snapshot == document:
        # A mixed context needs its own qualified composition, not implicit precedence.
        return None
    return "snapshot" if snapshot else "published_document"


def explain_operation(
    prepared: PreparedRelease,
    operation: str,
    *,
    subject: ProductReference | PublishedDocumentSubject | SnapshotBinding | None = None,
    connection: Connection | None = None,
    dependency_detail: bool = False,
    dependency_family: str | None = None,
    dependency_output: str | None = None,
    dependency_occurrence: str | None = None,
    dependency_after: int = 0,
    dependency_limit: int = 100,
) -> BaseModel:
    from .product_reference import ProductReference
    from .query import SnapshotBinding

    if isinstance(subject, ProductReference):
        subject = PublishedDocumentSubject(subject)
    model = bound_execution_model(prepared)
    found = next((item for item in model.operations if item.id == operation), None)
    if found is None:
        raise SemanticRefusal(f"operation is not declared by this release: {operation}")
    subject_family = _subject_family(found)
    if subject is not None and (
        subject_family is None
        or isinstance(subject, SnapshotBinding) != (subject_family == "snapshot")
    ):
        raise SemanticRefusal(
            "subject family has no qualified observer for this operation's declared concepts"
        )
    invariants = {item.id: item for item in model.invariants}
    checks = [
        dict(
            contract_ref="invariant:" + name,
            owner=invariants[name].implementation,
            scope=invariants[name].scope,
            status="unresolved",
            reason="No qualified live evaluator was selected for this subject and invariant.",
        )
        for name in found.applicability
    ]
    if found.implementation is not None:
        try:
            model.require_operation(found.id)
        except (SemanticRefusal, ValueError) as exc:
            compatible, reason = False, str(exc)
        else:
            compatible, reason = True, "The trusted implementation supports this bound operation."
        checks.append(
            dict(
                contract_ref="implementation:" + found.implementation,
                owner="semantic.contracts",
                scope=model.model_id,
                status="applicable" if compatible else "unavailable",
                expected="compatible trusted operation implementation",
                actual="compatible" if compatible else "refused",
                reason=reason,
            )
        )
    if connection is not None:
        from .contracts import require_database_operation

        # A refusal must not poison the caller's read snapshot. The same protected
        # admission check is used by invocation; this observation grants no authority.
        try:
            with connection.begin_nested():
                require_database_operation(connection, prepared.release_id, found.id)
        except DATABASE_ERRORS as exc:
            from corpus_structure.core.db.store import operation_failure

            failure = operation_failure(exc)
            if failure.failure.sqlstate not in {"P0001", "23514"}:
                raise
            native_status = "unavailable"
            reason = canonical_bytes(asdict(failure)).decode()
        else:
            native_status = "applicable"
            reason = "The protected native owner admits this release and operation."
        checks.append(
            dict(
                contract_ref="operation:" + found.id,
                owner="sem.require_execution_operation",
                scope=prepared.release_id,
                status=native_status,
                expected="native release and operation admission",
                reason=reason,
            )
        )
    if isinstance(subject, PublishedDocumentSubject) and connection is not None:
        from .pdf_record_reader import published_record_reader

        # Failed evaluation propagates to the located failure boundary; only an
        # actual empty lookup establishes an unavailable publication.
        with connection.begin_nested():
            reader = published_record_reader(
                connection, subject.reference, projection_context=prepared
            )
        published_status = "applicable" if reader is not None else "unavailable"
        published_actual = "present" if reader else "No supported published record binding."
        checks.append(
            dict(
                contract_ref="published_document",
                owner="semantic.pdf_record_reader",
                scope=canonical_bytes(subject.reference.values()).decode(),
                status=published_status,
                expected="supported exact published record binding",
                actual=published_actual,
                reason=(
                    "Publication lookup uses the protected reader; "
                    "other applicability remains independently assessed."
                ),
            )
        )
        _document_subject_checks(prepared, subject, connection, reader, checks)
    if subject_family == "snapshot" and isinstance(subject, SnapshotBinding):
        from .query import bind_realization

        status, actual = "unresolved", "A live read snapshot was not supplied."
        if subject.release_id != prepared.release_id:
            status, actual = "unavailable", "Subject release differs from the selected release."
        elif connection is not None:
            try:
                observed = bind_realization(connection, subject.realization_id, prepared.release_id)
            except SemanticRefusal as exc:
                status, actual = "unavailable", str(exc)
            else:
                revision = observed.binding.data_revision
                status = "applicable" if revision == subject.data_revision else "unavailable"
                actual = (
                    f"Observed data revision {revision}; supplied revision {subject.data_revision}."
                )
        checks.append(
            dict(
                contract_ref="SnapshotBinding",
                owner="semantic.query.bind_realization",
                scope=subject.realization_id,
                status=status,
                expected="exact release and data revision",
                actual=actual,
                reason=(
                    "Snapshot owner observation; "
                    "publication independently rechecks its revision fence."
                ),
            )
        )
    if not found.applicability:
        checks.insert(
            0,
            dict(
                contract_ref="operation:" + found.id,
                owner=found.implementation or "declared operation",
                scope=found.universe,
                status="unresolved",
                reason=(
                    "No complete operation-level applicability evaluator is declared; "
                    "qualified context checks are reported separately."
                ),
            ),
        )
    revision = None
    if isinstance(subject, PublishedDocumentSubject):
        revision = subject.reference.content_digest
    elif isinstance(subject, SnapshotBinding):
        revision = str(subject.data_revision)
    return _report(
        "OperationExplanation",
        dict(
            release_id=prepared.release_id,
            model_id=model.model_id,
            projection_dependencies=projection_dependency_detail(
                prepared,
                operation=found.id,
                family=dependency_family,
                output=dependency_output,
                occurrence=dependency_occurrence,
                after=dependency_after,
                limit=dependency_limit,
            )
            if dependency_detail
            else None,
            operation=found.id,
            implementation=found.implementation,
            inputs=list(found.inputs),
            results=list(found.results),
            effects=list(found.effects),
            transitions=list(found.transitions),
            checks=checks,
            observed_at=datetime.now(UTC).isoformat(),
            observed_revision=revision,
            complete=all(check["status"] != "unresolved" for check in checks),
        ),
    )


def parse_operation_subject(
    prepared: PreparedRelease, operation: str, raw: bytes, *, connection: Connection
) -> PublishedDocumentSubject | SnapshotBinding:
    """Use the exact retained execution boundary for this finite supported subject family."""
    from .pdf_contracts import pdf_context_for_release
    from .product_reference import ProductReference
    from .query import SnapshotBinding

    model = bound_execution_model(prepared)
    found = next((item for item in model.operations if item.id == operation), None)
    if found is None:
        raise SemanticRefusal(f"operation is not declared by this release: {operation}")
    family = _subject_family(found)
    if family is None:
        raise SemanticRefusal(
            "no qualified subject observer for this operation's declared concepts"
        )
    context = pdf_context_for_release(connection, prepared)
    subject_class = "CaptureSnapshotBinding" if family == "snapshot" else "PublishedDocumentSubject"
    if subject_class not in {definition.name for definition in context.boundary.definitions}:
        raise SemanticRefusal(
            f"retained release does not support subject contract {subject_class}; "
            "inspect the static operation or select a release that declares this subject"
        )
    if family == "snapshot":
        value = context.boundary.validate_json(subject_class, raw)
        return SnapshotBinding(**value.model_dump(mode="python"))
    value = context.boundary.validate_json(subject_class, raw)
    fields = value.model_dump(mode="python")
    reference = ProductReference(
        **{name: fields.pop(name) for name in ("task_id", "product_key", "content_digest")}
    )
    return PublishedDocumentSubject(reference, **fields)


def _document_subject_checks(
    prepared: PreparedRelease,
    subject: PublishedDocumentSubject,
    connection: Connection,
    reader: PublishedPdfReader | None,
    checks: list[dict[str, str]],
) -> None:
    """Observe existing owners; do not hydrate document bodies to explain prerequisites."""
    from sqlalchemy import select

    from .metadata import table
    from .pdf_record_reader import PublishedRegionUnavailable
    from .source_views import selected_source_views

    if subject.run_id is not None:
        run = table("ops.run")
        release = connection.execute(
            select(run.c.release_id).where(run.c.id == subject.run_id)
        ).scalar_one_or_none()
        if release == prepared.release_id:
            selected = tuple(
                view
                for view in selected_source_views(connection, subject.run_id)
                if view.native_product == subject.reference
                and (
                    subject.section_pointer is None
                    or view.section_pointer == subject.section_pointer
                )
            )
            status = "applicable" if selected else "unavailable"
            actual = f"{len(selected)} selected source view(s) for the exact product/section."
        else:
            status, actual = "unavailable", "Run is absent or belongs to another release."
        checks.append(
            dict(
                contract_ref="selected_source_views",
                owner="semantic.source_views.selected_source_views",
                scope=str(subject.run_id),
                status=status,
                expected="prepared selected source context",
                actual=actual,
                reason="Observation of the run's actual selected immutable source views.",
            )
        )
    if subject.pointer is not None or subject.region_index is not None:
        if reader is None:
            status, actual = "unavailable", "Exact published document is unavailable."
        elif subject.pointer is None or subject.region_index is None:
            status, actual = "unresolved", "Both pointer and region index are needed."
        else:
            try:
                region = reader.region(subject.pointer, subject.region_index)
            except PublishedRegionUnavailable as exc:
                status, actual = "unavailable", str(exc)
            else:
                status, actual = (
                    "applicable",
                    canonical_bytes(
                        dict(pointer=region["pointer"], region_index=region["region_index"])
                    ).decode(),
                )
        checks.append(
            dict(
                contract_ref="published_region",
                owner="semantic.pdf_record_reader.PublishedPdfReader.region",
                scope=subject.pointer or "region",
                status=status,
                expected="exact qualified region",
                actual=actual,
                reason="Protected finite region lookup; no rasterization is performed.",
            )
        )
        if reader is not None:
            digest = reader.revision.get("source_digest")
            artifact = table("kb.source_artifact")
            present = connection.execute(
                select(
                    select(artifact.c.artifact_digest)
                    .where(artifact.c.artifact_digest == digest)
                    .exists()
                )
            ).scalar_one()
            checks.append(
                dict(
                    contract_ref="original_source",
                    owner="semantic.pdf_record_reader",
                    scope=str(digest or "unresolved"),
                    status="applicable" if present else "unavailable",
                    expected="retained original artifact custody",
                    actual="present" if present else "absent",
                    reason="Metadata-only artifact lookup; rendering verifies actual bytes again.",
                )
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
            model_id=prepared.execution_model_id if prepared else None,
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
                item.outcome not in {"unsupported", "unresolved", "unchecked"}
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
    connection=None,
    source_run_id: int | None = None,
    review_run_id: int | None = None,
    review_cut_id: int | None = None,
    use_limit: int = 100,
    use_after: str | None = None,
    use_side: str = "before",
    before_runtime: RuntimeBinding | None = None,
    after_runtime: RuntimeBinding | None = None,
    dependency_detail: bool = False,
    dependency_family: str | None = None,
    dependency_output: str | None = None,
    dependency_occurrence: str | None = None,
    dependency_after: int = 0,
    dependency_limit: int = 100,
) -> BaseModel:
    """Compare declared meaning, with optional separately identified runtime provenance."""
    old_model, new_model = bound_execution_model(before), bound_execution_model(after)
    changes = []
    unknowns = set()
    # Retain both sides' declared edges: an operation can stop referring to the
    # changed definition in the same release, and is still an affected consumer.
    operations = (*old_model.operations, *new_model.operations)

    def dependencies(op):
        references = set()

        def add(kind, names):
            references.update((kind, name) for name in names)

        add("concept", (*op.inputs, *op.results))
        add("invariant", op.applicability)
        add("projection", op.projections)
        add("effect", op.effects)
        add("transition", op.transitions)
        add(
            "outcome_domain", (op.outcome_domain, *(d.outcome_domain for d in op.result_dimensions))
        )
        if op.implementation is not None:
            add("implementation", (op.implementation,))
        for model in (old_model, new_model):
            for projection in model.projections:
                if projection.id in op.projections:
                    add("concept", projection.sources)
                    add("relationship", projection.relationships)
                    add("implementation", (projection.implementation,))
            for invariant in model.invariants:
                if invariant.id in op.applicability:
                    add("concept", invariant.subjects)
                    add("relationship", invariant.relationships)
                    add("implementation", (invariant.implementation,))
                    add(
                        "native_guard",
                        (d.guard for d in invariant.diagnostics if d.guard is not None),
                    )
            for transition in model.transitions:
                if transition.id in op.transitions or transition.operation == op.id:
                    add("transition", (transition.id,))
                    add("lifecycle", (transition.lifecycle,))
                    add("invariant", transition.invariants)
                    add("effect", transition.effects)
            for lifecycle in model.lifecycles:
                if ("lifecycle", lifecycle.id) in references:
                    add("concept", (lifecycle.subject,))
            for concept in model.concepts:
                if ("concept", concept.id) in references:
                    add("relationship", concept.relationships)
            for profile in model.analysis_profiles:
                if op.id in profile.shared_consumers:
                    add("analysis_profile", (profile.id,))
        return references

    operation_dependencies = [(op.id, dependencies(op)) for op in operations]

    def compare_group(label, old_items, new_items, identity):
        old = {identity(item): item for item in old_items}
        new = {identity(item): item for item in new_items}
        for name in sorted(old.keys() | new.keys()):
            if name in old and name in new and asdict(old[name]) == asdict(new[name]):
                continue
            kind = "added" if name not in old else "removed" if name not in new else "changed"
            consumers = sorted(
                {
                    op_id
                    for op_id, references in operation_dependencies
                    if (label, name) in references or (label == "operation" and op_id == name)
                }
            )
            if not consumers:
                unknowns.add(f"Consumer closure not declared for {label}:{name}")
            changes.append(
                dict(
                    kind=kind,
                    model_ref=label + ":" + name,
                    aspect=label,
                    consumers=consumers,
                    reason="Normalized declared members differ; exact facts are retained below.",
                    members=_changed_members(
                        asdict(old[name]) if name in old else _NO_MEMBER,
                        asdict(new[name]) if name in new else _NO_MEMBER,
                        label + ":" + name,
                    ),
                )
            )

    compare_group("class", before.definitions, after.definitions, lambda item: item.name)
    for label, attr in [
        ("operation", "operations"),
        ("invariant", "invariants"),
        ("projection", "projections"),
        ("implementation", "implementations"),
        ("concept", "concepts"),
        ("relationship", "relationships"),
        ("lifecycle", "lifecycles"),
        ("transition", "transitions"),
        ("outcome_domain", "outcome_domains"),
        ("native_guard", "native_guards"),
        ("effect", "effect_definitions"),
        ("analysis_profile", "analysis_profiles"),
    ]:
        compare_group(
            label, getattr(old_model, attr), getattr(new_model, attr), lambda item: item.id
        )
    compare_group(
        "outcome_translation",
        old_model.outcome_translations,
        new_model.outcome_translations,
        lambda item: ":".join((item.source_domain, item.source, item.target_domain, item.target)),
    )
    compare_group(
        "parsing_adapter",
        old_model.parsing_adapters,
        new_model.parsing_adapters,
        lambda item: item.adapter_id,
    )
    if old_model.required_capabilities != new_model.required_capabilities:
        changes.append(
            dict(
                kind="changed",
                model_ref="execution:required_capabilities",
                aspect="required_capabilities",
                consumers=[],
                reason=canonical_bytes(
                    dict(
                        before=old_model.required_capabilities,
                        after=new_model.required_capabilities,
                    )
                ).decode(),
                members=_changed_members(
                    old_model.required_capabilities,
                    new_model.required_capabilities,
                    "execution:required_capabilities",
                ),
            )
        )
        unknowns.add(
            "Release capability changes require native admission; consumer closure unassessed."
        )
    old_comparison = next(
        (a.content for a in before.artifacts if a.kind == "comparison_projection.json"), None
    )
    new_comparison = next(
        (a.content for a in after.artifacts if a.kind == "comparison_projection.json"), None
    )
    if old_comparison != new_comparison:
        changes.append(
            dict(
                kind="added"
                if old_comparison is None
                else "removed"
                if new_comparison is None
                else "changed",
                model_ref="comparison_projection",
                aspect="comparison_roles",
                consumers=["scientific_decisions"],
                reason="Resolved comparison-role product differs.",
                members=_changed_members(
                    json.loads(old_comparison) if old_comparison is not None else _NO_MEMBER,
                    json.loads(new_comparison) if new_comparison is not None else _NO_MEMBER,
                    "comparison_projection",
                ),
            )
        )
    if old_model.implementation_digests != new_model.implementation_digests:
        legacy = any(
            int(json.loads(model.content)["inputs"]["compiler_version"]) <= 26
            for model in (old_model, new_model)
        )
        unknowns.add(
            "Changed legacy implementation custody mixes semantic determinants and executable "
            "runtime bytes; behavior equivalence is unassessed."
            if legacy
            else "Changed semantic determinant bytes require qualified compatibility; "
            "behavior equivalence is unassessed."
        )
    from .runtime_bindings import validate_runtime_binding

    for prepared, runtime in ((before, before_runtime), (after, after_runtime)):
        if runtime is not None:
            if runtime.release_id != prepared.release_id:
                raise ValueError("runtime binding belongs to another semantic release")
            validate_runtime_binding(runtime, prepared)
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
            "Executable runtime changed independently of semantic release meaning: "
            + before_runtime.runtime_id
            + " -> "
            + after_runtime.runtime_id
            + "; behavior equivalence is unassessed."
        )
    from .vocabulary_impact import append_vocabulary_impact

    append_vocabulary_impact(before, after, changes, unknowns, _changed_members, _NO_MEMBER)
    use_survey = None
    if use_after is not None and source_run_id is None:
        raise ValueError("vocabulary use continuation requires a selected population")
    if any(value is not None for value in (source_run_id, review_run_id, review_cut_id)):
        if (
            connection is None
            or source_run_id is None
            or review_run_id is None
            or review_cut_id is None
        ):
            raise ValueError(
                "vocabulary uses require source run, review run/cut and reader snapshot"
            )
        from .interpretation_queries import collect_interpretation_uses
        from .observations import source_value

        if use_side not in {"before", "after"}:
            raise ValueError("vocabulary use side must be before or after")
        selected = before if use_side == "before" else after
        use_cursor = None
        token = None
        if use_after is not None:
            try:
                token = json.loads(use_after)
                position = token["position"]
                if (
                    not isinstance(position, list)
                    or len(position) != 3
                    or type(position[0]) is not int
                    or not all(type(v) is str for v in position[1:])
                ):
                    raise ValueError("context differs")
                use_cursor = tuple(position)
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError("invalid or mismatched vocabulary use continuation") from exc
        survey = collect_interpretation_uses(
            connection,
            source_run_id=source_run_id,
            review_run_id=review_run_id,
            review_cut_id=review_cut_id,
            vocabulary_release=selected.release_id,
            limit=use_limit,
            after=use_cursor,
        )
        binding = sha256(
            canonical_bytes(
                dict(
                    version=1,
                    before=before.release_id,
                    after=after.release_id,
                    side=use_side,
                    population={
                        key: value
                        for key, value in survey.items()
                        if key not in {"items", "complete", "next_after"}
                    },
                )
            )
        ).hexdigest()
        if token is not None and token.get("binding") != binding:
            raise ValueError("invalid or mismatched vocabulary use continuation")
        survey["side"] = use_side
        if survey["next_after"] is not None:
            survey["next_after"] = canonical_bytes(
                dict(binding=binding, position=survey["next_after"])
            ).decode()
        use_survey = source_value(survey)
        unknowns.discard(
            "Retained vocabulary uses were not surveyed; supply an "
            "explicit source/review population for impact assessment."
        )
        unknowns.add("Other retained vocabulary populations were not surveyed.")
        if not survey["complete"]:
            unknowns.add("Selected vocabulary use survey is incomplete; follow its continuation.")
    _alias_impact(before, after, changes, unknowns)
    _projection_impact(before, after, changes, unknowns)
    return _report(
        "SemanticImpactReport",
        dict(
            vocabulary_uses=use_survey,
            before_release=before.release_id,
            after_release=after.release_id,
            projection_dependencies=_dependency_page(
                (("before", before), ("after", after)),
                family=dependency_family,
                output=dependency_output,
                occurrence=dependency_occurrence,
                after=dependency_after,
                limit=dependency_limit,
            )
            if dependency_detail
            else None,
            changes=changes,
            unknowns=sorted(unknowns),
            complete=not unknowns,
        ),
    )


def _alias_impact(before: PreparedRelease, after: PreparedRelease, changes, unknowns) -> None:
    from .alias_policy import released_alias_product

    try:
        old, new = released_alias_product(before), released_alias_product(after)
    except (ValueError, TypeError, KeyError) as error:
        unknowns.add(f"Released alias policy unassessed: {error}")
        return
    models = (bound_execution_model(before), bound_execution_model(after))
    consumers = set()
    consumer_unknowns = set()
    for model in models:
        for binding in model.implementations:
            if (binding.owner, binding.symbol) == (
                "semantic.domain_operations",
                "_entity_mappings",
            ):
                consumers.add("implementation:" + binding.id)
        for profile in model.analysis_profiles:
            if profile.alignment_policy is None:
                continue
            reference = "analysis_profile:" + profile.id + "/alignment_policy"
            if int(json.loads(model.content)["inputs"]["compiler_version"]) >= 27 or dict(
                model.implementation_digests
            ).get("alignment/semantic_alignment.py"):
                # Current semantic declarations identify the consumer; exact executable
                # custody belongs to a runtime binding, not this semantic product.
                consumers.add(reference)
            else:
                consumer_unknowns.add(reference + ": alignment implementation custody unavailable")
    for group, aspect in (("classes", "alias_normalization"), ("origins", "alias_origin")):
        left, right = old[group], new[group]
        for iri in sorted(left.keys() | right.keys()):
            previous, current = left.get(iri, _NO_MEMBER), right.get(iri, _NO_MEMBER)
            if previous == current:
                continue
            kind = (
                "added"
                if previous is _NO_MEMBER
                else "removed"
                if current is _NO_MEMBER
                else "changed"
            )
            reason = (
                "Released alias normalization differs."
                if group == "classes"
                else "Alias source origin differs; normalization is assessed separately."
            )
            changes.append(
                dict(
                    kind=kind,
                    model_ref="alias_policy:" + iri,
                    aspect=aspect,
                    consumers=sorted(consumers) if group == "classes" else [],
                    reason=reason,
                    members=_changed_members(
                        previous, current, "alias_policy:" + iri + "/" + group
                    ),
                )
            )
            if group == "classes":
                unknowns.update(consumer_unknowns)
                unknowns.add("Dynamic alias-policy consumer closure is unassessed for " + iri)


def _projection_impact(before: PreparedRelease, after: PreparedRelease, changes, unknowns) -> None:
    from .projection_analysis_products import read_projection_analysis

    old, new = read_projection_analysis(before), read_projection_analysis(after)
    for side, product in (("before", old), ("after", new)):
        if product is None:
            unknowns.add(f"{side}: archived qualified projection analysis unavailable")
            continue
        unknowns.update(f"{side}: {message}" for message in product.unknowns)
        for entry in product.projections:
            if entry.analysis.detail_status != "available":
                unknowns.add(f"{side}: projection:{entry.family}: occurrence detail unavailable")
            unknowns.update(
                f"{side}: projection:{entry.family}: {message}"
                for message in entry.analysis.unknowns
            )

        if (
            not product.complete
            and not product.unknowns
            and not any(item.analysis.unknowns for item in product.projections)
        ):
            unknowns.add(f"{side}: projection dependency coverage is incomplete")
    if old is None or new is None:
        return
    old_rows = {item.family: item.analysis for item in old.projections}
    new_rows = {item.family: item.analysis for item in new.projections}
    for family in sorted(old_rows.keys() | new_rows.keys()):
        left, right = old_rows.get(family), new_rows.get(family)
        if (left is None and not old.complete) or (right is None and not new.complete):
            unknowns.add(
                f"projection:{family}: absent from incomplete analysis; "
                "addition or removal is unassessed"
            )
            continue
        if left == right:
            continue
        consumers = sorted({name for row in (left, right) if row for name in row.consumers})
        if not consumers:
            unknowns.add(f"projection:{family}: consumer dependencies are not declared")
        aspects = (
            "profile",
            "library_version",
            "consumers",
            "output_origins",
            "output_types",
            "value_dependencies",
            "relational_sources",
            "relational_dependencies",
            "expressions",
            "relationships",
            "helpers",
            "projection_id",
            "logical_sources",
            "occurrences",
            "detail_status",
        )
        for aspect in aspects:
            if aspect == "occurrences" and any(
                row is not None and row.detail_status != "available" for row in (left, right)
            ):
                continue
            old_value = getattr(left, aspect) if left else None
            new_value = getattr(right, aspect) if right else None
            if aspect == "occurrences":
                old_value = [asdict(item) for item in old_value] if old_value is not None else None
                new_value = [asdict(item) for item in new_value] if new_value is not None else None
            if old_value == new_value:
                continue
            changes.append(
                dict(
                    kind="added" if left is None else "removed" if right is None else "changed",
                    model_ref=f"projection:{family}",
                    aspect=aspect,
                    consumers=consumers,
                    reason=canonical_bytes(dict(before=old_value, after=new_value)).decode(),
                    members=_changed_members(
                        old_value if left is not None else _NO_MEMBER,
                        new_value if right is not None else _NO_MEMBER,
                        f"projection:{family}/{aspect}",
                    ),
                )
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


def compatibility_advice(impact: BaseModel) -> tuple[str, ...]:
    """Advice from the shared comparison; admission and migration stay independent."""
    value = impact.model_dump(mode="json")
    advice = []
    semantic_changes = [change for change in value["changes"] if change["aspect"] != "alias_origin"]
    if any(change["aspect"] == "alias_origin" for change in value["changes"]):
        advice.append(
            "Alias source provenance changed; normalization changes are reported separately."
        )
    if semantic_changes:
        consumers = sorted({name for change in semantic_changes for name in change["consumers"]})
        advice.append(
            "Regenerate and qualify affected declared consumers"
            + (": " + ", ".join(consumers) if consumers else "; consumer closure is unassessed")
            + "."
        )
    else:
        advice.append(
            "No examined normalization changed."
            if value["changes"]
            else "No examined declared definitions changed."
        )
    if not value["complete"]:
        advice.append("Resolve unknown dependency coverage before claiming compatibility.")
    advice.append("Native admission, revision fences and explicit activation remain required.")
    return tuple(advice)


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
    from jsonschema import Draft202012Validator

    boundary, _digest = _report_model()
    schemas = {name: boundary.json_schema(name, mode="serialization") for name in _SCHEMA_NAMES}
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
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
    from .refusals import DATABASE_ERRORS
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
        if release_id not in {None, prepared.release_id} or model_id not in {
            None,
            prepared.execution_model_id,
        }:
            raise SemanticRefusal(
                "validation report context differs from trusted release"
            ) from error
        release_id, model_id = prepared.release_id, prepared.execution_model_id

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
        if model_id is not None and model_id != failure.model_id:
            raise SemanticRefusal(
                "native diagnostic model differs from supplied report context"
            ) from error
        model_id = failure.model_id
        release_id = owner_release(failure.native.release_id)
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
    prepared: PreparedRelease | None = None,
    binding: GraphProjectionBinding | None = None,
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
    if prepared is None and binding is None:
        raise SemanticRefusal("graph report requires a trusted release binding")
    if prepared is not None:
        release_id, model_id = prepared.release_id, prepared.execution_model_id
    else:
        assert binding is not None
        release_id, model_id = binding.release_id, binding.execution_model_id
    if binding is not None and (binding.release_id, binding.execution_model_id) != (
        release_id,
        model_id,
    ):
        raise SemanticRefusal("graph report binding differs from supplied release")
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
