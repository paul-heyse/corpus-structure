"""Prepared source-local structural joins over exact retained native products."""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .data_operation_model import ResolvedRoleBinding, SubjectContext
from .identity import canonical_bytes
from .types import PreparedRelease, SourceArtifact
from .python_module_projection import admitted_operation_module_meaning

_ROOT = Path(__file__).parents[1]
_PATHS = (
    "methods/scoped_relations_declared.py",
    "semantic/scoped_products.py",
    "methods/scoped_relations.py",
    "methods/structural_roles.py",
    "methods/inline_formula_occurrences.py",
    "methods/witnessed_source_links.py",
    "semantic/declared_formal_readings.py",
    "semantic/constructions/navigation.py",
    "semantic/source_contexts.py",
    "semantic/declared_record_sources.py",
    "semantic/declared_candidate_products.py",
    "semantic/contributions.py",
    "semantic/record_contracts.py",
)


def scoped_inputs(bundle):
    from .construction_products import construction_product_inputs
    from .declared_candidate_products import candidate_inspection_inputs

    if "data_operation_constructions" not in {source.name for source in bundle.sources}:
        bundle = construction_product_inputs(bundle)
    return candidate_inspection_inputs(bundle)


def scoped_profile_assets():
    return SourceArtifact(
        "scoped/profile-assets",
        canonical_bytes(
            {
                "version": "declared-source-local-joins-v1",
                "files": [(name, (admitted_operation_module_meaning((_ROOT / name).read_bytes()).hex() if name in ('methods/scoped_relations_declared.py',) else (_ROOT / name).read_bytes().hex())) for name in _PATHS],
            }
        ),
    )


def scoped_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in (
                "methods/scoped_relations_declared.py",
                "semantic/scoped_products.py",
                "semantic/data_operation_prepared_call.py",
            )
        ),
        boundary_contracts=(scoped_profile_assets(),),
    )


@dataclass(frozen=True)
class PreparedScopedInputs:
    prepared: PreparedRelease
    roles: tuple[ResolvedRoleBinding, ...]
    context: SubjectContext
    check_active: Callable[[], None]

    def members(self, role):
        return next(value.members for value in self.roles if value.role == role)


