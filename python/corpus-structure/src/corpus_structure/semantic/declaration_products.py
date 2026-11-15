"""Acquired shared declaration syntax, separate from source grammar production."""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from .construction_products import (
    CharacterizationSnapshot,
    InterpretedProduct,
    construction_product_inputs,
    interpreted_member_contracts,
    interpreted_product_value,
    validate_interpreted_product,
)
from .data_operation_model import ResolvedRoleBinding, SubjectContext
from .identity import canonical_bytes
from .types import PreparedRelease, SourceArtifact

_ROOT = Path(__file__).parents[1]
_PATHS = (
    "methods/declaration_syntax.py",
    "semantic/declaration_products.py",
    "semantic/constructions/retained_declarations.py",
    "semantic/constructions/layers.py",
    "semantic/constructions/retained_rules.py",
    "semantic/constructions/retained_rules.json",
    "semantic/construction_products.py",
    "semantic/declared_record_sources.py",
    "semantic/source_contexts.py",
    "semantic/canonical_sentences.py",
    "semantic/hanlp_products.py",
    "semantic/characterization_manifests.py",
    "semantic/enriched_document_products.py",
    "model/semantic/data-operation-constructions.yaml",
)


@dataclass(frozen=True)
class DeclarationSyntaxProduct(InterpretedProduct):
    kind_name: ClassVar[str] = "DdoDeclarationSyntaxProduct"
    manifest_name: ClassVar[str] = "DdoConstructionManifest"


def declaration_inputs(bundle):
    from .hanlp_products import hanlp_product_inputs

    names = {source.name for source in bundle.sources}
    if "data_operation_constructions" not in names:
        bundle = construction_product_inputs(bundle)
    return hanlp_product_inputs(bundle)


def declaration_profile_assets():
    return SourceArtifact(
        "declarations/profile-assets",
        canonical_bytes(
            {
                "version": "declared-canonical-hanlp-syntax-v1",
                "files": [(name, (_ROOT / name).read_bytes().hex()) for name in _PATHS],
            }
        ),
    )


def declaration_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in (
                "methods/declaration_syntax.py",
                "semantic/declaration_products.py",
                "semantic/data_operation_prepared_call.py",
            )
        ),
        boundary_contracts=(declaration_profile_assets(),),
    )


def declaration_product_values(
    source, source_frame, canonical, hanlp, contracts, *, check_active=lambda: None
):
    from .construction_products import _requested_regions
    from .constructions.layers import ConstructionLayer, ConstructionSource
    from .constructions.retained_declarations import (
        DECLARATION_FAMILY,
        populate_declaration_products,
    )

    selected = source.value
    view = ConstructionSource.from_native(source)
    layer = ConstructionLayer(
        selected["source"],
        {"selectors": selected["selectors"]},
        {"key": "text.declaration_syntax/source-native"},
        families=(DECLARATION_FAMILY,),
        semantic=True,
    )
    requested, unavailable = _requested_regions(source)
    for selector in unavailable:
        layer.record(
            DECLARATION_FAMILY, selector, "unknown", "selected original ancestry is unavailable"
        )
    populate_declaration_products(
        layer,
        view,
        source,
        None,
        canonical,
        hanlp,
        annotation_products=(),
        source_frame=source_frame,
        check_active=check_active,
        admitted=lambda a, b: any(start <= a < b <= end for start, end in requested),
    )
    return interpreted_product_value(source, layer.facts(), contracts, (canonical, hanlp))


