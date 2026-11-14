"""Acquired semantic characterization profiles on the invocation's existing CPU owner."""

from __future__ import annotations

import inspect
import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, replace
from importlib.metadata import version
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel

from .construction_products import (
    CharacterizationSnapshot,
    ConstructionOptions,
    ConstructionProduct,
    ContextualMeaningProduct,
    PreparedConstructionProfile,
    PreparedContextualProfile,
    construction_product_values,
    contextual_product_values,
    interpreted_member_contracts,
    validate_construction_product,
)
from .data_operation_identity import decode_semantic_value, semantic_value
from .data_operation_model import SubjectContext
from .data_operation_outcomes import successful_return_outcome
from .data_product_reference import DataProductReference
from .enriched_document_products import (
    EnrichedDocumentProduct,
    RetainedCharacterizationProduct,
    compose_enriched_document,
    compose_enriched_document_values,
)
from .formal_products import FormalEvidenceProduct, _semantic_nodes, validate_formal_product
from .identity import canonical_bytes
from .python_operation_sources import PythonSource, PythonSourceCollection
from .sentence_products import SourceAnnotations
from .source_products import FrozenNativeSource, source_subject
from .types import PreparedRelease, SourceArtifact


def _semantic_assets(profile: str) -> SourceArtifact:
    root = Path(__file__).parent
    common = (
        "characterization.py",
        "characterization_manifests.py",
        "characterization_evidence.py",
        "constructions/declarations.py",
        "constructions/nodes.py",
    )
    files = {
        "construction": (
            *common,
            "formal_readings.py",
            "constructions/forest.py",
            "constructions/lexical.py",
            "constructions/layers.py",
            "constructions/reuse.py",
            "constructions/named.py",
            "constructions/named_nominations.py",
            "constructions/math_scope.py",
            "constructions/retained_rules.py",
            "constructions/retained_rules.json",
            "constructions/grammars/prose.lark",
        ),
        "contextual": (*common, "constructions/evaluation.py"),
        "view": ("enriched_document_products.py",),
    }
    selected = {
        "construction": (
            "_INVENTORIES",
            "_MEMBER_VARIANTS",
            "ConstructionOptions",
            "CharacterizationSnapshot",
            "InterpretedProduct",
            "construction_product_values",
            "_requested_regions",
            "interpreted_member_contracts",
            "ConstructionProduct",
            "validate_interpreted_product",
            "validate_construction_product",
            "PreparedConstructionProfile",
        ),
        "contextual": (
            "_INVENTORIES",
            "_MEMBER_VARIANTS",
            "CharacterizationSnapshot",
            "InterpretedProduct",
            "ConstructionProduct",
            "ContextualMeaningProduct",
            "PreparedContextualProfile",
            "contextual_product_values",
            "interpreted_member_contracts",
            "validate_interpreted_product",
        ),
        "view": (),
    }
    if profile not in files:
        raise ValueError("unknown concrete characterization asset profile")
    return SourceArtifact(
        "characterization/" + profile + "-assets",
        canonical_bytes(
            dict(
                source_files=[(name, (root / name).read_bytes().hex()) for name in files[profile]],
                native_working=_semantic_nodes(
                    (root / "constructions/matching.py").read_bytes(),
                    (
                        "RAW_GROUP",
                        "Match",
                        "PreparedConstructions",
                        "_working_document",
                        "retained_native_vocab",
                        "retained_native_documents",
                    ),
                )
                if profile == "construction"
                else (),
                named_rule_engine=(root.parent / "methods/annotation_rules.py").read_bytes().hex() if profile == "construction" else None,
                native_view=(root.parent / "ingest/annotation_views.py").read_bytes().hex() if profile == "construction" else None,
                typed_profile=_semantic_nodes(
                    (root / "construction_products.py").read_bytes(), selected[profile]
                ),
                kernel=_semantic_nodes(
                    Path(__file__).read_bytes(),
                    (
                        "_semantic_assets",
                        "_body",
                        "_ConstructionInputs",
                        "_ContextualInputs",
                        "_DocumentInputs",
                        "PreparedCharacterizationPort._inputs",
                        "PreparedCharacterizationPort._roles",
                        "PreparedCharacterizationPort._formal",
                        "PreparedCharacterizationPort._retained",
                        "execute_" + profile + "_profile",
                        "execute_" + profile + "_kernel",
                    ),
                ),
                references=_semantic_nodes(
                    (root / "data_product_reference.py").read_bytes(),
                    (
                        "DataProductReference",
                        "DataProductMemberReference",
                        "member_reference",
                        "read_member_reference",
                    ),
                ),
                native_access=_semantic_nodes(
                    (root / "sentence_products.py").read_bytes(),
                    (
                        "_id",
                        "source_annotation_member_values",
                        "source_annotation_rows",
                        "retained_source_annotation_products",
                        "validate_source_annotations",
                    ),
                )
                if profile == "construction"
                else (),
                source_access=_semantic_nodes(
                    (root / "source_products.py").read_bytes(),
                    (
                        "NativeSourceSelectorIndex",
                        "FrozenNativeSource.value",
                        "FrozenNativeSource.selector_index",
                    ),
                ),
                model=(root.parent / "model/semantic/data-operation-constructions.yaml")
                .read_bytes()
                .hex(),
                libraries={
                    name: version(name)
                    for name in (
                        ("lark", "pydantic", "spacy")
                        if profile == "construction"
                        else ("pydantic",)
                    )
                },
            )
        ),
    )


