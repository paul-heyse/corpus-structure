"""The pump passage as observations from three stream groups (prototype 1, D5 §14.10).

"The centrifugal pump (CP) was tested in March 2024. At suction pressures above 2 bar, it
delivered 120 m³/h, exceeding the 100 m³/h rating in Table 3. Earlier work suggested that
centrifugal pumps may cavitate below this pressure."

Scores are already calibrated LLRs (score kind `LLR`), so the test reads the joint model itself;
calibration is tested separately. Proximity alone prefers the nearest quantity, the 100 m³/h
rating, which is wrong.
"""

from __future__ import annotations

from corpus_structure.interpret.calibration import CalibrationTable
from corpus_structure.interpret.observations import (
    Alternative,
    Observation,
    ObservationStore,
    ScoreKind,
)
from corpus_structure.interpret.records import RecordRegistry, RecordType
from corpus_structure.interpret.templates.numeric_reference import (
    REFERENCE_RECORD,
    ROLE_RECORD,
    NumericReferenceTemplate,
    QuantityMention,
    ReferenceMention,
)

GROUPS = ("units", "proximity", "frames")

QUANTITIES = (
    QuantityMention("q_2bar", "2 bar", 2),
    QuantityMention("q_120", "120 m³/h", 2),
    QuantityMention("q_100", "100 m³/h", 2),
)
REFERENCE = ReferenceMention("this_pressure", "this pressure", 3, "pressure")

GOLD = {
    "ref:this_pressure": "q_2bar",
    "role:q_2bar": "condition_threshold",
    "role:q_120": "measured",
    "role:q_100": "rated",
}


def registry() -> RecordRegistry:
    return RecordRegistry(
        [
            RecordType(REFERENCE_RECORD, value=1.0, cost=3.0),  # tau = 0.75
            RecordType(ROLE_RECORD, value=1.0, cost=1.0),  # tau = 0.5
        ]
    )


def observation(
    stream: str,
    group: str,
    decision: str,
    decision_type: str,
    scores: dict[str, float],
    *,
    kind: ScoreKind = ScoreKind.LLR,
    tag: str | None = None,
) -> Observation:
    return Observation(
        stream=stream,
        group=group,
        model=f"{stream}-model",
        model_version="1",
        config_hash="cfg-1",
        input_digest="pump-passage",
        document="doc:pump",
        decision=decision,
        decision_type=decision_type,
        score_kind=kind,
        alternatives=tuple(Alternative(o, s) for o, s in scores.items()),
        tags=frozenset({tag or f"x:{stream}:{decision}"}),
    )


def store() -> ObservationStore:
    return ObservationStore(
        [
            # Unit parser: each quantity's dimension (a deterministic lookup).
            observation("pint", "units", "dim:q_2bar", "unit_dimension", {"pressure": 1.0},
                        kind=ScoreKind.INDICATOR),
            observation("pint", "units", "dim:q_120", "unit_dimension", {"volumetric_flow": 1.0},
                        kind=ScoreKind.INDICATOR),
            observation("pint", "units", "dim:q_100", "unit_dimension", {"volumetric_flow": 1.0},
                        kind=ScoreKind.INDICATOR),
            # Proximity and syntax: favours the nearest quantity.
            observation("proximity", "proximity", "ref:this_pressure", REFERENCE_RECORD,
                        {"q_100": 2.0, "q_2bar": 1.5, "q_120": 0.5}),
            # Frames: role cues per quantity, and the slot "cavitate below X" expects.
            observation("frame-cues", "frames", "role:q_2bar", ROLE_RECORD,
                        {"condition_threshold": 2.0}),
            observation("frame-cues", "frames", "role:q_120", ROLE_RECORD, {"measured": 2.0}),
            observation("frame-cues", "frames", "role:q_100", ROLE_RECORD, {"rated": 2.0}),
            observation("frame-slots", "frames", "slot:this_pressure", "frame_slot",
                        {"condition_threshold": 1.5}),
        ]
    )  # fmt: skip


def template() -> NumericReferenceTemplate:
    return NumericReferenceTemplate(
        QUANTITIES, (REFERENCE,), calibration=CalibrationTable(), registry=registry()
    )


def realized_value(accepted: dict[str, str], decisions: set[str] | None = None) -> float:
    """V: +v for each accepted correct record, -c for each accepted wrong one."""
    reg = registry()
    total = 0.0
    for decision, option in accepted.items():
        if decisions is not None and decision not in decisions:
            continue
        record_type = reg[REFERENCE_RECORD if decision.startswith("ref:") else ROLE_RECORD]
        total += record_type.value if GOLD[decision] == option else -record_type.cost
    return total