@dataclass(frozen=True)
class PreparedDeclarationInputs:
    prepared: PreparedRelease
    roles: tuple[ResolvedRoleBinding, ...]
    context: SubjectContext
    check_active: Callable[[], None]

    def member(self, name, *, whole=True):
        (role,) = (role for role in self.roles if role.role == name)
        (member,) = role.members
        if member.multiplicity != 1 or (whole and member.member is not None):
            raise ValueError("declaration input requires exact scalar product custody")
        return member

    def retained(self, name, value, kind, model):
        from .enriched_document_products import RetainedCharacterizationProduct

        member = self.member(name)
        context = SubjectContext(
            self.context.project_id, member.subject, member.original_source, member.analyzed_scope
        )
        product = RetainedCharacterizationProduct.acquire(
            self.prepared,
            model,
            self.prepared.index.definitions[kind].iri,
            canonical_bytes(value),
            subject_context=context,
        )
        if product.semantic_id != member.product:
            raise ValueError("declaration body differs from its exact bound product")
        return CharacterizationSnapshot(product.semantic_id, product.content)

    def run(self, source, canonical, hanlp):
        from .data_operation_admission import bound_data_operation_model
        from .declared_record_sources import DeclaredNativeFrameSource
        from .source_products import FrozenNativeSource

        model = bound_data_operation_model(self.prepared)
        selected = FrozenNativeSource.acquire(self.prepared, source)
        frame = DeclaredNativeFrameSource.acquire(
            self.prepared,
            source,
            self.member("source", whole=False),
            project=self.context.project_id,
        )
        canonical = self.retained("canonical", canonical, "DdoCanonicalSentences", model)
        hanlp = self.retained("hanlp", hanlp, "DdoHanlpInventory", model)
        self.check_active()
        value = declaration_product_values(
            selected,
            frame,
            canonical,
            hanlp,
            interpreted_member_contracts(self.prepared, model),
            check_active=self.check_active,
        )
        product = validate_interpreted_product(
            self.prepared,
            model,
            value,
            selected,
            (canonical, hanlp),
            product_type=DeclarationSyntaxProduct,
            subject_context=self.context,
        )
        self.check_active()
        return json.loads(product.content)


def execute_declaration_profile(receiver, source, canonical, hanlp):
    if receiver.inputs is None:
        raise ValueError("declaration syntax requires its actual acquired native input binding")
    return receiver.inputs.run(source, canonical, hanlp)


def declaration_kernel(
    arguments: dict,
    roles: tuple[ResolvedRoleBinding, ...],
    context: SubjectContext,
    *,
    prepared: PreparedRelease,
    check_active: Callable[[], None],
) -> dict:
    from corpus_structure.methods.declaration_syntax import DeclarationSyntaxOperation

    return DeclarationSyntaxOperation(
        PreparedDeclarationInputs(prepared, roles, context, check_active)
    ).run(**arguments)


@dataclass
class DeclarationCallPlan:
    prepared: PreparedRelease
    port: Any = None

    def verify(self):
        if declaration_profile_assets() != self.port.assets[0]:
            raise ValueError("declaration original semantic assets changed")

    def plan(self, arguments, *, binding, check_active, execution_owner):

        if binding is None or binding.subject_context is None:
            raise ValueError("declaration syntax lacks its qualified native binding")
        signature = inspect.signature(declaration_kernel, eval_str=True)
        bound = signature.bind(
            arguments=arguments.arguments,
            roles=binding.roles,
            context=binding.subject_context,
            prepared=self.prepared,
            check_active=check_active,
        )
        captured = declaration_operation_sources()
        return (yield from self.port.plan_cpu(
            declaration_kernel,
            bound,
            captured,
            prepared_release_id=self.prepared.release_id,
            verify=self.verify,
            execution_owner=execution_owner,
            check_active=check_active,
        ))


def resolve_declaration_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.declaration_syntax import DeclarationSyntaxOperation

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != DeclarationSyntaxOperation.__data_operation__["id"]:
        raise PortRefusal("declaration factory differs from its governing operation")
    receiver = DeclarationSyntaxOperation(None)
    plan = DeclarationCallPlan(prepared)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.declaration_products.DeclarationCallPlan.plan",
        authorize,
        (declaration_profile_assets(),),
        declaration_operation_sources(),
        functions=(
            (
                "corpus_structure.semantic.declaration_products.declaration_kernel",
                declaration_kernel,
            ),
            (
                "corpus_structure.semantic.declaration_products.execute_declaration_profile",
                execute_declaration_profile,
            ),
            (
                "corpus_structure.semantic.declaration_products.PreparedDeclarationInputs.run",
                PreparedDeclarationInputs.run,
            ),
        ),
        requires_prepared_schema=True,
    )
    plan.port = port
    return port
