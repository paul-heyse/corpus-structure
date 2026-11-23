"""Immutable handoff from admitted relational binding to target consumer selection.

Selection has already happened in the binding owner. This representation exposes its
exact role pins to an admitted consumer without opening a reader or selecting again.
It grants no native publication, hydration or effect permission.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Any, ClassVar

from corpus_structure.caches import declare

from .data_operation_bindings import BindingResult
from .data_operation_model import BoundRoleMember, ResolvedRoleBinding
from .data_operation_partitions import PartitionedInput
from .data_operation_version import MODEL_VERSION
from .python_module_projection import admitted_operation_module_digest


@dataclass(frozen=True)
class BoundConsumerSelection:
    binding: BindingResult

    def __post_init__(self) -> None:
        if not self.binding.sufficient:
            raise ValueError("consumer selection requires a sufficient retained binding")
        names = tuple(role.role for role in self.binding.roles)
        if len(names) != len(set(names)):
            raise ValueError("consumer selection has ambiguous role names")

    @classmethod
    def from_binding(cls, binding: BindingResult, *, operation: str) -> BoundConsumerSelection:
        if binding.operation != operation:
            raise ValueError("consumer selection belongs to another operation")
        return cls(binding)

    @property
    def operation(self) -> str:
        return self.binding.operation

    @property
    def subject(self) -> str:
        return self.binding.subject

    @property
    def roles(self) -> tuple[ResolvedRoleBinding, ...]:
        return self.binding.roles

    def role(self, name: str) -> ResolvedRoleBinding:
        matches = tuple(role for role in self.roles if role.role == name)
        if len(matches) != 1:
            raise ValueError("consumer selection does not declare role: " + name)
        return matches[0]


@dataclass(frozen=True)
class _ConsumerPayload:
    content: bytes
    meaning: bytes
    value: Any
    decoder: tuple[str, str, int]


def _freeze_consumer(value):
    from .data_operation_values import CollectionValue, OptionalValue
    from .native_source_view import FrozenJsonArray

    if isinstance(value, CollectionValue):
        return CollectionValue(value.kind, tuple(_freeze_consumer(item) for item in value.members))
    if isinstance(value, OptionalValue):
        return OptionalValue(value.state, _freeze_consumer(value.value))
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_consumer(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return FrozenJsonArray(_freeze_consumer(item) for item in value)
    return value


@declare(
    "selected-consumer-payloads",
    "runtime_bytes",
    key=lambda content, meaning, decoder: (
        sha256(content).digest(),
        sha256(meaning).digest(),
        decoder,
    ),
    weight=lambda payload: len(payload.content) + len(payload.meaning),
)
def _consumer_payload(content, meaning, decoder):
    import json

    from .data_operation_values import decode_semantic_value

    value = decode_semantic_value(json.loads(meaning))
    return _ConsumerPayload(content, meaning, _freeze_consumer(value), decoder)


@dataclass(frozen=True, init=False)
class SelectedConsumerValue:
    """Exact selected occurrence over one validated immutable tagged body."""

    member: BoundRoleMember
    content: bytes
    meaning: bytes
    partitioned: PartitionedInput | None = None
    _payload: ClassVar[_ConsumerPayload]

    def __init__(self, *args, **kwargs):
        raise TypeError("selected native values require validating acquisition")

    @classmethod
    def _from_payload(cls, member, payload, partitioned=None):
        value = object.__new__(cls)
        object.__setattr__(value, "member", member)
        object.__setattr__(value, "content", payload.content)
        object.__setattr__(value, "meaning", payload.meaning)
        object.__setattr__(value, "partitioned", partitioned)
        object.__setattr__(value, "_payload", payload)
        return value

    @classmethod
    def acquire(cls, member: BoundRoleMember, content: bytes, meaning: bytes):
        """Decode tagged meaning, retaining its native owner's presentation bytes."""
        from .value_codec import decimal_digit_limit

        if type(content) is not bytes or type(meaning) is not bytes:
            raise TypeError("selected native values require exact body and tagged-meaning bytes")
        payload = _consumer_payload(
            content, meaning, (MODEL_VERSION, member.kind_contract, decimal_digit_limit())
        )
        return cls._from_payload(member, payload)

    def _require_acquired(self):
        if (
            type(self) is not SelectedConsumerValue
            or "_payload" not in vars(self)
            or self.content is not self._payload.content
            or self.meaning is not self._payload.meaning
            or self.member.kind_contract != self._payload.decoder[1]
        ):
            raise TypeError("selected native value lacks its validating acquisition")

    def with_partition(self, partitioned: PartitionedInput):
        """Retain the same validated payload with its admitted partition placement."""
        self._require_acquired()
        if partitioned.header != self.content:
            raise ValueError("selected partition placement has another native header")
        return type(self)._from_payload(self.member, self._payload, partitioned)

    def value(self):
        self._require_acquired()
        return self._payload.value


