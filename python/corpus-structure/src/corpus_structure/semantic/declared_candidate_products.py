"""One source-bound private candidate inspection artifact for declared producers."""

from hashlib import sha256
from pathlib import Path

import yaml

from .data_operation_json import json_bytes, json_loads
from .data_operation_model import json_context_meaning
from .identity import canonical_bytes
from .source_products import source_product_inputs
from .types import SourceArtifact, SourceBundle

_MODEL = Path(__file__).parents[1] / "model/semantic/data-operation-candidate-inspection.yaml"


def candidate_inspection_inputs(bundle):
    """Compose the shared current source/member contract."""
    from .source_discovery import source_discovery_inputs

    bundle = source_product_inputs(bundle)
    if "data_operation_source_discovery" not in {source.name for source in bundle.sources}:
        bundle = source_discovery_inputs(bundle)
    name, root = "data_operation_candidate_inspection", "data_operation_candidate_inspection_root"
    existing = {source.name: source for source in bundle.sources}
    if name in existing:
        if existing[name].content != _MODEL.read_bytes():
            raise ValueError("candidate inspection model differs from the installed owner")
        return bundle
    if root in existing:
        raise ValueError("candidate inspection inputs use a reserved schema root")
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact(name, _MODEL.read_bytes()),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    {
                        "id": "urn:corpus:candidate-inspection-root",
                        "name": root,
                        "imports": [bundle.root, name],
                    }
                ).encode(),
            ),
        ),
    )


def candidate_member_id(candidate_type, value):
    """Address an actual interpretation, preserving shared domain record identity."""
    if candidate_type == "record":
        return (
            "record:"
            + sha256(canonical_bytes([value["record_id"], value["interpretation_id"]])).hexdigest()
        )
    if candidate_type == "contribution":
        return "contribution:" + value["contribution_id"]
    raise ValueError("unknown candidate member family")


def candidate_observation_set_digest(operations):
    """Identify the exact retained request/reply set issued by a learned candidate producer."""
    digests = {operation["report_digest"] for operation in operations}
    if any(type(digest) is not str or not digest for digest in digests):
        raise ValueError("candidate observations require their actual retained reply digests")
    return sha256(canonical_bytes(["retained-function-reply-set-1", sorted(digests)])).hexdigest()


