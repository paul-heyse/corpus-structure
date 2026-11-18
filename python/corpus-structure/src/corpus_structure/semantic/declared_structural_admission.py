"""Ordinary conclusions from the native protected structural adjudication issuer."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .data_operation_model import EffectContract
from .declared_structural_references import DeclaredProductRef
from .identity import canonical_bytes

ADMISSION_OPERATION = "structure.admit"
ADMISSION_FACTORY = "corpus_structure.methods.structural_admission.StructuralAdmission.acquire_port"
ADMISSION_KIND = "urn:corpus:structural-admission:DdoStructuralAdmission"
REFERENCE_KIND = "urn:corpus:structural-admission:protected:DdoStructuralReferencePass"
ADMISSION_EFFECT = EffectContract(
    "native-evaluator-structural-admission",
    ("native-purpose:evaluate", "exact-protected-structural-adjudication"),
    "request-generation/exact-structural-statement",
    "native-publication-receipt",
)


class DdoStructuralAdmission(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["structural-admission-1"] = "structural-admission-1"
    report: DeclaredProductRef
    component_id: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")] | None
    policy_id: Literal[
        "independent-structural-comparison-1",
        "independent-condition-qualification-1",
        "independent-definition-component-1",
    ]
    policy_version: Literal["1"] = "1"
    statement_encoding: Literal["ddo-semantic-value-v1"] = "ddo-semantic-value-v1"
    statement_meaning_json: Annotated[str, Field(min_length=1)]
    standing: Literal["admitted_structural_statement"] = "admitted_structural_statement"
    assessment_basis: Literal["independently_attributed_authored_judgments"] = (
        "independently_attributed_authored_judgments"
    )
    scientific_truth: Literal["not_established"] = "not_established"
    member_truth: Literal["not_established_by_assembly_admission"] = (
        "not_established_by_assembly_admission"
    )

    @model_validator(mode="after")
    def exact_statement(self):
        from .data_operation_identity import semantic_value
        from .structural_admission import POLICIES

        value = self.statement
        if (
            canonical_bytes(semantic_value(value)).decode() != self.statement_meaning_json
            or value.get("kind")
            not in {"qualified_comparison", "condition_qualification", "definition_components"}
            or value.get("version") != "structural-public-statement-3"
            or self.policy_id != POLICIES.get(value.get("kind"))
            or (self.component_id is not None) != (value.get("kind") == "definition_components")
        ):
            raise ValueError("structural admission differs from its exact canonical statement")
        return self

    @property
    def statement(self):
        import json

        from .data_operation_identity import decode_semantic_value

        value = decode_semantic_value(json.loads(self.statement_meaning_json))
        if not isinstance(value, dict):
            raise ValueError("structural statement requires its tagged mapping")
        return value


def structural_admission_kind_declarations():
    from .data_operation_model import MODEL_VERSION
    from .nominal_schema_kinds import nominal_schema_kinds
    from .types import SourceArtifact

    return SourceArtifact(
        "structural-admission/public-kinds.json",
        canonical_bytes(
            dict(
                version=MODEL_VERSION,
                kinds=nominal_schema_kinds(
                    DdoStructuralAdmission.model_json_schema(),
                    namespace="urn:corpus:structural-admission:",
                    root_name="DdoStructuralAdmission",
                ),
            )
        ),
    )


def structural_admission_assets():
    from pathlib import Path

    from .python_module_projection import admitted_operation_module_meaning
    from .types import SourceArtifact

    root = Path(__file__).parents[1]
    paths = (
        "methods/structural_admission.py",
        "semantic/declared_structural_admission.py",
        "evaluate/declared_structural_admission.py",
        "semantic/structural_admission.py",
        "semantic/structural_products.py",
        "semantic/declared_structural_references.py",
        "semantic/structural_admission_native.py",
    )
    return SourceArtifact(
        "structural-admission/assets",
        canonical_bytes(
            dict(
                version="structural-admission-preparation-1",
                files=[
                    (path, admitted_operation_module_meaning((root / path).read_bytes()).hex())
                    for path in paths
                ],
            )
        ),
    )


def structural_admission_sources():
    from pathlib import Path

    from .python_operation_sources import PythonSource, PythonSourceCollection

    root = Path(__file__).parents[1]
    paths = (
        "methods/structural_admission.py",
        "semantic/declared_structural_admission.py",
        "evaluate/declared_structural_admission.py",
        "semantic/data_operation_effects.py",
        "semantic/data_operation_prepared_call.py",
    )
    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + path.removesuffix(".py").replace("/", "."),
                (root / path).read_bytes(),
                str((root / path).resolve()),
            )
            for path in paths
        ),
        boundary_contracts=(structural_admission_assets(),),
    )


class StructuralAdmissionInvocationPlan:
    def plan(self, arguments, *, binding, check_active, execution_owner):
        from corpus_structure.evaluate.declared_structural_admission import (
            structural_admission_value,
        )

        from .data_operation_prepared_call import PreparedCallResult
        from .declared_structural_references import DeclaredProductRef

        yield from ()
        check_active()
        if binding is None or not binding.sufficient or binding.subject_context is None:
            raise ValueError("structural admission requires its actual sufficient native binding")
        roles = {role.role: role for role in binding.roles}
        selected_reports = [
            role for name, role in roles.items() if name != "passes" and role.members
        ]
        if (
            set(roles) != {"comparison", "condition", "definition", "passes"}
            or len(selected_reports) != 1
            or len(selected_reports[0].members) != 1
            or len(roles["passes"].members) != 3
        ):
            raise ValueError("structural admission requires exact report and three original passes")
        report_member = selected_reports[0].members[0]
        if any(
            member.member is not None or member.multiplicity != 1
            for role in roles.values()
            for member in role.members
        ):
            raise ValueError("structural admission consumes exact whole scalar products")
        values = arguments.arguments
        references = tuple(
            DeclaredProductRef.from_bound(member, project=binding.subject_context.project_id)
            for member in roles["passes"].members
        )
        result = structural_admission_value(
            values[selected_reports[0].role], values["passes"], references=references
        )
        expected = DeclaredProductRef.from_bound(
            report_member, project=binding.subject_context.project_id
        )
        if result.report != expected:
            raise ValueError(
                "structural adjudication report address differs from actual native input"
            )
        return PreparedCallResult(result.model_dump(mode="json"))


def acquire_structural_admission_port(
    prepared, model, operation, *, identity, authorize, custody, sources
):
    from corpus_structure.methods.structural_admission import StructuralAdmission

    from .data_operation_effects import PreparedNativePublicationEffect
    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if (
        selected.semantic_id != ADMISSION_OPERATION
        or selected.effects != (ADMISSION_EFFECT,)
        or selected.capabilities.prepared_factory is None
        or selected.capabilities.prepared_factory.entrypoint != ADMISSION_FACTORY
    ):
        raise PortRefusal("structural issuer requires its exact command/effect/factory")
    receiver = StructuralAdmission()
    plan = StructuralAdmissionInvocationPlan()
    return PreparedNativePublicationEffect(
        PreparedOriginalCallPort(
            identity,
            model,
            selected,
            sources,
            custody,
            receiver.run,
            plan.plan,
            "corpus_structure.semantic.declared_structural_admission.StructuralAdmissionInvocationPlan.plan",
            authorize,
            (structural_admission_assets(),),
            structural_admission_sources(),
        )
    )


def validate_structural_authority_leaf(leaf, *, products, kinds, definitions, runtimes):
    """Interpret an authenticated disclosure; never validate undisclosed adjudication."""
    from dataclasses import asdict

    from .data_operation_identity import decode_semantic_value
    from .data_operation_json import json_bytes

    definition = definitions.get((leaf.release_id, leaf.issuer_operation))
    product = products.get(leaf.product_id)
    kind = kinds.get(leaf.kind_contract)
    if (
        leaf.issuer_operation != ADMISSION_OPERATION
        or definition is None
        or product is None
        or product["kind_contract"] != leaf.kind_contract
        or kind is None
        or kind["kind"] != ADMISSION_KIND
        or kind["universe"] != "ordinary"
        or (leaf.release_id, leaf.runtime_id) not in runtimes
    ):
        raise ValueError(
            "structural authority differs from its captured issuer and ordinary conclusion"
        )
    support = definition["support_contract"]
    capability = support.get("capabilities", {})
    effect = {**asdict(ADMISSION_EFFECT), "authorization": list(ADMISSION_EFFECT.authorization)}
    if (
        definition["profile"] != "command"
        or definition["recipe"] != leaf.recipe
        or support.get("effects") != [effect]
        or capability.get("preparation") != "native-publication"
        or capability.get("forms") != ["scalar"]
        or capability.get("prepared_factory", {}).get("entrypoint") != ADMISSION_FACTORY
    ):
        raise ValueError("structural authority differs from its captured command/effect/factory")
    DdoStructuralAdmission.model_validate_json(
        json_bytes(decode_semantic_value(product["canonical_body"]))
    )
    return leaf


STRUCTURAL_REPORT_PRODUCERS = {
    "qualified_comparison": (
        (
            "structure.compare/declared",
            "corpus_structure.methods.structural_declared.DeclaredStructuralComparison.acquire_port",
        ),
    ),
    "condition_qualification": (
        (
            "structure.condition_qualification/declared",
            "corpus_structure.methods.structural_declared.DeclaredConditionQualification.acquire_port",
        ),
    ),
    "definition_components": (
        (
            "structure.definition_components/declared",
            "corpus_structure.methods.definition_components_declared.DefinitionComponentsOperation.acquire_port",
        ),
        (
            "structure.definition_declaration_components/declared",
            "corpus_structure.methods.definition_declared.DefinitionDeclarationOperation.acquire_port",
        ),
        (
            "structure.definition_named_components/declared",
            "corpus_structure.methods.definition_named_declared.NamedDefinitionComponentsOperation.acquire_port",
        ),
    ),
}


def validate_structural_report_support(
    edge,
    *,
    leaf,
    products,
    kinds,
    uses,
    episodes,
    outputs,
    requests,
    definitions,
    intents,
    receipts,
):
    """Validate the one disclosed ordinary report edge of a bounded native issuer.

    Authentic native acquisition owns visibility and trust. Detached validation
    checks captured meaning/custody; it cannot attest current permission or trust.
    No protected issuer request, frame, actor or parent is required or disclosed.
    """
    import re

    # Leaf authenticity/runtime visibility is supplied by the existing native
    # acquisition or detached validate_authority_leaf owner before this projection.
    from .authority_leaf import NativeAuthorityLeaf
    from .data_operation_identity import decode_semantic_value, semantic_value
    from .data_operation_json import json_bytes
    from .data_operation_model import json_context_meaning
    from .structural_admission import structural_statement
    from .structural_products import (
        DeclaredComparisonReport,
        DeclaredConditionReport,
        DeclaredDefinitionComponentsReport,
    )

    leaf = NativeAuthorityLeaf.model_validate(leaf)
    conclusion = products[leaf.product_id]
    conclusion_kind = kinds[conclusion["kind_contract"]]
    if (
        leaf.issuer_operation != ADMISSION_OPERATION
        or leaf.kind_contract != conclusion["kind_contract"]
        or conclusion_kind["kind"] != ADMISSION_KIND
        or conclusion_kind["universe"] != "ordinary"
    ):
        raise ValueError(
            "structural report support requires its authenticated structural authority"
        )
    value = DdoStructuralAdmission.model_validate_json(
        json_bytes(decode_semantic_value(conclusion["canonical_body"]))
    )
    variant = value.statement["kind"]
    role = {
        "qualified_comparison": "comparison",
        "condition_qualification": "condition",
        "definition_components": "definition",
    }[variant]
    nominal, report_type = {
        "qualified_comparison": (
            "urn:corpus:structural:DeclaredComparisonReport",
            DeclaredComparisonReport,
        ),
        "condition_qualification": (
            "urn:corpus:structural:DeclaredConditionReport",
            DeclaredConditionReport,
        ),
        "definition_components": (
            "urn:corpus:structural:DeclaredDefinitionComponentsReport",
            DeclaredDefinitionComponentsReport,
        ),
    }[variant]
    used = uses.get(edge.get("admission_use_id"))
    episode = episodes.get(edge.get("support_derivation_id"))
    product = products.get(value.report.product_id)
    if (
        leaf.standing != "valid"
        or edge.get("derivation_id") != leaf.derivation_id
        or edge.get("role") != role
        or edge.get("position") != 0
        or value.report.member_id is not None
        or used is None
        or used.get("fate") != "fulfilled"
        or episode is None
        or used.get("derivation_id") != episode["id"]
        or episode.get("outcome") != "success"
        or product is None
    ):
        raise ValueError("structural report support differs from exact ordinary issuer/use/episode")
    kind = kinds.get(product["kind_contract"])
    actual = DeclaredProductRef(
        product_id=product["id"],
        member_id=None,
        kind_contract=product["kind_contract"],
        project_id=product["project_id"],
        subject=product["subject"],
        subject_definition=product["subject_definition"],
        original_source=product["original_source"],
        analyzed_scope_meaning=json_context_meaning(json_bytes(product["analyzed_scope"])).decode(),
    )
    selected_outputs = [
        row
        for row in outputs
        if row["derivation_id"] == episode["id"] and row["product_id"] == product["id"]
    ]
    if (
        actual != value.report
        or product["project_id"] != conclusion["project_id"]
        or kind is None
        or kind["kind"] != nominal
        or kind["universe"] != "ordinary"
        or len(selected_outputs) != 1
        or any(
            selected_outputs[0][name] != expected
            for name, expected in (
                ("role", "result"),
                ("position", 0),
                ("multiplicity", 1),
                ("member_id", None),
            )
        )
    ):
        raise ValueError("structural report support substitutes its exact kind/context/output")
    request = requests.get(episode["request_id"])
    definition = (
        None
        if request is None
        else definitions.get((episode["release_id"], request["operation_id"]))
    )
    capability = (
        {} if definition is None else definition["support_contract"].get("capabilities", {})
    )
    factory = capability.get("prepared_factory", {})
    intent = intents.get(episode["intent_id"])
    actual_receipts = [
        row
        for row in receipts
        if row["derivation_id"] == episode["id"] and row["intent_id"] == episode["intent_id"]
    ]
    if (
        request is None
        or request["project_id"] != product["project_id"]
        or definition is None
        or definition["profile"] != "derivation"
        or definition["recipe"] != episode["recipe"]
        or definition["support_contract"].get("effects") != []
        or (request["operation_id"], factory.get("entrypoint"))
        not in STRUCTURAL_REPORT_PRODUCERS[variant]
        or re.fullmatch("[a-f0-9]{64}", factory.get("source_digest", "")) is None
        or intent is None
        or intent["payload"].get("implementation_revision") != definition["implementation_revision"]
        or len(intent["payload"].get("execution_evidence", {}).get("cpu_receipts", [])) != 1
        or len(actual_receipts) != 1
    ):
        raise ValueError("structural report support lacks its actual captured producer/CPU receipt")
    report = report_type.model_validate(decode_semantic_value(product["canonical_body"]))
    if (
        value.statement_meaning_json
        != canonical_bytes(
            semantic_value(structural_statement(report, value.component_id))
        ).decode()
    ):
        raise ValueError("structural report support differs from exact whole statement")
    return value, used, episode, selected_outputs[0]