@dataclass(frozen=True)
class HydratedConsumerSelection:
    selection: BoundConsumerSelection
    values: tuple[tuple[str, tuple[SelectedConsumerValue, ...]], ...]
    measured_bytes: int = 0

    def __post_init__(self):
        if tuple(name for name, _ in self.values) != tuple(
            role.role for role in self.selection.roles
        ):
            raise ValueError("hydration must retain exactly the selected roles")
        for role, (_, values) in zip(self.selection.roles, self.values, strict=True):
            expected = tuple(member for member in role.members for _ in range(member.multiplicity))
            if tuple(value.member for value in values) != expected or any(
                type(value.content) is not bytes for value in values
            ):
                raise ValueError("hydration must retain exact ordered selected member pins")

    def role(self, name: str) -> tuple[SelectedConsumerValue, ...]:
        matches = tuple(values for role, values in self.values if role == name)
        if len(matches) != 1:
            raise ValueError("hydrated selection lacks its exact role: " + name)
        return matches[0]

    def one(self, name: str) -> SelectedConsumerValue:
        values = self.role(name)
        if len(values) != 1:
            raise ValueError("consumer requires one bound member: " + name)
        return values[0]


def hydrate_consumer_selection(
    connection, model, selection, *, demand_id, read_id, trust_snapshot, max_bytes, prepared=None
):
    """Hydrate only retained role pins under the same authenticated native read.

    This is not a new selector. No unselected body or mutable latest/default query
    can supply an input. Native custody and purpose remain enforced by its owner.
    """
    from itertools import batched

    from sqlalchemy import BigInteger, and_, cast, column, select, values

    from .data_operation_json import json_loads
    from .data_operation_jsonb import json_context_equal, json_context_value
    from .data_operation_projections import binding_columns
    from .data_operation_storage import admitted_data_read
    from .data_operation_support import support_reference_records
    from .identity import canonical_bytes

    binding = selection.binding
    identities = {(value.owner, value.domain): value.key for value in model.identities}
    if (
        binding.definition != identities[binding.operation, "definition"]
        or binding.eligibility != identities[binding.operation, "eligibility"]
        or binding.model_version != model.version
    ):
        raise ValueError("consumer binding differs from its admitted model interpretation")
    context = binding.subject_context
    if (
        context is None
        or context.subject != binding.subject
        or context.subject_definition != model.operation(binding.operation).subject
    ):
        raise ValueError("native consumer hydration requires its acquired subject context")
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("native hydration requires explicit positive packet capacity")
    declarations = {role.name: role for role in model.operation(binding.operation).roles}
    read = admitted_data_read(
        connection,
        demand_id,
        binding.operation,
        trust_snapshot,
        model,
        read_id=read_id,
        subject=context.subject,
        original_source=context.original_source,
        analyzed_scope=json_loads(context.analyzed_scope),
        selected_pins=[
            {"product_id": product, "member_id": member}
            for product, member in dict.fromkeys(
                (member.product, member.member) for role in binding.roles for member in role.members
            )
        ],
    )
    expected_evidence = {read.admission_evidence} if read.accepted_kind_contracts else set()
    if set(binding.admission_evidence) != expected_evidence:
        raise ValueError("retained consumer binding belongs to a different native read boundary")
    relation = read.relation
    pin_names = (
        "product",
        "member",
        "kind_contract",
        "subject",
        "subject_definition",
        "original_source",
        "analyzed_scope",
        "support_evidence",
        "support_episodes",
        "support_references",
        "position",
        "multiplicity",
    )
    columns = {item.name: item for item in binding_columns(decoder=True)}
    selected_members = (
        (role_ordinal, member_ordinal, role, member)
        for role_ordinal, role in enumerate(binding.roles)
        for member_ordinal, member in enumerate(role.members)
    )
    hydrated, used = {}, 0
    # Fourteen binds per VALUES row stay well below the extended-query parameter
    # ceiling. Pages bound SQL/driver state; the owned packet bound spans all pages.
    for page in batched(selected_members, 1024, strict=False):
        members, records = {}, []
        for role_ordinal, member_ordinal, role, member in page:
            if (
                member.kind_contract
                not in read.accepted_kind_contracts[declarations[role.role].kind]
            ):
                raise ValueError("retained consumer member no longer has one admitted body")
            members[role_ordinal, member_ordinal] = member
            records.append(
                (
                    role_ordinal,
                    member_ordinal,
                    member.product,
                    member.member,
                    member.kind_contract,
                    member.subject,
                    member.subject_definition,
                    member.original_source,
                    json_context_value(json_loads(member.analyzed_scope)),
                    json_context_value(json_loads(member.support_evidence)),
                    list(member.support_episodes),
                    support_reference_records(member.support_references),
                    cast(member.position, columns["position"].type),
                    member.multiplicity,
                )
            )
        pins = values(
            column("role_ordinal", BigInteger()),
            column("member_ordinal", BigInteger()),
            *(column(name, columns[name].type) for name in pin_names),
            name="consumer_pins",
        ).data(records)
        predicates = [
            relation.c[name].is_not_distinct_from(pins.c[name])
            if name in {"member", "position", "original_source"}
            else json_context_equal(relation.c[name], pins.c[name])
            if name == "analyzed_scope"
            else relation.c[name] == pins.c[name]
            for name in pin_names
        ]
        query = (
            select(
                pins.c.role_ordinal,
                pins.c.member_ordinal,
                relation.c.meaning_body,
                relation.c.body.label("json_body"),
            )
            .select_from(pins.join(relation, and_(*predicates)))
            .limit(len(page) + 1)
        )
        found = set()
        # Fetch one body at a time: a driver batch of large bodies must not exceed
        # the caller's owned packet before its capacity check can run.
        with connection.execute(query.execution_options(yield_per=1)) as rows:
            for row in rows:
                key = row.role_ordinal, row.member_ordinal
                if key in found:
                    raise ValueError("retained consumer member no longer has one admitted body")
                found.add(key)
                member = members[key]
                content = canonical_bytes(row.json_body)
                meaning = canonical_bytes(row.meaning_body)
                used += (len(content) + len(meaning)) * member.multiplicity
                if used > max_bytes:
                    raise ValueError("complete consumer inputs exceed owned packet capacity")
                hydrated[key] = SelectedConsumerValue.acquire(member, content, meaning)
        if found != members.keys():
            raise ValueError("retained consumer member no longer has one admitted body")
    hydrated, used = _hydrate_partitions(
        connection, prepared, model, read, hydrated, used, max_bytes
    )
    return HydratedConsumerSelection(
        selection,
        tuple(
            (
                role.role,
                tuple(
                    hydrated[role_ordinal, member_ordinal]
                    for member_ordinal, member in enumerate(role.members)
                    for _ in range(member.multiplicity)
                ),
            )
            for role_ordinal, role in enumerate(binding.roles)
        ),
        measured_bytes=used,
    )


