"""Closed typed identity, eligibility and scientific selection results for rich graphs."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Nonempty = Annotated[str, Field(min_length=1)]
RuleOutcome = Literal["passed", "failed", "not-applicable", "not-checkable"]
RuleSeverity = Literal["error", "warning"]
OccurrenceStatus = Literal["accepted", "rejected", "ambiguous", "candidate"]
IdentityBasis = Literal["declared_key", "global_label", "source_local"]
IdentityOutcome = Literal["resolved", "incomplete_key", "ambiguous_anchor", "ungrounded_cycle"]


class RichDecisionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DdoRichRuleFinding(RichDecisionRecord):
    rule: Nonempty
    outcome: RuleOutcome
    severity: RuleSeverity
    assessment_id: Nonempty | None


class DdoRichOccurrenceDecision(RichDecisionRecord):
    member_type: Literal["occurrence-decision"]
    decision_id: Nonempty
    occurrence_id: Nonempty
    fact_id: Nonempty
    status: OccurrenceStatus
    findings: tuple[DdoRichRuleFinding, ...]


class DdoRichScientificRepresentative(RichDecisionRecord):
    fact_id: Nonempty
    representative_fact_id: Nonempty
    component_id: Nonempty
    policy: Literal["min-fact-id-1"]


class DdoRichEligibility(RichDecisionRecord):
    eligibility_policy_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    selected_fact_ids: tuple[Nonempty, ...]
    selected_occurrence_ids: tuple[Nonempty, ...]
    scientific_representatives: tuple[DdoRichScientificRepresentative, ...]

    @model_validator(mode="after")
    def actual_canonical_sets(self):
        require_selected_sets(self.selected_fact_ids, self.selected_occurrence_ids)
        facts = tuple(item.fact_id for item in self.scientific_representatives)
        if facts != tuple(sorted(set(facts))):
            raise ValueError("scientific representative rows must identify unique ordered actual facts")
        return self


def require_selected_sets(*selections):
    for selected in selections:
        if selected != tuple(sorted(set(selected))):
            raise ValueError("rich selection requires unique ordered actual member identities")
