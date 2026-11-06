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
        if row["score_state"] == "native":
            from .observations import source_python

            if type(source_python(row["score"])) not in {int, float}:
                raise ValueError("native contribution score requires an actual numeric value")
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
    by_identity = {row["contribution_id"]: row for row in output}
    by_operation = {op["operation_key"]: op for op in ops}
    endpoint_signatures = component_endpoint_signatures(prepared.index.definitions.values())
    for row in output:
        validate_component(
            row, by_operation[row["operation_key"]], by_identity, endpoint_signatures
        )
    from .local_interpretation_reports import validate_local_interpretation_report

    for op in ops:
        validate_local_interpretation_report(op, output)
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
                component_endpoints=component_endpoint_signatures(definitions),
                relations=[
                    "kb.source_contribution_operation",
                    "kb.source_contribution",
                    "kb.source_contribution_endpoint",
                    "kb.source_contribution_anchor",
                ],
                standing="retained_private",
                detail_owner="ops.task_result",
                occurrence_recipe="ordered-native-source-pieces-1",
            )
        ),
    )


def component_endpoint_signatures(definitions):
    return {
        next(p.equals_string for p in definition.properties if p.name == "kind"): tuple(
            sorted(
                p.name.removesuffix("_contribution_id")
                for p in definition.properties
                if p.name.endswith("_contribution_id")
            )
        )
        for definition in definitions
        if "WitnessedComponent" in definition.ancestors and not definition.abstract
    }


def validate_component(row, operation, population, endpoint_signatures):
    """Bind released component evidence to actual operation/source participants.

    Shape validation is performed by the effective release. This checks the
    cross-row meaning that neither a JSON schema nor a matcher establishes.
    """
    component = row.get("component")
    if component is None:
        return
    if (
        component["question"] != operation["question"]
        or component["question_version"] != operation["operation_version"]
    ):
        raise ValueError("component differs from its producing operation question/version")
    dependencies = component["dependencies"]
    if len(set(dependencies)) != len(dependencies) or not set(dependencies) <= set(
        row.get("computation_dependencies", ())
    ):
        raise ValueError("component dependencies differ from retained computation")
    anchors = {a["anchor_id"] for a in row.get("anchors", ())}
    for endpoint in row.get("endpoints", ()):
        participant = population[endpoint["contribution_id"]]
        anchors.update(a["anchor_id"] for a in participant.get("anchors", ()))
    for basis in component["bases"]:
        if len(set(basis["dependencies"])) != len(basis["dependencies"]) or not set(
            basis["dependencies"]
        ) <= set(dependencies):
            raise ValueError("component basis has unavailable dependency")
        if not set(basis.get("anchor_ids", ())) <= anchors:
            raise ValueError("component basis has unavailable source anchor")
    if component["kind"] == "located_role":
        roles = component["roles"]
        if len({role["role"] for role in roles}) != len(roles):
            raise ValueError("located component repeats a role")
        if not row.get("occurrence_id"):
            raise ValueError("located component requires its physical occurrence")
        for role in roles:
            if not set(role["anchor_ids"]) <= {a["anchor_id"] for a in row.get("anchors", ())}:
                raise ValueError("located component role has unavailable source anchor")
    else:
        roles = endpoint_signatures.get(component["kind"])
        if not roles or row["kind"] != "relation":
            raise ValueError("unsupported relational component operation")
        expected = {role: component[role + "_contribution_id"] for role in roles}
        actual = {
            endpoint["role"]: endpoint["contribution_id"] for endpoint in row.get("endpoints", ())
        }
        if len(row.get("endpoints", ())) != len(expected) or actual != expected:
            raise ValueError("component endpoints differ from released role signature")


def component_statement(row, population):
    """Exact private assessed statement, not a public claim identity or eligibility.

    Derivation identities remain intentional here: independent assessment binds
    the exact retained component. A future public component policy must project
    its own source-resolved semantic statement before admission.
    """
    if "component" not in row:
        raise ValueError("component statement requires a retained component")
    return dict(
        version="private-component-assessment-statement-1",
        component=row["component"],
        anchors=row.get("anchors", ()),
        endpoints=tuple(
            dict(role=e["role"], participant=population[e["contribution_id"]])
            for e in row.get("endpoints", ())
        ),
        publication_authority=False,
    )
