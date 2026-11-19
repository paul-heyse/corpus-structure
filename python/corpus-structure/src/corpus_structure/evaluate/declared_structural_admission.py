"""Protected, independently attributed structural statements over exact native inputs.

Authored attribution is preserved as such. These values do not attest that a provider
executed, nor does possession of them grant ordinary publication authority.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from corpus_structure.semantic.data_operation_identity import body_identity
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.declared_structural_references import DeclaredProductRef
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_admission import POLICIES, structural_statement
from corpus_structure.semantic.structural_products import (
    DeclaredComparisonReport,
    DeclaredConditionReport,
    DeclaredDefinitionComponentsReport,
    DeclaredStructuralInput,
)

Nonempty = Annotated[str, Field(min_length=1)]


class StructuralAssessmentValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DdoStructuralActor(StructuralAssessmentValue):
    principal: Nonempty
    session_id: Nonempty
    basis: Literal["authored_attribution"]


class DdoStructuralAssessmentFrame(StructuralAssessmentValue):
    report: DeclaredProductRef
    inputs: DeclaredStructuralInput
    question: Nonempty
    case_id: Nonempty
    operation: Literal["qualified_comparison", "condition_qualification", "definition_components"]
    component_id: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")] | None
    rubric_version: Literal[
        "independent-structural-comparison-1",
        "independent-condition-qualification-1",
        "independent-definition-component-1",
    ]
    direction: Literal["source_first", "output_first"]
    exposed_outputs: tuple[DeclaredProductRef, ...]

    @model_validator(mode="after")
    def exact_exposure(self):
        if self.rubric_version != POLICIES[self.operation]:
            raise ValueError("structural rubric differs from its actual report variant")
        if (self.component_id is not None) != (self.operation == "definition_components"):
            raise ValueError(
                "only definition component admission requires one exact component selector"
            )
        if self.question != self.inputs.question:
            raise ValueError("structural frame question differs from its selected source question")
        if self.direction == "source_first" and self.exposed_outputs:
            raise ValueError("source-first structural frame cannot declare exposed outputs")
        if self.direction == "output_first" and not any(
            value == self.report for value in self.exposed_outputs
        ):
            raise ValueError("output-first structural frame requires its exact frozen report")
        if any(source.project_id != self.report.project_id for source in self.inputs.sources):
            raise ValueError("structural frame crosses its exact source project")
        return self


class DdoStructuralPassParent(StructuralAssessmentValue):
    reference: DeclaredProductRef
    body_digest: Nonempty


class DdoStructuralReferenceCase(StructuralAssessmentValue):
    case_id: Nonempty
    facet: Literal["public_statement"]
    path: tuple[Literal["public_statement"], ...]
    judgment: Literal["supported", "unsupported", "ambiguous", "unassessed"]
    expected_meaning_json: Nonempty
    source_passages: tuple[Nonempty, ...]

    @model_validator(mode="after")
    def exact_case(self):
        import json

        from corpus_structure.semantic.data_operation_values import decode_semantic_value

        if self.path != ("public_statement",) or len(set(self.source_passages)) != len(
            self.source_passages
        ):
            raise ValueError(
                "structural case requires its exact facet and distinct source passages"
            )
        value = decode_semantic_value(json.loads(self.expected_meaning_json))
        if (
            not isinstance(value, dict)
            or canonical_bytes(semantic_value(value)).decode() != self.expected_meaning_json
        ):
            raise ValueError("structural case requires its canonical tagged object expectation")
        return self


class DdoStructuralReferencePass(StructuralAssessmentValue):
    version: Literal["structural-reference-pass-1"]
    frame: DdoStructuralAssessmentFrame
    pass_kind: Literal["A", "B", "C"]
    actor: DdoStructuralActor
    author_assertion: Nonempty
    parents: tuple[DdoStructuralPassParent, ...]
    cases: Annotated[tuple[DdoStructuralReferenceCase, ...], Field(min_length=1, max_length=1)]

    @model_validator(mode="after")
    def exact_pass(self):
        if self.author_assertion != self.actor.principal:
            raise ValueError("structural actor differs from its submitted author assertion")
        if self.pass_kind in {"A", "B"} and self.parents:
            raise ValueError("independent A/B passes cannot declare adjudication parents")
        if self.pass_kind == "C" and (
            len(self.parents) != 2
            or len(
                {
                    (parent.reference.product_id, parent.reference.member_id)
                    for parent in self.parents
                }
            )
            != 2
        ):
            raise ValueError("C requires its two distinct exact A/B parents")
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("structural pass repeats a case identity")
        if self.cases[0].case_id != self.frame.case_id:
            raise ValueError("structural pass substitutes its frozen whole-statement case")
        return self


def structural_admission_value(report, passes, *, references=None):
    """Compute a permitted conclusion; native completion authenticates its authority."""
    from corpus_structure.semantic.declared_structural_admission import DdoStructuralAdmission

    checked = TypeAdapter(
        Annotated[
            DeclaredComparisonReport | DeclaredConditionReport | DeclaredDefinitionComponentsReport,
            Field(discriminator="kind"),
        ]
    ).validate_python(report)
    typed = tuple(DdoStructuralReferencePass.model_validate(value) for value in passes)
    by_kind = {value.pass_kind: value for value in typed}
    if len(typed) != 3 or set(by_kind) != {"A", "B", "C"}:
        raise ValueError("structural admission requires exact A/B/C pass population")
    c = by_kind["C"]
    if len({(value.actor.principal, value.actor.session_id) for value in typed}) != 3:
        raise ValueError("structural A/B/C require independently attributed actor identities")
    if any(value.frame != c.frame for value in typed):
        raise ValueError("structural A/B/C differ from their exact frozen frame")
    if c.frame.inputs != checked.inputs or c.frame.operation != checked.kind:
        raise ValueError("structural adjudication differs from its exact report and source inputs")
    actual = {
        value.pass_kind: body_identity(raw).key for raw, value in zip(passes, typed, strict=True)
    }
    if {parent.body_digest for parent in c.parents} != {actual["A"], actual["B"]}:
        raise ValueError("C does not adjudicate the exact original A/B body identities")
    if references is not None:
        # The acquired binding supplies these addresses; caller labels cannot.
        actual_parents = {
            canonical_bytes(
                dict(
                    reference=reference.model_dump(mode="json"), body_digest=body_identity(raw).key
                )
            )
            for raw, value, reference in zip(passes, typed, references, strict=True)
            if value.pass_kind in {"A", "B"}
        }
        if {
            canonical_bytes(parent.model_dump(mode="json")) for parent in c.parents
        } != actual_parents:
            raise ValueError("C parent references differ from the actual admitted A/B products")
    statement = structural_statement(checked, component_id=c.frame.component_id)
    meaning = canonical_bytes(semantic_value(statement)).decode()
    matches = tuple(
        case
        for case in c.cases
        if case.judgment == "supported" and case.expected_meaning_json == meaning
    )
    if len(matches) != 1:
        raise ValueError("structural admission requires one exact supported whole statement")
    if not {passage.passage_id for passage in checked.inputs.passages} <= set(
        matches[0].source_passages
    ):
        raise ValueError("structural support omits a selected source passage")
    return DdoStructuralAdmission.model_validate(
        dict(
            report=c.frame.report,
            component_id=c.frame.component_id,
            policy_id=POLICIES[checked.kind],
            statement_meaning_json=meaning,
        )
    )


def structural_reference_kind_declarations():
    from corpus_structure.semantic.data_operation_model import MODEL_VERSION
    from corpus_structure.semantic.nominal_schema_kinds import nominal_schema_kinds
    from corpus_structure.semantic.types import SourceArtifact

    return SourceArtifact(
        "structural-admission/protected-kinds.json",
        canonical_bytes(
            dict(
                version=MODEL_VERSION,
                kinds=[
                    dict(value, universe="evaluator")
                    for value in nominal_schema_kinds(
                        DdoStructuralReferencePass.model_json_schema(),
                        namespace="urn:corpus:structural-admission:protected:",
                        root_name="DdoStructuralReferencePass",
                    )
                ],
            )
        ),
    )
