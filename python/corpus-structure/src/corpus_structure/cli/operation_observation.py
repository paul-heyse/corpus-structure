"""Bounded attributed facts shared by operational JSON and terminal views."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .observations import Bindings, ObservationPage

Phase = Literal[
    "loading", "ready", "inference_submitted", "inference_completed", "settlement", "publication"
]


class PhaseFact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    phase: Phase
    standing: Literal["unknown", "observed", "stale"] = "unknown"
    observed_at: str | None = None
    source: str | None = None
    assurance: Literal["native", "provider_reported", "observation"] | None = None
    bindings: Bindings | None = None


class ScopedCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    value: int
    unit: str
    scope: str
    source: str
    read_id: str | None = None
    complete: bool = False


class OperationalObservation(BaseModel):
    version: Literal[1] = 1
    observed_at: str
    phases: tuple[PhaseFact, ...]
    counts: tuple[ScopedCount, ...] = ()
    coverage: str
    omissions: tuple[str, ...] = ()


def operational_observation(
    page: ObservationPage, native, *, running: bool
) -> OperationalObservation:
    """Project only structured owner facts; missing phases remain unknown."""
    latest = {}
    for row in page.rows:
        phase = row.fields.get("operational_phase")
        if phase in (
            "loading",
            "ready",
            "inference_submitted",
            "inference_completed",
            "settlement",
            "publication",
        ):
            latest[phase] = row
    now = datetime.now(UTC)
    phases = []
    for phase in (
        "loading",
        "ready",
        "inference_submitted",
        "inference_completed",
        "settlement",
        "publication",
    ):
        row = latest.get(phase)
        if row is None:
            phases.append(PhaseFact(phase=phase))
            continue
        try:
            timestamp = datetime.fromisoformat(row.timestamp.replace("Z", "+00:00"))
            stale = running and (timestamp.tzinfo is None or (now - timestamp).total_seconds() > 30)
        except ValueError:
            stale = True
        phases.append(
            PhaseFact(
                phase=phase,
                standing="stale" if stale else "observed",
                observed_at=row.timestamp,
                source=row.producer,
                assurance=row.assurance,
                bindings=row.bindings,
            )
        )
    counts = []
    if native.availability == "available" and native.demand is not None:
        snapshot = native.demand
        for name, unit in (("obligations", "obligations"), ("uses", "uses")):
            rows = snapshot.get(name)
            if isinstance(rows, list):
                counts.append(
                    ScopedCount(
                        value=len(rows),
                        unit=unit,
                        scope="selected native frontier page",
                        source="native demand",
                        read_id=snapshot.get("read_id"),
                        complete=False,
                    )
                )
    return OperationalObservation(
        observed_at=now.isoformat(),
        phases=tuple(phases),
        counts=tuple(counts),
        coverage=page.coverage,
        omissions=(
            "Phase facts cover retained structured observations only.",
            "Frontier counts do not establish whole-demand totals.",
        ),
    )
