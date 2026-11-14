"""Acquired finite factor execution over admitted private candidate products."""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .identity import canonical_bytes
from .types import SourceArtifact, SourceBundle

_ROOT = Path(__file__).parents[1]
_MODEL = _ROOT / "model/semantic/data-operation-interpretation.yaml"
_FILES = (
    "methods/finite_interpretation.py",
    "semantic/finite_interpretation_products.py",
    "semantic/record_interpretation.py",
    "methods/record_readings.py",
    "methods/local_interpretation.py",
    "methods/table_interpretation.py",
    "semantic/local_interpretation_reports.py",
    "semantic/declared_candidate_products.py",
)


def finite_interpretation_inputs(bundle):
    import yaml

    from .declared_candidate_products import candidate_inspection_inputs

    bundle = candidate_inspection_inputs(bundle)
    name, root = "data_operation_interpretation", "data_operation_interpretation_root"
    existing = {source.name: source.content for source in bundle.sources}
    if name in existing:
        if existing[name] != _MODEL.read_bytes():
            raise ValueError("finite interpretation schema differs from its acquired owner")
        return bundle
    if root in existing:
        raise ValueError("finite interpretation uses its reserved schema root")
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact(name, _MODEL.read_bytes()),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    {
                        "id": "urn:corpus:finite-interpretation-root",
                        "name": root,
                        "imports": [bundle.root, name],
                    }
                ).encode(),
            ),
        ),
    )


def finite_interpretation_assets():
    return SourceArtifact(
        "finite/algorithm-assets",
        canonical_bytes(
            {
                "version": "finite-interpretation-1",
                "schema": _MODEL.read_bytes().hex(),
                "files": [(name, (_ROOT / name).read_bytes().hex()) for name in _FILES],
            }
        ),
    )


def finite_interpretation_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in _FILES[:2]
        ),
        boundary_contracts=(finite_interpretation_assets(),),
    )