def _hydrate_partitions(connection, prepared, model, read, hydrated, used, max_bytes):
    from itertools import chain, groupby

    from sqlalchemy import BigInteger, Text, column, func, select
    from sqlalchemy.dialects.postgresql import JSONB

    from .data_operation_json import json_loads, native_json_loads
    from .data_operation_partitions import (
        AcquiredPopulationPartition,
        PartitionCommitment,
        partition_commitment_header,
    )
    from .data_operation_population import population_layout
    from .data_operation_values import decode_semantic_value

    selected_contracts = {
        value.member.kind_contract for value in hydrated.values() if value.member.member is None
    }
    if not selected_contracts:
        return hydrated, used
    contracts = {
        identity.key: identity.owner
        for identity in model.identities
        if identity.domain == "kind" and identity.key in selected_contracts
    }
    if not contracts:
        return hydrated, used
    selected_kinds = set(contracts.values())
    collections = {
        kind.semantic_id: tuple(
            name
            for name, spec in json_loads(kind.facts).get("collections", {}).items()
            if spec["unit"] == "partitioned"
        )
        for kind in model.kinds
        if kind.semantic_id in selected_kinds and kind.category == "class"
    }
    selected = {
        key: names
        for key, value in hydrated.items()
        if value.member.member is None
        and (names := collections.get(contracts.get(value.member.kind_contract, "")))
    }
    if not selected:
        return hydrated, used
    if prepared is None:
        raise ValueError("population hydration requires the acquired release layout")

    kinds = {kind.semantic_id: kind for kind in model.kinds if kind.semantic_id in selected_kinds}
    products = {
        hydrated[key].member.product: kinds[contracts[hydrated[key].member.kind_contract]]
        for key in selected
    }
    acquired: dict[str, dict[str, list[AcquiredPopulationPartition]]] = {
        product: {} for product in products
    }
    rows = func.ops.data_binding_population_items(
        *read.binding_arguments, max(1, max_bytes - used)
    ).table_valued(
        column("product_id", Text()),
        column("collection", Text()),
        column("partition_key", Text()),
        column("ordinal", BigInteger()),
        column("partition_digest", Text()),
        column("item_count", BigInteger()),
        column("group_digests", JSONB()),
        column("placement", JSONB()),
        column("item_ordinal", BigInteger()),
        column("canonical_text", Text()),
    )
    layouts = {}
    owned_bytes = 0
    with connection.execute(select(*rows.c).execution_options(yield_per=256)) as returned:
        grouped_rows = groupby(
            returned, key=lambda row: (row.product_id, row.collection, row.partition_key)
        )
        for (product, collection, partition_key), items in grouped_rows:
            if product is None:
                raise ValueError("complete consumer inputs exceed owned population capacity")
            if (
                product not in products
                or collection not in collections[products[product].semantic_id]
            ):
                raise ValueError("population hydration returned an unselected collection")
            kind = products[product]
            layout_key = kind.semantic_id, collection
            if layout_key not in layouts:
                layouts[layout_key] = population_layout(prepared, kind, collection)
            head = next(items)
            commitment = PartitionCommitment(
                collection,
                partition_key,
                head.ordinal,
                head.placement["start"],
                head.placement["end"],
                head.partition_digest,
                head.item_count,
            )
            if head.item_ordinal is None:
                if head.item_count != 0 or next(items, None) is not None:
                    raise ValueError("population hydration returned invalid empty placement")
                values = ()
            else:

                def item_values(source):
                    for ordinal, row in enumerate(source):
                        if row.item_ordinal != ordinal or row.canonical_text is None:
                            raise ValueError("population hydration returned non-dense items")
                        yield decode_semantic_value(native_json_loads(row.canonical_text))

                values = item_values(chain((head,), items))
            typed = layouts[layout_key].from_rows(values)
            if typed.table.num_rows != commitment.item_count:
                raise ValueError("population hydration returned incomplete items")
            owned_bytes += typed.table.get_total_buffer_size()
            if used + owned_bytes > max_bytes:
                raise ValueError("complete consumer inputs exceed owned population capacity")
            acquired[product].setdefault(collection, []).append(
                AcquiredPopulationPartition(commitment, head.group_digests, typed)
            )

    detached = {}
    for key, names in selected.items():
        value = hydrated[key]
        product = value.member.product
        if product not in detached:
            grouped = acquired[product]
            header = value.value()
            if grouped.keys() - set(names) or any(
                partition_commitment_header(part.commitment for part in grouped.get(name, ()))
                != header.get(name)
                for name in names
            ):
                raise ValueError("partition hydration differs from the admitted collection header")
            detached[product] = PartitionedInput(
                value.content,
                (),
                tuple(part for name in sorted(names) for part in grouped.get(name, ())),
            )
        partitioned = detached[product]
        used += (
            sum(part.population.table.get_total_buffer_size() for part in partitioned.populations)
            * value.member.multiplicity
        )
        if used > max_bytes:
            raise ValueError("complete consumer inputs exceed owned packet capacity")
        hydrated[key] = value.with_partition(partitioned)
    return hydrated, used


