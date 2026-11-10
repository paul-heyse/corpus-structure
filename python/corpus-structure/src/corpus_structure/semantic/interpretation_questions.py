"""Release-owned question declarations for private d1 interpretation."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Family = Literal[
    "passage_function_v1",
    "literal_completion_v1",
    "frame_interpretation_v1",
    "qualification_scope_v1",
    "local_referent_choice_v1",
    "relation_interpretation_v1",
    "contextual_link_assessment_v1",
]
ANSWER_READS = frozenset({"text", "number", "date"})
QUESTION_INPUT = "operation/interpretation-questions.yaml"
QUESTION_KIND = "interpretation_question_family"
Key = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,79}$")]
Description = Annotated[str, Field(min_length=1, max_length=1024)]


class _Declaration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Option(_Declaration):
    key: Key
    criterion: Description
    disposition: Literal["proposed", "no_match", "insufficient_evidence", "missing_candidate"] = (
        "proposed"
    )


class Question(_Declaration):
    key: Key
    kind: Literal["text", "number", "date", "choice", "noul"]
    instructions: Description
    explicit_only: bool = Field(default=False, exclude_if=lambda value: not value)
    options: tuple[Option, ...] = Field(default=(), max_length=16)
    multiple: bool = False
    candidate_options: bool = False
    minimum_probability: float | None = Field(default=None, ge=0, le=1)
    unit: Description | None = None
    positive: Description | None = None
    negative: Description | None = None

    @model_validator(mode="after")
    def coherent(self):
        if len({item.key for item in self.options}) != len(self.options):
            raise ValueError("duplicate released option key")
        if self.kind == "choice":
            if len(self.options) < 2:
                raise ValueError("choice requires at least two explicit alternatives")
            if self.multiple and any(option.disposition != "proposed" for option in self.options):
                raise ValueError(
                    "independent choices cannot contain exclusive unresolved alternatives"
                )
        elif self.options or self.multiple or self.candidate_options:
            raise ValueError("only a choice can supply alternatives")
        if self.kind == "noul" and (self.positive is None or self.negative is None):
            raise ValueError("binary decisions require separate positive and negative criteria")
        if self.kind != "noul" and (self.positive is not None or self.negative is not None):
            raise ValueError("binary criteria belong to a binary decision")
        if self.unit is not None and self.kind != "number":
            raise ValueError("a unit belongs to a number read")
        if self.minimum_probability is not None and self.kind != "choice":
            raise ValueError("the initial selective policy applies only to choice probabilities")
        return self

    def native(self, candidates: list[dict]) -> dict:
        result: dict[str, Any] = {"type": self.kind, "instructions": self.instructions}
        if self.kind == "choice":
            criteria = {item.key: item.criterion for item in self.options}
            if self.candidate_options:
                for candidate in candidates:
                    key = candidate["key"]
                    if key in criteria:
                        raise ValueError("candidate key collides with a released alternative")
                    criteria[key] = (
                        f"Choose the supplied candidate {key} if the source supports it."
                    )
            result.update(criteria=criteria, multiple=self.multiple)
        elif self.kind == "noul":
            result["criteria"] = {"true": self.positive, "false": self.negative}
        elif self.unit is not None:
            result["unit"] = self.unit
        return result


class QuestionFamily(_Declaration):
    family: Family
    version: Literal["1"] = "1"
    source_field: Literal["/source"] = "/source"
    questions: tuple[Question, ...] = Field(min_length=1, max_length=16)
    candidate_types: tuple[Description, ...] = Field(default=(), max_length=16)
    focus_types: tuple[Description, ...] = Field(default=(), max_length=16)
    require_focus: bool = False
    min_candidates: int = Field(default=0, ge=0, le=12)
    max_candidates: int = Field(default=12, ge=0, le=12)

    @property
    def digest(self) -> str:
        from .identity import canonical_bytes

        return sha256(canonical_bytes(self.model_dump(mode="json"))).hexdigest()

    def select_questions(self, keys: tuple[str, ...]) -> tuple[Question, ...]:
        selected = tuple(
            question
            for question in self.questions
            if (question.key in keys if keys else not question.explicit_only)
        )
        if keys and {question.key for question in selected} != set(keys):
            raise ValueError(
                "an interpretation question key is unavailable in this released family"
            )
        if not selected:
            raise ValueError("this interpretation family requires explicit question selection")
        return selected

    @model_validator(mode="after")
    def coherent(self):
        if len({item.key for item in self.questions}) != len(self.questions):
            raise ValueError("duplicate released question key")
        kinds = {item.kind for item in self.questions}
        if self.family == "passage_function_v1" and (
            self.candidate_types
            or self.focus_types
            or any(
                q.kind != "choice" or not q.multiple or q.candidate_options for q in self.questions
            )
        ):
            raise ValueError("passage function needs independent source-only choices")
        if self.family == "literal_completion_v1" and (
            kinds - ANSWER_READS or self.candidate_types or self.focus_types
        ):
            raise ValueError("literal completion requires source-only typed reads")
        if any(q.candidate_options for q in self.questions) and not self.candidate_types:
            raise ValueError("candidate choices require declared candidate types")
        if self.require_focus and not self.focus_types:
            raise ValueError("required focus needs declared source roles")
        if self.min_candidates > self.max_candidates or (
            self.min_candidates and not self.candidate_types
        ):
            raise ValueError("candidate population bounds differ from the released types")
        return self


def is_question_input(name: str) -> bool:
    return name == QUESTION_INPUT or (
        name.startswith("pack/") and name.endswith("/" + QUESTION_INPUT)
    )


def compile_question_families(artifacts):
    """Compile pack-owned declarations without consulting the runtime or reference data."""
    import yaml
    from pydantic import TypeAdapter

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.types import RegistryRow

    adapter = TypeAdapter(tuple[QuestionFamily, ...])
    result: dict[str, RegistryRow] = {}
    for artifact in artifacts:
        if not is_question_input(artifact.name):
            continue
        for family in adapter.validate_json(json.dumps(yaml.safe_load(artifact.content))):
            if family.family in result:
                raise ValueError(f"competing interpretation declarations for {family.family}")
            result[family.family] = RegistryRow(
                QUESTION_KIND, family.family, canonical_bytes(family.model_dump(mode="json"))
            )
    return tuple(result[key] for key in sorted(result))


def declared_families(rows) -> dict[str, QuestionFamily]:
    """Resolve the typed declarations retained in the exact release registry."""
    return {
        row.name: QuestionFamily.model_validate_json(row.body)
        for row in rows
        if row.kind == QUESTION_KIND
    }