def _request_value(value):
    """Restore explicit hard-zero factors; never supply a missing factor or score."""
    if isinstance(value, dict):
        if set(value) == {"nonfinite_float"}:
            if value["nonfinite_float"] not in {"-inf", "inf", "nan"}:
                raise ValueError("unknown retained nonfinite factor spelling")
            return float(value["nonfinite_float"])
        return {key: _request_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return tuple(_request_value(item) for item in value)
    return value


def finite_interpretation_values(candidates, policy, *, check_active=lambda: None):
    """Use the existing record/local/table kernels, preserving honest unavailable outcomes."""
    from pydantic import TypeAdapter

    from corpus_structure.methods.local_interpretation import local_question_operation
    from corpus_structure.methods.record_readings import (
        interpret_candidate_readings,
        retained_reading_groups,
    )
    from corpus_structure.methods.table_interpretation import table_policy_operations

    from .declared_candidate_products import candidate_member_values
    from .observations import source_python, source_value
    from .record_interpretation import InterpretationRequest, LocalInterpretationRequest

    if (
        candidates["standing"] != "private_uncalibrated_candidates"
        or policy["version"] != "finite-interpretation-policy-1"
    ):
        raise ValueError("finite interpretation requires private candidates and its actual policy")
    check_active()
    selected = source_python(policy["requests"])
    dependencies = tuple(policy["dependencies"])
    if len(set(dependencies)) != len(dependencies):
        raise ValueError("finite policy repeats a computation dependency")
    if policy["mode"] == "records":
        records = candidate_member_values(candidates, candidate_type="record")
        groups = retained_reading_groups(records)
        if not isinstance(selected, dict) or set(selected) - {group.record_id for group in groups}:
            raise ValueError("finite record policy references an unselected occurrence")
        requests = {
            key: TypeAdapter(InterpretationRequest).validate_python(_request_value(value))
            for key, value in selected.items()
            if value is not None
        }
        if any(
            not set(dependencies) <= {item.key for item in request.dependencies}
            for request in requests.values()
        ):
            raise ValueError("finite request omits its selected policy dependencies")
        reports = interpret_candidate_readings(
            records, request_factory=lambda group: requests.get(group.record_id)
        )
    elif policy["mode"] == "local":
        contributions = candidate_member_values(candidates, candidate_type="contribution")
        by_id = {row["contribution_id"]: row for row in contributions}
        if len(by_id) != len(contributions) or not isinstance(selected, (list, tuple)):
            raise ValueError(
                "finite local policy requires distinct retained contribution identities"
            )
        reports = []
        for question in selected:
            check_active()
            identifiers = tuple(question["contribution_ids"])
            if len(set(identifiers)) != len(identifiers) or set(identifiers) - by_id.keys():
                raise ValueError("finite local question references an unselected contribution")
            raw_request = question.get("request")
            request = (
                None
                if raw_request is None
                else TypeAdapter(LocalInterpretationRequest).validate_python(
                    _request_value(raw_request)
                )
            )
            reports.append(
                local_question_operation(
                    question=question["question"],
                    contributions=tuple(by_id[key] for key in identifiers),
                    dependency_ids=tuple(sorted(set(dependencies) | set(question["dependencies"]))),
                    request=request,
                    check_active=check_active,
                    unavailable_reason=question.get("unavailable_reason"),
                )
            )
    elif policy["mode"] == "table":
        if not isinstance(selected, dict) or set(selected) != {"mode", "weight_scale"}:
            raise ValueError("finite table policy requires its exact mode and weight scale")
        reports = table_policy_operations(
            contributions=candidate_member_values(candidates, candidate_type="contribution"),
            dependency_ids=dependencies,
            source_revision=candidates["source_pin"]["source_product"],
            mode=selected["mode"],
            weight_scale=selected["weight_scale"],
        )
    else:
        raise ValueError("unknown finite interpretation mode")
    check_active()
    return {
        "version": "finite-interpretation-1",
        "source_pin": candidates["source_pin"],
        "mode": policy["mode"],
        "standing": "private_candidate_relative",
        "reports": source_value(json.loads(canonical_bytes(reports))),
    }


def finite_interpretation_reports(product):
    """Immediate consumer projection, preserving the selected private result's outcomes."""
    from .observations import source_python

    if (
        product["version"] != "finite-interpretation-1"
        or product["standing"] != "private_candidate_relative"
    ):
        raise ValueError("finite report consumer requires its private native product")
    reports = source_python(product["reports"])
    if not isinstance(reports, list):
        raise ValueError("finite reports require their complete retained sequence")
    return tuple(reports)


def execute_finite_profile(receiver, candidates, policy):
    return receiver.execute(candidates, policy)


def execute_finite_kernel(
    candidates: dict[str, Any], policy: dict[str, Any], *, check_active
) -> dict[str, Any]:
    return finite_interpretation_values(candidates, policy, check_active=check_active)


@dataclass
class FiniteInvocationPlan:
    prepared: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from .data_operation_cpu import PythonCPUDescriptor, plan_cpu_call
        from .data_operation_json import json_bytes
        from .data_operation_prepared_call import PreparedCallResult

        if binding is None or binding.subject_context is None:
            raise ValueError("finite interpretation requires its admitted source context")
        values = arguments.arguments
        candidates = self.prepared.validate_json(
            "DdoCandidateInspectionReport", json_bytes(values["candidates"])
        ).model_dump(mode="python", exclude_unset=True)
        policy = self.prepared.validate_json(
            "DdoFiniteInterpretationPolicy", json_bytes(values["policy"])
        ).model_dump(mode="python", exclude_unset=True)
        pin, context = candidates["source_pin"], binding.subject_context
        from .data_operation_model import json_context_meaning

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
            raise ValueError("finite candidate source differs from its acquired context")
        signature = inspect.signature(execute_finite_kernel, eval_str=True)
        bound = signature.bind(candidates=candidates, policy=policy, check_active=check_active)
        captured = finite_interpretation_operation_sources()
        descriptor = PythonCPUDescriptor(
            tuple((source.module, source.filename, source.content) for source in captured.sources),
            "corpus_structure.semantic.finite_interpretation_products.execute_finite_kernel",
            (),
            verification="prepared-kernel",
            control_parameter="check_active",
        )
        reply = yield from plan_cpu_call(
            descriptor,
            bound,
            signature,
            verify=self.port._verify,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        product = self.prepared.validate_json(
            "DdoFiniteInterpretationProduct", reply.content
        ).model_dump(mode="python", exclude_unset=True)
        return PreparedCallResult(
            product, cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record())
        )


def resolve_finite_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.finite_interpretation import FiniteInterpretationOperation

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != FiniteInterpretationOperation.__data_operation__["id"]:
        raise PortRefusal("finite prepared factory belongs to another operation")
    receiver = FiniteInterpretationOperation(finite_interpretation_values)
    plan = FiniteInvocationPlan(prepared)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.finite_interpretation_products.FiniteInvocationPlan.plan",
        authorize,
        (finite_interpretation_assets(),),
        finite_interpretation_operation_sources(),
        functions=(
            (
                "corpus_structure.semantic.finite_interpretation_products.execute_finite_kernel",
                execute_finite_kernel,
            ),
        ),
        requires_prepared_schema=True,
    )
    plan.port = port
    return port
