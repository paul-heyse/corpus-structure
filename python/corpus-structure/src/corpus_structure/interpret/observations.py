"""Stream observations and their store (D5 §14.2).

An observation is one stream's reading of one decision: the alternatives it scored, or an
explicit abstention. It keeps what interpretation needs later: the kind of score (so the right
calibrator turns it into a likelihood ratio), the reliability grade of its input, the
correlation group it shares with other models trained on the same signal, and the provenance
variables its use introduces into a record's lineage.

The cache key covers everything that determines the output: stream, model, model version, the
full configuration hash and the input digest. Changing any of them is a new observation, never
an overwrite, so a cached observation can be reused across interpretation runs and masked out of
one to measure what its stream contributes.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from enum import StrEnum

from corpus_structure.core.canonical import make_key


class ScoreKind(StrEnum):
    """What an alternative's score means, which decides how it is calibrated."""

    PROBABILITY = "probability"  # a model probability, not necessarily calibrated
    LOGIT = "logit"  # an unnormalized log-score
    SIMILARITY = "similarity"  # a bounded similarity (cosine, overlap)
    LLR = "llr"  # already a calibrated log-likelihood ratio; used as is
    INDICATOR = "indicator"  # 1 for a deterministic rule or lookup hit


@dataclass(frozen=True, slots=True)
class Alternative:
    """One option a stream scored for a decision."""

    option: str
    score: float


@dataclass(frozen=True, slots=True)
class Observation:
    """One stream's reading of one decision, with the provenance its use carries."""

    stream: str
    group: str  # the stream group masked as one unit in the evaluation harness
    model: str
    model_version: str
    config_hash: str
    input_digest: str
    document: str
    decision: str
    decision_type: str
    score_kind: ScoreKind
    alternatives: tuple[Alternative, ...] = ()
    abstained: bool = False
    reliability_grade: str = "default"
    correlation_group: str | None = None
    tags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if self.abstained and self.alternatives:
            raise ValueError(f"{self.stream} on {self.decision}: an abstention has no alternatives")
        if not self.abstained and not self.alternatives:
            raise ValueError(
                f"{self.stream} on {self.decision}: give alternatives or abstain explicitly"
            )
        options = [alternative.option for alternative in self.alternatives]
        if len(options) != len(set(options)):
            raise ValueError(f"{self.stream} on {self.decision}: an option is scored twice")

    @property
    def cache_key(self) -> str:
        """The key under which this output is cached and reused (D1 §10.1 key form)."""
        return make_key(
            "obs",
            [
                self.stream,
                self.model,
                self.model_version,
                self.config_hash,
                self.input_digest,
                self.decision,
            ],
        )

    def score_of(self, option: str) -> float | None:
        for alternative in self.alternatives:
            if alternative.option == option:
                return alternative.score
        return None


class ObservationStore:
    """Observations indexed by decision, with masking by stream group.

    Adding an observation whose cache key is already present is refused unless it is identical,
    because a key names one output.
    """

    def __init__(self, observations: Iterable[Observation] = ()) -> None:
        self._by_key: dict[str, Observation] = {}
        self._by_decision: dict[str, list[Observation]] = defaultdict(list)
        for observation in observations:
            self.add(observation)

    def add(self, observation: Observation) -> None:
        key = observation.cache_key
        existing = self._by_key.get(key)
        if existing is not None:
            if existing != observation:
                raise ValueError(f"cache key {key} already holds a different observation")
            return
        self._by_key[key] = observation
        self._by_decision[observation.decision].append(observation)

    def __iter__(self) -> Iterator[Observation]:
        return iter(self._by_key.values())

    def __len__(self) -> int:
        return len(self._by_key)

    def get(self, cache_key: str) -> Observation | None:
        return self._by_key.get(cache_key)

    def for_decision(self, decision: str) -> tuple[Observation, ...]:
        return tuple(self._by_decision.get(decision, ()))

    @property
    def groups(self) -> frozenset[str]:
        return frozenset(observation.group for observation in self)

    @property
    def documents(self) -> frozenset[str]:
        return frozenset(observation.document for observation in self)

    def masked(self, groups: Iterable[str]) -> ObservationStore:
        """The store restricted to the given stream groups (layer masking, D5 §14.9)."""
        keep = frozenset(groups)
        return ObservationStore(o for o in self if o.group in keep)

    def for_documents(self, documents: Iterable[str]) -> ObservationStore:
        keep = frozenset(documents)
        return ObservationStore(o for o in self if o.document in keep)
