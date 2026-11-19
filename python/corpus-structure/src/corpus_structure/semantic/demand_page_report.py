"""Owned native-demand page reporting over already acquired presentation inputs."""

from __future__ import annotations

from dataclasses import dataclass

from .continuation_codec import encode_cursor


@dataclass(frozen=True)
class DemandPageReport:
    """One page's fixed envelope and its exact current and following cursor bases."""

    header: dict
    current_cursor: dict
    following_cursor: str | None

    def render(self, end: int, values: list, more: bool) -> dict:
        continuation = (
            encode_cursor(dict(self.current_cursor, ordinal=end)) if more else self.following_cursor
        )
        return dict(
            self.header,
            items=values,
            knowledge="observed" if values else "unknown",
            continuation=continuation,
            page_complete=continuation is None,
        )