@dataclass(frozen=True)
class ResolvedConsumerSelection:
    """Captured consumer method over admitted members; no ambient selection authority."""

    operation: str
    function: Callable[[HydratedConsumerSelection], Any]
    verify: Callable[[], None]
    authorize: Callable[[], None]

    def select_hydrated(self, inputs: HydratedConsumerSelection):
        if inputs.selection.operation != self.operation:
            raise ValueError("consumer capability belongs to another admitted selection")
        self.verify()
        self.authorize()
        result = self.function(inputs)
        self.verify()
        self.authorize()
        return result


def resolve_consumer_selection(model, sources, operation, receiver, *, authorize):
    """Acquire only the compiled class method, after native execution authorization.

    The caller owns the admitted receiver/prepared resources. This boundary captures
    no registry and offers no method-name fallback or unbound context defaults.
    """
    import ast
    import importlib
    import inspect
    from pathlib import Path

    from .data_operation_ports import PortRefusal, _runtime_members

    if model.version != MODEL_VERSION:
        raise PortRefusal("historical model cannot acquire current consumer capabilities")
    capability = model.operation(operation).consumer_selection
    if capability is None:
        raise PortRefusal("operation has no captured consumer-selection capability")
    candidates = [
        source
        for source in sources.sources
        if capability.entrypoint.startswith(source.module + ".")
    ]
    if not candidates:
        raise PortRefusal("consumer implementation is outside acquired sources")
    source = max(candidates, key=lambda value: len(value.module))
    path = Path(source.filename).resolve()
    module = importlib.import_module(source.module)
    code = compile(source.content, str(path), "exec", dont_inherit=True)
    entries = tuple(_runtime_members(ast.parse(source.content).body, module, code, source.module))
    entry = next((entry for entry in entries if entry[0] == capability.entrypoint), None)
    if entry is None:
        raise PortRefusal("consumer implementation is absent from acquired source")
    owner_name, method_name = capability.entrypoint.removeprefix(source.module + ".").rsplit(".", 1)
    owner = module
    for name in owner_name.split("."):
        owner = inspect.getattr_static(owner, name)
    if type(receiver) is not owner:
        raise PortRefusal("consumer receiver differs from its captured owner")
    function = getattr(receiver, method_name)

    def verify():
        if (
            path.read_bytes() != source.content
            or sha256(source.content).hexdigest() != capability.source_digest
            or admitted_operation_module_digest(source.content) != capability.semantic_digest
        ):
            raise PortRefusal("consumer source differs from captured capability")
        if Path(inspect.getfile(module)).resolve() != path or not inspect.ismethod(function):
            raise PortRefusal("consumer runtime differs from captured source")
        actual = inspect.getattr_static(owner, method_name)
        if (
            actual is not function.__func__
            or actual is not entry[2]
            or actual.__code__ != entry[3]
            or actual.__globals__ is not module.__dict__
        ):
            raise PortRefusal("consumer implementation was rebound")

    verify()
    authorize()
    return ResolvedConsumerSelection(operation, function, verify, authorize)


