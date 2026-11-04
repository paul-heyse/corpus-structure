"""Whole-reading overlays and the final cap on record-produced facts.

Private source records keep their sealed standing. Only this explicit complete overlay
can select their field assertions; ordinary domain rules supply no admission authority.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import replace

from .record_projection import RecordAdmissionRow


def cap_record_selections(batch, selected: frozenset[str], overlay: Sequence[RecordAdmissionRow]):
    """Apply one complete decision per record, refusing partial or foreign overlays."""
    roots = {(r.record_id, r.interpretation_id) for r in batch.source_record}
    decisions = {(r.record_id, r.interpretation_id): r for r in overlay}
    if len(decisions) != len(overlay) or decisions.keys() - roots:
        raise ValueError("record admission overlay has duplicate or foreign interpretations")
    defaults = {(r.record_id, r.interpretation_id): r for r in batch.record_admission}
    decisions = {**defaults, **decisions}
    if decisions.keys() != roots:
        raise ValueError("record admission overlay omits an interpretation")
    fields = {}
    for row in batch.record_field:
        fields.setdefault((row.record_id, row.interpretation_id), set()).add(row.role)
    assertions = {}
    for row in batch.record_assertion:
        assertions.setdefault((row.record_id, row.interpretation_id), []).append(row)
    accepted = set()
    occurrences = set()
    for key, decision in decisions.items():
        if decision.decision not in {"candidate", "accepted", "rejected", "unresolved"}:
            raise ValueError("record admission has an unsupported disposition")
        if decision.decision != "accepted":
            continue
        members = assertions.get(key, ())
        if {r.role for r in members} != fields.get(key) or len(members) != len(fields[key]):
            raise ValueError("accepted reading lacks complete field assertion membership")
        if (
            any(
                getattr(decision, field) is None
                for field in (
                    "instance_digest",
                    "evaluation_id",
                    "evaluation_digest",
                    "probability_lexical",
                    "binding_json",
                )
            )
            or decision.calibration != "calibrated_whole_record_event"
        ):
            raise ValueError("accepted reading lacks evaluated calibrated instance binding")
        if key[0] in occurrences:
            raise ValueError("one occurrence has multiple accepted interpretations")
        occurrences.add(key[0])
        accepted.update(r.fact_id for r in members)
    record_facts = {r.fact_id for r in batch.record_assertion}
    return frozenset((set(selected) - record_facts) | accepted), tuple(
        decisions[k] for k in sorted(decisions)
    )


def evaluate_record_admissions(prepared, reports, bindings):
    """Prepare overlay requests from frozen policy events; native publication grants standing.

    No labels or evaluator tables are read here. The protected publication operation
    authenticates the exact run binding and evaluator product in its final transaction.
    """
    if not any(report.get("records") for report in reports):
        return ()
    from .identity import canonical_bytes
    from .record_policy import assess_record_admission, derive_record_features, score_record
    from .record_policy_products import validate_record_policy_binding
    from .record_projection import CALIBRATION, CANDIDATE_POLICY, CANDIDATE_POLICY_VERSION

    instances = [
        (binding, validate_record_policy_binding(prepared, binding)) for binding in bindings
    ]
    decisions = {}
    for report in reports:
        events = report.get("record_policy_events", ())
        for record in report.get("records") or ():
            row = (
                record.model_dump(mode="python") if hasattr(record, "model_dump") else dict(record)
            )
            key = row["record_id"], row["interpretation_id"]
            if key in decisions:
                continue
            decision = RecordAdmissionRow(
                *key,
                row["standing"],
                CANDIDATE_POLICY,
                CANDIDATE_POLICY_VERSION,
                CALIBRATION,
                "Retained source interpretation; no evaluated whole-record event is available",
            )
            applicable = [
                (binding, instance)
                for binding, instance in instances
                if (
                    instance.feature.applicability.release_id,
                    instance.feature.applicability.family,
                )
                == (prepared.release_id, row["family"])
            ]
            if len(applicable) > 1:
                raise ValueError("record has multiple applicable immutable policy instances")
            if applicable:
                binding, instance = applicable[0]
                matched = [
                    event
                    for event in events
                    if (event.get("record_id"), event.get("interpretation_id")) == key
                ]
                if len(matched) > 1:
                    raise ValueError("sealed record has duplicate whole-event scores")
                event = matched[0] if matched else {}
                vector = derive_record_features(
                    prepared,
                    row,
                    algorithm=instance.feature.algorithm,
                    diagnostics=event.get("diagnostics"),
                )
                serialized = event.get("feature_input_canonical_json")
                canonical_input = canonical_bytes([row, event.get("diagnostics")]).decode()
                compatible = (
                    event.get("feature_instance_digest") == instance.feature.digest
                    and event.get("feature_input_digest") == vector.input_digest
                    and serialized == canonical_input
                    and event.get("outcome") == "completed"
                )
                try:
                    expected_score = score_record(
                        instance.feature, vector, subset=instance.feature.applicability.subset
                    ).compatibility_potential
                except ValueError, ArithmeticError:
                    expected_score = None
                declared_score = event.get("final_event_score")
                score_compatible = (
                    expected_score is not None
                    and type(declared_score) in (float, int)
                    and math.isfinite(declared_score)
                    and math.isclose(declared_score, expected_score, rel_tol=1e-12, abs_tol=1e-12)
                )
                supported_procedure = (
                    event.get("event_procedure") == "independent-complete-reading-logistic-1"
                )
                compatible = compatible and score_compatible and supported_procedure
                proposal = assess_record_admission(
                    prepared,
                    row,
                    instance,
                    subset=instance.feature.applicability.subset,
                    final_event_score=event.get("final_event_score") if compatible else None,
                    event_procedure=event.get("event_procedure", ""),
                )
                blockers = (
                    tuple(proposal.blockers)
                    + (() if compatible else ("no_completed_bound_policy_event",))
                    + (
                        ()
                        if score_compatible
                        else ("final_event_score_differs_from_frozen_predictor",)
                    )
                    + (() if supported_procedure else ("unsupported_final_event_procedure",))
                )
                eligible = proposal.eligible_for_native_validation and not blockers
                decision = RecordAdmissionRow(
                    *key,
                    "accepted" if eligible else row["standing"],
                    "m1-grouped-reading-logistic",
                    instance.feature.algorithm.version,
                    "calibrated_whole_record_event" if instance.calibration else "not_calibrated",
                    "Evaluated whole-record policy admits complete source reading"
                    if eligible
                    else "; ".join(blockers),
                    binding["instance_digest"],
                    binding.get("evaluation_id"),
                    binding.get("evaluation_digest"),
                    str(proposal.calibrated_probability)
                    if proposal.calibrated_probability is not None
                    else None,
                    canonical_bytes(binding).decode(),
                )
            decisions[key] = decision
    accepted = {}
    for key, decision in decisions.items():
        if decision.decision == "accepted":
            accepted.setdefault(key[0], []).append(key)
    for keys in accepted.values():
        if len(keys) > 1:
            for key in keys:
                decisions[key] = replace(
                    decisions[key],
                    decision="unresolved",
                    reason="Multiple evaluated interpretations compete for one source occurrence",
                )
    return tuple(decisions[key] for key in sorted(decisions))
