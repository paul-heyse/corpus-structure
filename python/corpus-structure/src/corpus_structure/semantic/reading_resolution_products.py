"""Private reading/event scores over admitted candidates and authored fitted parameters."""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .identity import canonical_bytes
from .types import SourceArtifact, SourceBundle

RECIPE = "retained-m1-reading-resolution-1"
EVENT_PROCEDURE = "independent-complete-reading-logistic-1"
_ROOT = Path(__file__).parents[1]
_MODEL = _ROOT / "model/semantic/data-operation-reading-resolution.yaml"
_FILES = ("methods/reading_resolution.py", "semantic/reading_resolution_products.py", "semantic/record_policy.py", "semantic/record_contracts.py", "semantic/declared_candidate_products.py")


def reading_resolution_inputs(bundle):
    import yaml

    from .declared_candidate_products import candidate_inspection_inputs

    bundle = candidate_inspection_inputs(bundle)
    name, root = "data_operation_reading_resolution", "data_operation_reading_resolution_root"
    existing = {source.name: source.content for source in bundle.sources}
    if name in existing:
        if existing[name] != _MODEL.read_bytes():
            raise ValueError("reading resolution schema differs from its acquired owner")
        return bundle
    if root in existing:
        raise ValueError("reading resolution uses its reserved schema root")
    return SourceBundle(root, (*bundle.sources, SourceArtifact(name, _MODEL.read_bytes()), SourceArtifact(root, yaml.safe_dump({"id": "urn:corpus:reading-resolution-root", "name": root, "imports": [bundle.root, name]}).encode())))


def reading_resolution_assets():
    return SourceArtifact("readings/algorithm-assets", canonical_bytes({"version": "declared-reading-resolution-1", "schema": _MODEL.read_bytes().hex(), "files": [(name, (_ROOT / name).read_bytes().hex()) for name in _FILES]}))


def reading_resolution_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    return PythonSourceCollection(tuple(PythonSource("corpus_structure." + name.removesuffix(".py").replace("/", "."), (_ROOT / name).read_bytes(), str((_ROOT / name).resolve())) for name in _FILES[:2]), boundary_contracts=(reading_resolution_assets(),))


def reading_diagnostics(row, details):
    """Keep one actual diagnostic per retained producer group, including repeated outputs."""
    group_ids = {value for value in row["computation_dependencies"] if value.startswith("native-group:")}
    unique = {}
    for report in details.get("reports", ()):
        for diagnostic in report.get("diagnostics", ()):
            if diagnostic.get("group_dependency") in group_ids:
                key = canonical_bytes({name: value for name, value in diagnostic.items() if name != "group"})
                unique.setdefault(key, diagnostic)
    return list(unique.values())


def resolve_reading_values(prepared, candidates, policy, *, check_active=lambda: None):
    from .data_operation_json import json_bytes
    from .declared_candidate_products import candidate_member_id
    from .observations import source_python, source_value
    from .record_contracts import interpretation_identity
    from .record_policy import FeatureInstance, derive_record_features, score_record

    if candidates["standing"] != "private_uncalibrated_candidates" or policy["version"] != "reading-feature-policy-1" or policy["recipe"] != RECIPE:
        raise ValueError("reading resolution requires private candidates and its actual feature policy")
    if not policy["subset"]:
        raise ValueError("reading resolution requires an explicit applicability subset")
    raw_instances = source_python(policy["feature_instances"])
    if not isinstance(raw_instances, list):
        raise ValueError("reading feature policy requires its complete instance sequence")
    instances = tuple(FeatureInstance.model_validate_json(json_bytes(value)) for value in raw_instances)
    by_applicability = {(item.applicability.release_id, item.applicability.family, item.applicability.subset): item for item in instances}
    if len(by_applicability) != len(instances):
        raise ValueError("reading policy repeats a fitted instance applicability")
    detail = json.loads(candidates["diagnostics_json"])
    digest = sha256(json_bytes(candidates)).hexdigest()
    packets, events = [], []
    for packet in candidates["members"]:
        check_active()
        if packet["body"]["candidate_type"] != "record":
            packets.append(packet)
            continue
        row = prepared.validate_json("SourceRecord", json_bytes({name: value for name, value in packet["body"].items() if name != "candidate_type"})).model_dump(mode="python", exclude_unset=True)
        if row["standing"] != "candidate":
            raise ValueError("reading resolution requires private upstream candidates")
        instance = by_applicability.get((prepared.release_id, row["family"], policy["subset"]))
        row["computation_dependencies"] = tuple(sorted({*row["computation_dependencies"], "reading-recipe:" + RECIPE, "raw-candidate-result:" + digest, *(("record-feature-instance:" + instance.digest,) if instance else ())}))
        row["interpretation_id"] = interpretation_identity(row)
        event = {"record_id": row["record_id"], "interpretation_id": row["interpretation_id"], "feature_instance_digest": instance.digest if instance else None, "feature_input_digest": None, "event_procedure": EVENT_PROCEDURE, "final_event_score": None, "outcome": "not_run", "diagnostics": ["applicable fitted feature instance unavailable"]}
        if instance is not None:
            diagnostics = reading_diagnostics(row, detail)
            vector = derive_record_features(prepared, row, algorithm=instance.algorithm, diagnostics=diagnostics)
            event.update(feature_input_digest=vector.input_digest, feature_diagnostics=diagnostics, feature_input_canonical_json=canonical_bytes([row, diagnostics]).decode())
            try:
                score = score_record(instance, vector, subset=policy["subset"])
                event.update(final_event_score=score.compatibility_potential, outcome="completed", diagnostics=diagnostics, score=score.model_dump(mode="json"))
            except (ValueError, ArithmeticError) as error:
                event.update(outcome="limited", diagnostics=[str(error)])
        events.append(event)
        body = {**row, "candidate_type": "record"}
        packets.append({**packet, "member_id": candidate_member_id("record", row), "body": body})
    check_active()
    policy_digest = sha256(json_bytes(policy)).hexdigest()
    resolved = {**candidates, "members": tuple(packets), "reading_policy_digest": policy_digest, "reading_events": source_value(json.loads(json_bytes(events))), "diagnostics_json": json_bytes({"version": "declared-reading-resolution-1", "producer_diagnostics": detail, "record_policy_events": events, "reading_policy_digest": policy_digest}).decode()}
    return prepared.validate_json("DdoResolvedReadingReport", json_bytes(resolved)).model_dump(mode="python", exclude_unset=True)


