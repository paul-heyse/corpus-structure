"""Ordinary conclusions from the native protected structural adjudication issuer."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .data_operation_model import EffectContract
from .declared_structural_references import DeclaredProductRef
from .identity import canonical_bytes

ADMISSION_OPERATION = "structure.admit_comparison"
ADMISSION_FACTORY = (
    "corpus_structure.methods.structural_admission.StructuralComparisonAdmission.acquire_port"
)
ADMISSION_KIND = "urn:corpus:structural-admission:DdoStructuralAdmission"
REFERENCE_KIND = "urn:corpus:structural-admission:protected:DdoStructuralReferencePass"
ADMISSION_EFFECT = EffectContract(
    "native-evaluator-structural-admission",
    ("native-purpose:evaluator", "exact-protected-structural-adjudication"),
    "request-generation/exact-structural-statement",
    "native-publication-receipt",
)


class DdoStructuralAdmission(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["structural-admission-1"] = "structural-admission-1"
    report: DeclaredProductRef
    policy_id: Literal["independent-structural-comparison-1"] = (
        "independent-structural-comparison-1"
    )
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

        value = self.statement
        if (
            canonical_bytes(semantic_value(value)).decode() != self.statement_meaning_json
            or value.get("kind") != "qualified_comparison"
            or value.get("version") != "structural-public-statement-3"
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
        if (
            set(roles) != {"report", "passes"}
            or len(roles["report"].members) != 1
            or len(roles["passes"].members) != 3
        ):
            raise ValueError("structural admission requires exact report and three original passes")
        report_member = roles["report"].members[0]
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
            values["report"], values["passes"], references=references
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
    from corpus_structure.methods.structural_admission import StructuralComparisonAdmission

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
    receiver = StructuralComparisonAdmission()
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
