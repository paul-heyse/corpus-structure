"""Finite mathematical analysis over genuine native sources and retained premises."""

from __future__ import annotations

import inspect
import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, JsonValue

from .analysis_contracts import acquire_analysis_context_profile, prepare_interpretation_context
from .declared_structural_references import DeclaredStructuralSource
from .identity import canonical_bytes
from .structural_products import DeclaredStructuralInputPin
from .types import SourceArtifact

_ROOT = Path(__file__).parents[1]
_FILES = ("methods/math/analysis.py", "semantic/declared_math_analysis.py", "methods/math/native.py", "methods/math/prepared.py", "methods/math/native_topology.py", "methods/math/configuration.py", "semantic/formal_forest.py", "semantic/analysis_contracts.py", "semantic/declared_math_products.py", "semantic/constructions/math_scope.py")


class DeclaredMathAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source: DeclaredStructuralSource
    formal_input: DeclaredStructuralInputPin
    construction_input: DeclaredStructuralInputPin | None = None
    inherited_inputs: tuple[DeclaredStructuralInputPin, ...] = ()
    demand: Literal["lexical", "structure", "syntax", "interpretation", "occurrences", "symbolic", "scientific"]
    items: tuple[dict[str, JsonValue], ...]
    issues: tuple[str, ...] = ()
    outcome: Literal["complete", "partial"]


class DeclaredWeakMathAnalysis(DeclaredMathAnalysis):
    demand: Literal["lexical", "structure", "syntax"]


class DeclaredContextualMathAnalysis(DeclaredMathAnalysis):
    demand: Literal["interpretation", "occurrences", "symbolic", "scientific"]
    construction_input: DeclaredStructuralInputPin


class _AnalysisKinds(BaseModel):
    weak: tuple[DeclaredWeakMathAnalysis, ...] = ()
    contextual: tuple[DeclaredContextualMathAnalysis, ...] = ()


@lru_cache(maxsize=1)
def math_analysis_declarations():
    from .data_operation_model import MODEL_VERSION
    from .nominal_schema_kinds import nominal_schema_kinds

    return SourceArtifact("math-analysis/nominal-kinds.json", canonical_bytes({"version": MODEL_VERSION, "kinds": nominal_schema_kinds(_AnalysisKinds.model_json_schema(), namespace="urn:corpus:math-analysis:", root_name="MathAnalysisKinds")}))


def math_analysis_assets(options):
    from .declared_math_products import _normalized_math_source

    return SourceArtifact("math-analysis/profile", canonical_bytes({"version": "declared-native-math-analysis-v1", "options": options.model_dump(mode="json"), "profile": asdict(acquire_analysis_context_profile()), "schema": math_analysis_declarations().content.decode(), "algorithms": [(name, _normalized_math_source((_ROOT / name).read_bytes())) for name in _FILES]}))


def math_analysis_operation_sources(options=None):
    from .declared_math_products import DeclaredMathOptions
    from .python_operation_sources import PythonSource, PythonSourceCollection

    options = DeclaredMathOptions() if options is None else options
    return PythonSourceCollection(tuple(PythonSource("corpus_structure." + name.removesuffix(".py").replace("/", "."), (_ROOT / name).read_bytes(), str((_ROOT / name).resolve())) for name in _FILES[:2]), boundary_contracts=(math_analysis_assets(options),))


