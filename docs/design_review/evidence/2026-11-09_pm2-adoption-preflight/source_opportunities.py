"""Inspect only immutable source, never extraction or retrieval results."""

import re

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

if __name__ == "__main__":
    with (
        open_runtime_engine(Settings(), "pm2-source-opportunities", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        bound = bind_completed_result(conn, 407)
        source = BoundReader(
            conn,
            407,
            bound.prepared,
            bound.completed_cut_id,
            analysis=False,
            read_budget=PublishedReadBudget(100_000, 256 * 1024 * 1024),
        ).source_view(391)
        matches = []
        for token in (
            "binomial distribution",
            "normal density function",
            "normal distribution",
            "exponential density",
            "joint cumulative distribution function",
            "the variance",
        ):
            for match in list(re.finditer(re.escape(token), source.text, re.IGNORECASE))[:20]:
                start, end = match.span()
                anchors = [p for p in source.pieces if p["start"] <= start and end <= p["end"]]
                if len(anchors) != 1:
                    continue
                a, b = max(0, start - 115), min(len(source.text), end + 125)
                matches.append(
                    dict(
                        focal=match.group(),
                        start=start,
                        end=end,
                        context_start=a,
                        context_end=b,
                        text=source.text[a:b],
                        piece=anchors[0],
                    )
                )
    print(
        canonical_bytes(
            {
                "run": 407,
                "cut": bound.completed_cut_id,
                "source_view": 391,
                "key": source.ref.key,
                "opportunities": matches,
            }
        ).decode()
    )
