"""Invocation-owned interval access preserving the supplied product's row order."""

from bisect import bisect_left, bisect_right
from collections.abc import Callable, Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionedRows[T]:
    rows: tuple[tuple[int, int, int, T], ...]
    starts: tuple[int, ...]
    maximum_ends: tuple[int, ...]

    @classmethod
    def build(cls, rows: Iterable[T], bounds: Callable[[T], tuple[int, int]]) -> PositionedRows[T]:
        positioned = tuple(
            sorted(
                ((*bounds(row), ordinal, row) for ordinal, row in enumerate(rows)),
                key=lambda row: (row[0], row[2]),
            )
        )
        maximum, ends = -1, []
        for _start, end, _ordinal, _row in positioned:
            maximum = max(maximum, end)
            ends.append(maximum)
        return cls(positioned, tuple(row[0] for row in positioned), tuple(ends))

    def contained(self, start: int, end: int) -> tuple[T, ...]:
        first, last = bisect_left(self.starts, start), bisect_left(self.starts, end)
        return self._ordered(row for row in self.rows[first:last] if row[0] < row[1] <= end)

    def containing(self, start: int, end: int) -> tuple[T, ...]:
        first = bisect_left(self.maximum_ends, end)
        last = bisect_right(self.starts, start)
        return self._ordered(row for row in self.rows[first:last] if row[1] >= end)

    def overlapping(self, start: int, end: int) -> tuple[T, ...]:
        first = bisect_right(self.maximum_ends, start)
        last = bisect_left(self.starts, end)
        return self._ordered(row for row in self.rows[first:last] if row[1] > start)

    @staticmethod
    def _ordered(rows: Iterable[tuple[int, int, int, T]]) -> tuple[T, ...]:
        return tuple(row[3] for row in sorted(rows, key=lambda row: row[2]))