def inherited_analysis_declarations(frame, products, product_members, ancestors, ancestor_members, *, prepared, project):
    """Project actual retained parent bindings; unavailable context stays unavailable."""
    from corpus_structure.methods.math.native import before_descendant_columns
    from .declared_math_products import DeclaredMathScopeProduct
    from .declared_record_sources import DeclaredNativeFrameSource

    parents = {(pin.product, pin.member): DeclaredNativeFrameSource.acquire(prepared, body, pin, project=project) for pin, body in zip(ancestor_members, ancestors, strict=True)}
    ranked, issues, supplied = {}, [], set()
    ancestry = {row["self_ref"]: index for index, row in enumerate(frame.ancestors) if row["self_ref"] != frame.section_pointer}
    for member, body in zip(product_members, products, strict=True):
        product = DeclaredMathScopeProduct.model_validate(body)
        parent = parents.get((product.source.source_product, product.source.source_member))
        if parent is None or not product.source.matches_pin(parent.pin.values()) or product.source.original_source != frame.original_key or product.source.section_pointer not in ancestry:
            raise ValueError("mathematical context requires exact retained ancestor source/scope products")
        supplied.add(parent.section_pointer)
        if product.outcome != "complete":
            issues.append("partial ancestor mathematical context: " + parent.section_pointer)
        order = {item["self_ref"]: index for index, item in enumerate(parent.items)}
        values: list[tuple[str, str, str, dict]] = []
        for rows, role, pointer_field in ((product.source_declarations, "function", "pointer"), (product.items, "variable", "binding_pointer")):
            for row in rows:
                if role == "function":
                    if row.get("role") != "function" or row.get("scope") != parent.source_key + ":section:" + parent.section_pointer:
                        continue
                elif row.get("outcome") != "resolved" or row.get("scope_pointer") != parent.section_pointer or row.get("binding_source") != product.source.model_dump(mode="json"):
                    continue
                symbol, pointer = row.get("symbol"), row.get(pointer_field)
                if not isinstance(symbol, str) or not symbol or not isinstance(pointer, str):
                    raise ValueError("retained ancestor declaration lacks its actual symbol/native pointer")
                values.append((symbol, role, pointer, row))
        for symbol, role, pointer, row in values:
            before = before_descendant_columns(parent_items=parent.items, parent_ancestors=parent.ancestors, child_items=frame.items, child_ancestors=frame.ancestors, ancestor=parent.section_pointer, child_pointer=frame.section_pointer, pointer=pointer)
            if before is None:
                issues.append("ancestor declaration source order unavailable: " + pointer)
            if before is not True or pointer not in order:
                continue
            start = row.get("binding_start", row.get("recognized_start", 0))
            if type(start) is not int or start < 0:
                raise ValueError("retained ancestor declaration changes its original formula offset")
            rank = (len(parent.ancestors), order[pointer], start)
            evidence = canonical_bytes({"preparation_input": member.product, "ancestor_source": product.source.model_dump(mode="json", exclude_none=True), "declaration": row, "before_descendant": True}).decode()
            declaration = dict(symbol=symbol, role=role, authority="source", source_id=frame.source_key, scope=frame.source_key + ":section:" + frame.section_pointer, start=0, end=len(frame.items), evidence=evidence)
            key = symbol, role
            if key not in ranked or rank > ranked[key][0]:
                ranked[key] = rank, [declaration]
            elif rank == ranked[key][0] and declaration not in ranked[key][1]:
                ranked[key][1].append(declaration)
    issues.extend("unavailable ancestor mathematical context: " + pointer for pointer in ancestry if pointer not in supplied)
    return tuple(row for _, rows in ranked.values() for row in rows), tuple(dict.fromkeys(issues))


