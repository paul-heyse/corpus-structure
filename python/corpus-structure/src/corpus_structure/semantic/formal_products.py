"""Source-native positioned formal production, separate from execution custody.

The released characterization classes own constituent shapes. This profile reuses the
actual nomination/parser/reducer and graph validators, with source identity established
before extraction rather than rewriting task-keyed reports after extraction.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.core.evidence import MacroDef
from corpus_structure.methods.math import grammar as math_grammar

from .characterization import (
    occurrence_id,
    validate_inventory_graph,
)
from .characterization_evidence import validate_evidence
from .data_operation_model import EffectiveDataOperationModel, EffectiveOperation
from .formal_evidence import (
    FAMILIES,
    FormalIdentity,
    _LayerBuilder,
    extract_formal_facts,
    grammar_identity,
)
from .identity import canonical_bytes
from .source_products import (
    FrozenNativeSource as FrozenFormalSource,
)
from .source_products import (
    source_product_inputs,
    source_subject,
)
from .types import PreparedRelease, SourceArtifact, SourceBundle

if TYPE_CHECKING:
    from .data_operation_admission import PreparedCapabilityIdentity
    from .data_operation_bindings import BindingResult
    from .data_operation_ports import PortCompletion, PythonRoleValue

_MODEL = Path(__file__).resolve().parents[1] / "model/semantic/data-operation-characterization.yaml"
_INVENTORIES = (
    ("occurrences", "occurrence"),
    ("annotations", "annotation"),
    ("memberships", "membership"),
    ("terms", "term"),
    ("choices", "choice"),
)


def formal_product_inputs(
    bundle: SourceBundle, *, model_content: bytes | None = None
) -> SourceBundle:
    """Acquire the nominal profile alongside its reused released constituent types."""
    bundle = source_product_inputs(bundle)
    reserved = {"data_operation_characterization", "data_operation_characterization_root"}
    if reserved & {source.name for source in bundle.sources}:
        raise ValueError("formal profile schema uses reserved trusted names")
    content = _MODEL.read_bytes() if model_content is None else model_content
    root = "data_operation_characterization_root"
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact("data_operation_characterization", content),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    {
                        "id": "urn:corpus:data-operation-characterization-root",
                        "name": root,
                        "imports": [bundle.root, "data_operation_characterization"],
                    }
                ).encode(),
            ),
        ),
    )


def _values(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude_unset=True)


@dataclass(frozen=True)
class _RecognizerSource:
    text: str
    pieces: tuple[dict[str, Any], ...]
    items: tuple[dict[str, Any], ...]
    health: dict[str, Any]


class FormalEvidenceOptions(BaseModel):
    """Execution limits/macros are recipe custody, never product identity salt."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    math_start: math_grammar.Kind = "any_value"
    parse_seconds: float = Field(default=math_grammar.PARSE_SECONDS, gt=0)
    max_forest_nodes: int = Field(default=20000, ge=1)
    max_inline_chars: int = Field(default=2048, ge=1)
    macros: dict[str, MacroDef] = Field(default_factory=dict)


@dataclass(frozen=True)
class FormalMember:
    member_id: str
    subject_id: str
    role: str
    ordinal: int
    kind: str
    body: BaseModel


@dataclass(frozen=True)
class FormalEvidenceProduct:
    """Typed nominal product. Fresh models prevent mutable caller aliases escaping."""

    content: bytes
    prepared: PreparedRelease
    model: EffectiveDataOperationModel

    @property
    def value(self) -> BaseModel:
        return self.prepared.validate_json("DdoFormalProduct", self.content)

    @property
    def semantic_id(self) -> str:
        return "formal-product:" + sha256(self.content).hexdigest()

    @property
    def members(self) -> tuple[FormalMember, ...]:
        inventory = {kind: name for name, kind in _INVENTORIES}
        return tuple(
            FormalMember(
                row.member_id,
                row.context.subject,
                inventory[row.body.record_type],
                ordinal,
                self.prepared.index.definitions[type(row.body).__name__].iri,
                row.body,
            )
            for ordinal, row in enumerate(cast(Any, self.value).members)
        )

    def inventory(self) -> dict[str, Any]:
        """Shared read-only algorithm view; it has no legacy layer/task identity."""
        body = json.loads(self.content)
        result = {name: [] for name, _ in _INVENTORIES}
        by_kind = {kind: name for name, kind in _INVENTORIES}
        for packet in body["members"]:
            result[by_kind[packet["body"]["record_type"]]].append(packet["body"])
        return {**result, "coverage": body["coverage"]}


