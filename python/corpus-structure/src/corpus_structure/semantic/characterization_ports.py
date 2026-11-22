"""Acquired semantic characterization profiles on the invocation's existing CPU owner."""

from __future__ import annotations

import inspect
import json
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from functools import cached_property, lru_cache
from hashlib import sha256
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
    acquired_construction_product,
    construction_product_values,
    contextual_product_values,
    interpreted_member_contracts,
    validate_construction_product,
)
from .data_operation_model import SubjectContext
from .data_operation_outcomes import successful_return_outcome
from .data_operation_values import decode_semantic_value
from .data_product_reference import DataProductReference
from .enriched_document_products import (
    EnrichedDocumentProduct,
    RetainedCharacterizationProduct,
    compose_enriched_document,
    compose_enriched_document_values,
    ordered_composition_inputs,
)
from .formal_products import (
    FormalEvidenceProduct,
    acquired_formal_product,
    validate_formal_product,
)
from .identity import canonical_bytes
from .python_operation_sources import PythonSource, PythonSourceCollection
from .sentence_products import SourceAnnotations
from .source_products import FrozenNativeSource, source_subject
from .types import PreparedRelease, SourceArtifact


@lru_cache(maxsize=3)
def _semantic_assets(profile: str) -> SourceArtifact:
    from .operation_code_assets import code_asset

    root = Path(__file__).parent
    entries = {
        "construction": (execute_construction_kernel, PreparedConstructionProfile.run),
        "contextual": (execute_contextual_kernel, PreparedContextualProfile.run),
        "view": (execute_view_kernel, compose_enriched_document),
    }
    paths = ("model/semantic/data-operation-constructions.yaml",)
    if profile == "construction":
        paths += (
            "semantic/constructions/navigation_rules.json",
            "semantic/constructions/navigation_coverage.json",
            "semantic/constructions/navigation_native_pieces.json",
            "semantic/constructions/retained_rules.json",
            "semantic/constructions/grammars/prose.lark",
        )
    if profile not in entries:
        raise ValueError("unknown concrete characterization asset profile")
    return code_asset(
        "characterization/" + profile + "-assets",
        entries[profile],
        tuple((name, root.parent / name) for name in paths),
    )


def _execution_custody() -> SourceArtifact:
    root = Path(__file__).parent
    names = (
        "established_validity.py",
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
        "constructions/navigation.py",
        "constructions/retained_rules.py",
        "../methods/annotation_rules.py",
        "../ingest/annotation_views.py",
    )
    return SourceArtifact(
        "characterization/execution-custody",
        canonical_bytes(dict(files=[(name, (root / name).read_bytes().hex()) for name in names])),
        runtime_transport=True,
    )


def _geometry_runtime() -> SourceArtifact:
    from .external_runtime import acquire_bisect_runtime
    from .native_source_view import bisect_left

    runtime = acquire_bisect_runtime()
    if dict(runtime.symbols)["bisect.bisect_left"] is not bisect_left:
        raise ValueError("positioned source checker differs from its acquired native search")
    return SourceArtifact("characterization/source-geometry-runtime", bytes.fromhex(runtime.digest))


def _operation_sources(module: str, profile: str) -> PythonSourceCollection:
    from .characterization import occurrence_identity_runtime_artifact
    from .observations import native_number_runtime_artifact

    path = Path(__file__)
    sources = (
        ("semantic.characterization_ports", path),
        ("methods." + module, path.parents[1] / "methods" / (module + ".py")),
    )
    if profile in {"construction", "contextual"}:
        sources += (
            ("semantic.characterization", path.with_name("characterization.py")),
            ("semantic.characterization_evidence", path.with_name("characterization_evidence.py")),
            ("semantic.construction_products", path.with_name("construction_products.py")),
            ("semantic.data_operation_json", path.with_name("data_operation_json.py")),
            ("semantic.source_products", path.with_name("source_products.py")),
            ("semantic.native_source_view", path.with_name("native_source_view.py")),
            ("semantic.observations", path.with_name("observations.py")),
        )
    return PythonSourceCollection(
        tuple(
            PythonSource("corpus_structure." + name, file.read_bytes(), str(file))
            for name, file in sources
        ),
        boundary_contracts=(
            _semantic_assets(profile),
            _execution_custody(),
            *(
                ()
                if profile == "view"
                else (
                    _geometry_runtime(),
                    native_number_runtime_artifact(),
                    occurrence_identity_runtime_artifact(),
                )
            ),
        ),
    )


