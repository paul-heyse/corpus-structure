"""Read-only hydration of qualified native analysis records and their named inputs.

No parser, symbolic engine, source mutation or current-default preparation is invoked here.
"""
from __future__ import annotations

from typing import Any

from corpus_structure.core.vocab import ObservationKind


class NativeAnalysisUnavailable(ValueError):
    """The retained analysis is unsupported, ambiguous, corrupt or outside source custody."""


def stored_native_analysis(reader: Any, source_view_id: int,
                           pointer: str | None = None) -> dict[str, dict[str, Any]]:
    """Return recorded stage results with observation identities, refusing stale references."""
    view=reader.source_view(source_view_id)
    formulas={item["self_ref"] for item in view.items if item.get("label")=="formula"}
    if pointer is not None and pointer not in formulas:
        raise NativeAnalysisUnavailable("formula selector is outside the pinned native source view")
    pointers=sorted(formulas) if pointer is None else [pointer]
    rows={};by_method={}
    for method in ("extract.math","normalize.formula"):
        values=list(reader.source_observations(source_view_id,method,ObservationKind.RECORD))
        for row in values:
            payload=row.payload
            if payload.get("demand") not in {"occurrences","symbolic"}:
                raise NativeAnalysisUnavailable("native analysis record ABI is unsupported")
            if (payload.get("source_view_id")!=source_view_id
                or payload.get("native_product")!=view.ref.native_product.values()
                or payload.get("projection_digest")!=view.ref.projection_digest):
                raise NativeAnalysisUnavailable("analysis record differs from its pinned source view")
            if payload.get("recipe_digest")!=view.ref.recipe_digest:
                raise NativeAnalysisUnavailable("analysis recipe differs from its pinned source view")
            if row.observation_key in rows:
                raise NativeAnalysisUnavailable("native analysis observation identity is duplicated")
            rows[row.observation_key]=(method,row)
        if len(values)>1:
            raise NativeAnalysisUnavailable("native analysis has competing producers; select its origin")
        by_method[method]=values

    def resolve(key:str,ref:str,path:frozenset[str]):
        if key in path:
            raise NativeAnalysisUnavailable("native analysis input references contain a cycle")
        if key not in rows:
            raise NativeAnalysisUnavailable("named native analysis input is outside the selected source cut")
        method,row=rows[key];payload=row.payload
        identity=dict(observation_key=key,task_id=row.task_id,payload_hash=row.payload_hash,method=method)
        if payload.get("source_record") is not None:
            value=resolve(payload["source_record"],ref,path|{key})
            return {**value,"observations":[*value["observations"],identity]}
        matched=[item for item in payload.get("items",()) if item.get("pointer")==ref]
        if len(matched)!=1:
            raise NativeAnalysisUnavailable("native analysis item is missing or ambiguous")
        item=dict(matched[0])
        dependency=item.get("interpretation_ref")
        if dependency is not None:
            if dependency.get("pointer")!=ref:
                raise NativeAnalysisUnavailable("normalization references another formula occurrence")
            value=resolve(dependency["observation_key"],ref,path|{key})
            if value["interpretation"] is None:
                raise NativeAnalysisUnavailable("normalization has no recorded occurrence interpretation")
            return dict(interpretation=value["interpretation"],normalization=item,
                        observations=[*value["observations"],identity])
        if payload["demand"]=="symbolic":
            weak=item.get("weak_interpretation")
            if weak is None:
                raise NativeAnalysisUnavailable("normalization lost its occurrence interpretation basis")
            return dict(interpretation=weak,normalization=item,observations=[identity])
        return dict(interpretation=item,normalization=None,observations=[identity])

    health={item["pointer"]:item["outcome"] for item in view.health.get("formula_outcomes",())}
    result={}
    for ref in pointers:
        normal=by_method["normalize.formula"]
        weak=by_method["extract.math"]
        if health.get(ref)!="succeeded":
            value=dict(interpretation=None,normalization=None,observations=[],availability="unavailable")
        elif normal or weak:
            row=(normal or weak)[0]
            value=resolve(row.observation_key,ref,frozenset())
            value["availability"]="available"
        else:
            value=dict(interpretation=None,normalization=None,observations=[],availability="not_requested")
        result[ref]=dict(source_view_id=source_view_id,pointer=ref,
            native_product=view.ref.native_product.values(),projection_digest=view.ref.projection_digest,
            recognition_health=health.get(ref,"unknown"),**value)
    return result