def validate_formal_product(
    prepared: PreparedRelease,
    value: Mapping[str, Any],
    source: FrozenFormalSource,
    *,
    model: EffectiveDataOperationModel,
) -> FormalEvidenceProduct:
    checked = _values(prepared.validate_json("DdoFormalProduct", canonical_bytes(value)))
    selected = source.value
    member_contracts = formal_member_contracts(prepared, model)
    if checked["source"] != selected["source"] or checked["selectors"] != selected["selectors"]:
        raise ValueError("formal product differs from exact selected source/scope")
    data = {name: [] for name, _ in _INVENTORIES}
    data["roles"] = []
    by_kind = {kind: name for name, kind in _INVENTORIES}
    subject = source_subject(checked["source"])
    seen = set()
    for packet in checked["members"]:
        if packet["kind_contract"] != member_contracts[packet["body"]["record_type"]]:
            raise ValueError("formal packet has another admitted nominal member contract")
        if (
            packet["context"]
            != dict(
                subject=subject,
                original_source=checked["source"]["document"],
                analyzed_scope=dict(source=checked["source"], selectors=selected["selectors"]),
            )
            or packet["member_id"] != packet["body"]["local_id"]
        ):
            raise ValueError("formal packet differs from original semantic source/member")
        if packet["member_id"] in seen:
            raise ValueError("formal packet repeats member identity")
        seen.add(packet["member_id"])
        data[by_kind[packet["body"]["record_type"]]].append(packet["body"])
    indexes = {name: {row["local_id"]: row for row in rows} for name, rows in data.items()}
    all_nodes = {key: row for index in indexes.values() for key, row in index.items()}
    choices = {}
    for group in data["choices"]:
        for member in group["members"]:
            if member["local_id"] in all_nodes:
                raise ValueError("formal choice member repeats local identity")
            all_nodes[member["local_id"]] = member
            choices[member["local_id"]] = group
    for occurrence in data["occurrences"]:
        if occurrence["local_id"] != occurrence_id(checked["source"], occurrence["extents"]):
            raise ValueError("formal occurrence differs from original semantic source address")
        for extent in occurrence["extents"]:
            pointer = extent["native_pointer"]
            original = next(
                (item for item in selected["items"] if item["self_ref"] == pointer), None
            )
            if original is None:
                raise ValueError("formal occurrence has no original native atom")
            if "page" in extent and {row["page_no"] for row in original.get("prov", ())} != {
                extent["page"]
            }:
                raise ValueError("formal occurrence has another original page")
            if extent["projection"] != checked["source"]["projection"]:
                raise ValueError("formal occurrence has another original projection")
            if "start" in extent:
                a, b = extent["start"], extent.get("end", -1)
                if (
                    not 0 <= a < b <= len(selected["text"])
                    or extent.get("text") != selected["text"][a:b]
                ):
                    raise ValueError("formal occurrence differs from original literal slice")
                if not any(
                    piece["kind"] == "native_text"
                    and piece.get("item_ref") == pointer
                    and piece["start"] <= a < b <= piece["end"]
                    for piece in selected["pieces"]
                ):
                    raise ValueError("formal occurrence escapes its original native piece")
                if not any(
                    selector.get("native_pointer", pointer) == pointer
                    and selector.get("start", 0)
                    <= a
                    < b
                    <= selector.get("end", len(selected["text"]))
                    for selector in selected["selectors"]
                ):
                    raise ValueError("formal occurrence escapes the selected examined scope")
    validate_evidence(data, indexes)
    validate_inventory_graph(data, indexes, all_nodes, choices, lambda _: None)
    if [row["family"] for row in checked["coverage"]] != list(FAMILIES):
        raise ValueError("formal product must retain every examined family outcome")
    if any(
        row["eligible"] != selected["selectors"] or row["examined"] != selected["selectors"]
        for row in checked["coverage"]
    ):
        raise ValueError("formal coverage differs from original examined scope")
    if checked["outcome"] == "complete" and any(
        row["outcome"] not in {"complete", "empty"} for row in checked["coverage"]
    ):
        raise ValueError("complete formal product contains incomplete family coverage")
    return FormalEvidenceProduct(canonical_bytes(checked), prepared, model)