def candidate_inspection_report(
    prepared,
    model,
    primary,
    context,
    *,
    inspection_outcome,
    records=(),
    contributions=(),
    operations=(),
    coordinate_texts=(),
    coverage=(),
    diagnostics=None,
    report_class="DdoCandidateInspectionReport",
    record_class="DdoCandidateSourceRecord",
    contribution_class="DdoCandidateSourceContribution",
    input_support=None,
):
    """Store each actual candidate once; empty output retains its inspection scope.

    The producer owns its assertions, raw scores and failure policy. A successful
    report is neither knowledge acceptance nor an assertion of unavailable coverage.
    Native publication remains with the caller and the grouped output witnesses.
    """
    if inspection_outcome not in {"produced", "empty"}:
        raise ValueError("failed/unperformed inspection cannot publish a candidate report")
    pin = primary.pin.values()
    if (
        pin["project_id"],
        pin["subject"],
        pin["original_source"],
        pin["analyzed_scope_meaning"],
    ) != (
        context.project_id,
        context.subject,
        context.original_source,
        json_context_meaning(context.analyzed_scope).decode(),
    ):
        raise ValueError(
            "candidate inspection context differs from its actual bound primary source"
        )
    kinds = {kind.name: kind.semantic_id for kind in model.kinds}
    contracts = {(identity.owner, identity.domain): identity.key for identity in model.identities}
    packets = []
    for candidate_type, class_name, values in (
        ("record", record_class, records),
        ("contribution", contribution_class, contributions),
    ):
        for value in values:
            if value.get("candidate_type", candidate_type) != candidate_type:
                raise ValueError("candidate body cannot change its declared semantic family")
            body = {**value, "candidate_type": candidate_type}
            checked = prepared.validate_json(class_name, json_bytes(body)).model_dump(
                mode="python", exclude_unset=True
            )
            packets.append(
                {
                    "member_id": candidate_member_id(candidate_type, checked),
                    "kind_contract": contracts[kinds[class_name], "kind"],
                    "context": {
                        "subject": context.subject,
                        "subject_definition": context.subject_definition,
                        "original_source": context.original_source,
                        "analyzed_scope": json_loads(context.analyzed_scope),
                    },
                    "body": checked,
                }
            )
    if inspection_outcome == "empty" and packets:
        raise ValueError("empty inspection cannot carry produced candidates")
    report = {
        "source_pin": pin,
        "inspection_outcome": inspection_outcome,
        "standing": "private_uncalibrated_candidates",
        "members": packets,
        "operations": operations,
        "coordinate_texts": coordinate_texts,
        "coverage": coverage,
        "diagnostics_json": json_bytes(diagnostics or {}).decode(),
    }
    if report_class in {"DdoPredicateInspectionReport", "DdoScopedRelationsReport"}:
        from .contribution_input_references import SUPPORT_FIELDS, check_contribution_input_support

        support = (
            {field: [] for field in SUPPORT_FIELDS}
            if input_support is None
            else dict(input_support)
        )
        if report_class == "DdoPredicateInspectionReport" and support.pop("inherited_support", ()):
            raise ValueError("predicate report cannot inherit a second predicate producer")
        report.update(support)
        check_contribution_input_support(report)
    if report_class in {"DdoGlinerFunctionCandidatesReport", "DdoD1SourceCandidatesReport"}:
        report["observation_set_digest"] = candidate_observation_set_digest(operations)
    return prepared.validate_json(report_class, json_bytes(report)).model_dump(
        mode="python", exclude_unset=True
    )


def candidate_member_values(report, *, candidate_type):
    """Project validated candidate domain fields, excluding the carrier discriminator.

    Domain record/contribution IDs predate the packet's candidate_type label. This
    explicit view preserves that domain payload; it does not relabel its native kind.
    """
    if candidate_type not in {"record", "contribution"}:
        raise ValueError("unknown candidate member family")
    return tuple(
        {name: value for name, value in packet["body"].items() if name != "candidate_type"}
        for packet in report["members"]
        if packet["body"]["candidate_type"] == candidate_type
    )


def validate_bound_candidate_report(prepared, model, binding, role_name, value):
    """Validate the actual admitted candidate kind, preserving legitimate refinement fields."""
    from .data_operation_kind_refinements import input_kind_contracts
    from .data_operation_ports import PortRefusal

    if binding is None or not binding.sufficient:
        raise PortRefusal("candidate report requires its sufficient native binding")
    declarations = [
        role
        for role in model.operation(binding.operation).roles
        if role.name == role_name and role.direction == "input"
    ]
    selected = [role for role in binding.roles if role.role == role_name]
    if len(declarations) != 1 or len(selected) != 1:
        raise PortRefusal("candidate report requires its one declared input role")
    members = selected[0].members
    if len(members) != 1 or members[0].multiplicity != 1:
        raise PortRefusal("candidate report requires its exact scalar native member")
    member = members[0]
    accepted = input_kind_contracts(model, (declarations[0].kind,))[declarations[0].kind]
    actual = [
        identity.owner
        for identity in model.identities
        if identity.domain == "kind" and identity.key == member.kind_contract
    ]
    if member.kind_contract not in accepted or len(actual) != 1:
        raise PortRefusal("candidate report kind is outside its declared input family")
    definitions = [definition for definition in prepared.definitions if definition.iri == actual[0]]
    if len(definitions) != 1:
        raise PortRefusal("candidate report lacks its actual concrete nominal definition")
    return prepared.validate_json(definitions[0].name, json_bytes(value)).model_dump(
        mode="python", exclude_unset=True
    )