def analyze_declared_math(prepared, roles, context, options, context_profile, arguments, *, check_active):
    from corpus_structure.methods.math.declared import selected_formula_inputs
    from corpus_structure.methods.math.native import analyze_native_operand, declaration_scope, domain_blocks_columns, _heads
    from corpus_structure.methods.math.native_topology import prepare_native_topology_columns
    from corpus_structure.methods.math.prepared import PreparedMathInput
    from .constructions.math_scope import retained_math_scope_products
    from .declared_math_products import _RetainedCharacterization
    from .declared_record_sources import DeclaredNativeFrameSource
    from .formal_forest import SourceNativeMathReadings
    from .source_products import FrozenNativeSource

    def members(name):
        return next(role.members for role in roles if role.role == name)
    def member(name):
        (value,) = members(name)
        if (name != "source" and value.member is not None) or value.multiplicity != 1:
            raise ValueError("mathematical analysis requires exact whole premise products")
        return value

    source = arguments["source"]
    selected = FrozenNativeSource.acquire(prepared, source)
    frame = DeclaredNativeFrameSource.acquire(prepared, source, member("source"), project=context.project_id)
    demand, pointer = arguments["demand"], arguments["pointer"] or None
    question, predicate, seconds = arguments["question"] or None, arguments["predicate"] or None, arguments["seconds"]
    contextual = "constructions" in arguments
    import math

    if demand not in ({"interpretation", "occurrences", "symbolic", "scientific"} if contextual else {"lexical", "structure", "syntax"}) or not math.isfinite(seconds) or seconds <= 0 or (demand == "scientific" and question is None):
        raise ValueError("analysis demand/question differs from its actual acquired capability")
    formal = _RetainedCharacterization(member("formal").product, canonical_bytes(arguments["formal"]), prepared)
    retained = SourceNativeMathReadings(selected, (formal,))
    selected_pointers, clipped = selected_formula_inputs(selected)
    if pointer is not None and pointer not in selected_pointers:
        raise ValueError("formula selector is outside the exact analyzed original source scope")
    issues = tuple("clipped or unavailable formula scope: " + value for value in sorted(clipped))
    definitions, blocks = (), ()
    if contextual:
        definitions, inherited_issues = inherited_analysis_declarations(frame, arguments["inherited"], members("inherited"), arguments["ancestor_sources"], members("ancestor_sources"), prepared=prepared, project=context.project_id)
        issues += inherited_issues
        primary = _RetainedCharacterization(member("constructions").product, canonical_bytes(arguments["constructions"]), prepared, "DdoPrimaryConstructionProduct")
        scope = retained_math_scope_products((primary,), selected, binders=options.math_scope_binders, rules=options.math_domain_rules)
        if not scope.complete:
            issues += ("primary mathematical source scope is incomplete",)
        blocks = domain_blocks_columns(root=frame.section_pointer, text=frame.text, items=frame.items, ancestors=frame.ancestors, pieces=frame.pieces, rules=options.math_domain_rules, primary_scope=scope)
    topology = prepare_native_topology_columns(root=frame.section_pointer, text=frame.text, items=frame.items, ancestors=frame.ancestors, pieces=frame.pieces)
    health = {row["pointer"]: row["outcome"] for row in source["recognition"]}
    results, declarations = [], list(definitions)
    for ordinal, item in enumerate(frame.items):
        if item["label"] != "formula" or item["self_ref"] not in selected_pointers:
            continue
        check_active()
        ref = item["self_ref"]
        if health.get(ref) != "succeeded":
            if pointer is None or ref == pointer:
                results.append(dict(pointer=ref, orig=item.get("orig", ""), recognized_latex=item["text"], recognition_health=health.get(ref, "unknown"), availability="unavailable"))
            continue
        source_id, scope_id, end = declaration_scope(source=frame.source_key, items=frame.items, topology=topology, rules=options.math_domain_rules if contextual else (), ordinal=ordinal, blocks=blocks)
        interpretation = prepare_interpretation_context(prepared, context_profile=context_profile, macros=options.section().macro_table(), constants=options.constants, source_id=source_id, scope=scope_id, offset=ordinal, scope_chain=topology.scope_chain(ref, source_id), declarations=declarations if contextual else (), demand=demand)
        operand = PreparedMathInput(interpretation, item["text"], seconds=seconds)
        syntax = retained.syntax(ref, operand.latex, macros=interpretation.macros, kind=operand.kind or interpretation.kind)
        inventory = retained.inventory(ref, operand.latex, macros=interpretation.macros)
        operand.retain_primary_syntax(syntax, primary_input=inventory["input"])
        if contextual and interpretation.allow_local_definitions:
            for symbol, extent in _heads(operand.syntax()):
                declarations.append(dict(symbol=symbol, role="function", authority="source", evidence=f"{ref}:{extent[0]}:{extent[1]}", source_id=source_id, scope=scope_id, start=ordinal + 1, end=end))
        if pointer is not None and pointer != ref:
            continue
        results.append(analyze_native_operand(operand, demand=demand, pointer=ref, original=item.get("orig", ""), recognition_health="succeeded", context_issues=issues, context_coverage="complete" if contextual and options.math_domain_rules and not issues else "unknown", retained_inventory=lambda: inventory, question=question, predicate=predicate))
    result_type = DeclaredContextualMathAnalysis if contextual else DeclaredWeakMathAnalysis
    partial = bool(issues) or (contextual and not options.math_domain_rules) or any(item.get("availability") != "available" or item.get("outcome") in {"failed", "ambiguous", "unsupported"} or any(stage.get("coverage") == "partial" for stage in item.get("stages", {}).values()) for item in results)
    report = result_type(source=DeclaredStructuralSource.model_validate(frame.pin.values()), formal_input=DeclaredStructuralInputPin.from_bound(member("formal"), project=context.project_id), **({"construction_input": DeclaredStructuralInputPin.from_bound(member("constructions"), project=context.project_id), "inherited_inputs": tuple(DeclaredStructuralInputPin.from_bound(pin, project=context.project_id) for pin in members("inherited"))} if contextual else {}), demand=demand, items=json.loads(canonical_bytes(results)), issues=tuple(dict.fromkeys(issues)), outcome="partial" if partial else "complete")
    check_active()
    return report.model_dump(mode="json", exclude_none=True)