@dataclass(frozen=True)
class PreparedFormalEvidence:
    """Explicit acquired grammar/schema capability; no Reader, selection or GPU access."""

    prepared: PreparedRelease
    grammar: str
    model: EffectiveDataOperationModel

    def run(
        self,
        source: FrozenFormalSource,
        options: FormalEvidenceOptions,
        *,
        check_active: Callable[[], None] = lambda: None,
    ) -> FormalEvidenceProduct:
        # Revalidate owned boundary bytes; model_construct/hand-created wrappers are not authority.
        source = FrozenFormalSource.acquire(self.prepared, source.value)
        options = FormalEvidenceOptions.model_validate(options.model_dump(mode="python"))
        if self.grammar != grammar_identity():
            raise ValueError("formal capability differs from acquired effective grammar assets")
        value = formal_product_values(
            source,
            options,
            formal_member_contracts(self.prepared, self.model),
            check_active=check_active,
        )
        return validate_formal_product(self.prepared, value, source, model=self.model)


def formal_member_contracts(
    prepared: PreparedRelease, model: EffectiveDataOperationModel
) -> dict[str, str]:
    """Use the admitted packet variants' nominal body graph, never guessed kind names."""
    identities = {(item.owner, item.domain): item.key for item in model.identities}
    result = {}
    for definition in prepared.definitions:
        if "DdoFormalMember" not in definition.ancestors or definition.abstract:
            continue
        discriminator = next(
            prop.equals_string for prop in definition.properties if prop.name == "record_type"
        )
        if discriminator is None or discriminator in result:
            raise ValueError("formal packet variants require unique declared kind correspondence")
        result[discriminator] = identities[definition.iri, "kind"]
    if set(result) != {kind for _, kind in _INVENTORIES}:
        raise ValueError("formal member contracts differ from the actual produced inventories")
    return result


def formal_product_values(
    source: FrozenFormalSource,
    options: FormalEvidenceOptions,
    member_contracts: Mapping[str, str],
    *,
    check_active: Callable[[], None] = lambda: None,
) -> dict[str, Any]:
    """The one pure extraction/packet construction kernel over owned typed ingress.

    Private child transport is admitted by its parent; the parent validates the full
    nominal product before anything can become a PortCompletion/native intent.
    """
    selected = source.value
    coordinate = selected["source"]
    check_active()
    view = _RecognizerSource(
        selected["text"],
        tuple(selected["pieces"]),
        tuple(selected["items"]),
        {"formula_outcomes": selected.get("recognition", [])},
    )
    builder = _LayerBuilder(
        view,
        {},
        FormalIdentity(
            canonical_bytes(coordinate), coordinate["projection"], source_subject(coordinate), True
        ),
    )
    builder.macros = dict(options.macros)
    extract_formal_facts(
        builder,
        selected["selectors"],
        math_start=options.math_start,
        parse_seconds=options.parse_seconds,
        max_forest_nodes=options.max_forest_nodes,
        max_inline_chars=options.max_inline_chars,
        check_active=check_active,
    )
    coverage = [
        dict(
            family=family,
            eligible=selected["selectors"],
            examined=selected["selectors"],
            availability="available",
            outcome="partial"
            if builder.problems[family]
            else "complete"
            if builder.counts[family]
            else "empty",
            **(
                {"reason": "; ".join(dict.fromkeys(builder.problems[family]))}
                if builder.problems[family]
                else {}
            ),
        )
        for family in FAMILIES
    ]
    members = []
    for inventory, kind in _INVENTORIES:
        values = getattr(builder, inventory)
        rows = values.values() if isinstance(values, dict) else values
        for row in rows:
            members.append(
                dict(
                    member_id=row["local_id"],
                    kind_contract=member_contracts[kind],
                    context=dict(
                        subject=source_subject(coordinate),
                        original_source=coordinate["document"],
                        analyzed_scope=dict(source=coordinate, selectors=selected["selectors"]),
                    ),
                    body={"record_type": kind, **row},
                )
            )
    check_active()
    return dict(
        source=coordinate,
        selectors=selected["selectors"],
        outcome="partial" if any(builder.problems.values()) else "complete",
        coverage=coverage,
        members=members,
    )


