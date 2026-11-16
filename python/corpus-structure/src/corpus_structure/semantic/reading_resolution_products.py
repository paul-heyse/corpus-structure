"""Private reading/event scores over admitted candidates and authored fitted parameters."""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, get_args

from .identity import canonical_bytes
from .python_module_projection import admitted_operation_module_meaning
from .record_policy import FeatureInstance, FrozenContract, Nonempty
from .types import SourceArtifact, SourceBundle

ReadingRecipe = Literal["retained-m1-reading-resolution-2"]
RECIPE: ReadingRecipe = get_args(ReadingRecipe)[0]
EVENT_PROCEDURE = "independent-complete-reading-logistic-1"
_ROOT = Path(__file__).parents[1]
_MODEL = _ROOT / "model/semantic/data-operation-reading-resolution.yaml"
_FILES = (
    "methods/reading_resolution.py",
    "semantic/reading_resolution_products.py",
    "semantic/record_policy.py",
    "semantic/record_contracts.py",
    "semantic/declared_candidate_products.py",
    "semantic/data_operation_cpu_basis.py",
)


def reading_resolution_inputs(bundle):
    import yaml

    from .declared_candidate_products import candidate_inspection_inputs

    bundle = candidate_inspection_inputs(bundle)
    declaration = yaml.safe_load(_MODEL.read_bytes())
    declaration["classes"]["DdoReadingFeaturePolicy"]["attributes"]["recipe"]["equals_string"] = (
        RECIPE
    )
    content = yaml.safe_dump(declaration, sort_keys=False).encode()
    name, root = "data_operation_reading_resolution", "data_operation_reading_resolution_root"
    existing = {source.name: source.content for source in bundle.sources}
    if name in existing:
        if existing[name] != content:
            raise ValueError("reading resolution schema differs from its acquired owner")
        return bundle
    if root in existing:
        raise ValueError("reading resolution uses its reserved schema root")
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact(name, content),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    {
                        "id": "urn:corpus:reading-resolution-root",
                        "name": root,
                        "imports": [bundle.root, name],
                    }
                ).encode(),
            ),
        ),
    )


def reading_resolution_assets():
    from .record_policy import READING_NUMERICS

    return SourceArtifact(
        "readings/algorithm-assets",
        canonical_bytes(
            {
                "version": "declared-reading-resolution-1",
                "schema": _MODEL.read_bytes().hex(),
                "feature_instance_schema": DeclaredReadingFeatureInstance.model_json_schema(),
                "numerical_policy": READING_NUMERICS.model_dump(mode="json"),
                "files": [
                    (
                        name,
                        (
                            admitted_operation_module_meaning((_ROOT / name).read_bytes()).hex()
                            if name in ("methods/reading_resolution.py",)
                            else (_ROOT / name).read_bytes().hex()
                        ),
                    )
                    for name in _FILES
                ],
            }
        ),
    )


def reading_resolution_declarations():
    from .data_operation_model import MODEL_VERSION
    from .nominal_schema_kinds import nominal_schema_kinds
    from .record_policy import ReadingNumericalPolicy

    return SourceArtifact(
        "reading_resolution/numerical-kinds",
        canonical_bytes(
            {
                "version": MODEL_VERSION,
                "kinds": nominal_schema_kinds(
                    ReadingNumericalPolicy.model_json_schema(),
                    namespace="urn:corpus:kind:reading:",
                    root_name="NumericalPolicy",
                ),
            }
        ),
    )


def reading_resolution_operation_sources():
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
        boundary_contracts=(reading_resolution_assets(),),
    )


def reading_diagnostics(row, details):
    """Keep one actual diagnostic per retained producer group, including repeated outputs."""
    group_ids = {
        value
        for value in row.get("computation_dependencies", ())
        if value.startswith("native-group:")
    }
    unique = {}
    for report in details.get("reports", ()):
        for diagnostic in report.get("diagnostics", ()):
            if diagnostic.get("group_dependency") in group_ids:
                key = canonical_bytes(
                    {name: value for name, value in diagnostic.items() if name != "group"}
                )
                unique.setdefault(key, diagnostic)
    return list(unique.values())


class DeclaredReadingFeatureInstance(FrozenContract):
    """Frozen predictor plus the exact consumed semantics needed for later scoring."""

    feature: FeatureInstance
    family_contract: Nonempty
    reading_recipe: Nonempty


