"""Read-only hydration of qualified native analysis records and their named inputs.

No parser, symbolic engine, source mutation or current-default preparation is invoked here.
"""

from __future__ import annotations

from typing import Any

from corpus_structure.core.vocab import ObservationKind


class NativeAnalysisUnavailable(ValueError):
    """The retained analysis is unsupported, ambiguous, corrupt or outside source custody."""


def stored_native_analysis(
    reader: Any, source_view_id: int, pointer: str | None = None
) -> dict[str, dict[str, Any]]:
    """Return recorded stage results with observation identities, refusing stale references."""
    methods = ("extract.math", "normalize.formula")
    if pointer is None:
        view = reader.source_view(source_view_id)
        reference = view.ref
        pointers = sorted(
            {item["self_ref"] for item in view.items if item.get("label") == "formula"}
        )
        health = {
            item["pointer"]: item["outcome"] for item in view.health.get("formula_outcomes", ())
        }
        by_method = {
            method: list(reader.source_observations(source_view_id, method, ObservationKind.RECORD))
            for method in methods
        }
    else:
        reference, health = reader.source_formula_metadata(source_view_id, pointer)
        pointers = [pointer]
        by_method = {
            method: list(
                reader.source_observations_for_ref(reference, method, ObservationKind.RECORD)
            )
            for method in methods
        }
    return _resolve_native_analysis(reference, pointers, health, by_method)


def _resolve_native_analysis(reference, pointers, health, by_method):
    """Preserve retained analysis validation for both complete and occurrence reads."""
    source_view_id = reference.id
    rows = {}
    for method in ("extract.math", "normalize.formula"):
        values = by_method[method]
        for row in values:
            payload = row.payload
            if payload.get("demand") not in {"occurrences", "symbolic"}:
                raise NativeAnalysisUnavailable("native analysis record ABI is unsupported")
            if (
                payload.get("source_view_id") != source_view_id
                or payload.get("native_product") != reference.native_product.values()
                or payload.get("projection_digest") != reference.projection_digest
            ):
                raise NativeAnalysisUnavailable(
                    "analysis record differs from its pinned source view"
                )
            if payload.get("recipe_digest") != reference.recipe_digest:
                raise NativeAnalysisUnavailable(
                    "analysis recipe differs from its pinned source view"
                )
            if row.observation_key in rows:
                raise NativeAnalysisUnavailable(
                    "native analysis observation identity is duplicated"
                )
            rows[row.observation_key] = (method, row)
        if len(values) > 1:
            raise NativeAnalysisUnavailable(
                "native analysis has competing producers; select its origin"
            )

    def resolve(key: str, ref: str, path: frozenset[str]):
        if key in path:
            raise NativeAnalysisUnavailable("native analysis input references contain a cycle")
        if key not in rows:
            raise NativeAnalysisUnavailable(
                "named native analysis input is outside the selected source cut"
            )
        method, row = rows[key]
        payload = row.payload
        identity = dict(
            observation_key=key, task_id=row.task_id, payload_hash=row.payload_hash, method=method
        )
        if payload.get("source_record") is not None:
            value = resolve(payload["source_record"], ref, path | {key})
            return {**value, "observations": [*value["observations"], identity]}
        matched = [item for item in payload.get("items", ()) if item.get("pointer") == ref]
        if len(matched) != 1:
            raise NativeAnalysisUnavailable("native analysis item is missing or ambiguous")
        item = dict(matched[0])
        dependency = item.get("interpretation_ref")
        if dependency is not None:
            if dependency.get("pointer") != ref:
                raise NativeAnalysisUnavailable(
                    "normalization references another formula occurrence"
                )
            value = resolve(dependency["observation_key"], ref, path | {key})
            if value["interpretation"] is None:
                raise NativeAnalysisUnavailable(
                    "normalization has no recorded occurrence interpretation"
                )
            return dict(
                interpretation=value["interpretation"],
                normalization=item,
                observations=[*value["observations"], identity],
            )
        if payload["demand"] == "symbolic":
            weak = item.get("weak_interpretation")
            if weak is None:
                raise NativeAnalysisUnavailable(
                    "normalization lost its occurrence interpretation basis"
                )
            return dict(interpretation=weak, normalization=item, observations=[identity])
        return dict(interpretation=item, normalization=None, observations=[identity])

    result = {}
    for ref in pointers:
        normal = by_method["normalize.formula"]
        weak = by_method["extract.math"]
        if health.get(ref) != "succeeded":
            value = dict(
                interpretation=None, normalization=None, observations=[], availability="unavailable"
            )
        elif normal or weak:
            row = (normal or weak)[0]
            value = resolve(row.observation_key, ref, frozenset())
            value["availability"] = "available"
        else:
            value = dict(
                interpretation=None,
                normalization=None,
                observations=[],
                availability="not_requested",
            )
        result[ref] = dict(
            source_view_id=source_view_id,
            pointer=ref,
            native_product=reference.native_product.values(),
            projection_digest=reference.projection_digest,
            recognition_health=health.get(ref, "unknown"),
            **value,
        )
    return result
