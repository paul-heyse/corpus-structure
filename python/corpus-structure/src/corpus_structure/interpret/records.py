"""Record types and their acceptance thresholds (D5 §14.1).

Each record type carries the value `v` of accepting a correct record and the cost `c` of
accepting a wrong one. Accepting a record whose posterior probability is `p` has expected
utility `p v - (1 - p) c`, which is positive exactly when `p > c / (c + v)`. That ratio is the
type's threshold `tau`; it replaces a single global confidence cut-off. The values are policy
data held beside the predicate-group thresholds of D5 §6, not constants in code.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RecordType:
    """One kind of record the layer can accept, with its value and error cost."""

    name: str
    value: float
    cost: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("a record type needs a name")
        if self.value <= 0 or self.cost <= 0:
            raise ValueError(f"{self.name}: value and cost must be positive")

    @property
    def threshold(self) -> float:
        """The posterior probability above which accepting has positive expected utility."""
        return self.cost / (self.cost + self.value)


class RecordRegistry(Mapping[str, RecordType]):
    """The record types in force, by name."""

    def __init__(self, types: Iterable[RecordType] = ()) -> None:
        self._types: dict[str, RecordType] = {}
        for record_type in types:
            self.register(record_type)

    def register(self, record_type: RecordType) -> None:
        if record_type.name in self._types:
            raise ValueError(f"record type {record_type.name!r} is already registered")
        self._types[record_type.name] = record_type

    def __getitem__(self, name: str) -> RecordType:
        try:
            return self._types[name]
        except KeyError:
            raise KeyError(f"unknown record type {name!r}") from None

    def __iter__(self) -> Iterator[str]:
        return iter(self._types)

    def __len__(self) -> int:
        return len(self._types)