def execute_scoped_relations(
    receiver, source, constructions, formal, predicates, *, passages, source_work
):
    from corpus_structure.methods.scoped_relations import discover_relations

    from .construction_products import CharacterizationSnapshot
    from .constructions.navigation import NativeNavigationIndex
    from .contributions import contribution_identity
    from .data_operation_admission import bound_data_operation_model
    from .data_operation_json import json_bytes
    from .data_product_reference import DataProductReference
    from .declared_candidate_products import candidate_inspection_report, candidate_member_values
    from .declared_formal_readings import declared_formal_layers
    from .declared_record_sources import DeclaredNativeFrameSource
    from .declared_structural_references import DeclaredStructuralSource
    from .enriched_document_products import RetainedCharacterizationProduct
    from .formal_products import validate_formal_product
    from .source_products import FrozenNativeSource
    from .structural_products import StructuralPassage

    profile = receiver.inputs
    profile.check_active()
    model = bound_data_operation_model(profile.prepared)
    (source_member,) = profile.members("source")
    selected = FrozenNativeSource.acquire(profile.prepared, source)
    frame = DeclaredNativeFrameSource.acquire(
        profile.prepared, source, source_member, project=profile.context.project_id
    )
    if any(
        member.member is not None or member.multiplicity != 1
        for role in ("constructions", "formal", "predicates")
        for member in profile.members(role)
    ):
        raise ValueError("scoped relations require exact whole retained primary products")
    products, formal_products = [], []
    for member, value in zip(profile.members("constructions"), constructions, strict=True):
        product = RetainedCharacterizationProduct.acquire(
            profile.prepared,
            model,
            profile.prepared.index.definitions["DdoPrimaryConstructionProduct"].iri,
            canonical_bytes(value),
            subject_context=SubjectContext(
                profile.context.project_id,
                member.subject,
                member.original_source,
                member.analyzed_scope,
             subject_definition=member.subject_definition),
        )
        if product.semantic_id != member.product:
            raise ValueError("scoped construction body differs from its selected product")
        products.append(CharacterizationSnapshot(product.semantic_id, product.content))
    navigation = NativeNavigationIndex(tuple(products), selected).require()
    for member, value in zip(profile.members("formal"), formal, strict=True):
        product = validate_formal_product(
            profile.prepared,
            value,
            selected,
            model=model,
            subject_context=SubjectContext(
                profile.context.project_id,
                member.subject,
                member.original_source,
                member.analyzed_scope,
             subject_definition=member.subject_definition),
        )
        if product.semantic_id != member.product:
            raise ValueError("scoped formal body differs from its exact selected product")
        formal_products.append(product)
    retained = profile.prepared.validate_json(
        "DdoPredicateInspectionReport", json_bytes(predicates)
    ).model_dump(mode="python", exclude_unset=True)
    if retained["source_pin"] != frame.pin.values():
        raise ValueError("scoped predicate inspection differs from its exact original source")
    rows = candidate_member_values(retained, candidate_type="contribution")
    if any(
        contribution_identity(row) != row["contribution_id"] or row["pin"] != frame.pin.values()
        for row in rows
    ):
        raise ValueError(
            "scoped predicate contribution differs from its actual source-bound identity"
        )
    reference = DeclaredStructuralSource.model_validate(frame.pin.values())
    chosen = tuple(StructuralPassage.model_validate(value) for value in passages)
    if not chosen:
        chosen = tuple(
            StructuralPassage(
                passage_id="native-passage:"
                + sha256(canonical_bytes([reference.identity, start, end])).hexdigest(),
                source_ref=reference.identity,
                start=start,
                end=end,
                text=frame.text[start:end],
                scope=frame.source_key,
            )
            for start, end in frame.selected_ranges
        )
    if any(
        passage.source_ref != reference.identity
        or passage.text != frame.text[passage.start : passage.end]
        or not any(
            start <= passage.start < passage.end <= end for start, end in frame.selected_ranges
        )
        for passage in chosen
    ):
        raise ValueError("scoped passage differs from its actual analyzed original source")
    if len({passage.passage_id for passage in chosen}) != len(chosen):
        raise ValueError("scoped source repeats an authored passage identity")
    diagnostics = json.loads(retained["diagnostics_json"])
    errors = (
        ()
        if diagnostics.get("inspection_complete") is True
        else ("Retained predicate inspection has unavailable source coverage.",)
    )
    result = discover_relations(
        frame,
        source_work=source_work or None,
        passages=chosen,
        navigation=navigation,
        formal_layers=declared_formal_layers(formal_products, selected),
        retained_predicates=rows,
        retained_predicate_operations=tuple(retained["operations"]),
        retained_coordinate_texts=tuple(retained["coordinate_texts"]),
        primary_product_refs=tuple(
            DataProductReference(member.product)
            for role in ("constructions", "formal", "predicates")
            for member in profile.members(role)
        ),
        annotation_errors=errors,
        inline_equations_enabled=True,
        witnessed_links_enabled=True,
        max_formula_chars=max(1, len(frame.text)),
    )
    profile.check_active()
    return candidate_inspection_report(
        profile.prepared,
        model,
        frame,
        profile.context,
        inspection_outcome="produced" if result["contributions"] else "empty",
        contributions=result["contributions"],
        operations=(result["operation"], *result["extra_operations"]),
        coordinate_texts=result["coordinates"],
        coverage=tuple(
            {
                "family": operation["question"],
                "scope": canonical_bytes(selected.value["selectors"]).decode(),
                "outcome": operation["outcome"],
                **({"reason": operation["reason"]} if "reason" in operation else {}),
            }
            for operation in (result["operation"], *result["extra_operations"])
        ),
        diagnostics={
            "formula_diagnostics": result["formula_diagnostics"],
            "retained_predicate_inspection_complete": not errors,
        },
        report_class="DdoScopedRelationsReport",
    )


def scoped_kernel(
    arguments: dict,
    roles: tuple[ResolvedRoleBinding, ...],
    context: SubjectContext,
    *,
    prepared: PreparedRelease,
    check_active: Callable[[], None],
) -> dict:
    from corpus_structure.methods.scoped_relations_declared import ScopedRelationsOperation

    return ScopedRelationsOperation(
        PreparedScopedInputs(prepared, roles, context, check_active)
    ).run(**arguments)


@dataclass
class ScopedCallPlan:
    prepared: PreparedRelease
    port: Any = None

    def verify(self):
        if scoped_profile_assets() != self.port.assets[0]:
            raise ValueError("scoped relation source or semantic assets changed")

    def plan(self, arguments, *, binding, check_active, execution_owner):

        if binding is None or binding.subject_context is None:
            raise ValueError("scoped relation call requires its exact qualified binding")
        signature = inspect.signature(scoped_kernel, eval_str=True)
        bound = signature.bind(
            arguments=arguments.arguments,
            roles=binding.roles,
            context=binding.subject_context,
            prepared=self.prepared,
            check_active=check_active,
        )
        captured = scoped_operation_sources()
        return (yield from self.port.plan_cpu(
            scoped_kernel,
            bound,
            captured,
            prepared_release_id=self.prepared.release_id,
            verify=self.verify,
            execution_owner=execution_owner,
            check_active=check_active,
        ))


def resolve_scoped_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.scoped_relations_declared import ScopedRelationsOperation

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != ScopedRelationsOperation.__data_operation__["id"]:
        raise PortRefusal("scoped relation factory differs from its governing operation")
    receiver, plan = ScopedRelationsOperation(None), ScopedCallPlan(prepared)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.scoped_products.ScopedCallPlan.plan",
        authorize,
        (scoped_profile_assets(),),
        scoped_operation_sources(),
        functions=(
            ("corpus_structure.semantic.scoped_products.scoped_kernel", scoped_kernel),
            (
                "corpus_structure.semantic.scoped_products.execute_scoped_relations",
                execute_scoped_relations,
            ),
        ),
        requires_prepared_schema=True,
    )
    plan.port = port
    return port
