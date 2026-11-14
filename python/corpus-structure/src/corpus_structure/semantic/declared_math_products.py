"""Mathematical products over admitted source, retained syntax and explicit context.

Original mathematical kernels own interpretation. Acquisition captures their
profile without manufacturing a legacy execution binding or a Reader.
"""

from __future__ import annotations

import ast
import inspect
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from .analysis_contracts import (
    AnalysisContextProfile,
    acquire_analysis_context_profile,
    prepare_interpretation_context,
)
from .data_operation_model import MODEL_VERSION, ResolvedRoleBinding
from .declared_record_sources import DeclaredNativeFrameSource
from .declared_structural_references import DeclaredProductRef, DeclaredStructuralSource
from .identity import canonical_bytes
from .types import PreparedRelease, SourceArtifact

NAMESPACE = "urn:corpus:math:"
_ASSET = "math/declared-profile"
_PATHS = (
    "methods/math/declared.py", "methods/math/native.py", "methods/math/prepared.py",
    "methods/math/native_topology.py", "methods/math/native_context.py",
    "methods/math/grammar.py", "methods/math/transform.py", "semantic/analysis_contracts.py",
    "semantic/declared_math_products.py", "semantic/formal_forest.py",
)


class DeclaredMathProduct(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source: DeclaredStructuralSource
    phase: Literal["occurrences", "symbolic"]
    formal_input: DeclaredProductRef | None = None
    occurrence_input: DeclaredProductRef | None = None
    inherited_inputs: tuple[DeclaredProductRef, ...] = ()
    items: tuple[dict[str, JsonValue], ...]
    issues: tuple[str, ...] = ()
    outcome: Literal["complete", "partial"]


class DeclaredMathOptions(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    parse_seconds: float = Field(default=2.0, gt=0)
    macros: dict[str, str] = Field(default_factory=dict)
    constants: tuple[str, ...] = ()

    def section(self):
        from corpus_structure.methods.math.methods import MathSection

        return MathSection(macros=self.macros, constants=self.constants)


def math_operation_declarations():
    from .nominal_schema_kinds import nominal_schema_kinds

    return SourceArtifact(
        "math/nominal-kinds.json",
        canonical_bytes({"version": MODEL_VERSION, "kinds": nominal_schema_kinds(
            DeclaredMathProduct.model_json_schema(), namespace=NAMESPACE, root_name="DeclaredMathProduct"
        )}),
    )


def math_profile_assets(options: DeclaredMathOptions) -> SourceArtifact:
    root = Path(__file__).parents[1]
    profile = acquire_analysis_context_profile()
    return SourceArtifact(_ASSET, canonical_bytes({
        "profile": asdict(profile), "options": options.model_dump(mode="json"),
        "schema": math_operation_declarations().content.decode(),
        "algorithms": [(name, ast.dump(ast.parse((root / name).read_bytes()), include_attributes=False)) for name in _PATHS],
    }))


def math_operation_sources(options: DeclaredMathOptions | None = None):
    from .python_operation_sources import PythonSource, PythonSourceCollection

    root = Path(__file__).parents[1]
    return PythonSourceCollection(tuple(
        PythonSource("corpus_structure." + name.removesuffix(".py").replace("/", "."),
                     (root / name).read_bytes(), str(root / name))
        for name in ("methods/math/declared.py", "semantic/declared_math_products.py", "semantic/data_operation_prepared_call.py")
    ), boundary_contracts=(math_profile_assets(options or DeclaredMathOptions()),))


@dataclass(frozen=True)
class _RetainedFormal:
    """An already admitted product address, not a recomputed product identity."""
    semantic_id: str
    content: dict
    prepared: PreparedRelease

    @property
    def value(self):
        return self.prepared.validate_json("DdoFormalProduct", canonical_bytes(self.content))

    def inventory(self):
        names = {"occurrence": "occurrences", "annotation": "annotations", "membership": "memberships", "term": "terms", "choice": "choices"}
        result = {name: [] for name in names.values()}
        for packet in self.content["members"]:
            tag = packet["body"]["record_type"]
            if tag in names:
                result[names[tag]].append(packet["body"])
        return {**result, "roles": [], "coverage": self.content["coverage"]}


@dataclass(frozen=True)
class PreparedMathInputs:
    prepared: PreparedRelease
    roles: tuple[ResolvedRoleBinding, ...]
    project: str
    options: DeclaredMathOptions
    context_profile: AnalysisContextProfile
    check_active: Callable[[], None]

    def members(self, name):
        return next(role.members for role in self.roles if role.role == name)

    def member(self, name):
        (member,) = self.members(name)
        return member

    def reference(self, name):
        return DeclaredProductRef.from_bound(self.member(name), project=self.project)

    def frame(self, value):
        return DeclaredNativeFrameSource.acquire(self.prepared, value, self.member("source"), project=self.project)

    def prepare_context(self, prepared, **values):
        return prepare_interpretation_context(prepared, context_profile=self.context_profile, **values)


def execute_occurrences(receiver, source, formal, inherited, ancestor_sources):
    from corpus_structure.methods.math.declared import declared_math_readings, selected_formula_inputs
    from corpus_structure.methods.math.native import native_reading_record
    from corpus_structure.methods.math.native import before_descendant_columns
    from .source_products import FrozenNativeSource

    profile = receiver.profile
    frame = profile.frame(source)
    inherited = tuple(DeclaredMathProduct.model_validate(value) for value in inherited)
    pins = profile.members("inherited")
    if len(pins) != len(inherited):
        raise ValueError("mathematical ancestor values differ from admitted population")
    declarations = []
    issues = []
    source_pins = profile.members("ancestor_sources")
    if len(source_pins) != len(ancestor_sources):
        raise ValueError("ancestor source bodies differ from their admitted population")
    parents = {
        (pin.product, pin.member): DeclaredNativeFrameSource.acquire(
            profile.prepared, value, pin, project=profile.project
        )
        for pin, value in zip(source_pins, ancestor_sources, strict=True)
    }
    for pin, product in zip(pins, inherited, strict=True):
        if product.phase != "occurrences" or product.source.original_source != frame.original_key:
            raise ValueError("inherited declarations require occurrence products of the same original")
        if product.source.section_pointer not in {row["self_ref"] for row in frame.ancestors}:
            raise ValueError("inherited mathematical product is not an explicit source ancestor")
        reference = DeclaredProductRef.from_bound(pin, project=profile.project)
        if product.source.subject != pin.subject or product.source.analyzed_scope_meaning != reference.analyzed_scope_meaning:
            raise ValueError("inherited mathematical product differs from its source subject")
        if product.outcome != "complete":
            issues.append("partial ancestor mathematical context: " + product.source.section_pointer)
        parent = parents.get((product.source.source_product, product.source.source_member))
        if parent is None or not product.source.matches_pin(parent.pin.values()):
            raise ValueError("inherited declarations require their exact retained ancestor source")
        for item in product.items:
            context = item.get("context")
            if isinstance(context, dict):
                before = before_descendant_columns(
                    parent_items=parent.items, parent_ancestors=parent.ancestors,
                    child_items=frame.items, child_ancestors=frame.ancestors,
                    ancestor=parent.section_pointer, child_pointer=frame.section_pointer,
                    pointer=item["pointer"],
                )
                if before is None:
                    issues.append("ancestor declaration source order unavailable: " + str(item["pointer"]))
                if before is not True:
                    continue
                parent_scope = parent.source_key + ":section:" + parent.section_pointer
                for row in context.get("declarations", ()):
                    if not isinstance(row, dict) or row.get("authority") != "source" or row.get("scope") != parent_scope:
                        continue
                    declarations.append({**row, "source_id": frame.source_key,
                        "scope": frame.source_key + ":section:" + frame.section_pointer,
                        "start": 0, "end": len(frame.items),
                        "evidence": canonical_bytes({"ancestor_product": pin.product,
                            "ancestor_source": product.source.model_dump(mode="json"),
                            "declaration": row, "before_descendant": True}).decode()})
    supplied = {value.source.section_pointer for value in inherited}
    missing = {row["self_ref"] for row in frame.ancestors if row.get("label") in {"section_header", "title"}} - supplied
    issues.extend("unavailable ancestor mathematical context: " + pointer for pointer in sorted(missing))
    retained = _RetainedFormal(profile.member("formal").product, formal, profile.prepared)
    readings = declared_math_readings(frame, (retained,), profile.options, prepared=profile.prepared,
        prepare_context=profile.prepare_context, inherited=tuple(declarations), context_issues=tuple(issues), check_active=profile.check_active)
    original = {row["self_ref"]: row.get("orig", "") for row in frame.items}
    selected, clipped = selected_formula_inputs(FrozenNativeSource.acquire(profile.prepared, source))
    records = tuple(native_reading_record(row, original=original[row.pointer], demand="occurrences") for row in readings)
    complete = not issues and not clipped and selected == {row.pointer for row in readings} and all(row.result.status.value == "ok" for row in readings)
    return DeclaredMathProduct(source=DeclaredStructuralSource.model_validate(frame.pin.values()), phase="occurrences",
        formal_input=profile.reference("formal"), inherited_inputs=tuple(DeclaredProductRef.from_bound(pin, project=profile.project) for pin in pins),
        items=json.loads(canonical_bytes(records)), issues=tuple(issues), outcome="complete" if complete else "partial").model_dump(mode="json")


def execute_normalization(receiver, source, occurrences):
    from corpus_structure.methods.math.declared import declared_normalization_readings
    from corpus_structure.methods.math.native import native_reading_record

    profile = receiver.profile
    frame = profile.frame(source)
    product = DeclaredMathProduct.model_validate(occurrences)
    if product.phase != "occurrences" or not product.source.matches_pin(frame.pin.values()):
        raise ValueError("normalization requires the exact selected source occurrence product")
    readings = declared_normalization_readings(frame, product.items, profile.options,
        prepared=profile.prepared, prepare_context=profile.prepare_context, check_active=profile.check_active)
    original = {row["self_ref"]: row.get("orig", "") for row in frame.items}
    return DeclaredMathProduct(source=product.source, phase="symbolic", occurrence_input=profile.reference("occurrences"),
        inherited_inputs=product.inherited_inputs, items=json.loads(canonical_bytes(tuple(native_reading_record(row, original=original[row.pointer], demand="symbolic") for row in readings))),
        issues=product.issues, outcome=product.outcome).model_dump(mode="json")


def math_kernel(arguments: dict, roles: tuple[ResolvedRoleBinding, ...], project: str, options: str, phase: str,
                *, prepared: PreparedRelease, check_active: Callable[[], None]) -> dict:
    from corpus_structure.methods.math.declared import DeclaredMathOccurrences, DeclaredMathNormalization

    profile = PreparedMathInputs(prepared, roles, project, DeclaredMathOptions.model_validate_json(options), acquire_analysis_context_profile(), check_active)
    receiver = DeclaredMathOccurrences(profile) if phase == "occurrences" else DeclaredMathNormalization(profile)
    return receiver.run(**arguments)


@dataclass
class MathCallPlan:
    prepared: PreparedRelease
    options: DeclaredMathOptions
    phase: str
    port: Any = None

    def verify(self):
        self.port._verify()
        if math_profile_assets(self.options) != self.port.assets[0]:
            raise ValueError("mathematical semantic profile or implementation assets changed")

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from .data_operation_cpu import PythonCPUDescriptor, plan_cpu_call
        from .data_operation_prepared_call import PreparedCallResult

        if binding is None or binding.subject_context is None:
            raise ValueError("mathematical call requires its admitted qualified binding")
        signature = inspect.signature(math_kernel, eval_str=True)
        bound = signature.bind(arguments=arguments.arguments, roles=binding.roles, project=binding.subject_context.project_id,
                               options=self.options.model_dump_json(), phase=self.phase, prepared=self.prepared, check_active=check_active)
        captured = math_operation_sources(self.options)
        descriptor = PythonCPUDescriptor(tuple((source.module, source.filename, source.content) for source in captured.sources),
            "corpus_structure.semantic.declared_math_products.math_kernel", (), verification="prepared-kernel",
            control_parameter="check_active", prepared_parameter="prepared", prepared_release_id=self.prepared.release_id)
        reply = yield from plan_cpu_call(descriptor, bound, signature, verify=self.verify, execution_owner=execution_owner, check_active=check_active)
        return PreparedCallResult(json.loads(reply.content), cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()))


def resolve_math_port(prepared, model, operation, *, receiver, phase, identity, authorize, custody, sources):
    from .data_operation_prepared_call import PreparedOriginalCallPort

    asset = next(value for value in custody if value.name == _ASSET)
    options = DeclaredMathOptions.model_validate(json.loads(asset.content)["options"])
    if math_profile_assets(options) != asset:
        raise ValueError("mathematical acquisition differs from captured semantic assets")
    selected = model.operation(operation)
    if selected.semantic_id != receiver.__data_operation__["id"]:
        raise ValueError("mathematical factory differs from its admitted operation")
    plan = MathCallPlan(prepared, options, phase)
    port = PreparedOriginalCallPort(identity, model, selected, sources, custody, receiver.run, plan.plan,
        "corpus_structure.semantic.declared_math_products.MathCallPlan.plan", authorize, (asset,), math_operation_sources(options),
        functions=(("corpus_structure.semantic.declared_math_products.math_kernel", math_kernel),), requires_prepared_schema=True)
    plan.port = port
    return port