def reading_recipe_identity(model):
    recipes = {
        item.key
        for item in model.identities
        if item.domain == "recipe" and item.owner == "resolve.m1_readings/declared"
    }
    if len(recipes) != 1:
        raise ValueError("reading resolution requires its actual admitted recipe identity")
    return next(iter(recipes))


def resolve_reading_values(prepared, candidates, policy, *, model, check_active=lambda: None):
    from .data_operation_json import json_bytes
    from .declared_candidate_products import candidate_member_id
    from .observations import source_python, source_value
    from .record_contracts import interpretation_identity, record_family_contract
    from .record_policy import derive_record_features, score_record_features

    if (
        candidates["standing"] != "private_uncalibrated_candidates"
        or policy["version"] != "reading-feature-policy-2"
        or policy["recipe"] != RECIPE
    ):
        raise ValueError(
            "reading resolution requires private candidates and its actual feature policy"
        )
    if not policy["subset"]:
        raise ValueError("reading resolution requires an explicit applicability subset")
    raw_instances = source_python(policy["feature_instances"])
    if not isinstance(raw_instances, list):
        raise ValueError("reading feature policy requires its complete instance sequence")
    instances = tuple(
        DeclaredReadingFeatureInstance.model_validate_json(json_bytes(value))
        for value in raw_instances
    )
    by_applicability = {
        (
            item.family_contract,
            item.reading_recipe,
            item.feature.applicability.family,
            item.feature.applicability.subset,
        ): item.feature
        for item in instances
    }
    if len(by_applicability) != len(instances):
        raise ValueError("reading policy repeats a fitted instance applicability")
    recipe = reading_recipe_identity(model)
    detail = json.loads(candidates["diagnostics_json"])
    from .data_operation_identity import semantic_value

    digest = sha256(canonical_bytes(semantic_value(candidates))).hexdigest()
    packets, events = [], []
    for packet in candidates["members"]:
        check_active()
        if packet["body"]["candidate_type"] != "record":
            packets.append(packet)
            continue
        row = prepared.validate_json(
            "SourceRecord",
            json_bytes(
                {name: value for name, value in packet["body"].items() if name != "candidate_type"}
            ),
        ).model_dump(mode="python", exclude_unset=True)
        if row["standing"] != "candidate":
            raise ValueError("reading resolution requires private upstream candidates")
        instance = by_applicability.get(
            (
                record_family_contract(model, row["contract"]),
                recipe,
                row["family"],
                policy["subset"],
            )
        )
        row["computation_dependencies"] = tuple(
            sorted(
                {
                    *row.get("computation_dependencies", ()),
                    "reading-recipe:" + RECIPE,
                    "raw-candidate-result:" + digest,
                    *(("record-feature-instance:" + instance.digest,) if instance else ()),
                }
            )
        )
        row["interpretation_id"] = interpretation_identity(row)
        event = {
            "record_id": row["record_id"],
            "interpretation_id": row["interpretation_id"],
            "feature_instance_digest": instance.digest if instance else None,
            "feature_input_digest": None,
            "event_procedure": EVENT_PROCEDURE,
            "final_event_score": None,
            "outcome": "not_run",
            "diagnostics": ["applicable fitted feature instance unavailable"],
        }
        if instance is not None:
            diagnostics = reading_diagnostics(row, detail)
            vector = derive_record_features(
                prepared, row, algorithm=instance.algorithm, diagnostics=diagnostics
            )
            event.update(
                feature_input_digest=vector.input_digest,
                feature_diagnostics=diagnostics,
                feature_input_canonical_json=canonical_bytes([row, diagnostics]).decode(),
            )
            try:
                score = score_record_features(instance, vector)
                event.update(
                    final_event_score=score.compatibility_potential,
                    outcome="completed",
                    diagnostics=diagnostics,
                    score=score.model_dump(mode="json"),
                )
            except (ValueError, ArithmeticError) as error:
                event.update(outcome="limited", diagnostics=[str(error)])
        events.append(event)
        body = {**row, "candidate_type": "record"}
        packets.append({**packet, "member_id": candidate_member_id("record", row), "body": body})
    check_active()
    policy_digest = sha256(json_bytes(policy)).hexdigest()
    resolved = {
        **candidates,
        "members": tuple(packets),
        "reading_policy_digest": policy_digest,
        "reading_events": source_value(json.loads(json_bytes(events))),
        "diagnostics_json": json_bytes(
            {
                "version": "declared-reading-resolution-1",
                "producer_diagnostics": detail,
                "record_policy_events": events,
                "reading_policy_digest": policy_digest,
            }
        ).decode(),
    }
    return prepared.validate_json("DdoResolvedReadingReport", json_bytes(resolved)).model_dump(
        mode="python", exclude_unset=True
    )


