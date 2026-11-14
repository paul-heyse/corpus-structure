"""One source-bound private candidate inspection artifact for declared producers."""

from pathlib import Path

import yaml

from .data_operation_json import json_bytes, json_loads
from .data_operation_model import json_context_meaning
from .declared_record_sources import declared_record_inputs
from .source_products import source_product_inputs
from .types import SourceArtifact, SourceBundle

_MODEL = Path(__file__).parents[1] / "model/semantic/data-operation-candidate-inspection.yaml"


def candidate_inspection_inputs(bundle):
    """Compose the shared nominal source/member contract, preserving old archives."""
    from .source_discovery import source_discovery_inputs

    bundle = declared_record_inputs(source_product_inputs(bundle))
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
    return SourceBundle(root, (*bundle.sources, SourceArtifact(name, _MODEL.read_bytes()), SourceArtifact(root, yaml.safe_dump({"id": "urn:corpus:candidate-inspection-root", "name": root, "imports": [bundle.root, name]}).encode())))


def candidate_inspection_report(prepared, model, primary, context, *, inspection_outcome,
    records=(), contributions=(), operations=(), coordinate_texts=(), coverage=(), diagnostics=None,
    report_class="DdoCandidateInspectionReport", record_class="DdoCandidateSourceRecord", contribution_class="DdoCandidateSourceContribution"):
    """Store each actual candidate once; empty output retains its inspection scope.

    The producer owns its assertions, raw scores and failure policy. A successful
    report is neither knowledge acceptance nor an assertion of unavailable coverage.
    Native publication remains with the caller and the grouped output witnesses.
    """
    if inspection_outcome not in {"produced", "empty"}:
        raise ValueError("failed/unperformed inspection cannot publish a candidate report")
    pin = primary.pin.values()
    if (pin["project_id"], pin["subject"], pin["original_source"], pin["analyzed_scope_meaning"]) != (context.project_id, context.subject, context.original_source, json_context_meaning(context.analyzed_scope).decode()):
        raise ValueError("candidate inspection context differs from its actual bound primary source")
    kinds = {kind.name: kind.semantic_id for kind in model.kinds}
    contracts = {(identity.owner, identity.domain): identity.key for identity in model.identities}
    packets = []
    for candidate_type, class_name, identifier, values in (("record", record_class, "record_id", records), ("contribution", contribution_class, "contribution_id", contributions)):
        for value in values:
            if value.get("candidate_type", candidate_type) != candidate_type:
                raise ValueError("candidate body cannot change its declared semantic family")
            body = {**value, "candidate_type": candidate_type}
            checked = prepared.validate_json(class_name, json_bytes(body)).model_dump(mode="python", exclude_unset=True)
            packets.append({"member_id": candidate_type + ":" + value[identifier], "kind_contract": contracts[kinds[class_name], "kind"], "context": {"subject": context.subject, "original_source": context.original_source, "analyzed_scope": json_loads(context.analyzed_scope)}, "body": checked})
    if inspection_outcome == "empty" and packets:
        raise ValueError("empty inspection cannot carry produced candidates")
    report = {"source_pin": pin, "inspection_outcome": inspection_outcome, "standing": "private_uncalibrated_candidates", "members": packets, "operations": operations, "coordinate_texts": coordinate_texts, "coverage": coverage, "diagnostics_json": json_bytes(diagnostics or {}).decode()}
    return prepared.validate_json(report_class, json_bytes(report)).model_dump(mode="python", exclude_unset=True)


def candidate_member_values(report, *, candidate_type):
    """Project already validated immutable report membership without another read."""
    if candidate_type not in {"record", "contribution"}:
        raise ValueError("unknown candidate member family")
    return tuple(packet["body"] for packet in report["members"] if packet["body"]["candidate_type"] == candidate_type)