def math_analysis_kernel(arguments: dict, roles: tuple, context: Any, options: str, *, prepared: Any, check_active: Any) -> dict:
    from .declared_math_products import DeclaredMathOptions

    return analyze_declared_math(prepared, roles, context, DeclaredMathOptions.model_validate_json(options), acquire_analysis_context_profile(), arguments, check_active=check_active)


@dataclass
class MathAnalysisPlan:
    prepared: Any
    options: Any
    port: Any = None

    def verify(self):
        self.port._verify()
        if math_analysis_assets(self.options) != self.port.assets[0]:
            raise ValueError("mathematical analysis source or captured profile changed")

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from .data_operation_cpu import PythonCPUDescriptor, plan_cpu_call
        from .data_operation_prepared_call import PreparedCallResult
        from corpus_structure.methods.math.native import analysis_failure

        if binding is None or binding.subject_context is None:
            raise ValueError("mathematical analysis requires its exact qualified native binding")
        signature = inspect.signature(math_analysis_kernel, eval_str=True)
        bound = signature.bind(arguments=arguments.arguments, roles=binding.roles, context=binding.subject_context, options=self.options.model_dump_json(), prepared=self.prepared, check_active=check_active)
        captured = math_analysis_operation_sources(self.options)
        descriptor = PythonCPUDescriptor(tuple((source.module, source.filename, source.content) for source in captured.sources), "corpus_structure.semantic.declared_math_analysis.math_analysis_kernel", (), verification="prepared-kernel", control_parameter="check_active", prepared_parameter="prepared", prepared_release_id=self.prepared.release_id)
        reply = yield from plan_cpu_call(descriptor, bound, signature, verify=self.verify, execution_owner=execution_owner, check_active=check_active)
        body = json.loads(reply.content)
        failure = analysis_failure(SimpleNamespace(items=body["items"]))
        if failure is not None:
            # A timeout remains an unsuccessful physical attempt. No semantic
            # product or available capability is published for subsequent reuse.
            raise ValueError(failure + ": " + canonical_bytes(body).decode())
        return PreparedCallResult(body, cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()))


def execute_math_analysis(receiver, **arguments):
    return analyze_declared_math(receiver.prepared, receiver.roles, receiver.context, receiver.options, receiver.context_profile, arguments, check_active=receiver.check_active)


def resolve_math_analysis_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.math.analysis import ContextualMathAnalysis, WeakMathAnalysis
    from .data_operation_prepared_call import PreparedOriginalCallPort
    from .declared_math_products import DeclaredMathOptions

    selected = model.operation(operation)
    classes = {cls.__data_operation__["id"]: cls for cls in (WeakMathAnalysis, ContextualMathAnalysis)}
    if selected.semantic_id not in classes:
        raise ValueError("analysis factory differs from its actual admitted operation")
    body = json.loads(next(artifact.content for artifact in custody if artifact.name == "math-analysis/profile"))
    options = DeclaredMathOptions.model_validate(body["options"])
    receiver = classes[selected.semantic_id](None)
    plan = MathAnalysisPlan(prepared, options)
    port = PreparedOriginalCallPort(identity, model, selected, sources, custody, receiver.run, plan.plan, "corpus_structure.semantic.declared_math_analysis.MathAnalysisPlan.plan", authorize, (math_analysis_assets(options),), math_analysis_operation_sources(options), functions=(("corpus_structure.semantic.declared_math_analysis.execute_math_analysis", execute_math_analysis), ("corpus_structure.semantic.declared_math_analysis.math_analysis_kernel", math_analysis_kernel), ("corpus_structure.semantic.declared_math_analysis.analyze_declared_math", analyze_declared_math)), requires_prepared_schema=True)
    plan.port = port
    return port