def resolve_prepared_factory(model, sources, operation):
    """Resolve the compiled original static acquisition method, never an ambient registry."""
    import ast
    import importlib
    import importlib.util
    import inspect
    from pathlib import Path

    from .data_operation_ports import PortRefusal, _runtime_members

    if model.version != MODEL_VERSION:
        raise PortRefusal("historical model cannot acquire current prepared capabilities")
    capability = model.operation(operation).capabilities.prepared_factory
    if capability is None:
        raise PortRefusal("operation has no captured prepared acquisition")
    candidates = [
        source
        for source in sources.sources
        if capability.entrypoint.startswith(source.module + ".")
    ]
    if not candidates:
        raise PortRefusal("prepared acquisition is outside acquired source")
    source = max(candidates, key=lambda value: len(value.module))
    module = importlib.import_module(source.module)
    path = Path(source.filename).resolve()
    expected = compile(source.content, str(path), "exec", dont_inherit=True)
    entries = tuple(
        _runtime_members(ast.parse(source.content).body, module, expected, source.module)
    )
    entry = next((entry for entry in entries if entry[0] == capability.entrypoint), None)
    if entry is None or not isinstance(entry[2], staticmethod):
        raise PortRefusal("prepared acquisition requires its original static method")
    function = entry[2].__func__

    # Resolve exactly the factory's called bindings, including local imports.
    # Existing prepared-callable validation supplies code/global-owner checks;
    # source custody below binds those checks to this acquired snapshot.
    from .data_operation_prepared_products import _verify_prepared_callable

    module_tree = ast.parse(source.content)
    imports = {}
    package = source.module if path.name == "__init__.py" else source.module.rpartition(".")[0]
    for node in (*module_tree.body, *ast.walk(entry[1])):
        if isinstance(node, ast.ImportFrom):
            reference = "." * node.level + (node.module or "")
            module_name = (
                importlib.util.resolve_name(reference, package) if node.level else reference
            )
            for alias in node.names:
                if alias.name != "*":
                    imports[alias.asname or alias.name] = (module_name, alias.name)
    called = set()
    for node in ast.walk(entry[1]):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called.add(node.func.id)
    captured = {value.module: value for value in sources.sources}

    def verify_callable(expected_owner, actual):
        module_name = actual.__module__
        original = captured.get(module_name)
        if original is None:
            raise PortRefusal("prepared callable is outside acquired source: " + expected_owner)
        owner_module = importlib.import_module(module_name)
        if (
            Path(inspect.getfile(owner_module)).resolve() != Path(original.filename).resolve()
            or Path(original.filename).read_bytes() != original.content
        ):
            raise PortRefusal("prepared callable source differs from acquired bytes")
        _verify_prepared_callable(expected_owner, actual)

    def verify_bindings():
        for name in called:
            if name in imports:
                supplying_module, member_name = imports[name]
                actual = inspect.getattr_static(
                    importlib.import_module(supplying_module), member_name
                )
                if inspect.isfunction(actual):
                    verify_callable(supplying_module + "." + member_name, actual)
            elif name in module.__dict__ and inspect.isfunction(module.__dict__[name]):
                verify_callable(source.module + "." + name, module.__dict__[name])

    def acquire(*args, **kwargs):
        if (
            path.read_bytes() != source.content
            or sha256(source.content).hexdigest() != capability.source_digest
            or admitted_operation_module_digest(source.content) != capability.semantic_digest
        ):
            raise PortRefusal("prepared acquisition source differs from admitted bytes")
        actual = module
        for name in capability.entrypoint.removeprefix(source.module + ".").split("."):
            actual = inspect.getattr_static(actual, name)
        if (
            not isinstance(actual, staticmethod)
            or actual.__func__ is not function
            or function.__code__ != entry[3]
            or function.__globals__ is not module.__dict__
            or Path(inspect.getfile(module)).resolve() != path
        ):
            raise PortRefusal("prepared acquisition runtime was rebound")
        verify_bindings()
        result = function(*args, **kwargs)
        verify_bindings()
        from .data_operation_effects import CapturedEffectPort

        if isinstance(result, CapturedEffectPort):
            method = result.effect_implementation
            verify_callable(method.__module__ + "." + method.__qualname__, method)
        implementations = (
            (result, result.effect_implementation())
            if isinstance(result, CapturedEffectPort)
            else (result,)
        )
        for implementation in implementations:
            if hasattr(implementation, "plan_python"):
                concrete = type(implementation)
                original_type = importlib.import_module(concrete.__module__)
                if concrete.__module__ not in captured:
                    raise PortRefusal("prepared port type is outside acquired source")
                for name in concrete.__qualname__.split("."):
                    original_type = inspect.getattr_static(original_type, name)
                if original_type is not concrete:
                    raise PortRefusal("prepared port type differs from its captured owner")
                method = implementation.plan_python
                original_method = method.__func__ if inspect.ismethod(method) else method
                verify_callable(
                    original_method.__module__ + "." + original_method.__qualname__, method
                )
        return result

    return acquire
