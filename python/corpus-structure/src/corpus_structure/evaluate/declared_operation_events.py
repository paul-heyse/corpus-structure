"""Current selected component-event acquisition, CPU fitting and finite parameter issuance.

Independent C labels remain protected evaluator inputs. The numerical kernel emits
only a protected result; the native command authenticates its exact producing
receipt before an ordinary parameter product can exist.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from corpus_structure.semantic.data_operation_model import EffectContract, json_context_meaning
from corpus_structure.semantic.declared_structural_references import DeclaredProductRef
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.refusal_types import SemanticRefusal

from .selected_operation_events import (
    DdoOperationEventFit,
    DdoOperationEventFitSpecification,
    DdoOperationEventFrame,
    DdoOperationEventQuestion,
    operation_event_parameter_value,
    prepare_operation_event_frame,
)

NAMESPACE = "https://corpus-structure.dev/semantic/operation-events/protected/"
PARAMETERS_KIND = "urn:corpus:kind:operation-event:parameters"
AUTHORIZATION_OPERATION = "operation_event.authorize"
AUTHORIZATION_FACTORY = (
    "corpus_structure.methods.operation_events.OperationEventAuthorization.acquire_port"
)
AUTHORIZATION_EFFECT = EffectContract(
    "native-evaluator-operation-event-authorization",
    ("native-purpose:evaluate", "exact-protected-operation-event-fit"),
    "request-generation/exact-fit",
    "native-publication-receipt",
)
_PRODUCERS = {
    "structure.definition_components/declared": "corpus_structure.methods.definition_components_declared.DefinitionComponentsOperation.acquire_port",
    "structure.definition_declaration_components/declared": "corpus_structure.methods.definition_declared.DefinitionDeclarationOperation.acquire_port",
    "structure.definition_named_components/declared": "corpus_structure.methods.definition_named_declared.NamedDefinitionComponentsOperation.acquire_port",
}
_PATHS = (
    "methods/operation_events.py",
    "evaluate/declared_operation_events.py",
    "evaluate/selected_operation_events.py",
    "evaluate/operation_fitting.py",
    "semantic/operation_policy.py",
    "semantic/data_operation_cpu_basis.py",
    "semantic/declared_structural_references.py",
    "semantic/structural_products.py",
    "semantic/source_products.py",
    "semantic/declared_record_sources.py",
)


def operation_event_kind_declarations():
    from pydantic import BaseModel

    from corpus_structure.semantic.data_operation_version import MODEL_VERSION
    from corpus_structure.semantic.nominal_schema_kinds import nominal_schema_kinds
    from corpus_structure.semantic.types import SourceArtifact

    class ProtectedOperationEventContracts(BaseModel):
        question: DdoOperationEventQuestion
        frame: DdoOperationEventFrame
        specification: DdoOperationEventFitSpecification
        fit: DdoOperationEventFit

    return SourceArtifact(
        "operation-events/protected-kinds.json",
        canonical_bytes(
            dict(
                version=MODEL_VERSION,
                kinds=[
                    dict(row, universe="evaluator")
                    for row in nominal_schema_kinds(
                        ProtectedOperationEventContracts.model_json_schema(),
                        namespace=NAMESPACE,
                        root_name="ProtectedOperationEventContracts",
                    )
                ],
            )
        ),
    )


def operation_event_computation_assets():
    from corpus_structure.semantic.operation_policy import operation_score_numerical_policy
    from corpus_structure.semantic.python_module_projection import admitted_operation_module_meaning
    from corpus_structure.semantic.types import SourceArtifact

    root = Path(__file__).parents[1]
    return SourceArtifact(
        "operation-events/computation-assets",
        canonical_bytes(
            dict(
                version="selected-operation-event-computation-1",
                numerical_policy=operation_score_numerical_policy().model_dump(mode="json"),
                protected_kinds=operation_event_kind_declarations().content.hex(),
                files=[
                    (name, admitted_operation_module_meaning((root / name).read_bytes()).hex())
                    for name in _PATHS
                ],
            )
        ),
    )


def operation_event_operation_sources():
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )

    root = Path(__file__).parents[1]
    paths = ("methods/operation_events.py", "evaluate/declared_operation_events.py")
    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (root / name).read_bytes(),
                str((root / name).resolve()),
            )
            for name in paths
        ),
        boundary_contracts=(operation_event_computation_assets(),),
    )


def _bound_members(binding, role, *, scalar=False, whole=True):
    if binding is None or not binding.sufficient or binding.subject_context is None:
        raise SemanticRefusal("event computation requires its sufficient exact current binding")
    selected = [row for row in binding.roles if row.role == role and row.state == "present"]
    if (
        len(selected) != 1
        or not selected[0].members
        or (scalar and len(selected[0].members) != 1)
        or any(
            row.multiplicity != 1 or (whole and row.member is not None)
            for row in selected[0].members
        )
    ):
        raise SemanticRefusal("event input differs from its exact whole scalar/set role")
    return selected[0].members


def _input_basis(port, binding, values):
    from pydantic import BaseModel

    from corpus_structure.semantic.data_operation_cpu_basis import cpu_input_basis_from_binding

    roles = [row for row in port.operation.roles if row.direction == "input"]
    recipe = next(
        row.key
        for row in port.model.identities
        if row.owner == port.operation.semantic_id and row.domain == "recipe"
    )

    def value(item):
        return item.model_dump(mode="python") if isinstance(item, BaseModel) else item

    return cpu_input_basis_from_binding(
        recipe,
        binding,
        {
            row.name: (value(values[row.parameter or row.name]),)
            if row.collection == "scalar"
            else tuple(value(item) for item in values[row.parameter or row.name])
            for row in roles
        },
    )


def _selected_body(index, product, member=None):
    from corpus_structure.semantic.data_operation_values import decode_semantic_value

    row = (
        index.mapping("kb.data_product", ("id",)).get(product)
        if member is None
        else index.mapping("kb.data_product_member", ("product_id", "member_id")).get(
            (product, member)
        )
    )
    if row is None:
        raise SemanticRefusal("event input is outside its exact selected closure")
    return row, decode_semantic_value(row["canonical_body" if member is None else "body"])


def _check_selected_context(row, reference):
    from corpus_structure.semantic.data_operation_json import json_bytes

    if (
        row["kind_contract"] != reference.kind_contract
        or any(
            row[name] != getattr(reference, name)
            for name in ("subject", "subject_definition", "original_source")
        )
        or json_context_meaning(json_bytes(row["analyzed_scope"])).decode()
        != reference.analyzed_scope_meaning
    ):
        raise SemanticRefusal("event reference changes its actual selected kind/context")


def _require_report_outputs(expected, acquired):
    """Find missing exact producer occurrences in one set operation per frame."""
    import pyarrow as pa

    from corpus_structure.analytics import connection

    schema = pa.schema(
        [
            ("derivation_id", pa.string()),
            ("product_id", pa.string()),
            ("member_id", pa.string()),
            ("role", pa.string()),
            ("position", pa.int64()),
            ("multiplicity", pa.int64()),
        ]
    )
    with connection() as engine:
        required = engine.from_arrow(pa.Table.from_pylist(expected, schema=schema))
        available = engine.from_arrow(pa.Table.from_pylist(list(acquired), schema=schema))
        if required.except_(available).limit(1).fetchall():
            raise SemanticRefusal(
                "event report lacks its exact selected current producing use/episode"
            )


def execute_frame_profile(receiver, question, reports, sources):
    raise SemanticRefusal("event frame requires its acquired selected-source CPU plan")


def execute_frame_kernel(
    input_basis: list, historical_capsule: str, *, prepared, check_active
) -> dict:
    from corpus_structure.semantic.cpu_execution import hydrate_capsule
    from corpus_structure.semantic.data_operation_cpu_basis import (
        cpu_authority_reply,
        cpu_basis_values,
    )
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.source_products import FrozenNativeSource
    from corpus_structure.semantic.structural_products import read_definition_components_report

    grouped, context = cpu_basis_values(
        input_basis, scalar_roles=("question",), set_roles=("reports", "sources")
    )
    check_active()
    question_role = grouped["question"][0]
    question = DdoOperationEventQuestion.model_validate_json(json_bytes(question_role.body))
    original = (
        hydrate_capsule(bytes.fromhex(historical_capsule)) if historical_capsule else prepared
    )
    if original.release_id != question.original_selection.release_id:
        raise SemanticRefusal(
            "event frame original source archive differs from its selected release"
        )
    reference = DeclaredProductRef(
        product_id=question_role.product_id,
        member_id=question_role.member_id,
        kind_contract=question_role.kind_contract,
        project_id=context.project_id,
        subject=question_role.context.subject,
        subject_definition=question_role.context.subject_definition,
        original_source=question_role.context.original_source,
        analyzed_scope_meaning=json_context_meaning(question_role.context.analyzed_scope).decode(),
    )
    reports_by_id = {
        row.product_id: read_definition_components_report(row.body) for row in grouped["reports"]
    }
    source_values = {
        canonical_bytes([row.product_id, row.member_id]).decode(): FrozenNativeSource.acquire(
            original, row.body
        )
        for row in grouped["sources"]
    }
    frame = prepare_operation_event_frame(question, reference, reports_by_id, source_values)
    check_active()
    return cpu_authority_reply(
        input_basis, DdoOperationEventFrame.capture(frame).model_dump(mode="python")
    )


@dataclass
class EventFramePlan:
    prepared: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from corpus_structure.semantic.cpu_execution import release_capsule
        from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_value
        from corpus_structure.semantic.data_operation_prepared_call import PreparedCallResult
        from corpus_structure.semantic.demand_results import (
            CutSelection,
            acquired_selected_relations,
        )
        from corpus_structure.semantic.native_definition_projection import (
            read_native_definition_projection,
        )
        from corpus_structure.semantic.releases import open_release

        check_active()
        question = DdoOperationEventQuestion.model_validate_json(
            canonical_bytes(arguments.arguments["question"])
        )
        context = binding.subject_context if binding is not None else None
        if (
            context is None
            or context.original_source is not None
            or context.project_id != question.prediction_selection.project_id
        ):
            raise SemanticRefusal(
                "event frame requires its exact project fitted-operation-event context"
            )
        _bound_members(binding, "question", scalar=True)
        reports = _bound_members(binding, "reports")
        sources = _bound_members(binding, "sources", whole=False)
        expected_reports = {row.selection.report.product_id for row in question.judgments}
        expected_sources = {
            (row.selection.source.source_product, row.selection.source.source_member)
            for row in question.judgments
        }
        actual_reports = {row.product for row in reports}
        actual_sources = {(row.product, row.member) for row in sources}
        if (
            actual_reports != expected_reports
            or len(reports) != len(expected_reports)
            or actual_sources != expected_sources
            or len(sources) != len(expected_sources)
        ):
            raise SemanticRefusal(
                "event frame bound population differs from its exact output-first question "
                f"(reports: selected={len(reports)}, distinct={len(actual_reports)}, "
                f"expected={len(expected_reports)}, values_match={actual_reports == expected_reports}; "
                f"sources: selected={len(sources)}, distinct={len(actual_sources)}, "
                f"expected={len(expected_sources)}, values_match={actual_sources == expected_sources})"
            )
        original_selection = question.original_selection
        prediction_selection = question.prediction_selection
        with execution_owner.engine.begin() as connection:
            original_prepared = open_release(connection, original_selection.release_id)
            prediction_prepared = (
                original_prepared
                if prediction_selection.release_id == original_selection.release_id
                else open_release(connection, prediction_selection.release_id)
            )
            definitions = {
                row["operation_id"]: row
                for row in read_native_definition_projection(prediction_prepared)["operations"]
            }
            original_cut = CutSelection(original_selection.cut_canonical_json.encode())
            prediction_cut = CutSelection(prediction_selection.cut_canonical_json.encode())
            source_references = tuple(
                dict.fromkeys(row.selection.source for row in question.judgments)
            )
            with acquired_selected_relations(
                connection,
                original_selection.demand_id,
                project_id=context.project_id,
                scope=original_cut.record["scope"],
                read_id=original_selection.read_id,
                expected_cut=original_selection.cut_id,
                retain_population_items=False,
            ) as (_, originals):
                source_rows = {}
                for member, body in zip(sources, arguments.arguments["sources"], strict=True):
                    row, actual = _selected_body(originals, member.product, member.member)
                    if canonical_bytes(actual) != canonical_bytes(body):
                        raise SemanticRefusal(
                            "event original source differs from actual selected body"
                        )
                    source_rows[member.product, member.member] = row
                for reference in source_references:
                    _check_selected_context(
                        source_rows[reference.source_product, reference.source_member], reference
                    )
            selected_reports = tuple(
                dict.fromkeys(
                    (
                        item.selection.use_id,
                        item.selection.derivation_id,
                        item.selection.report,
                        item.selection.producer_operation,
                        item.selection.producer_revision,
                    )
                    for item in question.judgments
                )
            )
            report_members = {member.product: member for member in reports}
            with acquired_selected_relations(
                connection,
                prediction_selection.demand_id,
                project_id=context.project_id,
                scope=prediction_cut.record["scope"],
                read_id=prediction_selection.read_id,
                expected_cut=prediction_selection.cut_id,
                capture_frontier=True,
                use_ids={use for use, *_ in selected_reports},
                retain_population_items=False,
            ) as (_, predictions):
                report_rows = {}
                for member, body in zip(reports, arguments.arguments["reports"], strict=True):
                    row, actual = _selected_body(predictions, member.product)
                    if canonical_bytes(actual) != canonical_bytes(body):
                        raise SemanticRefusal("event report differs from its actual selected body")
                    report_rows[member.product] = row
                episodes = predictions.mapping("ops.data_derivation", ("id",))
                requests = predictions.mapping("ops.data_request", ("id",))
                expected_outputs = []
                for use_id, derivation_id, report, operation, revision in selected_reports:
                    _check_selected_context(report_rows[report.product_id], report)
                    use = predictions.frontier_row("uses", use_id)
                    episode = episodes.get(derivation_id)
                    request = None if episode is None else requests.get(episode["request_id"])
                    definition = definitions.get(operation)
                    factory = (
                        None
                        if definition is None
                        else definition["support_contract"]["capabilities"].get("prepared_factory")
                    )
                    member = report_members[report.product_id]
                    output = member.producer_output
                    if (
                        use is None
                        or use["derivation_id"] != derivation_id
                        or use["completion_state"] != "success"
                        or use["fate"] not in {"fulfilled", "attached"}
                        or episode is None
                        or request is None
                        or request["operation_id"] != operation
                        or definition is None
                        or factory is None
                        or factory["entrypoint"] != _PRODUCERS[operation]
                        or episode["release_id"] != prediction_prepared.release_id
                        or episode["recipe"] != request["recipe"]
                        or definition["implementation_revision"] != revision
                        or derivation_id not in member.support_episodes
                        or output is None
                        or output.member_id is not None
                    ):
                        raise SemanticRefusal(
                            "event report lacks its exact selected current producing use/episode"
                        )
                    expected_outputs.append(
                        dict(
                            derivation_id=derivation_id,
                            product_id=report.product_id,
                            **output.model_dump(),
                        )
                    )
                acquired_outputs = tuple(
                    output
                    for derivation_id in dict.fromkeys(
                        row["derivation_id"] for row in expected_outputs
                    )
                    for output in predictions.rows_for(
                        "ops.data_derivation_output", derivation_id=derivation_id
                    )
                )
        check_active()
        _require_report_outputs(expected_outputs, acquired_outputs)
        capsule = (
            ""
            if original_prepared.release_id == self.prepared.release_id
            else release_capsule(original_prepared).hex()
        )
        input_basis = _input_basis(self.port, binding, arguments.arguments)
        bound = inspect.signature(execute_frame_kernel).bind(
            input_basis, capsule, prepared=self.prepared, check_active=check_active
        )
        reply = yield from self.port.plan_cpu_reply(
            execute_frame_kernel,
            bound,
            operation_event_operation_sources(),
            prepared_release_id=self.prepared.release_id,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        value = cpu_authority_value(reply.content, expected_basis=input_basis)
        return PreparedCallResult(
            value,
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
            cpu_execution_reply=reply.content,
        )


def execute_fit_profile(receiver, frame, specification):
    from .operation_fitting import fit_operation_event

    checked = DdoOperationEventFrame.model_validate_json(canonical_bytes(frame))
    spec = DdoOperationEventFitSpecification.model_validate_json(canonical_bytes(specification))
    return DdoOperationEventFit(
        specification=spec, result=fit_operation_event(checked.frame, spec.algorithm)
    ).model_dump(mode="json")


def execute_fit_kernel(input_basis: list, *, check_active) -> dict:
    from corpus_structure.semantic.data_operation_cpu_basis import (
        cpu_authority_reply,
        cpu_basis_values,
    )
    from corpus_structure.semantic.data_operation_json import json_bytes

    from .operation_fitting import fit_operation_event

    grouped, _ = cpu_basis_values(
        input_basis, scalar_roles=("frame", "specification"), set_roles=()
    )
    check_active()
    frame = DdoOperationEventFrame.model_validate_json(json_bytes(grouped["frame"][0].body))
    specification = DdoOperationEventFitSpecification.model_validate_json(
        json_bytes(grouped["specification"][0].body)
    )
    result = DdoOperationEventFit(
        specification=specification,
        result=fit_operation_event(frame.frame, specification.algorithm),
    )
    check_active()
    return cpu_authority_reply(input_basis, result.model_dump(mode="python"))


@dataclass
class EventFitPlan:
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_value
        from corpus_structure.semantic.data_operation_prepared_call import PreparedCallResult
        from corpus_structure.semantic.demand_results import CutSelection
        from corpus_structure.semantic.record_policy_native import read_selected_feature_fit_frame

        member = _bound_members(binding, "frame", scalar=True)[0]
        specification = DdoOperationEventFitSpecification.model_validate_json(
            canonical_bytes(arguments.arguments["specification"])
        )
        selected = specification.frame
        if (
            execution_owner.fitter_engine is None
            or selected.reference
            != DeclaredProductRef.from_bound(member, project=binding.subject_context.project_id)
            or selected.derivation_id not in member.support_episodes
        ):
            raise SemanticRefusal(
                "event fitting requires its actual selected frame and separately acquired fit purpose"
            )
        cut = CutSelection(selected.selection.cut_canonical_json.encode())
        with execution_owner.fitter_engine.begin() as connection:
            result = read_selected_feature_fit_frame(
                connection,
                variant="operation-event-frame",
                project_id=selected.selection.project_id,
                demand_id=selected.selection.demand_id,
                read_id=selected.selection.read_id,
                use_id=selected.use_id,
                product_id=selected.reference.product_id,
                derivation_id=selected.derivation_id,
                expected_cut=selected.selection.cut_id,
                frame_digest=selected.frame_digest,
                cut=cut,
            )
        if canonical_bytes(result["frame"]) != canonical_bytes(arguments.arguments["frame"]):
            raise SemanticRefusal("event fit body differs from the restricted selected frame")
        input_basis = _input_basis(self.port, binding, arguments.arguments)
        bound = inspect.signature(execute_fit_kernel).bind(input_basis, check_active=check_active)
        reply = yield from self.port.plan_cpu_reply(
            execute_fit_kernel,
            bound,
            operation_event_operation_sources(),
            execution_owner=execution_owner,
            check_active=check_active,
        )
        return PreparedCallResult(
            cpu_authority_value(reply.content, expected_basis=input_basis),
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
            cpu_execution_reply=reply.content,
        )


def execute_authorize_profile(receiver, basis):
    return operation_event_parameter_value(
        DdoOperationEventFit.model_validate_json(canonical_bytes(basis))
    ).model_dump(mode="json")


class EventAuthorizationPlan:
    def plan(self, arguments, *, binding, check_active, execution_owner):
        from corpus_structure.semantic.data_operation_prepared_call import PreparedCallResult

        yield from ()
        check_active()
        member = _bound_members(binding, "basis", scalar=True)[0]
        basis = DdoOperationEventFit.model_validate_json(
            canonical_bytes(arguments.arguments["basis"])
        )
        if (
            basis.specification.frame.selection.project_id != binding.subject_context.project_id
            or not member.support_episodes
        ):
            raise SemanticRefusal(
                "event parameter issuance differs from its actual project/protected fit"
            )
        return PreparedCallResult(operation_event_parameter_value(basis).model_dump(mode="json"))


def _acquire(prepared, model, operation, *, identity, authorize, custody, sources, variant):
    from corpus_structure.methods.operation_events import (
        OperationEventAuthorization,
        OperationEventFit,
        OperationEventFrame,
    )
    from corpus_structure.semantic.data_operation_effects import PreparedNativePublicationEffect
    from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort

    classes = {
        "frame": OperationEventFrame,
        "fit": OperationEventFit,
        "authorize": OperationEventAuthorization,
    }
    selected = model.operation(operation)
    receiver = classes[variant]()
    factory = (
        "corpus_structure.methods.operation_events." + type(receiver).__name__ + ".acquire_port"
    )
    if (
        selected.semantic_id != "operation_event." + variant
        or selected.capabilities.prepared_factory is None
        or selected.capabilities.prepared_factory.entrypoint != factory
        or selected.effects != ((AUTHORIZATION_EFFECT,) if variant == "authorize" else ())
    ):
        raise SemanticRefusal("event operation requires its exact current profile/factory/effect")
    plan: Any = (
        EventFramePlan(prepared)
        if variant == "frame"
        else EventFitPlan()
        if variant == "fit"
        else EventAuthorizationPlan()
    )
    kernel = (
        execute_frame_kernel
        if variant == "frame"
        else execute_fit_kernel
        if variant == "fit"
        else None
    )
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.evaluate.declared_operation_events." + type(plan).__name__ + ".plan",
        authorize,
        (operation_event_computation_assets(),),
        operation_event_operation_sources(),
        functions=()
        if kernel is None
        else (("corpus_structure.evaluate.declared_operation_events." + kernel.__name__, kernel),),
        retain_cpu_reply=kernel is not None,
        requires_prepared_schema=variant == "frame",
    )
    if variant != "authorize":
        plan.port = port
        return port
    return PreparedNativePublicationEffect(port)


def acquire_frame_port(prepared, model, operation, **kwargs):
    return _acquire(prepared, model, operation, variant="frame", **kwargs)


def acquire_fit_port(prepared, model, operation, **kwargs):
    return _acquire(prepared, model, operation, variant="fit", **kwargs)


def acquire_authorize_port(prepared, model, operation, **kwargs):
    return _acquire(prepared, model, operation, variant="authorize", **kwargs)


def validate_operation_event_authority_leaf(leaf, *, products, kinds, definitions, runtimes):
    """Interpret native-attributed finite parameters without disclosing private labels."""
    import re
    from dataclasses import asdict

    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_values import decode_semantic_value
    from corpus_structure.semantic.operation_policy import OperationEventParameters

    definition = definitions.get((leaf.release_id, leaf.issuer_operation))
    product = products.get(leaf.product_id)
    kind = kinds.get(leaf.kind_contract)
    if (
        leaf.issuer_operation != AUTHORIZATION_OPERATION
        or definition is None
        or product is None
        or product["kind_contract"] != leaf.kind_contract
        or kind is None
        or kind["kind"] != PARAMETERS_KIND
        or kind["universe"] != "ordinary"
        or (leaf.release_id, leaf.runtime_id) not in runtimes
    ):
        raise ValueError(
            "operation event authority differs from captured issuer and ordinary parameters"
        )
    support = definition["support_contract"]
    capability = support.get("capabilities", {})
    factory = capability.get("prepared_factory", {})
    effect = {
        **asdict(AUTHORIZATION_EFFECT),
        "authorization": list(AUTHORIZATION_EFFECT.authorization),
    }
    if (
        definition["profile"] != "command"
        or definition["recipe"] != leaf.recipe
        or support.get("effects") != [effect]
        or capability.get("preparation") != "native-publication"
        or capability.get("forms") != ["scalar"]
        or factory.get("entrypoint") != AUTHORIZATION_FACTORY
        or re.fullmatch(r"[0-9a-f]{64}", factory.get("source_digest", "")) is None
        or not definition["implementation_revision"].startswith("implementation-slice:")
    ):
        raise ValueError("operation event authority differs from captured command/effect/factory")
    OperationEventParameters.model_validate_json(
        json_bytes(decode_semantic_value(product["canonical_body"]))
    )
    return leaf


def execute_score_kernel(input_basis: list, *, check_active) -> dict:
    from corpus_structure.semantic.data_operation_cpu_basis import (
        cpu_authority_reply,
        cpu_basis_values,
    )
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_values import decode_semantic_value
    from corpus_structure.semantic.operation_policy import (
        OperationEventParameters,
        score_operation_event,
    )

    grouped, _ = cpu_basis_values(
        input_basis, scalar_roles=("parameters",), set_roles=(), sequence_roles=("features",)
    )
    parameters = OperationEventParameters.model_validate_json(
        json_bytes(grouped["parameters"][0].body)
    )
    frozen = decode_semantic_value(input_basis)["parameters"]
    check_active()
    value = score_operation_event(
        parameters,
        tuple(row.body for row in grouped["features"]),
        corpus_id=frozen["corpus_id"],
        event=frozen["event"],
        event_version=frozen["event_version"],
        producer_version=frozen["producer_version"],
    )
    check_active()
    return cpu_authority_reply(input_basis, value)


@dataclass
class EventScorePlan:
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_value
        from corpus_structure.semantic.data_operation_prepared_call import PreparedCallResult

        check_active()
        parameters = _bound_members(binding, "parameters", scalar=True)[0]
        context = binding.subject_context
        if (
            not parameters.support_episodes
            or parameters.subject != context.subject
            or parameters.subject_definition != context.subject_definition
            or parameters.original_source != context.original_source
            or json_context_meaning(parameters.analyzed_scope)
            != json_context_meaning(context.analyzed_scope)
        ):
            raise SemanticRefusal(
                "operation event scoring requires actual producing parameter-issuer support"
            )
        # Native publication checks the exact actual issuer, not merely this
        # structural preflight or the parameter body's numerical self-consistency.
        input_basis = _input_basis(self.port, binding, arguments.arguments)
        bound = inspect.signature(execute_score_kernel).bind(input_basis, check_active=check_active)
        reply = yield from self.port.plan_cpu_reply(
            execute_score_kernel,
            bound,
            operation_event_operation_sources(),
            execution_owner=execution_owner,
            check_active=check_active,
        )
        return PreparedCallResult(
            cpu_authority_value(reply.content, expected_basis=input_basis),
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
            cpu_execution_reply=reply.content,
        )


def acquire_score_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort
    from corpus_structure.semantic.operation_policy import OperationEventScore
    from corpus_structure.semantic.operation_score_sources import operation_score_sources

    selected = model.operation(operation)
    if (
        selected.semantic_id != "urn:corpus:operation:score-operation-event"
        or selected.effects
        or selected.capabilities.prepared_factory is None
        or selected.capabilities.prepared_factory.entrypoint
        != "corpus_structure.semantic.operation_policy.OperationEventScore.acquire_port"
    ):
        raise SemanticRefusal(
            "operation event score requires its exact current pure callable/factory"
        )
    plan = EventScorePlan()
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        OperationEventScore().run,
        plan.plan,
        "corpus_structure.evaluate.declared_operation_events.EventScorePlan.plan",
        authorize,
        operation_score_sources().boundary_contracts,
        operation_score_sources(),
        functions=(
            (
                "corpus_structure.evaluate.declared_operation_events.execute_score_kernel",
                execute_score_kernel,
            ),
        ),
        retain_cpu_reply=True,
    )
    plan.port = port
    return port