def _execution_custody() -> SourceArtifact:
    root = Path(__file__).parent
    names = (
        "characterization_ports.py",
        "construction_products.py",
        "enriched_document_products.py",
        "formal_readings.py",
        "formal_products.py",
        "source_products.py",
        "characterization_manifests.py",
        "sentence_products.py",
        "declared_record_sources.py",
        "data_product_reference.py",
        "data_operation_cpu.py",
        "data_operation_prepared_products.py",
        "cpu_receipts.py",
        "cpu_execution.py",
        "constructions/forest.py",
        "constructions/lexical.py",
        "constructions/layers.py",
        "constructions/reuse.py",
        "constructions/nodes.py",
        "constructions/declarations.py",
        "constructions/evaluation.py",
        "constructions/matching.py",
        "constructions/named.py",
        "constructions/named_nominations.py",
        "constructions/math_scope.py",
        "constructions/retained_rules.py",
        "../methods/annotation_rules.py",
        "../ingest/annotation_views.py",
    )
    return SourceArtifact(
        "characterization/execution-custody",
        canonical_bytes(dict(files=[(name, (root / name).read_bytes().hex()) for name in names])),
    )


def _operation_sources(module: str, profile: str) -> PythonSourceCollection:
    path = Path(__file__).parents[1] / "methods" / (module + ".py")
    return PythonSourceCollection(
        (
            PythonSource(
                "corpus_structure.semantic.characterization_ports",
                Path(__file__).read_bytes(),
                str(Path(__file__)),
            ),
            PythonSource("corpus_structure.methods." + module, path.read_bytes(), str(path)),
        ),
        boundary_contracts=(_semantic_assets(profile), _execution_custody()),
    )


def construction_configuration(options=None):
    options = ConstructionOptions() if options is None else ConstructionOptions.model_validate(options)
    return SourceArtifact("characterization/construction-configuration", canonical_bytes(options.model_dump(mode="json")))


def construction_operation_sources(*, include_dependencies=True, construction_options=None) -> PythonSourceCollection:
    own = _operation_sources("construction_characterization", "construction")
    own = replace(own, boundary_contracts=(*own.boundary_contracts, construction_configuration(construction_options)))
    if not include_dependencies:
        return own
    from .formal_products import formal_operation_sources
    from .primary_operations import combine_primary_sources

    return combine_primary_sources(formal_operation_sources(), own)


def contextual_operation_sources(*, include_dependencies=True, construction_options=None) -> PythonSourceCollection:
    own = _operation_sources("contextual_interpretation", "contextual")
    if not include_dependencies:
        return own
    from .primary_operations import combine_primary_sources

    return combine_primary_sources(construction_operation_sources(construction_options=construction_options), own)


