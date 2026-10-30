"""Source-qualified transport for operation-owned mathematical interpretations.

Native objects remain owned by PreparedMathInput. These envelopes contain original
spelling, identified source occurrences and explicit explanatory evidence only.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

import sympy

from corpus_structure.core import tex
from corpus_structure.semantic.identity import canonical_bytes

from . import grammar
from .prepared import MathAssessment, PreparedMathInput
from .transform import NotRepresentable

ADAPTER_ID = "lark-math-3"
_CATEGORIES = {"word": "control_word", "symbol": "control_symbol", "open": "group_open",
               "close": "group_close", "param": "parameter", "space": "whitespace",
               "char": "character"}


def _reference(value) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else dataclasses.asdict(value)


def _dependency(name: str, reference) -> dict[str, Any]:
    ref = _reference(reference)
    return dict(name=name, kind="product", target_task_id=ref["task_id"],
                target_product_key=ref["product_key"], target_content_digest=ref["content_digest"])


def _envelope(kind: str, root, product_key: str, semantic_state: str, coverage: str):
    return dict(product_key=product_key, kind=kind, root=_reference(root),
                operation="interpret_parsing_math" if kind == "interpretation" else "assess_parsing_math",
                adapter_id=ADAPTER_ID, lifecycle="available", semantic_state=semantic_state,
                coverage=coverage, representations=[], components=[], nodes=[], relationships=[],
                endpoints=[], mappings=[], mapping_endpoints=[], dependencies=[],
                interpretations=[], assessments=[])


def _external_endpoint(dependency, **values):
    return {**values, "dependency_name": dependency["name"],
            **{name: dependency[name] for name in
               ("target_task_id", "target_product_key", "target_content_digest")}}


def _meaning(status: str) -> str:
    return {"resolved": "ok", "partial": "unknown", "failed": "invalid", "timeout": "unknown"}.get(status, status)


def interpretation_product_payload(
    operand: PreparedMathInput,
    *,
    root,
    text_product,
    source_node_id: str,
    product_key: str = "math",
    symbolic: bool = False,
    stage: str = "interpretation",
) -> dict[str, Any]:
    """Use the selected text product's canonical coordinates, never an unselected rendition.

    ``operand.parse_start`` is the absolute canonical start of its exact parse view.
    ``source_node_id`` names the selected text product's enclosing parse-view node.
    """
    if stage not in {"syntax", "interpretation", "symbolic"}:
        raise ValueError("mathematical product stage must be syntax, interpretation or symbolic")
    symbolic = symbolic or stage == "symbolic"
    reading = operand.syntax() if stage == "syntax" else (
        operand.symbolic_reading() if symbolic else operand.interpretation()
    )
    coverage = "complete" if reading.status.value == "ok" else "partial"
    meaning = "unknown" if stage == "syntax" else _meaning(reading.status.value)
    p = _envelope("interpretation", root, product_key, meaning, coverage)
    dependency = _dependency("text", text_product)
    p["dependencies"] = [_dependency("source", root), dependency]
    p["representations"] = [dict(representation_id="parse_input", kind="parse_view", unit="codepoint",
                                 extent_length=len(operand.latex), text_content=operand.latex,
                                 partition_state="complete", recognition_state="unknown")]
    p["components"] = [dict(component_id=f"lexical:{index}", ordinal=index, category=_CATEGORIES[t.kind],
                            representation_id="parse_input", unit="codepoint", start_offset=t.start,
                            end_offset=t.end) for index, t in enumerate(tex.tokens(operand.latex))]
    p["mappings"] = [dict(mapping_id="parse-view", operation="copy", fidelity="exact",
                           reason="selected canonical text to exact mathematical parse view")]
    p["mapping_endpoints"] = [
        _external_endpoint(dependency, mapping_id="parse-view", side="source", ordinal=0,
                           representation_id="canonical", unit="codepoint", start_offset=operand.parse_start,
                           end_offset=operand.parse_start + len(operand.latex)),
        dict(mapping_id="parse-view", side="target", ordinal=0, representation_id="parse_input",
             unit="codepoint", start_offset=0, end_offset=len(operand.latex)),
    ]
    native_evidence = None
    if stage == "symbolic":
        try:
            native_evidence = dict(format="sympy-srepr-1", text=sympy.srepr(operand.symbolic_value()))
        except grammar.Expired:
            p["lifecycle"], p["semantic_state"], p["coverage"] = "failed", "unknown", "partial"
        except (NotRepresentable, grammar.NotParsed, grammar.Ambiguous):
            p["semantic_state"], p["coverage"] = "unsupported", "partial"
        except ValueError:
            p["semantic_state"], p["coverage"] = "invalid", "partial"
        coverage = p["coverage"]
    details = dict(native_evidence=native_evidence, native_state=dataclasses.asdict(operand.state("symbolic")), requested_stage=stage, kind=reading.kind, status=reading.status.value, notes=reading.notes,
                   declarations=[dataclasses.asdict(d) for d in reading.declarations],
                   failure=None if reading.failure is None else dataclasses.asdict(reading.failure),
                   definedness=[] if stage == "syntax" else [dataclasses.asdict(c) for c in operand.definedness()],
                   conventions=["N denotes Naturals0", "unqualified set-builder domain is Reals"],
                   requested_native_equivalence=symbolic)
    p["nodes"] = [dict(node_id="interpretation:0", kind="math", origin="literal", name=reading.kind or reading.requested,
                       value=canonical_bytes(details).decode(), representation_id="parse_input",
                       unit="codepoint", start_offset=0, end_offset=len(operand.latex))]
    p["relationships"] = [dict(relationship_id="source-reading", kind="derived_from")]
    p["endpoints"] = [dict(relationship_id="source-reading", ordinal=0, role="target", node_id="interpretation:0"),
                      _external_endpoint(dependency, relationship_id="source-reading", ordinal=1,
                                         role="source", node_id=source_node_id)]
    occurrence_ids = []
    for ordinal, occurrence in enumerate(reading.occurrences):
        key = f"occurrence:{ordinal}"
        occurrence_ids.append(key)
        p["nodes"].append(dict(node_id=key, kind="symbol", origin="literal", name=occurrence.name,
                               representation_id="parse_input", unit="codepoint", start_offset=occurrence.start,
                               end_offset=occurrence.end, ordinal=ordinal))
        relationship = f"occurrence:{ordinal}"
        p["relationships"].append(dict(relationship_id=relationship, kind="contains"))
        p["endpoints"].extend([
            dict(relationship_id=relationship, ordinal=0, role="parent", node_id="interpretation:0"),
            dict(relationship_id=relationship, ordinal=1, role="child", node_id=key),
        ])
    p["interpretations"] = [dict(interpretation_id="interpretation:0", product_id=product_key,
        occurrence_ids=occurrence_ids or ["interpretation:0"], context_digest=operand.context.stage_key("interpretation"),
        declaration_digest=sha256(canonical_bytes([dataclasses.asdict(d) for d in operand.context.declarations])).hexdigest(),
        assumption_digest=sha256(operand.context.assumptions).hexdigest(), adapter_id=ADAPTER_ID,
        semantic_state=p["semantic_state"], coverage=coverage,
        **({"alternative_group":"alternatives:0"} if reading.status.value == "ambiguous" else {}))]
    if stage == "syntax":
        p["interpretations"] = []
    return p


def assessment_product_payload(
    operand: PreparedMathInput,
    assessment: MathAssessment,
    *,
    root,
    interpretation_product,
    interpretation_id: str = "interpretation:0",
    product_key: str = "assessment",
) -> dict[str, Any]:
    """Publish named evidence against one exact selected mathematical interpretation."""
    coverage = "partial" if assessment.outcome in {"unsupported", "invalid", "timeout"} else "complete"
    p = _envelope("assessment", root, product_key, _meaning(assessment.outcome), coverage)
    dependency = _dependency("interpretation", interpretation_product)
    p["dependencies"] = [_dependency("source", root), dependency]
    value = assessment.value
    if isinstance(value, sympy.Basic):
        explanation = dict(format="sympy-srepr-1", text=sympy.srepr(value))
    elif isinstance(value, (set, frozenset)) and all(isinstance(v, sympy.Basic) for v in value):
        explanation = dict(format="sympy-srepr-set-1", text=sorted(sympy.srepr(v) for v in value))
    elif assessment.question == "definedness":
        explanation = [dataclasses.asdict(c) for c in assessment.conditions]
    elif value is None or isinstance(value, (str, bool, int, float)):
        explanation = value
    else:
        raise ValueError("assessment value has no admitted explanatory transport")
    details = dict(question=assessment.question, outcome=assessment.outcome, evidence=explanation,
                   conditions=[dataclasses.asdict(c) for c in assessment.conditions],
                   diagnostic=assessment.diagnostic,
                   assumption_records=json.loads(operand.context.assumptions))
    p["nodes"] = [dict(node_id="evidence:0", kind="math", origin="derived",
                       origin_reason="named native mathematical assessment; not source spelling",
                       name=assessment.question, value=canonical_bytes(details).decode())]
    p["relationships"] = [dict(relationship_id="assessed-reading", kind="derived_from")]
    p["endpoints"] = [dict(relationship_id="assessed-reading", ordinal=0, role="target", node_id="evidence:0"),
                      _external_endpoint(dependency, relationship_id="assessed-reading", ordinal=1,
                                         role="source", node_id=interpretation_id)]
    p["assessments"] = [dict(assessment_id="assessment:0", product_id=product_key,
        interpretation_ids=[interpretation_id], question=assessment.question,
        conditions_digest=sha256(canonical_bytes(details["conditions"])).hexdigest(),
        algorithm_revision="native-assessment-1", policy_id=operand.context.profile.id + "/" + operand.context.profile.version,
        outcome=p["semantic_state"], coverage=coverage, evidence_ids=["evidence:0"])]
    if assessment.outcome == "timeout":
        p["lifecycle"] = "failed"
    return p