def prepare_formal_evidence(
    prepared: PreparedRelease, model: EffectiveDataOperationModel, *, grammar: str
) -> PreparedFormalEvidence:
    if grammar != grammar_identity():
        raise ValueError("formal profile requires explicitly acquired effective grammar assets")
    for name in ("DdoSelectedNativeSource", "DdoFormalProduct"):
        prepared.adapter(name)
    return PreparedFormalEvidence(prepared, grammar, model)


def execute_formal_profile(receiver, source: FrozenFormalSource) -> FormalEvidenceProduct:
    """The original endpoint's explicitly captured prepared-resource boundary."""
    from corpus_structure.methods.formal_evidence import FormalEvidenceOperation

    if type(receiver) is not FormalEvidenceOperation:
        raise ValueError("formal execution requires its exact prepared receiver")
    return receiver.profile.run(source, receiver.options, check_active=receiver.check_active)


def _semantic_nodes(content: bytes, names: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    """Normalize the selected actual definitions, excluding transport-only siblings."""
    import ast

    module = ast.parse(content)
    result = []
    for path in names:
        owner = module
        for name in path.split("."):
            if not isinstance(owner, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                raise ValueError("semantic asset slice does not name an owning definition: " + path)
            matches = [
                node
                for node in owner.body
                if (isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == name)
                or (
                    isinstance(node, ast.Assign)
                    and any(
                        isinstance(target, ast.Name) and target.id == name
                        for target in node.targets
                    )
                )
            ]
            if len(matches) != 1:
                raise ValueError("semantic asset slice has no unique actual definition: " + path)
            owner = matches[0]
        result.append((path, ast.dump(owner, include_attributes=False)))
    return tuple(result)


def formal_execution_custody() -> SourceArtifact:
    """Physical adapter/CPU/receipt code belongs to runtime custody, not recipe meaning."""
    root = Path(__file__).parent
    names = ("formal_products.py", "cpu_execution.py", "cpu_receipts.py")
    return SourceArtifact(
        "formal/execution-custody",
        canonical_bytes(
            {
                "version": "formal-execution-custody-v1",
                "files": [(name, (root / name).read_bytes().hex()) for name in names],
            }
        ),
    )


def formal_profile_assets() -> SourceArtifact:
    """Exact implementation/language bytes, separate from the resulting semantic facts."""
    from importlib.metadata import version

    from corpus_structure.core import tex
    from corpus_structure.methods.math import transform

    root = Path(__file__).parent
    paths = (
        root / "formal_evidence.py",
        root / "formal_forest.py",
        root / "formal_sources.py",
        root / "structural_parsing.py",
        root / "characterization.py",
        root / "characterization_evidence.py",
        root / "source_products.py",
        root / "constructions/reuse.py",
        root / "constructions/nodes.py",
        Path(math_grammar.__file__),
        Path(transform.__file__),
        Path(tex.__file__),
        math_grammar.SHIPPED,
        math_grammar.EXTENSION,
        _MODEL,
        root.parent / "model/semantic/characterization.yaml",
        root.parent / "model/semantic/data-operation-source.yaml",
    )
    # Labels are descriptive relative package addresses, never machine placement.
    payload = {
        "interpretation": "formal-semantic-assets-ast-v1",
        "target": _semantic_nodes(
            Path(__file__).read_bytes(),
            (
                "_INVENTORIES",
                "_RecognizerSource",
                "FormalEvidenceOptions",
                "FormalEvidenceProduct",
                "_values",
                "formal_product_values",
                "formal_member_contracts",
                "validate_formal_product",
                "PreparedFormalEvidence",
                "PreparedFormalEvidencePort._completion",
                "execute_formal_profile",
                "_semantic_nodes",
                "formal_profile_assets",
            ),
        ),
        "sources": [
            (
                str(path.relative_to(root.parent))
                if path.is_relative_to(root.parent)
                else "sympy/grammar/latex.lark",
                path.read_bytes().hex(),
            )
            for path in paths
        ],
        "libraries": {name: version(name) for name in ("lark", "sympy", "pydantic")},
    }
    return SourceArtifact("formal/profile-assets", canonical_bytes(payload))


def formal_operation_sources():
    """Capture the original endpoint plus its explicit immutable parser boundary."""
    from .python_operation_sources import PythonSource, PythonSourceCollection

    path = Path(__file__).parents[1] / "methods/formal_evidence.py"
    return PythonSourceCollection(
        (
            PythonSource(
                "corpus_structure.methods.formal_evidence",
                path.read_bytes(),
                str(path),
            ),
        ),
        boundary_contracts=(formal_profile_assets(), formal_execution_custody()),
    )


@dataclass(frozen=True)
class PreparedFormalEvidencePort:
    native_selections = ()

    """Admitted prepared implementation of the original source-native entrypoint."""

    identity: PreparedCapabilityIdentity
    operation: EffectiveOperation
    profile: PreparedFormalEvidence
    authorize: Callable[[PreparedCapabilityIdentity], None]
    custody: tuple[SourceArtifact, ...]

    @property
    def logical_signature(self):
        import inspect

        return inspect.Signature(
            (
                inspect.Parameter(
                    "source", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=FrozenFormalSource
                ),
            ),
            return_annotation=FormalEvidenceProduct,
        )

    def _verify(self) -> None:
        from dataclasses import asdict

        from .data_operation_ports import PortRefusal

        model = self.profile.model
        ids = {(item.owner, item.domain): item.key for item in model.identities}
        operation = self.operation
        if operation.implementation_root is None:
            raise PortRefusal("formal capability lacks an implementation root")
        expected = dict(
            model_digest=sha256(model.content).hexdigest(),
            operation=operation.semantic_id,
            definition=ids[operation.semantic_id, "definition"],
            recipe=ids[operation.semantic_id, "recipe"],
            implementation=ids[operation.implementation_root, "implementation-slice"],
            declaration="corpus_structure.methods.formal_evidence.FormalEvidenceOperation.run",
            capabilities=canonical_bytes(asdict(operation.capabilities)),
            eligibility=ids[operation.semantic_id, "eligibility"],
        )
        sources = formal_operation_sources()
        retained = {artifact.name: artifact for artifact in self.custody}
        if len(retained) != len(self.custody):
            raise PortRefusal("formal runtime custody repeats an acquired artifact name")
        for actual in (formal_profile_assets(), formal_execution_custody()):
            if retained.get(actual.name) != actual:
                raise PortRefusal("formal runtime/parser assets differ from acquired custody")
        expected["source_digest"] = sha256(
            canonical_bytes(
                tuple(
                    (source.module, sha256(source.content).hexdigest())
                    for source in sources.sources
                )
            )
        ).hexdigest()
        if any(getattr(self.identity, name) != value for name, value in expected.items()):
            raise PortRefusal(
                "formal capability differs from admitted source/operation correspondence"
            )
        # Prepared opaque resources are not closed Python functions, but their
        # original endpoint and resource bridge still require actual loaded-code
        # correspondence, not only a matching on-disk file.
        import inspect
        from types import CodeType

        from corpus_structure.methods import formal_evidence as endpoint

        def declared(content, filename, *path):
            code = compile(content, filename, "exec", dont_inherit=True)
            for name in path:
                code = next(
                    item
                    for item in code.co_consts
                    if isinstance(item, CodeType) and item.co_name == name
                )
            return code

        source = sources.sources[0]
        runtime = inspect.getattr_static(endpoint.FormalEvidenceOperation, "run")
        if (
            not inspect.isfunction(runtime)
            or runtime.__code__
            != declared(source.content, source.filename, "FormalEvidenceOperation", "run")
            or runtime.__globals__ is not endpoint.__dict__
        ):
            raise PortRefusal("loaded formal endpoint differs from acquired implementation")
        if (
            endpoint.execute_formal_profile is not execute_formal_profile
            or execute_formal_profile.__code__
            != declared(Path(__file__).read_bytes(), __file__, "execute_formal_profile")
        ):
            raise PortRefusal("loaded formal resource bridge differs from acquired implementation")
        if self.profile.run.__func__.__code__ != declared(
            Path(__file__).read_bytes(), __file__, "PreparedFormalEvidence", "run"
        ):
            raise PortRefusal(
                "loaded formal resource algorithm differs from acquired implementation"
            )
        contracts = {item.name: item.digest for item in self.custody}
        boundaries = (
            *operation.assets,
            *(
                boundary
                for implementation in model.implementation_slices
                if implementation.root == operation.implementation_root
                for boundary in implementation.boundaries
            ),
        )
        if not operation.assets or any(
            contracts.get(boundary.contract) != boundary.content_digest for boundary in boundaries
        ):
            raise PortRefusal(
                "formal parser assets differ from explicitly acquired boundary custody"
            )
        if self.identity.assets != canonical_bytes(
            tuple(asdict(boundary) for boundary in boundaries)
        ):
            raise PortRefusal("formal capability has another acquired resource boundary")
        self.authorize(self.identity)

    def _source(self, values, binding):
        from .data_operation_identity import decode_semantic_value
        from .data_operation_ports import PortRefusal, PythonRoleValue

        inputs = tuple(role for role in self.operation.roles if role.direction == "input")
        contracts = {(item.owner, item.domain): item.key for item in self.profile.model.identities}
        if len(values) != 1 or not isinstance(values[0], PythonRoleValue):
            raise PortRefusal("formal capability requires one typed selected-source role")
        value = values[0]
        if value.role != inputs[0].name or value.kind_contract != contracts[inputs[0].kind, "kind"]:
            raise PortRefusal("formal source role has another nominal contract")
        actual = value.value
        if isinstance(actual, FrozenFormalSource):
            source = FrozenFormalSource.acquire(self.profile.prepared, actual.value)
        elif isinstance(actual, BaseModel):
            source = FrozenFormalSource.acquire(self.profile.prepared, _values(actual))
        elif isinstance(actual, Mapping):
            source = FrozenFormalSource.acquire(self.profile.prepared, actual)
        else:
            raise PortRefusal("formal source ingress requires its explicit selected-source value")
        if binding is not None and (
            not binding.sufficient
            or binding.operation != self.operation.semantic_id
            or binding.subject != source_subject(source.value["source"])
            or decode_semantic_value(json.loads(binding.parameters)) != {}
        ):
            raise PortRefusal("formal input differs from the frozen source binding")
        return source

    def _completion(self, product):
        from .data_operation_identity import semantic_value
        from .data_operation_ports import PortCompletion, RoleValue

        # Product meaning uses the exact typed record's fields; display JSON and native
        # member packets are deliberate projections of that same validated product.
        model_value = product.value.model_dump(mode="python", exclude_unset=True)
        packets = json.loads(product.content)["members"]
        native_members = tuple(
            canonical_bytes(
                {
                    "member_id": packet["member_id"],
                    "kind_contract": packet["kind_contract"],
                    "context": packet["context"],
                    "body": semantic_value(packet["body"]),
                }
            )
            for packet in packets
        )
        output = next(role for role in self.operation.roles if role.direction == "output")
        contracts = {(item.owner, item.domain): item.key for item in self.profile.model.identities}
        return PortCompletion(
            self.operation.semantic_id,
            (
                RoleValue(
                    output.name,
                    contracts[output.kind, "kind"],
                    product.content,
                    canonical_bytes(semantic_value(model_value)),
                    native_members,
                ),
            ),
        )

    def invoke_python(
        self,
        values: tuple[PythonRoleValue, ...],
        *,
        binding: BindingResult | None = None,
        check_active: Callable[[], None] = lambda: None,
    ) -> PortCompletion:
        from corpus_structure.methods.formal_evidence import FormalEvidenceOperation

        # The actual math frontend owns process-main-thread SIGALRM deadlines.
        # Scheduler callers use plan_python to execute in the existing CPU owner.
        math_grammar.require_main_thread()
        self._verify()
        source = self._source(values, binding)
        product = FormalEvidenceOperation(self.profile, FormalEvidenceOptions(), check_active).run(
            source
        )
        self._verify()
        return self._completion(product)

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        """Yield admitted source-native CPU work under the invocation's one pool/credit."""
        from corpus_structure.core.method import PreparedWork

        self._verify()
        source = self._source(values, binding)
        cpu = execution_owner.cpu
        if cpu.prepared.release_id != self.profile.prepared.release_id:
            raise ValueError("formal CPU owner has another acquired schema")
        check_active()

        def submit():
            self._verify()
            admission = cpu.try_admit(check_active, reservation=execution_owner.reservation)
            if admission is None:
                return None
            try:
                packet = canonical_bytes(
                    dict(
                        profile="formal-source-native",
                        release_id=self.profile.prepared.release_id,
                        member_contracts=formal_member_contracts(
                            self.profile.prepared, self.profile.model
                        ),
                        source=source.content.decode(),
                        options=FormalEvidenceOptions().model_dump_json(),
                        grammar=self.profile.grammar,
                        assets=formal_profile_assets().digest,
                    )
                )
                return cpu.submit_formal(admission, packet, check_active)
            except BaseException:
                if not admission.submitted:
                    cpu.release_admission(admission)
                raise

        (reply,) = yield (PreparedWork(submit),)
        check_active()
        product = validate_formal_product(
            self.profile.prepared, json.loads(reply.content), source, model=self.profile.model
        )
        self._verify()
        return replace(
            self._completion(product),
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
        )


def resolve_formal_evidence_port(
    prepared: PreparedRelease,
    model: EffectiveDataOperationModel,
    operation: str,
    *,
    identity: PreparedCapabilityIdentity,
    authorize: Callable[[PreparedCapabilityIdentity], None],
    custody: tuple[SourceArtifact, ...],
) -> PreparedFormalEvidencePort:
    from .data_operation_ports import PortRefusal

    selected = model.operation(operation)
    inputs = tuple(role for role in selected.roles if role.direction == "input")
    outputs = tuple(role for role in selected.roles if role.direction == "output")
    expected = prepared.index.definitions
    if (
        selected.capabilities.forms != ("scalar",)
        or selected.capabilities.preparation != "resource"
        or selected.capabilities.cancellation != "cooperative"
        or selected.capabilities.ownership != "immutable"
        or selected.effects
        or len(inputs) != 1
        or len(outputs) != 1
        or inputs[0].kind != expected["DdoSelectedNativeSource"].iri
        or outputs[0].kind != expected["DdoFormalProduct"].iri
        or inputs[0].parameter != "source"
    ):
        raise PortRefusal("operation does not establish the prepared formal profile")
    port = PreparedFormalEvidencePort(
        identity,
        selected,
        prepare_formal_evidence(prepared, model, grammar=grammar_identity()),
        authorize,
        custody,
    )
    port._verify()
    return port