def resolved_reading_events(product):
    from .observations import source_python

    if product["standing"] != "private_uncalibrated_candidates" or not product["reading_policy_digest"]:
        raise ValueError("reading consumer requires its private resolved product")
    events = source_python(product["reading_events"])
    if not isinstance(events, list):
        raise ValueError("reading events require their complete retained sequence")
    return tuple(events)


def execute_reading_profile(receiver, candidates, policy):
    return receiver.execute(candidates, policy)


def execute_reading_kernel(candidates: dict, policy: dict, *, prepared, check_active) -> dict:
    return resolve_reading_values(prepared, candidates, policy, check_active=check_active)


@dataclass
class ReadingInvocationPlan:
    prepared: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from .data_operation_cpu import PythonCPUDescriptor, plan_cpu_call
        from .data_operation_json import json_bytes
        from .data_operation_model import json_context_meaning
        from .data_operation_prepared_call import PreparedCallResult

        if binding is None or binding.subject_context is None:
            raise ValueError("reading resolution requires its acquired source context")
        candidates = self.prepared.validate_json("DdoCandidateInspectionReport", json_bytes(arguments.arguments["candidates"])).model_dump(mode="python", exclude_unset=True)
        policy = self.prepared.validate_json("DdoReadingFeaturePolicy", json_bytes(arguments.arguments["policy"])).model_dump(mode="python", exclude_unset=True)
        pin, context = candidates["source_pin"], binding.subject_context
        if (pin["project_id"], pin["subject"], pin["original_source"], pin["analyzed_scope_meaning"]) != (context.project_id, context.subject, context.original_source, json_context_meaning(context.analyzed_scope).decode()):
            raise ValueError("reading candidates differ from the acquired source context")
        signature = inspect.signature(execute_reading_kernel, eval_str=True)
        bound = signature.bind(candidates=candidates, policy=policy, prepared=self.prepared, check_active=check_active)
        captured = reading_resolution_operation_sources()
        descriptor = PythonCPUDescriptor(tuple((source.module, source.filename, source.content) for source in captured.sources), "corpus_structure.semantic.reading_resolution_products.execute_reading_kernel", (), verification="prepared-kernel", control_parameter="check_active", prepared_parameter="prepared", prepared_release_id=self.prepared.release_id)
        reply = yield from plan_cpu_call(descriptor, bound, signature, verify=self.port._verify, execution_owner=execution_owner, check_active=check_active)
        return PreparedCallResult(json.loads(reply.content), cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()))


def resolve_reading_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.reading_resolution import ReadingResolutionOperation

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != ReadingResolutionOperation.__data_operation__["id"]:
        raise PortRefusal("reading factory belongs to another operation")
    receiver = ReadingResolutionOperation(None)
    plan = ReadingInvocationPlan(prepared)
    port = PreparedOriginalCallPort(identity, model, selected, sources, custody, receiver.run, plan.plan, "corpus_structure.semantic.reading_resolution_products.ReadingInvocationPlan.plan", authorize, (reading_resolution_assets(),), reading_resolution_operation_sources(), functions=(("corpus_structure.semantic.reading_resolution_products.execute_reading_kernel", execute_reading_kernel),), requires_prepared_schema=True)
    plan.port = port
    return port
