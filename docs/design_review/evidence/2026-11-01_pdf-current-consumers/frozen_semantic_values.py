"""Value-only frozen challenges through existing mathematical comparison facilities.

These are local post-authoring assessments, not a production validator or a full
source-meaning grade. Frozen prose does not independently type symbol bindings or
qualification trees. Neither those trees nor assumptions are copied from pass C
onto the expected side.
"""
from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256

from corpus_structure.core.evidence import MacroDef
from corpus_structure.evaluate.semantic_alignment import equivalent
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.scientific_evidence import canonical_operand


def compare_value(expected_latex: str, actual: dict, *, prepared=None) -> dict:
    """Compare written mathematical values, retaining unsupported/unknown outcomes.

    Each operand keeps its own macro interpretation. Symbol/entity correspondence,
    conditions, quantity units and claim meaning are outside this value-only scope.
    The caller retains the complete actual claim separately.
    """
    result = {
        "scope": "mathematical value only; no binding, qualification or source-meaning grade",
        "expected_latex": expected_latex,
        "actual_operand": actual,
        "conditions_supplied": False,
        "bindings_compared": False,
    }
    stage = "value projection"
    try:
        if actual.get("kind") == "number":
            # Frozen scalar values are exact decimal literals; no float conversion.
            expected = {"kind": "number", "number": str(Decimal(expected_latex))}
            projected = {"kind": "number", "number": actual["number"]}
        elif actual.get("kind") in {"formula", "expression"} and actual.get("form") != "set":
            expected = {
                "kind": "expression", "language": "latex",
                "expression": expected_latex, "bindings": [],
            }
            projected = {
                "kind": "expression", "language": actual.get("language"),
                "expression": actual["expression"], "bindings": [],
            }
            if "macro_context" in actual:
                projected["macro_context"] = actual["macro_context"]
        else:
            return {
                **result, "outcome": "undecided", "mechanism": "unsupported value projection",
                "reason": (
                    "frozen scalar/formula has no independent typed projection "
                    "for this actual value kind"
                ),
            }
        result.update(expected_projection=expected, actual_projection=projected)
        macros = actual.get("macro_context", ())
        if isinstance(macros, dict):
            macros = macros.values()
        env = {
            macro["name"]: MacroDef(
                nargs=macro["nargs"], body=macro["body"], default=macro.get("default")
            )
            for macro in macros
        }
        stage = "existing canonical_operand/token_form"
        left = canonical_operand(expected, {})
        right = canonical_operand(projected, env)
        result.update(expected_canonical=left, actual_canonical=right)
        if left == right:
            return {**result, "outcome": "equivalent", "mechanism": stage}
        stage = "existing semantic_alignment.equivalent"
        decision = equivalent(expected, projected, {}, model=prepared)
        outcome = "equivalent" if decision.equal else (
            "undecided" if decision.outcome == "undecided" else "different"
        )
        return {
            **result,
            "outcome": outcome,
            "mechanism": stage,
            "decision": asdict(decision),
        }
    except Exception as error:
        # Failed mathematical interpretation is observable, never false inequality.
        # Cancellation/termination still propagate (BaseException is not caught).
        return {
            **result, "outcome": "undecided", "mechanism": stage,
            "error_type": f"{type(error).__module__}.{type(error).__qualname__}",
            "error": str(error),
        }


def assess_frozen_values(frozen: dict, adjudicated: dict, *, prepared=None) -> dict:
    """Link each unchanged expectation to actual C claims, never summary-only math."""
    assertions = {row["id"]: row for row in adjudicated["assertions"]}
    batches = {row["source_case"]: row["authored_batch"] for row in adjudicated["units"]}
    cases = []
    for key, source in frozen.items():
        batch = batches[key]
        claims = {claim["id"]: claim for claim in batch["claims"]}
        for expected in source["assertions"]:
            assertion = assertions[expected["id"]]
            linked = [claims[identity] for identity in assertion["claim_ids"]]
            designated = [
                claim for claim in linked
                if str(claim["object"].get("expression", claim["object"].get("number")))
                == assertion["latex"]
            ]
            if not designated:
                raise ValueError(
                    "assertion summary does not designate an actual linked mathematical claim"
                )
            cases.append({
                "id": expected["id"], "source_case": key,
                "frozen_assertion": expected,
                "authored_assertion": assertion,
                "retained_authored_batch": f"C.{key}.authored.json",
                "authored_batch_sha256": sha256(canonical_bytes(batch)).hexdigest(),
                "actual_linked_claims": linked,
                "value_comparisons": [
                    {
                        "claim_id": claim["id"],
                        **compare_value(expected["latex"], claim["object"], prepared=prepared),
                    }
                    for claim in designated
                ],
                "source_context_and_conditions": {
                    "outcome": "undecided",
                    "reason": (
                        "frozen source facts provide prose meaning/conditions, "
                        "without independently typed binding and qualification trees; "
                        "C context is retained, "
                        "not copied onto expected operands"
                    ),
                },
            })
    return {
        "outcome": "partial", "evaluation": "performed",
        "scope": (
            "six frozen mathematical values against actual linked C claims; "
            "source meaning and conditions remain separate"
        ),
        "cases": cases,
        "typed_reference_extraction_grade": (
            "not_run; existing evaluator separately compares complete authored/extracted batches "
            "including typed qualifications"
        ),
    }