def document_view_operation_sources(*, include_dependencies=True) -> PythonSourceCollection:
    return _operation_sources("characterization", "view")


def characterization_operation_sources(*, construction_options=None) -> PythonSourceCollection:
    collections = (
        construction_operation_sources(construction_options=construction_options),
        contextual_operation_sources(construction_options=construction_options),
        document_view_operation_sources(),
    )
    from .primary_operations import combine_primary_sources

    return combine_primary_sources(*collections)


def execute_construction_kernel(
    source: FrozenNativeSource,
    formal: tuple[CharacterizationSnapshot, ...],
    options: ConstructionOptions,
    contracts: dict[str, str],
    assets: str,
    native: CharacterizationSnapshot | None,
    *,
    check_active: Callable[[], None],
) -> dict[str, Any]:
    if assets != _semantic_assets("construction").digest:
        raise ValueError("construction child lacks acquired semantic assets")
    return construction_product_values(
        source, formal, options, contracts, native=native, check_active=check_active
    )


def execute_contextual_kernel(
    source: FrozenNativeSource,
    products: tuple[CharacterizationSnapshot, ...],
    symbolic: tuple[DataProductReference, ...],
    contracts: dict[str, str],
    assets: str,
    *,
    check_active: Callable[[], None],
) -> dict[str, Any]:
    if assets != _semantic_assets("contextual").digest:
        raise ValueError("contextual child lacks acquired semantic assets")
    return contextual_product_values(
        source, products, symbolic, contracts, check_active=check_active
    )


def execute_view_kernel(
    sources: tuple[FrozenNativeSource, ...],
    products: tuple[CharacterizationSnapshot, ...],
    active: tuple[DataProductReference, ...],
    profile: str,
    required_families: tuple[str, ...],
    assets: str,
    *,
    check_active: Callable[[], None],
) -> dict[str, Any]:
    if assets != _semantic_assets("view").digest:
        raise ValueError("composition child lacks acquired semantic assets")
    return compose_enriched_document_values(
        sources,
        products,
        active=active,
        profile=profile,
        required_families=required_families,
        check_active=check_active,
    )


def execute_construction_profile(receiver, source, formal, sentences=None):
    return receiver.profile.run(
        source, formal, sentences=sentences, check_active=receiver.check_active
    )


def execute_contextual_profile(receiver, source, formal, constructions, supporting=()):
    return receiver.profile.run(
        source, constructions, formal, supporting=supporting, check_active=receiver.check_active
    )


def execute_view_profile(receiver, sources, products, active, profile):
    return compose_enriched_document(
        receiver.profile.prepared,
        receiver.profile.model,
        sources,
        products,
        active=tuple(DataProductReference(product.semantic_id) for product in active),
        profile=profile,
    )


def _body(prepared, name, value):
    if isinstance(
        value,
        (
            FormalEvidenceProduct,
            ConstructionProduct,
            ContextualMeaningProduct,
            SourceAnnotations,
            FrozenNativeSource,
        ),
    ):
        value = value.value
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python", exclude_unset=True)

    def freeze_sequences(item):
        if isinstance(item, dict):
            return {key: freeze_sequences(member) for key, member in item.items()}
        if isinstance(item, (list, tuple)):
            return tuple(freeze_sequences(member) for member in item)
        return item

    checked = prepared.validate_python(name, freeze_sequences(value))
    return checked.model_dump(mode="json", exclude_unset=True)


@dataclass(frozen=True)
class _ConstructionInputs:
    source: FrozenNativeSource
    formal: tuple[FormalEvidenceProduct, ...]
    native: Any = None


@dataclass(frozen=True)
class _ContextualInputs:
    source: FrozenNativeSource
    formal: tuple[FormalEvidenceProduct, ...]
    constructions: tuple[ConstructionProduct, ...]
    supporting: tuple[RetainedCharacterizationProduct, ...] = ()


@dataclass(frozen=True)
class _DocumentInputs:
    sources: tuple[FrozenNativeSource, ...]
    products: tuple[RetainedCharacterizationProduct, ...]
    active: tuple[RetainedCharacterizationProduct, ...]
    profile: str


