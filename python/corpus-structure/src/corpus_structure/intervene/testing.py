"""The submission harness (agent interface §3.6; D8 §2.1; D9 §4; coordinator decision 8).

`submit_batches(server, run_id, batches)` submits authored batches, each with its citation frame
and keyed by unit key, as the session would: through one in-process `Client(server)` it leases with
`queue_next`, reads every part with `read_unit` and submits with `propose_claims`. It is a product
module, not test code: the deterministic acceptance test (P0-C-3) and evaluation's live-run answers
(P0-E-2b) call it, the latter outside pytest; `submit_batches_async` is the core and
`submit_batches` its synchronous wrapper (`anyio.run`).

**Mapping ids.** The batch's sentence ids are mapped onto the served packet with its sentence map:
each frame entry matches the served entry with the same locator and text;
none, or several, stops the harness with `HarnessError` naming the unit and the id, because the
fixture does not fit the packet. Ids are then rewritten at every citation position
(`core.batch.rewrite_citations`). The stored proposal records the served frame, not the fixture's.

Units the queue serves that no batch is for stay leased by the harness until the end, so the queue
moves on, and are then released. A held-open result is returned as it is: resubmission is the
caller's decision (for fixtures, a failure to report).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import anyio
from fastmcp import Client, FastMCP

from corpus_structure.core.batch import AuthoredBatch, rewrite_citations
from corpus_structure.intervene.submission import SubmissionResult


class HarnessError(RuntimeError):
    """A batch does not fit the served packet, or the queue does not hold its unit."""


def map_ids(
    unit_key: str, frame: Mapping[str, Mapping[str, str]], served: Sequence[Mapping[str, Any]]
) -> dict[str, str]:
    """The fixture's sentence id -> the served id (module doc)."""
    out = {}
    for sid, entry in frame.items():
        found = [
            s for s in served
            if s["locator"] == entry["locator"] and s["text"] == entry["text"]
        ]
        if len(found) != 1:
            why = "no served sentence" if not found else f"{len(found)} served sentences"
            raise HarnessError(
                f"{unit_key}: {sid} ({entry['locator']}) matches {why} by locator and text"
            )
        out[sid] = found[0]["id"]
    return out


def rewrite(batch: Mapping[str, Any], mapping: Mapping[str, str], unit_key: str) -> dict[str, Any]:
    model = AuthoredBatch.model_validate(batch)

    def cite(sid: str) -> str:
        if sid not in mapping:
            raise HarnessError(f"{unit_key}: the batch cites {sid}, which its frame lacks")
        return mapping[sid]

    return rewrite_citations(model, cite).model_dump(mode="json", by_alias=True)


def _data(result: Any) -> Any:
    return result.structured_content if result.structured_content is not None else result.data


async def submit_batches_async(
    client: Client[Any],
    run_id: int,
    batches: Mapping[str, tuple[Mapping[str, Any], Mapping[str, Mapping[str, str]]]],
) -> dict[str, SubmissionResult]:
    """Submit `batches` (unit key -> (authored batch, frame)) for the run (module doc)."""
    remaining = dict(batches)
    others: list[int] = []
    results: dict[str, SubmissionResult] = {}
    try:
        while remaining:
            leased = _data(await client.call_tool("queue_next", {"run": run_id}))["tasks"]
            if not leased:
                raise HarnessError(f"run {run_id}: the queue holds no unit for {sorted(remaining)}")
            task = leased[0]
            unit_key, task_id = task["unit_key"], task["task_id"]
            if unit_key not in remaining:
                others.append(task_id)
                continue
            served: list[Mapping[str, str]] = []
            for part in range(1, task["parts"] + 1):
                read = _data(
                    await client.call_tool("read_unit", {"task_id": task_id, "part": part})
                )
                served += [s for s in read["sentences"] if s not in served]
            batch, frame = remaining.pop(unit_key)
            mapped = rewrite(batch, map_ids(unit_key, frame, served), unit_key)
            out = _data(
                await client.call_tool("propose_claims", {"task_id": task_id, "batch": mapped})
            )
            results[unit_key] = SubmissionResult.model_validate(out)
    finally:
        for task_id in others:
            await client.call_tool(
                "release",
                {"task_id": task_id, "reason": "not among the harness's batches"},
                raise_on_error=False,
            )
    return results


def submit_batches(
    server: FastMCP,
    run_id: int,
    batches: Mapping[str, tuple[Mapping[str, Any], Mapping[str, Mapping[str, str]]]],
) -> dict[str, SubmissionResult]:
    """`submit_batches_async` through one in-process client, synchronously."""

    async def main() -> dict[str, SubmissionResult]:
        async with Client(server) as client:
            return await submit_batches_async(client, run_id, batches)

    return anyio.run(main)
