"""Typed served-answer context; domain values reuse the generated stored forms."""
from __future__ import annotations
from pydantic import BaseModel,ConfigDict,Field,JsonValue
from corpus_structure.core._model.shapes import StoredCondition,StoredDescriptor,StoredValue
from corpus_structure.core.vocab import EntityScope,ClaimStatus,Polarity,StatementRole

class Answer(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)

class EvidenceLocator(Answer):
    locator:str
    start:int
    end:int
    text:str
    role:str|None=None
    sentence:str|None=None
    unit_key:str|None=None

class EntityAnswer(Answer):
    key:str
    type:str
    label:str
    kind:str|None=None
    identity:dict[str,JsonValue]=Field(default_factory=dict)
    statement_ordinal:int|None=None
    scope:EntityScope
    scope_locator:str|None=None
    locator:str|None=None
    unresolved:bool|None=None
    descriptor:StoredDescriptor|None=None
    display:str|None=None
    citation:EvidenceLocator|None=None
    resolved_to:EntityAnswer|None=None

class ClaimReference(Answer):
    kind:str
    path:str
    key:str

class EntityReference(Answer):
    role:str
    path:str
    slot:str|None=None
    entity:EntityAnswer

class ClaimAnswer(Answer):
    key:str
    predicate:str
    subject:EntityAnswer
    object:EntityAnswer|StoredValue
    qualifiers:dict[str,JsonValue]
    conditions:StoredCondition|None=None
    conditions_text:str
    modality:str
    polarity:Polarity
    attribution:EntityAnswer|None=None
    status:ClaimStatus
    statement:EntityAnswer|None=None
    role:StatementRole|None=None
    evidence:list[EvidenceLocator]
    premises:list[ClaimReference]
    entity_references:list[EntityReference]
    conditional:bool
    premise:bool

class EvidenceAnswer(EvidenceLocator):
    key:str

class FindAnswer(Answer):
    key:str
    score:float
    locator:EvidenceLocator|None=None
    entity:EntityAnswer|None=None

class TransformationAnswer(Answer):
    key:str
    conclusion:ClaimAnswer
    premises:list[ClaimAnswer]
    definiens:list[ClaimAnswer]

class RelationAnswer(Answer):
    key:str
    depth:int
    claims:list[ClaimAnswer]

class FamilyAnswer(Answer):
    key:str
    family:EntityAnswer
    claim:ClaimAnswer

class StatementAnswer(Answer):
    key:str
    ordinal:int|None=None
    statement:EntityAnswer
    claims:list[ClaimAnswer]
    proofs:list[ClaimAnswer]=Field(default_factory=list)