@dataclass(frozen=True)
class PreparedCharacterizationPort(ABC):
    identity: Any
    operation: Any
    prepared: PreparedRelease
    model: Any
    authorize: Callable
    custody: tuple[SourceArtifact, ...]
    sources: PythonSourceCollection

    native_selections: ClassVar[tuple] = ()
    family: ClassVar[str]
    bridge: ClassVar[Callable]
    kernel: ClassVar[Callable]
    operation_sources: ClassVar[Callable]
    profiles: ClassVar[tuple[str, ...]] = ()

    @property
    @abstractmethod
    def endpoint(self):
        raise NotImplementedError

    @property
    def logical_signature(self):
        signature = inspect.signature(self.endpoint.run, eval_str=True)
        return signature.replace(parameters=tuple(signature.parameters.values())[1:])

    def construction_options(self):
        assets = {asset.name: asset for asset in self.custody}
        return ConstructionOptions.model_validate_json(assets["characterization/construction-configuration"].content)

    def _verify(self):
        import sys

        from .data_operation_ports import PortRefusal
        from .data_operation_prepared_products import verify_prepared_product

        bridge_name = "execute_" + self.family + "_profile"
        if getattr(sys.modules[self.endpoint.__module__], bridge_name) is not self.bridge:
            raise PortRefusal("prepared endpoint no longer binds its admitted resource bridge")
        functions = (
            (self.operation.callable_surfaces[0].declaration, self.endpoint.run),
            ("corpus_structure.semantic.characterization_ports." + bridge_name, self.bridge),
        )
        if self.family != "view":
            functions = (
                *functions,
                (
                    "corpus_structure.semantic.characterization_ports.execute_"
                    + self.family
                    + "_kernel",
                    self.kernel,
                ),
            )
        verify_prepared_product(
            self.identity,
            self.model,
            self.operation,
            self.sources,
            self.custody,
            assets=(_semantic_assets(self.family), _execution_custody(), *((construction_configuration(self.construction_options()),) if self.family == "construction" else ())),
            functions=functions,
            authorize=self.authorize,
            required_sources=self.operation_sources(
                include_dependencies=False, **({"construction_options": self.construction_options()} if self.family == "construction" else {})
            ),
        )

    def _roles(self, values, binding):
        from .data_operation_ports import PortRefusal, PythonRoleValue

        declared = {role.name: role for role in self.operation.roles if role.direction == "input"}
        contracts = {(item.owner, item.domain): item.key for item in self.model.identities}
        result = {}
        for value in values:
            if (
                not isinstance(value, PythonRoleValue)
                or value.role not in declared
                or value.role in result
                or value.kind_contract != contracts[declared[value.role].kind, "kind"]
            ):
                raise PortRefusal("characterization ingress changes declared role/kind")
            result[value.role] = value.value
        for name, role in declared.items():
            if name not in result:
                if role.minimum:
                    raise PortRefusal("characterization ingress omits a required typed role")
                result[name] = () if role.collection != "scalar" else None
        if binding is not None and (
            not binding.sufficient
            or binding.operation != self.operation.semantic_id
            or set(decode_semantic_value(json.loads(binding.parameters)))
            != set(json.loads(self.operation.parameters))
        ):
            raise PortRefusal("characterization ingress differs from acquired binding")
        return result

    def _selected_product(self, product, binding, role_name, index):
        """Restore the exact publication address from an admitted role member."""
        from .data_operation_ports import PortRefusal

        if binding is None:
            product._publication_context()
            return product
        if binding.subject_context is None:
            raise PortRefusal("product references require an explicit acquired subject context")
        role = next(role for role in binding.roles if role.role == role_name)
        members = tuple(member for member in role.members for _ in range(member.multiplicity))
        member = members[index]
        if member.member is not None:
            raise PortRefusal("whole family product cannot substitute for a selected member")
        context = SubjectContext(
            binding.subject_context.project_id,
            member.subject,
            member.original_source,
            member.analyzed_scope,
        )
        product = replace(product, subject_context=context)
        if product.semantic_id != member.product:
            raise PortRefusal("family body differs from its selected native product identity")
        return product

    def _formal(self, source, values, binding):
        result = []
        for value in values:
            body = _body(self.prepared, "DdoFormalProduct", value)
            original = FrozenNativeSource.acquire(
                self.prepared, {**source.value, "selectors": body["selectors"]}
            )
            result.append(
                self._selected_product(
                    validate_formal_product(
                        self.prepared,
                        body,
                        original,
                        model=self.model,
                        subject_context=value.subject_context
                        if isinstance(value, FormalEvidenceProduct)
                        else None,
                    ),
                    binding,
                    "formal",
                    len(result),
                )
            )
        return tuple(result)

    def _retained(self, raw, binding, name):
        from .data_operation_ports import PortRefusal

        if not raw:
            return ()
        if binding is None:
            if not all(isinstance(value, RetainedCharacterizationProduct) for value in raw):
                raise PortRefusal("heterogeneous inputs require their actual native kind lineage")
            return tuple(
                RetainedCharacterizationProduct.acquire(
                    self.prepared,
                    self.model,
                    value.kind,
                    value.content,
                    subject_context=value.subject_context,
                )
                for value in raw
            )
        selected = next(role for role in binding.roles if role.role == name)
        members = tuple(member for member in selected.members for _ in range(member.multiplicity))
        if len(members) != len(raw):
            raise PortRefusal("view value count differs from native logical members")
        products = []
        for value, member in zip(raw, members, strict=True):
            kind = next(
                (
                    item.owner
                    for item in self.model.identities
                    if item.domain == "kind" and item.key == member.kind_contract
                ),
                None,
            )
            if kind is None:
                raise PortRefusal("view member has no admitted concrete nominal kind")
            definition = next(row for row in self.prepared.definitions if row.iri == kind)
            product = RetainedCharacterizationProduct.acquire(
                self.prepared,
                self.model,
                kind,
                canonical_bytes(_body(self.prepared, definition.name, value)),
            )
            if member.member is not None:
                from .data_operation_model import SubjectContext

                context = SubjectContext(
                    binding.subject_context.project_id,
                    member.subject,
                    member.original_source,
                    member.analyzed_scope,
                )
                product = replace(
                    product,
                    subject_context=context,
                    selected_product=member.product,
                    selected_member=member.member,
                )
                products.append(product)
            else:
                products.append(self._selected_product(product, binding, name, len(products)))
        return tuple(products)

    def _inputs(self, values, binding):
        from .data_operation_ports import PortRefusal

        roles = self._roles(values, binding)
        if self.family == "view":
            if binding is None:
                raise PortRefusal(
                    "heterogeneous view inputs require exact native member kind lineage"
                )
            sources = tuple(
                FrozenNativeSource.acquire(
                    self.prepared, _body(self.prepared, "DdoSelectedNativeSource", value)
                )
                for value in roles["sources"]
            )
            if not sources and not getattr(self, "allow_empty", False):
                raise PortRefusal("view requires its explicitly bound original source population")
            if sources and binding.subject != sources[0].value["source"]["document_subject"]:
                raise PortRefusal("view subject is not its explicitly bound original document")
            if getattr(self, "activate_all", False):
                names = tuple(
                    role.name
                    for role in self.operation.roles
                    if role.direction == "input" and role.name != "sources"
                )
                retained = tuple(
                    product
                    for name in names
                    for product in self._retained(roles[name], binding, name)
                )
                products, active = retained, retained
            else:
                products = self._retained(roles["products"], binding, "products")
                active = self._retained(roles["active"], binding, "active")
            if not sources and (products or active):
                raise PortRefusal("closed empty view cannot contain characterization members")
            profile = decode_semantic_value(json.loads(binding.parameters))["profile"]
            if profile not in self.profiles:
                raise PortRefusal("composition profile is outside its admitted contract")
            return _DocumentInputs(sources, products, active, profile)

        source = FrozenNativeSource.acquire(
            self.prepared, _body(self.prepared, "DdoSelectedNativeSource", roles["source"])
        )
        if binding is not None and binding.subject != source_subject(source.value["source"]):
            raise PortRefusal(
                "characterization subject differs from exact original source coordinate"
            )
        formal = self._formal(source, roles["formal"], binding)
        if self.family == "construction":
            from .sentence_products import validate_source_annotations

            native = (
                None
                if roles["sentences"] is None
                else validate_source_annotations(
                    self.prepared,
                    self.model,
                    _body(self.prepared, "DdoSourceAnnotations", roles["sentences"]),
                    source,
                )
            )
            if native is not None:
                native = self._selected_product(native, binding, "sentences", 0)
            return _ConstructionInputs(source, formal, native)
        supporting = self._retained(roles["supporting"], binding, "supporting")
        constructions = tuple(
            self._selected_product(
                validate_construction_product(
                    self.prepared,
                    self.model,
                    _body(self.prepared, "DdoConstructionProduct", value),
                    source,
                    (*formal, *supporting),
                    subject_context=value.subject_context
                    if isinstance(value, ConstructionProduct)
                    else None,
                ),
                binding,
                "constructions",
                index,
            )
            for index, value in enumerate(roles["constructions"])
        )
        return _ContextualInputs(source, formal, constructions, supporting)

    def _completion(self, product, binding=None):
        if product is None:
            from .data_operation_ports import PortCompletion, PortRefusal

            if not getattr(self, "allow_empty", False) or "empty" not in self.operation.outcomes:
                raise PortRefusal(
                    "this composition contract does not admit a no-product completion"
                )
            return PortCompletion(self.operation.semantic_id, (), outcome="empty")
        if binding is not None:
            if binding.subject_context is None:
                raise ValueError("publication requires acquired output subject context")
            product = replace(product, subject_context=binding.subject_context)
        from .data_operation_ports import PortCompletion, RoleValue, project_product_members

        output = next(role for role in self.operation.roles if role.direction == "output")
        kind = next(
            item.key
            for item in self.model.identities
            if item.owner == output.kind and item.domain == "kind"
        )
        value = product.value.model_dump(mode="python", exclude_unset=True)
        return PortCompletion(
            self.operation.semantic_id,
            (
                RoleValue(
                    output.name,
                    kind,
                    product.content,
                    canonical_bytes(semantic_value(value)),
                    project_product_members(self.model, output.kind, value),
                ),
            ),
            outcome=successful_return_outcome(self.operation),
        )

    def invoke_python(self, values, *, binding=None, check_active=lambda: None):
        self._verify()
        check_active()
        inputs = self._inputs(values, binding)
        if isinstance(inputs, _DocumentInputs) and not inputs.sources:
            return self._completion(None, binding)
        if isinstance(inputs, _ConstructionInputs):
            product = PreparedConstructionProfile(self.prepared, self.model).run(
                inputs.source, inputs.formal, self.construction_options(), sentences=inputs.native, check_active=check_active
            )
        elif isinstance(inputs, _ContextualInputs):
            product = PreparedContextualProfile(self.prepared, self.model).run(
                inputs.source,
                inputs.constructions,
                inputs.formal,
                supporting=inputs.supporting,
                check_active=check_active,
            )
        else:
            product = compose_enriched_document(
                self.prepared,
                self.model,
                inputs.sources,
                inputs.products,
                active=tuple(
                    DataProductReference(product.semantic_id) for product in inputs.active
                ),
                profile=inputs.profile,
            )
        check_active()
        self._verify()
        return self._completion(product, binding)

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from .construction_products import validate_interpreted_product
        from .data_operation_cpu import PythonCPUDescriptor, plan_cpu_call

        self._verify()
        inputs = self._inputs(values, binding)
        if isinstance(inputs, _DocumentInputs) and not inputs.sources:
            return self._completion(None, binding)
        arguments: dict[str, Any]
        if isinstance(inputs, _DocumentInputs):
            from .characterization import characterization_profiles

            arguments = dict(
                sources=inputs.sources,
                products=tuple(
                    CharacterizationSnapshot(product.semantic_id, product.content)
                    for product in inputs.products
                ),
                active=tuple(
                    DataProductReference(product.semantic_id) for product in inputs.active
                ),
                profile=inputs.profile,
                required_families=tuple(
                    characterization_profiles(self.prepared).get("full_characterization", ())
                ),
                assets=_semantic_assets(self.family).digest,
                check_active=check_active,
            )
        elif isinstance(inputs, _ConstructionInputs):
            arguments = dict(
                source=inputs.source,
                formal=tuple(
                    CharacterizationSnapshot(product.semantic_id, product.content)
                    for product in inputs.formal
                ),
                options=self.construction_options(),
                contracts=interpreted_member_contracts(self.prepared, self.model),
                assets=_semantic_assets(self.family).digest,
                native=None
                if inputs.native is None
                else CharacterizationSnapshot(inputs.native.semantic_id, inputs.native.content),
                check_active=check_active,
            )
        elif isinstance(inputs, _ContextualInputs):
            constructions = inputs.constructions
            products = (*inputs.formal, *inputs.supporting, *constructions)
            arguments = dict(
                source=inputs.source,
                products=tuple(
                    CharacterizationSnapshot(product.semantic_id, product.content)
                    for product in products
                ),
                symbolic=tuple(product.reference for product in constructions),
                contracts=interpreted_member_contracts(self.prepared, self.model),
                assets=_semantic_assets(self.family).digest,
                check_active=check_active,
            )
        else:
            raise TypeError("unknown prepared characterization input profile")
        signature = inspect.signature(self.kernel, eval_str=True)
        owned = json.loads(_execution_custody().content)["files"]
        root = Path(__file__).parent
        sources = tuple(
            (
                "corpus_structure." + (root / name).resolve().relative_to(root.parent).as_posix().removesuffix(".py").replace("/", "."),
                str((root / name).resolve()),
                bytes.fromhex(content),
            )
            for name, content in owned
        )
        descriptor = PythonCPUDescriptor(
            sources,
            self.kernel.__module__ + "." + self.kernel.__name__,
            (),
            verification="prepared-kernel",
            control_parameter="check_active",
        )
        reply = yield from plan_cpu_call(
            descriptor,
            signature.bind(**arguments),
            signature,
            verify=self._verify,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        if isinstance(inputs, _DocumentInputs):
            checked = self.prepared.validate_json("DdoEnrichedDocumentView", reply.content)
            product = EnrichedDocumentProduct(
                canonical_bytes(checked.model_dump(mode="json", exclude_unset=True)),
                self.prepared,
                self.model,
            )
        elif isinstance(inputs, _ConstructionInputs):
            product = validate_construction_product(
                self.prepared,
                self.model,
                json.loads(reply.content),
                inputs.source,
                (*inputs.formal, *((inputs.native,) if inputs.native is not None else ())),
            )
        else:
            product = validate_interpreted_product(
                self.prepared,
                self.model,
                json.loads(reply.content),
                inputs.source,
                (*inputs.formal, *inputs.supporting, *inputs.constructions),
                product_type=ContextualMeaningProduct,
            )
        self._verify()
        return replace(
            self._completion(product, binding),
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
        )


class PreparedConstructionPort(PreparedCharacterizationPort):
    family = "construction"
    operation_sources = staticmethod(construction_operation_sources)
    bridge = staticmethod(execute_construction_profile)
    kernel = staticmethod(execute_construction_kernel)

    @property
    def endpoint(self):
        from corpus_structure.methods.construction_characterization import ConstructionOperation

        return ConstructionOperation


class PreparedContextualPort(PreparedCharacterizationPort):
    family = "contextual"
    operation_sources = staticmethod(contextual_operation_sources)
    bridge = staticmethod(execute_contextual_profile)
    kernel = staticmethod(execute_contextual_kernel)

    @property
    def endpoint(self):
        from corpus_structure.methods.contextual_interpretation import ContextualEvaluationOperation

        return ContextualEvaluationOperation


class _PreparedCompositionPort(PreparedCharacterizationPort):
    family = "view"
    kernel = staticmethod(execute_view_kernel)
    bridge = staticmethod(execute_view_profile)


class PreparedDocumentViewPort(_PreparedCompositionPort):
    profiles: ClassVar[tuple[str, ...]] = ("source_only", "selected_layers")
    operation_sources = staticmethod(document_view_operation_sources)

    @property
    def endpoint(self):
        from corpus_structure.methods.characterization import ComposeEnrichedDocumentOperation

        return ComposeEnrichedDocumentOperation


def _resolve(port_type, prepared, model, operation, *, identity, authorize, custody, sources=None):
    from .data_operation_ports import PortRefusal

    selected = model.operation(operation)
    port = port_type(
        identity,
        selected,
        prepared,
        model,
        authorize,
        custody,
        port_type.operation_sources() if sources is None else sources,
    )
    declaration = port.endpoint.__module__ + "." + port.endpoint.__qualname__ + ".run"
    if (
        selected.capabilities.forms != ("scalar",)
        or selected.capabilities.preparation != "resource"
        or selected.capabilities.cancellation != "cooperative"
        or selected.capabilities.ownership != "immutable"
        or selected.effects
        or len(selected.callable_surfaces) != 1
        or selected.callable_surfaces[0].declaration != declaration
    ):
        raise PortRefusal("operation is outside its concrete acquired characterization profile")
    port._verify()
    return port


def resolve_construction_port(prepared, model, operation, **admission):
    return _resolve(PreparedConstructionPort, prepared, model, operation, **admission)


def resolve_contextual_port(prepared, model, operation, **admission):
    return _resolve(PreparedContextualPort, prepared, model, operation, **admission)


def resolve_document_view_port(prepared, model, operation, **admission):
    return _resolve(PreparedDocumentViewPort, prepared, model, operation, **admission)


def full_document_view_operation_sources(
    *, sentence_configuration=None, hanlp_selection=None, include_dependencies=True
):
    own = _operation_sources("full_document_composition", "view")
    from .primary_operations import combine_primary_sources

    base = document_view_operation_sources(include_dependencies=False)
    if not include_dependencies:
        return combine_primary_sources(base, own)
    if sentence_configuration is None or hanlp_selection is None:
        raise ValueError(
            "full composition requires explicitly acquired sentence and HanLP profiles"
        )
    from .canonical_sentences import canonical_sentence_operation_sources
    from .hanlp_products import hanlp_operation_sources
    from .source_discovery import source_discovery_operation_sources

    return combine_primary_sources(
        characterization_operation_sources(),
        source_discovery_operation_sources(),
        canonical_sentence_operation_sources(sentence_configuration=sentence_configuration),
        hanlp_operation_sources(hanlp_selection, sentence_configuration=sentence_configuration),
        own,
    )


class PreparedFullDocumentViewPort(_PreparedCompositionPort):
    allow_empty = True
    activate_all = True
    profiles: ClassVar[tuple[str, ...]] = ("full_characterization",)
    operation_sources = staticmethod(full_document_view_operation_sources)

    @property
    def endpoint(self):
        from corpus_structure.methods.full_document_composition import ComposeFullDocumentOperation

        return ComposeFullDocumentOperation


def resolve_full_document_view_port(prepared, model, operation, **admission):
    return _resolve(PreparedFullDocumentViewPort, prepared, model, operation, **admission)


def captured_document_view_operation_sources(
    *,
    capture_sources=None,
    sentence_configuration=None,
    hanlp_selection=None,
    include_dependencies=True,
):
    from .primary_operations import combine_primary_sources

    own = _operation_sources("captured_document_composition", "view")
    base = full_document_view_operation_sources(include_dependencies=False)
    if not include_dependencies:
        return combine_primary_sources(base, own)
    from .pdf_views import pdf_views_operation_sources

    return combine_primary_sources(
        full_document_view_operation_sources(
            sentence_configuration=sentence_configuration, hanlp_selection=hanlp_selection
        ),
        pdf_views_operation_sources(capture_sources),
        own,
    )


class PreparedCapturedDocumentViewPort(PreparedFullDocumentViewPort):
    operation_sources = staticmethod(captured_document_view_operation_sources)

    @property
    def endpoint(self):
        from corpus_structure.methods.captured_document_composition import (
            ComposeCapturedDocumentOperation,
        )

        return ComposeCapturedDocumentOperation


def resolve_captured_document_view_port(prepared, model, operation, **admission):
    return _resolve(PreparedCapturedDocumentViewPort, prepared, model, operation, **admission)