def construction_configuration(options=None):
    options = (
        ConstructionOptions() if options is None else ConstructionOptions.model_validate(options)
    )
    return SourceArtifact(
        "characterization/construction-configuration",
        canonical_bytes(options.model_dump(mode="json")),
    )


def construction_operation_sources(
    *,
    include_dependencies=True,
    construction_options=None,
    sentence_configuration=None,
    sentence_selection=None,
) -> PythonSourceCollection:
    own = _operation_sources("construction_characterization", "construction")
    own = replace(
        own,
        boundary_contracts=(
            *own.boundary_contracts,
            construction_configuration(construction_options),
        ),
    )
    if not include_dependencies:
        return own
    if sentence_configuration is None:
        raise ValueError("construction dependencies require an explicit sentence configuration")
    from .formal_products import formal_operation_sources
    from .primary_operations import combine_primary_sources
    from .sentence_products import sentence_operation_sources

    return combine_primary_sources(
        formal_operation_sources(),
        sentence_operation_sources(sentence_configuration, selection=sentence_selection),
        own,
    )


def contextual_operation_sources(
    *,
    include_dependencies=True,
    construction_options=None,
    sentence_configuration=None,
    sentence_selection=None,
) -> PythonSourceCollection:
    own = _operation_sources("contextual_interpretation", "contextual")
    if not include_dependencies:
        return own
    from .primary_operations import combine_primary_sources

    return combine_primary_sources(
        construction_operation_sources(
            construction_options=construction_options,
            sentence_configuration=sentence_configuration,
            sentence_selection=sentence_selection,
        ),
        own,
    )


def document_view_operation_sources(*, include_dependencies=True) -> PythonSourceCollection:
    return _operation_sources("characterization", "view")


def characterization_operation_sources(
    *,
    construction_options=None,
    include_dependencies=True,
    sentence_configuration=None,
    sentence_selection=None,
) -> PythonSourceCollection:
    collections = (
        construction_operation_sources(
            construction_options=construction_options,
            include_dependencies=include_dependencies,
            sentence_configuration=sentence_configuration,
            sentence_selection=sentence_selection,
        ),
        contextual_operation_sources(include_dependencies=False),
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


def execute_construction_profile(receiver, source, formal, sentences):
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


def _body(value):
    if isinstance(value, (FormalEvidenceProduct, ConstructionProduct, ContextualMeaningProduct)):
        value = value.value
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_unset=True)
    return value


