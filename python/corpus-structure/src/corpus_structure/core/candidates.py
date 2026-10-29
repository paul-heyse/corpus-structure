"""The keyed candidate set: the complete core claim shape the rule-view builder and keying read.

D5 §8.2; foundations §3.5 (F2e: R04, DA-005, DA-006, DA-007); target model §3, §7. S2's batch
adapter (T2, at submission) and C1's pool loader (T3, at finalize) both produce it, and its
translations are declared in `core/translations.py`. It carries the whole batch:

- the renditions its offsets and segment keys are on, by their `ren` keys (`renditions`: one for a
  batch's set and for keying, every rendition of the run at finalize), so no reader
  needs a context supplied on the side; keying checks it against its `KeyContext`;
- entities, statements, `ExternalReference` nodes (`references`), claims with their
  `establishment`, `derived_from` and `rule`, alternatives and unsupported items.

At submission ids are local refs and keys are `UNKEYED`; at finalize ids are keys. An
`ExternalReference` awaiting consolidation's resolution is `AWAITING`. Both are typed states, never
`None`, and every optional field is absent by `MISSING`. References are typed by kind
(`EntityId`, `StatementId`, `ClaimId`, `SubjectId`). It is in stored form: classes, predicates,
qualifiers, identity slots and enums by their prefixed names; values and evidence as stored. The
grammar's facts at finalize and the derived view attributes are the view builder's arguments, not
fields here.

The classes are generated from the model's candidate classes (`_model/shapes.py`, Stage B,
P0-M-5; ADR-0020) and re-exported here with the typed states `UNKEYED` and `AWAITING`.
"""

from __future__ import annotations

from typing import Literal

from corpus_structure.core._model.shapes import (
    CandidateAlternative,
    CandidateClaim,
    CandidateEntity,
    CandidateReference,
    CandidateStatement,
    CandidateUnsupported,
    KeyedCandidateSet,
)
from corpus_structure.core._model.types import (
    ClaimKey,
    EntityKey,
    NonEmpty,
    ReferenceKey,
    StatementKey,
)
from corpus_structure.core.vocab import Awaiting, Unkeyed

__all__ = [
    "AWAITING", "UNKEYED", "Awaiting", "CandidateAlternative", "CandidateClaim", "CandidateEntity",
    "CandidateReference", "CandidateStatement", "CandidateUnsupported", "ClaimKey", "EntityKey",
    "Id", "KeyedCandidateSet", "ReferenceKey", "StatementKey", "Unkeyed",
]  # fmt: skip

Id = NonEmpty
UNKEYED: Literal[Unkeyed.UNKEYED] = Unkeyed.UNKEYED
AWAITING: Literal[Awaiting.AWAITING] = Awaiting.AWAITING
