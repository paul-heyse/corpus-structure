"""Invocation-owned interval access preserving the supplied product's row order."""

from bisect import bisect_left, bisect_right
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from .native_source_view import merge_touching_spans


@dataclass(frozen=True)
class PositionedRows:
    rows: tuple[tuple[int, int, int, Any], ...]
    starts: tuple[int, ...]
    maximum_ends: tuple[int, ...]
    ends: tuple[int, ...]
    ending_rows: tuple[tuple[int, int, int, Any], ...]

    @classmethod
    def build(cls, rows: Iterable, bounds: Callable[[Any], tuple[int, int]]) -> PositionedRows:
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
        ending = tuple(sorted(positioned, key=lambda row: (row[1], -row[2])))
        return cls(
            positioned,
            tuple(row[0] for row in positioned),
            tuple(ends),
            tuple(row[1] for row in ending),
            ending,
        )

    def contained(self, start: int, end: int) -> tuple[Any, ...]:
        first, last = bisect_left(self.starts, start), bisect_left(self.starts, end)
        return self._ordered(row for row in self.rows[first:last] if row[0] < row[1] <= end)

    def containing(self, start: int, end: int) -> tuple[Any, ...]:
        first = bisect_left(self.maximum_ends, end)
        last = bisect_right(self.starts, start)
        return self._ordered(row for row in self.rows[first:last] if row[1] >= end)

    def overlapping(self, start: int, end: int) -> tuple[Any, ...]:
        first = bisect_right(self.maximum_ends, start)
        last = bisect_left(self.starts, end)
        return self._ordered(row for row in self.rows[first:last] if row[1] > start)

    def nearest_enclosing(self, start: int, end: int) -> Any | None:
        candidates = (
            row
            for row in self.rows[
                bisect_left(self.maximum_ends, end) : bisect_right(self.starts, start)
            ]
            if row[1] >= end
        )
        selected = min(candidates, key=lambda row: (row[1] - row[0], row[2]), default=None)
        return None if selected is None else selected[3]

    def preceding(self, start: int) -> Any | None:
        """Nearest complete predecessor within this index's partition."""
        index = bisect_right(self.ends, start) - 1
        return self.ending_rows[index][3] if index >= 0 else None

    def following(self, end: int) -> Any | None:
        """Nearest successor within this index's partition, retaining ordinal ties."""
        index = bisect_left(self.starts, end)
        return self.rows[index][3] if index < len(self.rows) else None

    def ordinal_within(self, start: int, end: int, row: Any) -> int:
        """Original-order ordinal of a contained row, refusing a missing row."""
        return self.contained(start, end).index(row)

    @staticmethod
    def merge_touching(spans: Iterable[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
        return merge_touching_spans(spans)

    @staticmethod
    def translate(start: int, end: int, offset: int) -> tuple[int, int]:
        return start + offset, end + offset

    @staticmethod
    def _ordered(rows: Iterable[tuple[int, int, int, Any]]) -> tuple[Any, ...]:
        return tuple(row[3] for row in sorted(rows, key=lambda row: row[2]))