@dataclass(frozen=True)
class _ConstructionInputs:
    source: FrozenNativeSource
    formal: tuple[FormalEvidenceProduct, ...]
    native: SourceAnnotations


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
    _occurrence_runtime: tuple[Any, ...] = field(init=False, repr=False, compare=False)
    _verification: Any = field(init=False, repr=False, compare=False)
    _descriptor: Any = field(init=False, repr=False, compare=False)
    _signature: inspect.Signature = field(init=False, repr=False, compare=False)
    _asset_digest: str = field(init=False, repr=False, compare=False)

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
        return self._construction_options

    @cached_property
    def _construction_options(self):
        assets = {asset.name: asset for asset in self.custody}
        return ConstructionOptions.model_validate_json(
            assets["characterization/construction-configuration"].content
        )

    def _acquire_verification(self):
        import sys

        from .data_operation_cpu import prepared_cpu_descriptor
        from .data_operation_ports import PortRefusal
        from .data_operation_prepared_products import (
            authenticated_prepared_product,
            verify_prepared_product,
        )
        from .file_custody import verified_file

        bridge_name = "execute_" + self.family + "_profile"
        if getattr(sys.modules[self.endpoint.run.__module__], bridge_name) is not self.bridge:
            raise PortRefusal("prepared endpoint no longer binds its admitted resource bridge")
        entry = self.kernel.__module__ + "." + self.kernel.__name__
        functions = (
            (self.operation.callable_surfaces[0].declaration, self.endpoint.run),
            ("corpus_structure.semantic.characterization_ports." + bridge_name, self.bridge),
            (entry, self.kernel),
        )
        occurrence_runtime = ()
        if self.family != "view":
            from .characterization import (
                occurrence_identity_runtime,
                verify_interpreted_attachment_witnesses,
                verify_inventory_native_scores,
                verify_inventory_occurrence_ids,
            )
            from .characterization_evidence import verify_navigation_source_fields
            from .data_operation_json import canonical_json_bytes

            occurrence_runtime = occurrence_identity_runtime()
            from .construction_products import (
                verify_interpreted_body_coverage,
                verify_interpreted_dependency_members,
                verify_interpreted_inventory_topology,
                verify_interpreted_literal_source,
                verify_interpreted_positioned_geometry,
                verify_interpreted_source_coverage,
            )

            functions = (
                *functions,
                (
                    "corpus_structure.semantic.characterization_evidence.verify_navigation_source_fields",
                    verify_navigation_source_fields,
                ),
                (
                    "corpus_structure.semantic.characterization.verify_interpreted_attachment_witnesses",
                    verify_interpreted_attachment_witnesses,
                ),
                (
                    "corpus_structure.semantic.characterization.verify_inventory_native_scores",
                    verify_inventory_native_scores,
                ),
                (
                    "corpus_structure.semantic.characterization.verify_inventory_occurrence_ids",
                    verify_inventory_occurrence_ids,
                ),
                (
                    "corpus_structure.semantic.data_operation_json.canonical_json_bytes",
                    canonical_json_bytes,
                ),
                (
                    "corpus_structure.semantic.construction_products.verify_interpreted_literal_source",
                    verify_interpreted_literal_source,
                ),
                (
                    "corpus_structure.semantic.construction_products.verify_interpreted_inventory_topology",
                    verify_interpreted_inventory_topology,
                ),
                (
                    "corpus_structure.semantic.construction_products.verify_interpreted_dependency_members",
                    verify_interpreted_dependency_members,
                ),
                (
                    "corpus_structure.semantic.construction_products.verify_interpreted_body_coverage",
                    verify_interpreted_body_coverage,
                ),
                (
                    "corpus_structure.semantic.construction_products.verify_interpreted_positioned_geometry",
                    verify_interpreted_positioned_geometry,
                ),
                (
                    "corpus_structure.semantic.construction_products.verify_interpreted_source_coverage",
                    verify_interpreted_source_coverage,
                ),
            )
        required = self.operation_sources(
            include_dependencies=False,
            **(
                {"construction_options": self.construction_options()}
                if self.family == "construction"
                else {}
            ),
        )
        assets = {asset.name: asset for asset in required.boundary_contracts}
        semantic = assets["characterization/" + self.family + "-assets"]
        transport = assets["characterization/execution-custody"]
        verify_prepared_product(
            self.identity,
            self.model,
            self.operation,
            self.sources,
            self.custody,
            assets=required.boundary_contracts,
            functions=functions,
            authorize=self.authorize,
            required_sources=required,
        )
        verification = authenticated_prepared_product(
            self.sources, functions, required_sources=required
        )
        root = Path(__file__).parent
        sources = []
        files = []
        for name, content in json.loads(transport.content)["files"]:
            path = (root / name).resolve()
            acquired = bytes.fromhex(content)
            module = "corpus_structure." + path.relative_to(root.parent).as_posix().removesuffix(
                ".py"
            ).replace("/", ".")
            sources.append((module, str(path), acquired))
            files.append(verified_file(path, sha256(acquired).hexdigest()))
        files.extend(
            verified_file(root.parent / name, sha256(bytes.fromhex(content)).hexdigest())
            for name, content in json.loads(semantic.content)["assets"]
        )
        verification.files = tuple(
            {file.path: file for file in (*verification.files, *files)}.values()
        )
        object.__setattr__(self, "_verification", verification)
        object.__setattr__(self, "_occurrence_runtime", occurrence_runtime)
        object.__setattr__(self, "_signature", inspect.signature(self.kernel, eval_str=True))
        object.__setattr__(self, "_asset_digest", semantic.digest)
        object.__setattr__(
            self,
            "_descriptor",
            prepared_cpu_descriptor(
                tuple(sources), entry, None, tuple(file.receipt() for file in files)
            ),
        )

    def _verify(self):
        self._verification.check()
        for runtime in self._occurrence_runtime:
            runtime.check()
        self.authorize(self.identity)

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
            subject_definition=member.subject_definition,
        )
        if product.subject_context != context:
            product = product.with_context(context)
        if product.semantic_id != member.product:
            raise PortRefusal("family body differs from its selected native product identity")
        return product

    @staticmethod
    def _member(binding, role_name, index):
        if binding is None:
            return None
        role = next(role for role in binding.roles if role.role == role_name)
        return tuple(member for member in role.members for _ in range(member.multiplicity))[index]

    def _context(self, binding, role_name, index, value):
        member = self._member(binding, role_name, index)
        if member is None:
            return getattr(value, "subject_context", None)
        return SubjectContext(
            binding.subject_context.project_id,
            member.subject,
            member.original_source,
            member.analyzed_scope,
            subject_definition=member.subject_definition,
        )

    def _formal(self, source, values, binding):
        result = []
        for value in values:
            if binding is None and type(value) is FormalEvidenceProduct:
                value.require_readable_from(source, prepared=self.prepared, model=self.model)
                value._publication_context()
                result.append(value)
                continue
            body = _body(value)
            original = FrozenNativeSource.acquire(
                self.prepared, {**source.value, "selectors": body["selectors"]}
            )
            context = self._context(binding, "formal", len(result), value)
            if binding is None:
                product = validate_formal_product(
                    self.prepared, body, original, model=self.model, subject_context=context
                )
                product._publication_context()
            else:
                product = acquired_formal_product(
                    self.prepared,
                    body,
                    original,
                    model=self.model,
                    subject_context=context,
                    member=self._member(binding, "formal", len(result)),
                )
            result.append(product)
        return tuple(result)

    def _retained(self, raw, binding, name):
        from .data_operation_ports import PortRefusal

        if not raw:
            return ()
        if binding is None:
            for value in raw:
                if (
                    type(value) is not RetainedCharacterizationProduct
                    or value.prepared.release_id != self.prepared.release_id
                    or value.model.content != self.model.content
                ):
                    raise PortRefusal("heterogeneous inputs require their actual native kind lineage")
                value._require_acquired()
            return tuple(raw)
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
            partitioned = isinstance(value, Mapping) and set(value) == {"header", "partitions"}
            product = RetainedCharacterizationProduct.acquire(
                self.prepared,
                self.model,
                kind,
                canonical_bytes(value["header"] if partitioned else _body(value)),
                partitions=tuple(map(canonical_bytes, value["partitions"]))
                if partitioned
                else None,
            )
            if member.member is not None:
                from .data_operation_model import SubjectContext

                context = SubjectContext(
                    binding.subject_context.project_id,
                    member.subject,
                    member.original_source,
                    member.analyzed_scope,
                    subject_definition=member.subject_definition,
                )
                product = product.with_context(context, member=member)
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
                FrozenNativeSource.acquire(self.prepared, value) for value in roles["sources"]
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
                source_role = next(role for role in self.operation.roles if role.name == "sources")
                if source_role.collection == "set":
                    sources, products = ordered_composition_inputs(sources, products)
                    active = products
            else:
                products = self._retained(roles["products"], binding, "products")
                active = self._retained(roles["active"], binding, "active")
            if not sources and (products or active):
                raise PortRefusal("closed empty view cannot contain characterization members")
            profile = decode_semantic_value(json.loads(binding.parameters))["profile"]
            if profile not in self.profiles:
                raise PortRefusal("composition profile is outside its admitted contract")
            return _DocumentInputs(sources, products, active, profile)

        source = FrozenNativeSource.acquire(self.prepared, roles["source"])
        if binding is not None and binding.subject != source_subject(source.value["source"]):
            raise PortRefusal(
                "characterization subject differs from exact original source coordinate"
            )
        formal = self._formal(source, roles["formal"], binding)
        if self.family == "construction":
            from .sentence_products import acquired_source_annotations, validate_source_annotations

            selected = next(value for value in values if value.role == "sentences")
            supplied = roles["sentences"]
            if binding is not None:
                if binding.subject_context is None or selected.partitioned is None:
                    raise PortRefusal(
                        "construction requires its selected annotation row partitions"
                    )
                native = acquired_source_annotations(
                    self.prepared,
                    self.model,
                    selected.partitioned.header,
                    selected.partitioned.packets,
                    source,
                    member=self._member(binding, "sentences", 0),
                    project=binding.subject_context.project_id,
                )
            elif isinstance(supplied, SourceAnnotations):
                native = validate_source_annotations(
                    self.prepared,
                    self.model,
                    json.loads(supplied.content),
                    source,
                    subject_context=supplied.subject_context,
                    partitions=supplied.partitions,
                )
                native._publication_context()
            else:
                raise PortRefusal("construction requires its selected annotation row partitions")
            return _ConstructionInputs(source, formal, native)
        supporting = self._retained(roles["supporting"], binding, "supporting")
        constructions = []
        for index, value in enumerate(roles["constructions"]):
            context = self._context(binding, "constructions", index, value)
            if binding is None:
                if type(value) is not ConstructionProduct:
                    raise PortRefusal("contextual inputs require acquired construction products")
                value.require_readable_from(source, self.model, (*formal, *supporting))
                value._publication_context()
                product = value
            else:
                member = self._member(binding, "constructions", index)
                if context is None or member is None:
                    raise PortRefusal("selected construction needs its acquired member and context")
                product = acquired_construction_product(
                    self.prepared,
                    self.model,
                    _body(value),
                    source,
                    (*formal, *supporting),
                    subject_context=context,
                    member=member,
                )
            constructions.append(product)
        return _ContextualInputs(source, formal, tuple(constructions), supporting)

    @staticmethod
    def _observed_dependency_members(binding, inputs):
        from .established_validity import RuleObservedInput

        products = {"formal": inputs.formal}
        if isinstance(inputs, _ConstructionInputs):
            products["sentences"] = (inputs.native,)
        else:
            products.update(constructions=inputs.constructions, supporting=inputs.supporting)
        result = {}
        for name, values in products.items():
            selected = next(role for role in binding.roles if role.role == name)
            position = 0
            observed = []
            for member in selected.members:
                retained = values[position]
                if retained.semantic_id != member.product:
                    raise ValueError("dependency attestation requires its exact producing input")
                observed.append(
                    RuleObservedInput(retained.value, member.multiplicity)
                )
                position += member.multiplicity
            if position != len(values):
                raise ValueError("dependency attestation changes the selected input multiplicity")
            result[name] = tuple(observed)
        return result

    def _completion(self, product, binding=None, *, inputs=None):
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
            product = product.with_context(binding.subject_context)
        from ._data_operation_wire import WireKindContract, WireOutputMember
        from .data_operation_ports import PortCompletion
        from .established_validity import (
            RuleObservedInput,
            successful_rule_attestation,
        )

        output = next(role for role in self.operation.roles if role.direction == "output")
        kind = next(
            item.key
            for item in self.model.identities
            if item.owner == output.kind and item.domain == "kind"
        )
        publication = product.publication(output.name, kind)
        if isinstance(product, EnrichedDocumentProduct):
            return PortCompletion(
                self.operation.semantic_id,
                (publication,),
                outcome=successful_return_outcome(self.operation),
            )
        attestations = ()
        if binding is not None and isinstance(
            product, (ConstructionProduct, ContextualMeaningProduct)
        ):
            if (
                not isinstance(inputs, (_ConstructionInputs, _ContextualInputs))
                or product.subject_context is None
                or publication.meaning is None
            ):
                raise ValueError("interpreted attestation requires its selected source and subject")
            source = inputs.source
            checked = {
                "corpus_structure.semantic.characterization_evidence.verify_navigation_source_fields": None,
                "corpus_structure.semantic.characterization.verify_interpreted_attachment_witnesses": None,
                "corpus_structure.semantic.construction_products.verify_interpreted_dependency_members": self._observed_dependency_members(
                    binding, inputs
                ),
                "corpus_structure.semantic.construction_products.verify_interpreted_literal_source": {
                    "source": (RuleObservedInput(source.value),)
                },
                "corpus_structure.semantic.construction_products.verify_interpreted_body_coverage": None,
                "corpus_structure.semantic.construction_products.verify_interpreted_inventory_topology": None,
                "corpus_structure.semantic.characterization.verify_inventory_native_scores": None,
                "corpus_structure.semantic.characterization.verify_inventory_occurrence_ids": None,
                "corpus_structure.semantic.construction_products.verify_interpreted_positioned_geometry": {
                    "source": (RuleObservedInput(source.value),)
                },
                "corpus_structure.semantic.construction_products.verify_interpreted_source_coverage": {
                    "source": (RuleObservedInput(source.value),)
                },
            }
            owner_kind = next(item for item in self.model.kinds if item.semantic_id == output.kind)
            packet: WireOutputMember = {
                "role": output.name,
                "position": 0,
                "multiplicity": 1,
                "product": {
                    "kind_contract": WireKindContract(kind),
                    "body": json.loads(publication.meaning),
                    "members": [json.loads(member) for member in publication.members],
                },
            }
            attestations = tuple(
                successful_rule_attestation(
                    rule,
                    owner_kind,
                    self.operation.semantic_id,
                    packet,
                    product.subject_context,
                    selected_inputs=checked[rule.checker_callable],
                )
                for rule in self.model.rules
                if rule.checker_operation == self.operation.semantic_id
                and rule.checker_callable in checked
            )
        return PortCompletion(
            self.operation.semantic_id,
            (publication,),
            outcome=successful_return_outcome(self.operation),
            rule_attestations=attestations,
        )

    def invoke_python(self, values, *, binding=None, check_active=lambda: None):
        self._verify()
        check_active()
        inputs = self._inputs(values, binding)
        if isinstance(inputs, _DocumentInputs) and not inputs.sources:
            return self._completion(None, binding)
        if isinstance(inputs, _ConstructionInputs):
            product = PreparedConstructionProfile(self.prepared, self.model)._construct(
                inputs.source,
                inputs.formal,
                self.construction_options(),
                sentences=inputs.native,
                check_active=check_active,
            )
        elif isinstance(inputs, _ContextualInputs):
            product = PreparedContextualProfile(self.prepared, self.model)._evaluate(
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
        return self._completion(product, binding, inputs=inputs)

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from .construction_products import validate_interpreted_product
        from .data_operation_cpu import plan_cpu_call

        inputs = self._inputs(values, binding)
        if isinstance(inputs, _DocumentInputs) and not inputs.sources:
            self._verify()
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
                assets=self._asset_digest,
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
                assets=self._asset_digest,
                native=CharacterizationSnapshot(
                    inputs.native.semantic_id, inputs.native.content, inputs.native.partitions
                ),
                check_active=check_active,
            )
        elif isinstance(inputs, _ContextualInputs):
            constructions = inputs.constructions
            products = (*inputs.formal, *inputs.supporting, *constructions)
            arguments = dict(
                source=inputs.source,
                products=tuple(
                    CharacterizationSnapshot(
                        product.semantic_id, product.content, getattr(product, "partitions", None)
                    )
                    for product in products
                ),
                symbolic=tuple(product.reference for product in constructions),
                contracts=interpreted_member_contracts(self.prepared, self.model),
                assets=self._asset_digest,
                check_active=check_active,
            )
        else:
            raise TypeError("unknown prepared characterization input profile")
        reply = yield from plan_cpu_call(
            self._descriptor,
            self._signature.bind(**arguments),
            self._signature,
            verify=self._verify,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        if isinstance(inputs, _DocumentInputs):
            product = EnrichedDocumentProduct.acquire(self.prepared, self.model, reply.content)
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
        return replace(
            self._completion(product, binding, inputs=inputs),
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
        port_type.operation_sources(include_dependencies=False) if sources is None else sources,
    )
    declaration = port.endpoint.run.__module__ + "." + port.endpoint.run.__qualname__
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
    port._acquire_verification()
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
    composition = Path(__file__).with_name("enriched_document_products.py")
    own = replace(
        own,
        sources=(
            *own.sources,
            PythonSource(
                "corpus_structure.semantic.enriched_document_products",
                composition.read_bytes(),
                str(composition),
            ),
        ),
    )
    from .primary_operations import combine_primary_sources

    base = document_view_operation_sources(include_dependencies=False)
    if not include_dependencies:
        return combine_primary_sources(base, own)
    if sentence_configuration is None or hanlp_selection is None:
        raise ValueError(
            "full composition requires explicitly acquired sentence and HanLP profiles"
        )
    from .canonical_sentences import canonical_sentence_operation_sources
    from .declaration_products import declaration_operation_sources
    from .formal_products import formal_operation_sources
    from .hanlp_products import hanlp_operation_sources
    from .source_discovery import source_discovery_operation_sources

    return combine_primary_sources(
        characterization_operation_sources(include_dependencies=False),
        formal_operation_sources(),
        declaration_operation_sources(),
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


def organized_captured_document_view_operation_sources(*, include_dependencies=False):
    if include_dependencies:
        raise ValueError(
            "organized composition requires its separately captured actual PDF profile"
        )
    from .primary_operations import combine_primary_sources

    return combine_primary_sources(
        captured_document_view_operation_sources(include_dependencies=False),
        _operation_sources("captured_organized_composition", "view"),
    )


def enriched_captured_document_view_operation_sources(*, include_dependencies=False):
    if include_dependencies:
        raise ValueError("enriched composition requires its separately captured actual PDF profile")
    from .primary_operations import combine_primary_sources

    return combine_primary_sources(
        captured_document_view_operation_sources(include_dependencies=False),
        _operation_sources("captured_enriched_composition", "view"),
    )


def integrated_captured_document_view_operation_sources(*, include_dependencies=False):
    if include_dependencies:
        raise ValueError(
            "integrated composition requires its separately captured actual PDF profile"
        )
    from .primary_operations import combine_primary_sources

    return combine_primary_sources(
        captured_document_view_operation_sources(include_dependencies=False),
        _operation_sources("captured_integrated_composition", "view"),
    )


class PreparedCapturedDocumentViewPort(PreparedFullDocumentViewPort):
    operation_sources = staticmethod(captured_document_view_operation_sources)

    @property
    def endpoint(self):
        from corpus_structure.methods.captured_document_composition import (
            ComposeCapturedDocumentOperation,
        )

        return ComposeCapturedDocumentOperation


class PreparedOrganizedCapturedDocumentViewPort(PreparedFullDocumentViewPort):
    operation_sources = staticmethod(organized_captured_document_view_operation_sources)

    @property
    def endpoint(self):
        from corpus_structure.methods.captured_organized_composition import (
            ComposeOrganizedCapturedDocumentOperation,
        )

        return ComposeOrganizedCapturedDocumentOperation


class PreparedEnrichedCapturedDocumentViewPort(PreparedFullDocumentViewPort):
    operation_sources = staticmethod(enriched_captured_document_view_operation_sources)

    @property
    def endpoint(self):
        from corpus_structure.methods.captured_enriched_composition import (
            ComposeEnrichedCapturedDocumentOperation,
        )

        return ComposeEnrichedCapturedDocumentOperation


class PreparedIntegratedCapturedDocumentViewPort(PreparedFullDocumentViewPort):
    operation_sources = staticmethod(integrated_captured_document_view_operation_sources)

    @property
    def endpoint(self):
        from corpus_structure.methods.captured_integrated_composition import (
            ComposeIntegratedCapturedDocumentOperation,
        )

        return ComposeIntegratedCapturedDocumentOperation


def resolve_captured_document_view_port(prepared, model, operation, **admission):
    if operation == "text.compose_view/organized-captured-full-native":
        return _resolve(
            PreparedOrganizedCapturedDocumentViewPort, prepared, model, operation, **admission
        )
    if operation == "text.compose_view/enriched-captured-full-native":
        port = PreparedEnrichedCapturedDocumentViewPort
    elif operation == "text.compose_view/integrated-captured-full-native":
        port = PreparedIntegratedCapturedDocumentViewPort
    else:
        port = PreparedCapturedDocumentViewPort
    return _resolve(port, prepared, model, operation, **admission)
