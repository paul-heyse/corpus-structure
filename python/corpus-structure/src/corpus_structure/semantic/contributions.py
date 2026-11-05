"""Released private contributions, independent of complete source records.

Source anchors and authenticated coordinates remain owned by record_contracts/records.
This boundary adds semantic identities and closure, without publishing knowledge.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

from .identity import canonical_bytes
from .record_contracts import _text_key, anchor_identity, validate_anchor_binding
from .types import Diagnostic, PreparationError


def _identity(kind, value):
    return kind + ":" + sha256(canonical_bytes(value)).hexdigest()


def occurrence_identity(anchors: Sequence[Mapping[str, Any]]) -> str:
    """Ordered real source pieces; producer, release and interpretation are independent."""
    pieces = []
    for anchor in anchors:
        if anchor["space"] == "selected_projection":
            raise ValueError("physical occurrence requires canonical native coordinates")
        pieces.append(
            {
                **{k: v for k, v in anchor.items() if k not in {"anchor_id", "binding", "pin"}},
                "pin": {k: anchor["pin"][k] for k in ("product_key", "product_digest")},
            }
        )
    return _identity("source-occurrence", pieces)


def operation_identity(*values: Any, **dimensions: Any) -> str:
    return _identity("contribution-operation", [values, dimensions])


def contribution_identity(row: Mapping[str, Any]) -> str:
    return _identity(
        "source-contribution", {k: v for k, v in row.items() if k != "contribution_id"}
    )


def validate_contribution_declarations(definitions) -> None:
    for definition in definitions:
        if "ContributionSemantics" not in definition.ancestors or definition.abstract:
            continue
        properties = {p.name: p for p in definition.properties}
        if (
            properties["effect"].equals_string != "retain_private"
            or properties["assessment_event"].equals_string != "local-contribution-1"
        ):
            raise PreparationError(
                (
                    Diagnostic(
                        "contribution_effect",
                        definition.name,
                        "unsupported contribution effect or assessment event",
                        "unsupported",
                    ),
                )
            )


def bind_contributions(prepared, *, source, operations, contributions, coordinate_texts=()):
    """Validate actual pieces, operation population, identities and local endpoint closure."""
    contexts = {}
    for value in coordinate_texts:
        row = prepared.validate_python("RecordCoordinateText", value).model_dump(mode="python")
        key = _text_key(row["pin"], row["space"], row["pointer"], row.get("recognition"))
        if key in contexts and contexts[key] != row["text"]:
            raise ValueError("conflicting contribution coordinate text")
        contexts[key] = row["text"]
    ops = tuple(
        prepared.validate_python("SourceContributionOperation", op).model_dump(mode="python")
        for op in operations
    )
    operation_keys = {op["operation_key"] for op in ops}
    if len(operation_keys) != len(ops):
        raise ValueError("duplicate contribution operation identity")
    output = []
    for raw in contributions:
        row = prepared.validate_python("SourceContribution", raw).model_dump(mode="python")
        if row["operation_key"] not in operation_keys:
            raise ValueError("contribution has no operation population row")
        definition = prepared.index.definitions.get(row["contract"])
        if definition is None or "ContributionSemantics" not in definition.ancestors:
            raise ValueError("contribution requires a released semantic contract")
        prepared.validate_python(
            row["contract"],
            dict(
                kind=row["kind"],
                semantic_type=row["semantic_type"],
                effect="retain_private",
                assessment_event="local-contribution-1",
            ),
        )
        if row["pin"]["source"] != source:
            raise ValueError("contribution source differs from producing source")
        anchors = row.get("anchors", ())
        seen_anchors = set()
        previous = {}
        for anchor in anchors:
            if (
                anchor["anchor_id"] in seen_anchors
                or anchor_identity(anchor) != anchor["anchor_id"]
            ):
                raise ValueError("duplicate or invalid contribution anchor identity")
            seen_anchors.add(anchor["anchor_id"])
            validate_anchor_binding(anchor, row["pin"])
            if anchor["space"] == "model_context":
                raise ValueError("model context is not contribution source evidence")
            start, end = anchor.get("start"), anchor.get("end")
            if (start is None) != (end is None):
                raise ValueError("contribution anchor needs paired coordinates")
            if anchor["precision"] == "exact":
                key = _text_key(
                    anchor["pin"], anchor["space"], anchor["pointer"], anchor.get("recognition")
                )
                text = contexts.get(key)
                if (
                    text is None
                    or start is None
                    or not 0 <= start < end <= len(text)
                    or text[start:end] != anchor.get("source_piece")
                ):
                    raise ValueError("contribution anchor does not reconstruct actual source")
                if start < previous.get(key, 0):
                    raise ValueError("contribution source pieces overlap or reverse order")
                previous[key] = end
            elif start is not None:
                raise ValueError("coarse contribution evidence invents exact coordinates")
        if row["kind"] == "occurrence":
            if not anchors or row.get("occurrence_id") != occurrence_identity(anchors):
                raise ValueError("located occurrence requires its actual source-piece identity")
        elif anchors and row.get("occurrence_id") != occurrence_identity(anchors):
            raise ValueError("proposal occurrence differs from its source pieces")
        elif not anchors and "occurrence_id" in row:
            raise ValueError("unlocated contribution cannot claim an occurrence identity")
        if (row["score_state"] == "native") != ("score" in row):
            raise ValueError("contribution score availability differs from actual score")
        if contribution_identity(row) != row["contribution_id"]:
            raise ValueError("contribution identity differs from immutable contents")
        output.append(row)
    identities = {row["contribution_id"] for row in output}
    if len(identities) != len(output):
        raise ValueError("duplicate contribution identity")
    for row in output:
        endpoints = row.get("endpoints", ())
        members = row.get("members", ())
        if (
            any(endpoint["contribution_id"] not in identities for endpoint in endpoints)
            or not set(members) <= identities
        ):
            raise ValueError("contribution endpoint/member is unavailable")
        if row["contribution_id"] in members or any(
            endpoint["contribution_id"] == row["contribution_id"] for endpoint in endpoints
        ):
            raise ValueError("contribution cannot be its own endpoint/member")
        if row["kind"] == "relation" and len(endpoints) < 2:
            raise ValueError("relation contribution requires explicit endpoint roles")
        if row["kind"] == "composite" and not members:
            raise ValueError("composite contribution requires explicit members")
    for op in ops:
        retained = {"retained_task_id", "retained_result_digest", "retained_source_bindings"}
        if retained.intersection(op) and (
            not retained <= op.keys() or not op["retained_source_bindings"]
        ):
            raise ValueError("retained operation requires complete immutable source lineage")
        actual = sum(row["operation_key"] == op["operation_key"] for row in output)
        if actual != op["emitted_count"]:
            raise ValueError("operation emitted cardinality differs from contributions")
        if op["outcome"] in {"empty", "failed", "skipped", "unsupported", "not_run"} and actual:
            raise ValueError("non-producing operation cannot emit contributions")
        if op["outcome"] in {
            "failed",
            "skipped",
            "unsupported",
            "limited",
            "not_run",
        } and not op.get("reason"):
            raise ValueError("non-success operation requires an explicit reason")
    return ops, tuple(output)


def prepare_contribution_projection(definitions):
    from .types import PreparedArtifact

    if not any(d.name == "SourceContribution" for d in definitions):
        return None
    validate_contribution_declarations(definitions)
    contracts = sorted(
        d.name for d in definitions if "ContributionSemantics" in d.ancestors and not d.abstract
    )
    return PreparedArtifact(
        "contribution_projection.json",
        canonical_bytes(
            dict(
                abi="source-contribution-projection-1",
                contracts=contracts,
                relations=[
                    "kb.source_contribution_operation",
                    "kb.source_contribution",
                    "kb.source_contribution_endpoint",
                ],
                standing="retained_private",
                detail_owner="ops.task_result",
                occurrence_recipe="ordered-native-source-pieces-1",
            )
        ),
    )