def resolved_reading_events(product):
    from .observations import source_python

    if (
        product["standing"] != "private_uncalibrated_candidates"
        or not product["reading_policy_digest"]
    ):
        raise ValueError("reading consumer requires its private resolved product")
    events = source_python(product["reading_events"])
    if not isinstance(events, list):
        raise ValueError("reading events require their complete retained sequence")
    return tuple(events)


def execute_reading_profile(receiver, candidates, policy):
    return receiver.execute(candidates, policy)


def execute_reading_kernel(input_basis: list, *, prepared, check_active) -> dict:
    from .data_operation_admission import bound_data_operation_model
    from .data_operation_cpu_basis import cpu_authority_reply
    from .data_operation_identity import decode_semantic_value

    basis = decode_semantic_value(input_basis)
    roles = basis["roles"]
    if (
        basis["version"] != "cpu-input-basis-2"
        or len(roles) != 2
        or {role["role"] for role in roles} != {"candidates", "policy"}
        or any(role["multiplicity"] != 1 for role in roles)
    ):
        raise ValueError("reading CPU computation requires its exact two whole inputs")
    values = {role["role"]: role["body"] for role in roles}
    result = resolve_reading_values(
        prepared,
        values["candidates"],
        values["policy"],
        model=bound_data_operation_model(prepared),
        check_active=check_active,
    )
    return cpu_authority_reply(input_basis, result)


@dataclass
class ReadingInvocationPlan:
    prepared: Any
    model: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from .data_operation_json import json_bytes
        from .data_operation_model import json_context_meaning
        from .data_operation_prepared_call import PreparedCallResult

        if binding is None or binding.subject_context is None:
            raise ValueError("reading resolution requires its acquired source context")
        from .declared_candidate_products import validate_bound_candidate_report

        candidates = validate_bound_candidate_report(
            self.prepared, self.model, binding, "candidates", arguments.arguments["candidates"]
        )
        self.prepared.validate_json(
            "DdoReadingFeaturePolicy", json_bytes(arguments.arguments["policy"])
        )
        pin, context = candidates["source_pin"], binding.subject_context
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
            raise ValueError("reading candidates differ from the acquired source context")
        signature = inspect.signature(execute_reading_kernel, eval_str=True)
        from .data_operation_cpu_basis import cpu_authority_value, cpu_input_basis_from_binding

        recipe = next(
            item.key
            for item in self.model.identities
            if item.owner == self.port.operation.semantic_id and item.domain == "recipe"
        )
        input_basis = cpu_input_basis_from_binding(
            recipe,
            binding,
            {
                "candidates": (arguments.arguments["candidates"],),
                "policy": (arguments.arguments["policy"],),
            },
        )
        bound = signature.bind(
            input_basis=input_basis, prepared=self.prepared, check_active=check_active
        )
        captured = reading_resolution_operation_sources()
        reply = yield from self.port.plan_cpu_reply(
            execute_reading_kernel,
            bound,
            captured,
            prepared_release_id=self.prepared.release_id,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        return PreparedCallResult(
            cpu_authority_value(reply.content, expected_basis=input_basis),
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
            cpu_execution_reply=reply.content,
        )


def resolve_reading_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.reading_resolution import ReadingResolutionOperation

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != ReadingResolutionOperation.__data_operation__["id"]:
        raise PortRefusal("reading factory belongs to another operation")
    receiver = ReadingResolutionOperation(None)
    plan = ReadingInvocationPlan(prepared, model)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.reading_resolution_products.ReadingInvocationPlan.plan",
        authorize,
        (reading_resolution_assets(),),
        reading_resolution_operation_sources(),
        functions=(
            (
                "corpus_structure.semantic.reading_resolution_products.execute_reading_kernel",
                execute_reading_kernel,
            ),
        ),
        requires_prepared_schema=True,
        retain_cpu_reply=True,
    )
    plan.port = port
    return port
