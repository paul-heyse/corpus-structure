"""Direct original-callable ports for the admitted closed Python function profile.

Extraction is static. Runtime acquisition checks the complete source/recipe and
asks the acquired execution owner for permission. Structural values never grant
native publication authority; effects require a separately admitted implementation.
"""

from __future__ import annotations

import ast
import builtins
import copy
import dataclasses
import dis
import importlib
import importlib.util
import inspect
import json
import typing
from collections.abc import Callable, Generator, Iterator, Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import CodeType, ModuleType
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self, get_args, get_origin

if TYPE_CHECKING:
    from .data_operation_bindings import BindingResult
    from .data_operation_cpu import PythonCPUDescriptor
    from .types import PreparedRelease, SourceBundle

from pydantic import BaseModel, ConfigDict, TypeAdapter, model_validator

from .data_operation_model import EffectiveDataOperationModel, EffectiveOperation
from .identity import canonical_bytes
from .operation_value_types import decode_json_text, native_result_scope
from .python_operation_sources import PythonSourceCollection


class PortRefusal(ValueError):
    """The selected representation has not established this execution capability."""


class DataOperationWireValue(BaseModel):
    """Strict external values; field reads detach nested caller-owned structures."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        validate_default=True,
        revalidate_instances="always",
    )

    __wire_schema__: ClassVar[bytes | None] = None

    @model_validator(mode="after")
    def validate_captured_wire(self) -> Self:
        schema = type(self).__wire_schema__
        if schema is not None:
            from .data_operation_wire import validate_wire_schema

            validate_wire_schema(schema, self.model_dump(mode="python"))
        return self

    def model_post_init(self, context: Any) -> None:
        for name in type(self).model_fields:
            object.__setattr__(self, name, copy.deepcopy(object.__getattribute__(self, name)))

    def __getattribute__(self, name: str) -> Any:
        value = super().__getattribute__(name)
        if name in type(self).model_fields:
            return copy.deepcopy(value)
        return value


class DataOperationNativeRow(DataOperationWireValue):
    """Immutable/revalidated row values retaining explicit JSON-text decoding."""

    __json_fields__: ClassVar[tuple[str, ...]] = ()

    def decoded_json_fields(self, *, operation: str) -> dict[str, Any]:
        values = self.model_dump(mode="python")
        for name in self.__json_fields__:
            with native_result_scope(operation, type(self).__name__, name):
                values[name] = decode_json_text(values[name])
        return values


@dataclass(frozen=True)
class PythonPortIdentity:
    model_digest: str
    operation: str
    definition: str
    recipe: str
    implementation: str
    declaration: str
    source_digest: str
    capabilities: bytes
    eligibility: str


@dataclass(frozen=True)
class RoleValue:
    """An immutable nominal role value, independent of product/effect authority."""

    role: str
    kind_contract: str
    content: bytes
    meaning: bytes | None = None
    members: tuple[bytes, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.content) is not bytes
            or not self.role
            or not self.kind_contract
            or (self.meaning is not None and type(self.meaning) is not bytes)
            or type(self.members) is not tuple
            or any(type(member) is not bytes for member in self.members)
        ):
            raise TypeError("role values require nominal role/kind and owned immutable bytes")

    def value(self) -> Any:
        return json.loads(self.content)


@dataclass(frozen=True)
class PythonRoleValue:
    """Already typed Python ingress; the port validates before retaining anything."""

    role: str
    kind_contract: str
    value: Any


@dataclass(frozen=True)
class PortCompletion:
    operation: str
    outputs: tuple[RoleValue, ...]
    execution_evidence: bytes | None = None
    cpu_execution_evidence: bytes | None = None
    outcome: str = "success"
    pdf_execution_evidence: bytes | None = None

    def __post_init__(self) -> None:
        if type(self.outcome) is not str or not self.outcome:
            raise TypeError("completion requires an explicit semantic outcome")
        if self.execution_evidence is not None and type(self.execution_evidence) is not bytes:
            raise TypeError("execution evidence requires owned immutable bytes")
        if (
            self.cpu_execution_evidence is not None
            and type(self.cpu_execution_evidence) is not bytes
        ):
            raise TypeError("CPU execution evidence requires owned immutable bytes")
        if (
            self.pdf_execution_evidence is not None
            and type(self.pdf_execution_evidence) is not bytes
        ):
            raise TypeError("PDF execution evidence requires owned immutable bytes")


@dataclass(frozen=True)
class PythonBatchMember:
    member: str
    values: tuple[PythonRoleValue, ...]
    binding: BindingResult | None = None


@dataclass(frozen=True)
class JSONBatchMember:
    member: str
    values: tuple[RoleValue, ...]
    binding: BindingResult | None = None


@dataclass(frozen=True)
class BatchPortCompletion:
    members: tuple[tuple[str, PortCompletion], ...]


def project_product_members(
    model: EffectiveDataOperationModel, kind: str, value: Any
) -> tuple[bytes, ...]:
    """Copy actual declared packet facts; this grants no native publication authority."""
    from .data_operation_identity import semantic_value
    from .data_operation_member_contracts import derive_member_kinds

    raw = _untrusted_value(value)
    members = raw.get("members") if isinstance(raw, dict) else None
    allowed = derive_member_kinds(model, kind)
    if not allowed:
        if isinstance(members, (list, tuple)) and any(
            isinstance(packet, dict) and {"member_id", "kind_contract"} & packet.keys()
            for packet in members
        ):
            raise PortRefusal("noncontainer kind cannot project nominal members")
        return ()
    if not isinstance(members, (list, tuple)):
        raise PortRefusal("nominal member container lacks its actual packet array")
    contracts = {(item.owner, item.domain): item.key for item in model.identities}
    nominal = {contracts[owner, "kind"]: owner for owner in allowed}
    kind_facts = {item.semantic_id: json.loads(item.facts) for item in model.kinds}
    constants = {owner: [] for owner in allowed}
    for edge in model.edges:
        if edge.source in constants and edge.relation == "property":
            prop = kind_facts[edge.target]
            if prop.get("equals_string") is not None:
                constants[edge.source].append((prop["name"], prop["equals_string"]))
    seen, result = set(), []
    for packet in members:
        if not isinstance(packet, dict) or set(packet) != {
            "member_id",
            "kind_contract",
            "context",
            "body",
        }:
            raise PortRefusal("native member packet requires its exact four actual fields")
        identifier = packet["member_id"]
        if type(identifier) is not str or not identifier or identifier in seen:
            raise PortRefusal("native member packet has absent/repeated local identity")
        seen.add(identifier)
        owner = nominal.get(packet["kind_contract"])
        if owner is None:
            raise PortRefusal("native member packet has an undeclared nominal contract")
        context = packet["context"]
        if (
            not isinstance(context, dict)
            or set(context) != {"subject", "original_source", "analyzed_scope"}
            or any(
                type(context[name]) is not str or not context[name]
                for name in ("subject", "original_source")
            )
        ):
            raise PortRefusal("native member packet lacks its exact source/subject/scope context")
        if any(
            not isinstance(packet["body"], dict) or packet["body"].get(name) != value
            for name, value in constants[owner]
        ):
            raise PortRefusal("member body differs from its actual nominal discriminator")
        result.append(canonical_bytes({**packet, "body": semantic_value(packet["body"])}))
    return tuple(result)


@dataclass(frozen=True)
class StreamPortTerminal:
    """Explicit terminal standing; observed prefixes confer no completion."""

    state: Literal["complete", "cancelled", "failed"]
    items: int


class PortDataStream:
    """One acquired iterator with bounded, pull-driven validation and owned close."""

    def __init__(self, port, iterator, annotation, check_active):
        if not isinstance(iterator, Iterator):
            raise PortRefusal("stream callable did not return an iterator")
        self._port, self._iterator = port, iterator
        self._annotation, self._check_active = annotation, check_active
        self._count = 0
        self.terminal: StreamPortTerminal | None = None

    def __enter__(self):
        return self

    def __exit__(self, *error):
        self.close()

    def __iter__(self):
        return self

    def __next__(self) -> tuple[int, PortCompletion]:
        if self.terminal is not None:
            raise StopIteration
        try:
            self._check_active()
            self._port.verify_runtime()
            self._port.authorize(self._port.identity)
            try:
                value = next(self._iterator)
            except StopIteration:
                self._port.verify_runtime()
                self.terminal = StreamPortTerminal("complete", self._count)
                self._close_iterator()
                raise
            self._port.verify_runtime()
            completed = self._port._complete(value, self._annotation)
            position = self._count
            self._count += 1
            return position, completed
        except StopIteration:
            raise
        except BaseException:
            self.terminal = StreamPortTerminal("failed", self._count)
            self._close_iterator()
            raise

    def _close_iterator(self):
        close = getattr(self._iterator, "close", None)
        if close is not None:
            close()

    def close(self):
        if self.terminal is None:
            self.terminal = StreamPortTerminal("cancelled", self._count)
            self._close_iterator()


@dataclass(frozen=True)
class ResolvedPythonPort:
    identity: PythonPortIdentity
    model: EffectiveDataOperationModel
    operation: EffectiveOperation
    kind_contracts: tuple[tuple[str, str], ...]
    function: Callable[..., Any]
    signature: inspect.Signature
    authorize: Callable[[PythonPortIdentity], None]
    verify_runtime: Callable[[], None]
    logical_signature: inspect.Signature | None = None
    cpu_descriptor: PythonCPUDescriptor | None = None

    @property
    def native_selections(self) -> tuple:
        return ()

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from dataclasses import replace

        from .data_operation_cpu import plan_cpu_call

        if self.operation.capabilities.forms != ("scalar",):
            raise PortRefusal("batch capability requires explicit member invocation")
        bound = self._arguments(values, route="python", binding=binding, signature=self.signature)
        reply = yield from plan_cpu_call(
            self.cpu_descriptor,
            bound,
            self.signature,
            verify=self.verify_runtime,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        result = TypeAdapter(self.signature.return_annotation).validate_json(
            reply.content, strict=True
        )
        return replace(
            self._complete(result, self.signature.return_annotation),
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
        )

    def plan_batch_python(self, members, *, check_active=lambda: None, execution_owner):
        from dataclasses import replace

        from .data_operation_cpu import plan_cpu_call

        bound = self._batch_arguments(members, route="python")
        reply = yield from plan_cpu_call(
            self.cpu_descriptor,
            bound,
            self.signature,
            verify=self.verify_runtime,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        checked = TypeAdapter(self.signature.return_annotation).validate_json(
            reply.content, strict=True
        )
        completed = self._batch_complete(checked, members)
        evidence = canonical_bytes(reply.execution_receipt.record())
        return BatchPortCompletion(
            tuple(
                (member, replace(completion, cpu_execution_evidence=evidence))
                for member, completion in completed.members
            )
        )

    def open_stream_python(self, values, *, binding=None, check_active=lambda: None):
        """Invoke original data iterator; each pull preserves ingress and authority."""
        if self.operation.capabilities.forms != ("stream",):
            raise PortRefusal("operation has no admitted data stream capability")
        annotation = self.signature.return_annotation
        if get_origin(annotation) not in (Iterator, Generator):
            raise PortRefusal("stream result requires Iterator[T] or Generator[T, None, None]")
        arguments = get_args(annotation)
        if len(arguments) not in (1, 3) or (
            len(arguments) == 3 and arguments[1:] != (type(None), type(None))
        ):
            raise PortRefusal("data stream cannot receive values or hide a terminal result")
        bound = self._arguments(values, route="python", binding=binding, signature=self.signature)
        check_active()
        iterator = self.function(*bound.args, **bound.kwargs)
        return PortDataStream(self, iterator, arguments[0], check_active)

    def invoke_python(
        self, values: tuple[PythonRoleValue, ...], *, binding: BindingResult | None = None
    ) -> PortCompletion:
        return self._invoke(values, route="python", binding=binding)

    def invoke_json(
        self, values: tuple[RoleValue, ...], *, binding: BindingResult | None = None
    ) -> PortCompletion:
        return self._invoke(values, route="json", binding=binding)

    def _invoke(
        self,
        values: tuple[PythonRoleValue, ...] | tuple[RoleValue, ...],
        *,
        route: Literal["python", "json"],
        binding: BindingResult | None,
    ) -> PortCompletion:
        if self.operation.capabilities.forms != ("scalar",):
            raise PortRefusal("batch capability requires explicit member invocation")
        bound = self._arguments(values, route=route, binding=binding, signature=self.signature)
        result = self.function(*bound.args, **bound.kwargs)
        self.verify_runtime()
        return self._complete(result, self.signature.return_annotation)

    def _arguments(self, values, *, route, binding, signature, verify=True):
        # Recheck the acquired authority per invocation. A retained port is not a
        # durable permission after the target or source has changed.
        if binding is not None and (
            binding.operation != self.identity.operation
            or not binding.sufficient
            or binding.definition != self.identity.definition
            or binding.eligibility != self.identity.eligibility
        ):
            raise PortRefusal(
                "resolved binding is insufficient or differs from the admitted contract"
            )
        if verify:
            self.verify_runtime()
        self.authorize(self.identity)
        contracts = dict(self.kind_contracts)
        roles = {role.name: role for role in self.operation.roles if role.direction == "input"}
        supplied = {}
        for value in values:
            if value.role not in roles or value.role in supplied:
                raise PortRefusal("unknown or repeated input role: " + value.role)
            if value.kind_contract != contracts[roles[value.role].kind]:
                raise PortRefusal("nominal kind contract differs for role: " + value.role)
            supplied[value.role] = value
        arguments = {}
        for name, role in roles.items():
            if role.parameter is None:
                raise PortRefusal("input role has no authoritative callable parameter: " + name)
            parameter = signature.parameters[role.parameter]
            annotation = _input_annotation(parameter)
            adapter = TypeAdapter(annotation)
            if name in supplied:
                value = supplied[name]
                if route == "json":
                    assert isinstance(value, RoleValue)
                    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
                        raw = value.value()
                        fields = {
                            field.name for field in dataclasses.fields(annotation) if field.init
                        }
                        if not isinstance(raw, dict) or set(raw) - fields:
                            raise PortRefusal("dataclass JSON ingress contains undeclared fields")
                        checked = _validated_python_input(
                            annotation, adapter.validate_json(value.content, strict=True)
                        )
                    else:
                        checked = adapter.validate_json(value.content, strict=True)
                else:
                    assert isinstance(value, PythonRoleValue)
                    checked = _validated_python_input(annotation, value.value)
            elif parameter.default is not inspect.Parameter.empty:
                checked = adapter.validate_python(_untrusted_value(parameter.default), strict=True)
            else:
                raise PortRefusal("missing callable input role: " + name)
            if typing.is_typeddict(annotation):
                raw = value.value() if route == "json" else value.value
                if not isinstance(raw, dict) or set(raw) - set(annotation.__annotations__):
                    raise PortRefusal("TypedDict ingress contains undeclared fields")
            if role.collection != "scalar":
                length = len(checked)
                if length < role.minimum or (role.maximum is not None and length > role.maximum):
                    raise PortRefusal("input role cardinality differs: " + name)
            arguments[role.parameter] = copy.deepcopy(checked)
        # Semantic parameters come from the same frozen binding that determines
        # the native request. Never silently execute a different original default.
        semantic_parameters = {}
        if binding is not None:
            from .data_operation_bindings import effective_binding_parameters
            from .data_operation_identity import decode_semantic_value

            semantic_parameters = effective_binding_parameters(
                self.operation, decode_semantic_value(json.loads(binding.parameters))
            )
            declared = json.loads(self.operation.parameters)
            if set(semantic_parameters) - set(declared):
                raise PortRefusal("binding contains undeclared semantic parameters")
            if set(semantic_parameters) & set(arguments):
                raise PortRefusal("semantic parameter conflicts with a data input role")
            if set(semantic_parameters) - set(signature.parameters):
                raise PortRefusal("semantic parameter lacks an admitted callable correspondence")
        for name, parameter in signature.parameters.items():
            if name not in arguments:
                if name in semantic_parameters:
                    value = semantic_parameters[name]
                elif parameter.default is not inspect.Parameter.empty:
                    value = parameter.default
                else:
                    raise PortRefusal("unbound callable parameter: " + name)
                arguments[name] = TypeAdapter(parameter.annotation).validate_python(
                    _untrusted_value(value), strict=True
                )
        positional = tuple(
            arguments[p.name]
            for p in signature.parameters.values()
            if p.kind == inspect.Parameter.POSITIONAL_ONLY
        )
        keywords = {}
        for name, value in arguments.items():
            parameter = signature.parameters[name]
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                if set(keywords) & set(value):
                    raise PortRefusal("expanded TypedDict conflicts with callable parameters")
                keywords.update(value)
            elif parameter.kind != inspect.Parameter.POSITIONAL_ONLY:
                if name in keywords:
                    raise PortRefusal("expanded TypedDict conflicts with callable parameters")
                keywords[name] = value
        bound = signature.bind(*positional, **keywords)
        return bound

    def invoke_batch_python(self, members: tuple[PythonBatchMember, ...]) -> BatchPortCompletion:
        return self._invoke_batch(members, route="python")

    def invoke_batch_json(self, members: tuple[JSONBatchMember, ...]) -> BatchPortCompletion:
        return self._invoke_batch(members, route="json")

    def _batch_arguments(self, members, *, route):
        signature = self.logical_signature
        if self.operation.capabilities.forms != ("batch",) or signature is None:
            raise PortRefusal("operation has no admitted native batch capability")
        if (
            not members
            or any(not item.member for item in members)
            or len({item.member for item in members}) != len(members)
        ):
            raise PortRefusal("batch requires distinct explicit logical member identities")
        self.verify_runtime()
        rows = tuple(
            self._arguments(
                item.values, route=route, binding=item.binding, signature=signature, verify=False
            )
            for item in members
        )
        arguments = {
            name: tuple(row.arguments[name] for row in rows) for name in signature.parameters
        }
        positional = tuple(
            arguments[p.name]
            for p in self.signature.parameters.values()
            if p.kind == inspect.Parameter.POSITIONAL_ONLY
        )
        keywords = {
            name: value
            for name, value in arguments.items()
            if self.signature.parameters[name].kind != inspect.Parameter.POSITIONAL_ONLY
        }
        return self.signature.bind(*positional, **keywords)

    def _invoke_batch(self, members, *, route) -> BatchPortCompletion:
        """One original batch call; exact member order and all-or-nothing validation."""
        bound = self._batch_arguments(members, route=route)
        result = self.function(*bound.args, **bound.kwargs)
        self.verify_runtime()
        return self._batch_complete(result, members)

    def _batch_complete(self, result, members) -> BatchPortCompletion:
        signature = self.logical_signature
        assert signature is not None
        checked = TypeAdapter(self.signature.return_annotation).validate_python(
            _untrusted_value(result), strict=True
        )
        if len(checked) != len(members):
            raise PortRefusal("native batch result cardinality differs from logical membership")
        completions = tuple(self._complete(value, signature.return_annotation) for value in checked)
        return BatchPortCompletion(
            tuple(
                (member.member, completion)
                for member, completion in zip(members, completions, strict=True)
            )
        )

    def _complete(self, result, return_annotation) -> PortCompletion:
        from .data_operation_outcomes import successful_return_outcome

        outcome = successful_return_outcome(self.operation)
        contracts = dict(self.kind_contracts)
        checked = _validated_python_input(return_annotation, result)
        from .data_operation_identity import semantic_value

        outputs = [role for role in self.operation.roles if role.direction == "output"]
        if self.operation.result_fields:
            correspondence = dict(self.operation.result_fields)
            if not isinstance(checked, dict) or set(checked) != set(correspondence.values()):
                raise PortRefusal("returned fields differ from declared atomic output bundle")
            # The whole return annotation has already validated every field.
            # Encode privately; no partial PortCompletion escapes if encoding fails.
            value_type = get_args(return_annotation)[1]
            adapter = TypeAdapter(value_type)
            encoded_outputs = tuple(
                RoleValue(
                    role.name,
                    contracts[role.kind],
                    adapter.dump_json(checked[correspondence[role.name]]),
                    canonical_bytes(
                        semantic_value(
                            adapter.dump_python(checked[correspondence[role.name]], mode="python")
                        )
                    ),
                    project_product_members(
                        self.model,
                        role.kind,
                        adapter.dump_python(checked[correspondence[role.name]], mode="python"),
                    ),
                )
                for role in outputs
            )
            return PortCompletion(self.operation.semantic_id, encoded_outputs, outcome=outcome)
        # Multiple outputs require explicit correspondence, never tuple guessing.
        if len(outputs) != 1 or outputs[0].collection != "scalar":
            raise PortRefusal("direct function result requires one declared scalar output")
        output = outputs[0]
        adapter = TypeAdapter(return_annotation)
        encoded = adapter.dump_json(checked)
        semantic = adapter.dump_python(checked, mode="python")
        return PortCompletion(
            self.operation.semantic_id,
            (
                RoleValue(
                    output.name,
                    contracts[output.kind],
                    encoded,
                    canonical_bytes(semantic_value(semantic)),
                    project_product_members(self.model, output.kind, semantic),
                ),
            ),
            outcome=outcome,
        )


def _validated_python_input(annotation: Any, value: Any) -> Any:
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        if type(value) is not annotation:
            raise PortRefusal("typed Python dataclass ingress requires its exact nominal class")
        # Existing instances may have bypassed __init__ or later mutated fields.
        # Reconstruct only validated declared fields; do not run a second factory.
        result = object.__new__(annotation)
        fields = dataclasses.fields(annotation)
        if set(vars(value)) != {field.name for field in fields}:
            raise PortRefusal("typed dataclass ingress has missing or undeclared fields")
        annotations = typing.get_type_hints(annotation)
        for field in fields:
            checked = _validated_python_input(
                annotations[field.name], object.__getattribute__(value, field.name)
            )
            object.__setattr__(result, field.name, copy.deepcopy(checked))
        return result
    checked = TypeAdapter(annotation).validate_python(_untrusted_value(value), strict=True)

    def owned(item):
        if dataclasses.is_dataclass(item) and not isinstance(item, type):
            return _validated_python_input(type(item), item)
        if isinstance(item, dict):
            return {key: owned(value) for key, value in item.items()}
        if isinstance(item, tuple):
            return tuple(owned(value) for value in item)
        if isinstance(item, list):
            return [owned(value) for value in item]
        return item

    return owned(checked)


def _untrusted_value(value: Any) -> Any:
    """Model instances can have bypassed validation; reconstruct their public fields."""
    if isinstance(value, BaseModel):
        return {
            name: _untrusted_value(getattr(value, name))
            for name in type(value).model_fields
            if name in value.model_fields_set
        }
    if isinstance(value, Mapping):
        return {key: _untrusted_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_untrusted_value(item) for item in value)
    if isinstance(value, list):
        return [_untrusted_value(item) for item in value]
    return copy.deepcopy(value)


def python_port_identity(
    model: EffectiveDataOperationModel,
    sources: PythonSourceCollection,
    operation: str,
    *,
    schema: SourceBundle | None = None,
    prepared: PreparedRelease | None = None,
) -> PythonPortIdentity:
    """Prepare a correspondence statically; no import and no execution permission."""
    from dataclasses import asdict

    from .data_operation_compilation import compile_data_operations

    selected = model.operation(operation)
    if len(selected.callable_surfaces) != 1 or selected.implementation_root is None:
        raise PortRefusal("operation has no single closed original callable surface")
    # Re-extract the exact supplied source instead of trusting a caller-created
    # EffectiveOperation or a matching signature alone.
    observed = compile_data_operations(
        schema,
        python_sources=sources,
        definitions=prepared.definitions if prepared is not None else None,
        vocabularies=prepared.vocabularies if prepared is not None else (),
    )
    expected = {(i.owner, i.domain): i.key for i in model.identities}
    actual = {(i.owner, i.domain): i.key for i in observed.identities}
    required = (
        (operation, "definition"),
        (operation, "recipe"),
        (selected.implementation_root, "implementation-slice"),
        (operation, "eligibility"),
    )
    if any(key not in expected or actual.get(key) != expected[key] for key in required):
        raise PortRefusal(
            "complete source/definition/recipe correspondence is unavailable or differs"
        )
    if observed.operation(operation) != selected:
        # Origins are evidence, so filenames must also correspond for this runtime
        # archive. A broader model may still contain independent operations/kinds.
        raise PortRefusal("supplied operation facts differ from the compiled model")
    return PythonPortIdentity(
        sha256(model.content).hexdigest(),
        operation,
        expected[required[0]],
        expected[required[1]],
        expected[required[2]],
        selected.callable_surfaces[0].declaration,
        sha256(
            canonical_bytes(
                tuple((s.module, sha256(s.content).hexdigest()) for s in sources.sources)
            )
        ).hexdigest(),
        canonical_bytes(asdict(selected.capabilities)),
        expected[operation, "eligibility"],
    )


def resolve_python_port(
    model: EffectiveDataOperationModel,
    sources: PythonSourceCollection,
    operation: str,
    *,
    authorize: Callable[[PythonPortIdentity], None],
    receiver: object | None = None,
    runtime_locations: Mapping[str, Path] | None = None,
    schema: SourceBundle | None = None,
    prepared: PreparedRelease | None = None,
) -> ResolvedPythonPort:
    """Acquire the original callable after explicit execution-owner authorization.

    `authorize` must be supplied by the acquired execution-admission owner.
    A pure call-correspondence/context check is not such authority.

    This closed direct-function profile has no effects, preparation resource,
    streaming or batch completion mapping. Other declared forms are preserved in
    the model and refuse here until their implementation capability is admitted.
    There is no scalar fallback for them and no ambient Reader parameter.
    """
    identity = python_port_identity(model, sources, operation, schema=schema, prepared=prepared)
    selected = model.operation(operation)
    if (
        selected.effects
        or selected.capabilities.forms not in (("scalar",), ("batch",), ("stream",))
        or selected.capabilities.preparation != "none"
        or selected.capabilities.cancellation not in ("none", "call-boundary")
    ):
        raise PortRefusal(
            "the declared effects/form/preparation/cancellation need "
            "an explicit admitted implementation capability"
        )
    from .data_operation_outcomes import successful_return_outcome

    # Normal return semantics must be known before importing/calling the target.
    successful_return_outcome(selected)
    outputs = [r for r in selected.roles if r.direction == "output"]
    if len(outputs) != 1 and not selected.result_fields:
        raise PortRefusal(
            "multi-output completion requires an explicit admitted result correspondence"
        )
    authorize(identity)
    if runtime_locations is not None and set(runtime_locations) - {
        s.module for s in sources.sources
    }:
        raise PortRefusal("runtime locations name a module outside the captured source collection")
    paths = {
        source.module: Path(
            (runtime_locations or {}).get(source.module, Path(source.filename))
        ).resolve()
        for source in sources.sources
    }
    for source in sources.sources:
        # An archive records exact acquired paths, not a module search fallback.
        path = paths[source.module]
        if not path.is_file() or path.read_bytes() != source.content:
            raise PortRefusal("runtime source differs from supplied archive: " + source.module)
    modules = {}
    for source in sources.sources:
        path = paths[source.module]
        modules[source.module] = importlib.import_module(source.module)
        if Path(inspect.getfile(modules[source.module])).resolve() != path.resolve():
            raise PortRefusal("runtime module resolved to a different acquired source")
    module_name = max(
        (name for name in modules if identity.declaration.startswith(name + ".")), key=len
    )
    member = identity.declaration.removeprefix(module_name + ".")
    surface = selected.callable_surfaces[0]
    expected_parameters = tuple(p.name for p in surface.parameters)
    if "." in member:
        exposed_module = max(
            (name for name in modules if surface.exposed.startswith(name + ".")), key=len
        )
        exposed_path = surface.exposed.removeprefix(exposed_module + ".").split(".")
        owner = modules[exposed_module]
        for name in exposed_path[:-1]:
            owner = inspect.getattr_static(owner, name)
        if not isinstance(owner, type) or type(owner) is not type:
            raise PortRefusal("receiver requires a supplied plain class")
        if any(
            "__init__" in cls.__dict__ or "__new__" in cls.__dict__ for cls in owner.__mro__[:-1]
        ):
            raise PortRefusal(
                "receiver construction requires an explicit admitted preparation capability"
            )
        allowed_magic = {
            "__module__",
            "__qualname__",
            "__dict__",
            "__weakref__",
            "__doc__",
            "__firstlineno__",
            "__static_attributes__",
            "__annotations__",
            "__annotate_func__",
            "__data_operation__",
        }
        if any(
            name.startswith("__") and name.endswith("__") and name not in allowed_magic
            for cls in owner.__mro__[:-1]
            for name in vars(cls)
        ):
            raise PortRefusal("receiver magic methods require an admitted dispatch model")
        if receiver is None:
            receiver = object.__new__(owner)
        if type(receiver) is not owner or vars(receiver):
            raise PortRefusal(
                "receiver must match its exposed class with no unbound instance state"
            )
        function = getattr(receiver, exposed_path[-1])
        if not inspect.ismethod(function) or function.__self__ is not receiver:
            raise PortRefusal("receiver entrypoint must be an original instance method")
        expected_parameters = expected_parameters[1:]
    else:
        if receiver is not None:
            raise PortRefusal("function profile cannot accept a receiver")
        function = getattr(modules[module_name], member)
        if not inspect.isfunction(function):
            raise PortRefusal("original declaration is not a Python function")
    if hasattr(function, "__signature__") or hasattr(function, "__wrapped__"):
        raise PortRefusal("runtime signature override needs an admitted callable transformation")
    signature = inspect.signature(function, eval_str=True)
    logical_signature = None
    if selected.capabilities.forms == ("batch",):

        def element(annotation):
            args = get_args(annotation)
            if get_origin(annotation) is not tuple or len(args) != 2 or args[1] is not Ellipsis:
                raise PortRefusal("native batch fields require tuple[T, ...] annotations")
            return args[0]

        if any(p.default is not inspect.Parameter.empty for p in signature.parameters.values()):
            raise PortRefusal(
                "native batch callable defaults require explicit per-member correspondence"
            )
        logical_signature = signature.replace(
            parameters=[
                p.replace(annotation=element(p.annotation)) for p in signature.parameters.values()
            ],
            return_annotation=element(signature.return_annotation),
        )
    logical_return = (logical_signature or signature).return_annotation
    if selected.capabilities.forms == ("stream",):
        arguments = get_args(logical_return)
        if get_origin(logical_return) not in (Iterator, Generator) or not arguments:
            raise PortRefusal("stream result requires a typed data iterator")
        if selected.result_fields:
            raise PortRefusal("stream atomic bundles require a separately declared stream adapter")
    if selected.result_fields:
        return_args = get_args(logical_return)
        if (
            get_origin(logical_return) is not dict
            or len(return_args) != 2
            or return_args[0] is not str
            or {name for name, _ in selected.result_fields} != {role.name for role in outputs}
            or any(role.collection != "scalar" or role.presence != "required" for role in outputs)
        ):
            raise PortRefusal("atomic result fields require required scalar roles and dict[str, T]")
    if (
        any(
            (
                p.kind == inspect.Parameter.VAR_POSITIONAL
                or (
                    p.kind == inspect.Parameter.VAR_KEYWORD
                    and not (
                        "unpack-typeddict-runtime" in sources.generated_interfaces
                        and get_origin(p.annotation) is typing.Unpack
                        and len(get_args(p.annotation)) == 1
                        and typing.is_typeddict(get_args(p.annotation)[0])
                    )
                )
            )
            or p.annotation is inspect.Parameter.empty
            for p in signature.parameters.values()
        )
        or signature.return_annotation is inspect.Signature.empty
    ):
        raise PortRefusal("direct callable requires a complete fixed annotated signature")
    if tuple(signature.parameters) != expected_parameters:
        raise PortRefusal("runtime callable signature differs from compiled declaration")

    def verify_runtime() -> None:
        _verify_runtime_sources(model, selected, sources, modules, paths)
        if receiver is not None and vars(receiver):
            raise PortRefusal("receiver acquired unbound mutable instance state")

    verify_runtime()
    contracts = tuple((i.owner, i.key) for i in model.identities if i.domain == "kind")
    # Invalid defaults must fail at acquisition, even when the caller would supply
    # that argument and conceal the invalid default.
    for parameter in signature.parameters.values():
        if parameter.default is not inspect.Parameter.empty:
            TypeAdapter(parameter.annotation).validate_python(
                _untrusted_value(parameter.default), strict=True
            )
    return ResolvedPythonPort(
        identity,
        model,
        selected,
        contracts,
        function,
        signature,
        authorize,
        verify_runtime,
        logical_signature,
        _cpu_descriptor(model, selected, sources, paths, receiver is not None),
    )


def _cpu_descriptor(model, selected, sources, paths, receiver):
    from .data_operation_cpu import PythonCPUDescriptor

    return PythonCPUDescriptor(
        tuple(
            (source.module, str(paths[source.module]), source.content) for source in sources.sources
        ),
        selected.callable_surfaces[0].exposed,
        tuple(
            sorted(
                node.id.removeprefix("python:")
                for implementation in model.implementation_slices
                if implementation.root == selected.implementation_root
                for node in implementation.nodes
                if node.id.startswith("python:")
            )
        ),
        receiver,
    )


def _source_reference(node, module):
    if isinstance(node, ast.Name):
        return module.__dict__.get(node.id, getattr(builtins, node.id, None))
    if isinstance(node, ast.Attribute):
        return inspect.getattr_static(_source_reference(node.value, module), node.attr)
    raise PortRefusal("class base requires a closed named reference")


def _runtime_members(statements, owner, code, prefix):
    codes = {item.co_name: item for item in code.co_consts if isinstance(item, CodeType)}
    for node in statements:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            path = prefix + "." + node.name
            value = inspect.getattr_static(owner, node.name)
            yield path, node, value, codes.get(node.name)
            if isinstance(node, ast.ClassDef):
                expected = codes.get(node.name)
                if expected is None:
                    raise PortRefusal("class code is unavailable: " + path)
                yield from _runtime_members(node.body, value, expected, path)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and hasattr(owner, target.id):
                    yield (
                        prefix + "." + target.id,
                        node,
                        inspect.getattr_static(owner, target.id),
                        None,
                    )


def _verify_runtime_sources(model, operation, sources, modules, paths=None) -> None:
    if paths is None:
        paths = {source.module: Path(source.filename).resolve() for source in sources.sources}
    implementation = next(
        s for s in model.implementation_slices if s.root == operation.implementation_root
    )
    expected_nodes = {
        n.id.removeprefix("python:") for n in implementation.nodes if n.id.startswith("python:")
    }
    standard_references: dict[str, object] = {}
    if operation.capabilities.forms == ("stream",):
        standard_references = {
            "collections.abc.Iterator": Iterator,
            "collections.abc.Generator": Generator,
            "typing.Iterator": typing.Iterator,
            "typing.Generator": typing.Generator,
        }
    if "unpack-typeddict-runtime" in sources.generated_interfaces:
        standard_references.update(
            {
                "typing." + name: getattr(typing, name)
                for name in ("TypedDict", "Unpack", "NotRequired", "Required")
            }
        )
    if "dataclasses-runtime" in sources.generated_interfaces:
        standard_references.update(
            {"dataclasses.dataclass": dataclasses.dataclass, "dataclasses.field": dataclasses.field}
        )
    _verify_closed_runtime_sources(
        sources, modules, paths, expected_nodes, standard_references=standard_references
    )


def _verify_closed_runtime_sources(
    sources, modules, paths, expected_nodes, *, standard_references=None
) -> None:
    _verify_consumed_globals(
        sources, modules, expected_nodes, standard_references=standard_references
    )
    for source in sources.sources:
        module = modules[source.module]
        if paths[source.module].read_bytes() != source.content:
            raise PortRefusal("runtime source changed after acquisition")
        code = compile(source.content, str(paths[source.module]), "exec", dont_inherit=True)
        tree = ast.parse(source.content)
        for path, node, value, expected_code in _runtime_members(
            tree.body, module, code, source.module
        ):
            if path not in expected_nodes:
                continue
            name = path.removeprefix(source.module + ".")
            if isinstance(node, ast.FunctionDef):
                if (
                    not inspect.isfunction(value)
                    or value.__code__ != expected_code
                    or value.__globals__ is not module.__dict__
                ):
                    raise PortRefusal("runtime callable implementation differs: " + name)
                if hasattr(value, "__signature__") or hasattr(value, "__wrapped__"):
                    raise PortRefusal("runtime signature transformation differs: " + name)
                runtime_signature = inspect.signature(value, eval_str=True)
                parameters = runtime_signature.parameters
                annotated = [
                    (a.arg, a.annotation)
                    for a in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
                ]
                annotated.append(("return", node.returns))
                for annotation_name, annotation in annotated:
                    if annotation is None:
                        continue
                    for dependency in ast.walk(annotation):
                        if (
                            isinstance(dependency, ast.Name)
                            and hasattr(builtins, dependency.id)
                            and dependency.id in module.__dict__
                            and module.__dict__[dependency.id]
                            is not getattr(builtins, dependency.id)
                        ):
                            raise PortRefusal(
                                "runtime annotation dependency differs: " + dependency.id
                            )
                    expected_annotation = eval(
                        compile(ast.Expression(annotation), source.filename, "eval"),
                        module.__dict__,
                    )
                    if isinstance(expected_annotation, str):
                        expected_annotation = eval(expected_annotation, module.__dict__)
                    actual_annotation = (
                        runtime_signature.return_annotation
                        if annotation_name == "return"
                        else parameters[annotation_name].annotation
                    )
                    if actual_annotation != expected_annotation:
                        raise PortRefusal("runtime callable annotation differs: " + annotation_name)
                defaults = [
                    *zip(
                        node.args.posonlyargs + node.args.args,
                        [None]
                        * (len(node.args.posonlyargs + node.args.args) - len(node.args.defaults))
                        + list(node.args.defaults),
                        strict=True,
                    ),
                    *zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True),
                ]
                for argument, default in defaults:
                    actual = parameters[argument.arg].default
                    if default is None:
                        if actual is not inspect.Parameter.empty:
                            raise PortRefusal("runtime parameter default differs: " + argument.arg)
                        continue
                    try:
                        expected = ast.literal_eval(default)
                    except ValueError, TypeError:
                        raise PortRefusal(
                            "default requires an explicit acquired correspondence: " + argument.arg
                        ) from None
                    if type(actual) is not type(expected) or actual != expected:
                        raise PortRefusal("runtime parameter default differs: " + argument.arg)
                for global_name in value.__code__.co_names:
                    if (
                        hasattr(builtins, global_name)
                        and global_name in value.__globals__
                        and value.__globals__[global_name] is not getattr(builtins, global_name)
                    ):
                        raise PortRefusal("runtime builtin dependency was replaced: " + global_name)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                owner_name = path.rsplit(".", 1)[0]
                owner = module
                for component in owner_name.removeprefix(source.module).strip(".").split("."):
                    if component:
                        owner = inspect.getattr_static(owner, component)
                if (
                    "dataclasses-runtime" in sources.generated_interfaces
                    and isinstance(owner, type)
                    and dataclasses.is_dataclass(owner)
                    and isinstance(node.value, ast.Call)
                    and _source_reference(node.value.func, module) is dataclasses.field
                ):
                    # Source field/default/factory correspondence is checked as one
                    # generated constructor by the owning class below.
                    continue
                try:
                    if node.value is None:
                        raise PortRefusal("runtime determinant has no source value: " + name)
                    expected = ast.literal_eval(node.value)
                except ValueError, TypeError:
                    if isinstance(node.value, ast.Name):
                        # The consumed-global traversal already checked every
                        # link of this closed alias against its source owner.
                        continue
                    raise PortRefusal(
                        "runtime determinant needs an explicit acquired correspondence: " + name
                    ) from None
                if type(value) is not type(expected) or value != expected:
                    raise PortRefusal("runtime constant determinant differs: " + name)
            elif isinstance(node, ast.ClassDef):
                if (
                    "unpack-typeddict-runtime" in sources.generated_interfaces
                    and typing.is_typeddict(value)
                ):
                    _verify_generated_typeddict(value, node, module)
                    continue
                if (
                    "dataclasses-runtime" in sources.generated_interfaces
                    and dataclasses.is_dataclass(value)
                ):
                    _verify_generated_dataclass(value, node, module)
                    continue
                if (
                    not isinstance(value, type)
                    or type(value) is not type
                    or node.decorator_list
                    or node.keywords
                ):
                    raise PortRefusal("runtime class requires a plain supplied owner: " + name)
                expected_bases = tuple(_source_reference(base, module) for base in node.bases) or (
                    object,
                )
                if value.__bases__ != expected_bases:
                    raise PortRefusal("runtime class bases differ: " + name)
                allowed = {
                    "__module__",
                    "__dict__",
                    "__weakref__",
                    "__doc__",
                    "__firstlineno__",
                    "__static_attributes__",
                    "__annotations__",
                    "__annotate_func__",
                    "__data_operation__",
                }
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.ClassDef)):
                        allowed.add(item.name)
                    elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                        targets = item.targets if isinstance(item, ast.Assign) else [item.target]
                        allowed.update(t.id for t in targets if isinstance(t, ast.Name))
                if set(vars(value)) - allowed:
                    raise PortRefusal("runtime class acquired undeclared members: " + name)
            else:
                raise PortRefusal(
                    "runtime owner needs an explicit acquired correspondence: " + name
                )


def _input_annotation(parameter: inspect.Parameter) -> Any:
    annotation = parameter.annotation
    if parameter.kind == inspect.Parameter.VAR_KEYWORD:
        if get_origin(annotation) is not typing.Unpack or len(get_args(annotation)) != 1:
            raise PortRefusal("variadic keywords require an admitted TypedDict boundary")
        annotation = get_args(annotation)[0]
        if not typing.is_typeddict(annotation):
            raise PortRefusal("variadic keywords require a nominal TypedDict")
    return annotation


def _verify_generated_typeddict(value, node, module):
    if len(node.bases) != 1 or node.decorator_list or node.keywords:
        raise PortRefusal("TypedDict requires its closed standard class shape")
    if _source_reference(node.bases[0], module) is not typing.TypedDict:
        raise PortRefusal("TypedDict original base differs")
    annotations, required, optional = {}, set(), set()
    for declaration in node.body:
        if isinstance(declaration, ast.Pass) or (
            isinstance(declaration, ast.Expr) and isinstance(declaration.value, ast.Constant)
        ):
            continue
        if (
            not isinstance(declaration, ast.AnnAssign)
            or not isinstance(declaration.target, ast.Name)
            or declaration.value is not None
        ):
            raise PortRefusal("TypedDict boundary contains unsupported executable members")
        annotation = eval(
            compile(ast.Expression(declaration.annotation), module.__file__, "eval"),
            module.__dict__,
        )
        name = declaration.target.id
        annotations[name] = annotation
        (optional if get_origin(annotation) is typing.NotRequired else required).add(name)
    if (
        value.__annotations__ != annotations
        or value.__required_keys__ != required
        or value.__optional_keys__ != optional
        or not value.__total__
    ):
        raise PortRefusal("TypedDict runtime fields differ from captured declaration")


def _verify_generated_dataclass(value, node, module):
    """Check the selected standard transformation without running a factory."""
    if type(value) is not type or len(node.decorator_list) != 1 or node.keywords:
        raise PortRefusal("generated dataclass requires one captured standard decorator")
    decorator = node.decorator_list[0]
    function = decorator.func if isinstance(decorator, ast.Call) else decorator
    if _source_reference(function, module) is not dataclasses.dataclass:
        raise PortRefusal("generated dataclass decorator correspondence differs")
    expected_bases = tuple(_source_reference(base, module) for base in node.bases) or (object,)
    if value.__bases__ != expected_bases:
        raise PortRefusal("generated dataclass source bases differ")
    options = {}
    if isinstance(decorator, ast.Call):
        if decorator.args:
            raise PortRefusal("dataclass options must be named literals")
        for keyword in decorator.keywords:
            if keyword.arg not in {"init", "kw_only", "frozen"}:
                raise PortRefusal("unsupported generated dataclass option")
            options[keyword.arg] = ast.literal_eval(keyword.value)
    if options.get("init", True) is not True:
        raise PortRefusal("generated dataclass requires init=True")
    actual_fields = {field.name: field for field in dataclasses.fields(value)}
    expected_names = {
        field.name
        for base in value.__bases__
        if dataclasses.is_dataclass(base)
        for field in dataclasses.fields(base)
    }
    for declaration in node.body:
        if isinstance(declaration, ast.FunctionDef) and declaration.name in {
            "__init__",
            "__new__",
            "__post_init__",
        }:
            raise PortRefusal("custom dataclass construction needs an explicit model")
        if not isinstance(declaration, ast.AnnAssign) or not isinstance(
            declaration.target, ast.Name
        ):
            continue
        name = declaration.target.id
        expected_names.add(name)
        actual = actual_fields.get(name)
        if actual is None:
            raise PortRefusal("generated dataclass field correspondence differs")
        annotation = eval(
            compile(ast.Expression(declaration.annotation), module.__file__, "eval"),
            module.__dict__,
        )
        if actual.type != annotation:
            raise PortRefusal("generated dataclass field annotation differs")
        default, factory = dataclasses.MISSING, dataclasses.MISSING
        kw_only = options.get("kw_only", False)
        if isinstance(declaration.value, ast.Call):
            if _source_reference(declaration.value.func, module) is not dataclasses.field:
                raise PortRefusal("dataclass field requires its captured standard model")
            if declaration.value.args:
                raise PortRefusal("dataclass field options must be named")
            for keyword in declaration.value.keywords:
                if keyword.arg == "default_factory":
                    factory = _source_reference(keyword.value, module)
                    if not inspect.isfunction(factory) or factory.__module__ != module.__name__:
                        raise PortRefusal("dataclass factory requires a captured function")
                elif keyword.arg == "default":
                    default = ast.literal_eval(keyword.value)
                elif keyword.arg == "kw_only":
                    kw_only = ast.literal_eval(keyword.value)
                else:
                    raise PortRefusal("unsupported dataclass field option")
        elif declaration.value is not None:
            default = ast.literal_eval(declaration.value)
        if (
            actual.default_factory is not factory
            or actual.kw_only != kw_only
            or type(actual.default) is not type(default)
            or actual.default != default
        ):
            raise PortRefusal("dataclass default or factory correspondence differs")
    if set(actual_fields) != expected_names:
        raise PortRefusal("generated dataclass acquired undeclared fields")
    parameters = inspect.getattr_static(value, "__dataclass_params__")
    if parameters.frozen != options.get("frozen", False) or not parameters.init:
        raise PortRefusal("generated dataclass runtime options differ")
    specification = []
    for field in actual_fields.values():
        if field.default_factory is dataclasses.MISSING:
            modeled_field = dataclasses.field(default=field.default, kw_only=field.kw_only)
        else:
            if not callable(field.default_factory):
                raise PortRefusal("dataclass field factory is not callable")
            modeled_field = dataclasses.field(
                default_factory=field.default_factory, kw_only=field.kw_only
            )
        specification.append((field.name, field.type, modeled_field))
    expected = dataclasses.make_dataclass(
        value.__name__,
        specification,
        frozen=parameters.frozen,
        kw_only=options.get("kw_only", False),
    )
    if value.__init__.__code__ != expected.__init__.__code__:
        raise PortRefusal("generated dataclass constructor implementation differs")

    def same_default(actual: Any, modeled: Any) -> bool:
        # Generated factory defaults use the standard singleton sentinel. Literal
        # defaults need recursive type equality: (True,) must not match (1,).
        if actual is modeled:
            return True
        if type(actual) is not type(modeled):
            return False
        if isinstance(modeled, tuple):
            return len(actual) == len(modeled) and all(
                same_default(left, right) for left, right in zip(actual, modeled, strict=True)
            )
        return actual == modeled

    if not same_default(value.__init__.__defaults__, expected.__init__.__defaults__):
        raise PortRefusal("generated dataclass constructor defaults differ")
    actual_keywords = value.__init__.__kwdefaults__
    expected_keywords = expected.__init__.__kwdefaults__
    if expected_keywords is None:
        keywords_match = actual_keywords is None
    else:
        keywords_match = (
            isinstance(actual_keywords, dict)
            and type(actual_keywords) is dict
            and actual_keywords.keys() == expected_keywords.keys()
            and all(same_default(actual_keywords[name], default)
                    for name, default in expected_keywords.items())
        )
    if not keywords_match:
        raise PortRefusal("generated dataclass constructor keyword defaults differ")
    allowed = set(vars(expected)) | {"__firstlineno__", "__static_attributes__", "__annotate_func__"}
    if "__slotnames__" in vars(value):
        if vars(value)["__slotnames__"] != []:
            raise PortRefusal("generated dataclass has unexpected runtime slots")
        allowed.add("__slotnames__")  # copyreg caches the absence of slots during deepcopy.
    allowed.update(
        declaration.name
        for declaration in node.body
        if isinstance(declaration, (ast.FunctionDef, ast.ClassDef))
    )
    allowed.update(
        declaration.target.id
        for declaration in node.body
        if isinstance(declaration, ast.AnnAssign) and isinstance(declaration.target, ast.Name)
    )
    if set(vars(value)) - allowed:
        raise PortRefusal(
            "generated dataclass acquired undeclared class behavior: "
            + repr(sorted(set(vars(value)) - allowed))
        )
    for name in ("__setattr__", "__delattr__", "__getattribute__"):
        actual_method = inspect.getattr_static(value, name)
        expected_method = inspect.getattr_static(expected, name)
        if inspect.isfunction(expected_method):
            if (
                not inspect.isfunction(actual_method)
                or actual_method.__code__ != expected_method.__code__
            ):
                raise PortRefusal("generated dataclass mutation behavior differs")
        elif actual_method is not expected_method:
            raise PortRefusal("generated dataclass field access behavior differs")
    actual_closure = tuple(cell.cell_contents for cell in value.__init__.__closure__ or ())
    expected_closure = tuple(cell.cell_contents for cell in expected.__init__.__closure__ or ())
    if any(left is not right for left, right in zip(actual_closure, expected_closure, strict=True)):
        raise PortRefusal("generated dataclass constructor closure differs")


def _code_globals(code: CodeType) -> set[str]:
    names = {str(i.argval) for i in dis.get_instructions(code) if i.opname == "LOAD_GLOBAL"}
    for constant in code.co_consts:
        if isinstance(constant, CodeType):
            names.update(_code_globals(constant))
    return names


def _verify_consumed_globals(
    sources, modules, expected_nodes: set[str], *, standard_references=None
) -> None:
    """Authenticate each consumed global along its full closed import/alias chain.

    Verifying dep.helper alone says nothing about application.alias. Every link
    actually used by a function or its annotation must still name that object.
    We inspect only captured modules; an opaque import needs a different admitted
    runtime capability rather than an ambient import fallback.
    """
    standard_references = standard_references or {}
    bindings: dict[tuple[str, str], tuple[str, Any]] = {}
    uses: list[tuple[str, str]] = []
    attribute_uses: list[tuple[str, str, tuple[str, ...]]] = []
    for source in sources.sources:
        tree = ast.parse(source.content)
        package = (
            source.module
            if Path(source.filename).name == "__init__.py"
            else source.module.rpartition(".")[0]
        )
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    bindings[source.module, alias.asname or alias.name.split(".")[0]] = (
                        "module",
                        (alias.name, bool(alias.asname)),
                    )
            elif isinstance(node, ast.ImportFrom):
                reference = "." * node.level + (node.module or "")
                target = (
                    importlib.util.resolve_name(reference, package) if node.level else reference
                )
                for alias in node.names:
                    if alias.name == "*":
                        continue  # static extraction already withholds an open wildcard
                    bindings[source.module, alias.asname or alias.name] = (
                        "from",
                        (target, alias.name),
                    )
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                bindings[source.module, node.name] = ("definition", None)
                if (
                    isinstance(node, ast.FunctionDef)
                    and source.module + "." + node.name in expected_nodes
                ):
                    function = modules[source.module].__dict__.get(node.name)
                    if not inspect.isfunction(function):
                        raise PortRefusal("runtime global callable differs: " + node.name)
                    names = _code_globals(function.__code__)
                    for argument in (
                        *node.args.posonlyargs,
                        *node.args.args,
                        *node.args.kwonlyargs,
                    ):
                        if argument.annotation is not None:
                            names.update(
                                n.id
                                for n in ast.walk(argument.annotation)
                                if isinstance(n, ast.Name)
                            )
                    if node.returns is not None:
                        names.update(
                            n.id for n in ast.walk(node.returns) if isinstance(n, ast.Name)
                        )
                    uses.extend((source.module, name) for name in names)
                    for attribute in ast.walk(node):
                        if not isinstance(attribute, ast.Attribute):
                            continue
                        members = []
                        root: ast.expr = attribute
                        while isinstance(root, ast.Attribute):
                            members.append(root.attr)
                            root = root.value
                        if isinstance(root, ast.Name) and root.id in names:
                            attribute_uses.append(
                                (source.module, root.id, tuple(reversed(members)))
                            )
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                target = (
                    node.targets[0]
                    if isinstance(node, ast.Assign) and len(node.targets) == 1
                    else node.target
                    if isinstance(node, ast.AnnAssign)
                    else None
                )
                if isinstance(target, ast.Name):
                    bindings[source.module, target.id] = (
                        ("alias", node.value.id)
                        if isinstance(node.value, ast.Name)
                        else ("value", node.value)
                    )

    active: set[tuple[str, str]] = set()
    # Supplied methods consume module globals through the same closed alias
    # chain as top-level functions; class membership must not bypass that check.
    for source in sources.sources:
        module = modules[source.module]
        tree = ast.parse(source.content)
        code = compile(source.content, source.filename, "exec", dont_inherit=True)
        for path, node, value, _ in _runtime_members(tree.body, module, code, source.module):
            if path in expected_nodes and isinstance(node, ast.ClassDef):
                uses.extend(
                    (source.module, item.id)
                    for base in node.bases
                    for item in ast.walk(base)
                    if isinstance(item, ast.Name)
                )
            if (
                path not in expected_nodes
                or not isinstance(node, ast.FunctionDef)
                or path.count(".") <= source.module.count(".") + 1
            ):
                continue
            if not inspect.isfunction(value):
                raise PortRefusal("runtime method differs: " + path)
            names = _code_globals(value.__code__)
            for annotation in (
                *[
                    arg.annotation
                    for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
                ],
                node.returns,
            ):
                if annotation is not None:
                    names.update(
                        item.id for item in ast.walk(annotation) if isinstance(item, ast.Name)
                    )
            uses.extend((source.module, name) for name in names)
            for attribute in ast.walk(node):
                if not isinstance(attribute, ast.Attribute):
                    continue
                members = []
                root = attribute
                while isinstance(root, ast.Attribute):
                    members.append(root.attr)
                    root = root.value
                if isinstance(root, ast.Name) and root.id in names:
                    attribute_uses.append((source.module, root.id, tuple(reversed(members))))

    checked: dict[tuple[str, str], Any] = {}

    def module_value(name: str):
        if name not in modules and not any(key.startswith(name + ".") for key in modules):
            raise PortRefusal("runtime import is outside the captured closure: " + name)
        value = importlib.import_module(name)
        parts = name.split(".")
        for index in range(1, len(parts)):
            parent = importlib.import_module(".".join(parts[:index]))
            child = importlib.import_module(".".join(parts[: index + 1]))
            if parent.__dict__.get(parts[index]) is not child:
                raise PortRefusal("runtime imported module path was rebound: " + name)
        if name in modules and value is not modules[name]:
            raise PortRefusal("runtime captured module was replaced: " + name)
        return value

    def resolve(module_name: str, name: str):
        key = (module_name, name)
        if key in checked:
            return checked[key]
        if key in active:
            raise PortRefusal("runtime alias cycle requires an explicit correspondence")
        module = modules[module_name]
        actual = module.__dict__.get(name, inspect.Parameter.empty)
        binding = bindings.get(key)
        if binding is None:
            if module_name + "." + name in modules:
                expected = module_value(module_name + "." + name)
                if actual is not expected:
                    raise PortRefusal("runtime imported module attribute was rebound: " + name)
                return expected
            if hasattr(builtins, name):
                expected = getattr(builtins, name)
                if actual is not inspect.Parameter.empty and actual is not expected:
                    raise PortRefusal("runtime builtin dependency was replaced: " + name)
                return expected
            raise PortRefusal("runtime global has no captured binding: " + module_name + "." + name)
        active.add(key)
        tag, content = binding
        if tag == "module":
            target, aliased = content
            module_value(target)  # also verify the imported dotted module path
            expected = module_value(target if aliased else target.split(".")[0])
        elif tag == "from":
            target, member = content
            if target + "." + member in standard_references:
                expected = standard_references[target + "." + member]
            elif target in modules and (target, member) in bindings:
                expected = resolve(target, member)
            elif target + "." + member in modules:
                expected = module_value(target + "." + member)
            else:
                raise PortRefusal(
                    "runtime re-export is outside the captured closure: " + target + "." + member
                )
        elif tag == "alias":
            expected = resolve(module_name, content)
        elif tag == "value":
            if content is None:
                raise PortRefusal("runtime global has no acquired value: " + name)
            try:
                expected = ast.literal_eval(content)
            except ValueError, TypeError:
                raise PortRefusal(
                    "runtime global needs an explicit acquired correspondence: " + name
                ) from None
            if type(actual) is not type(expected) or actual != expected:
                raise PortRefusal("runtime constant determinant differs: " + name)
            expected = actual
        else:
            if module_name + "." + name not in expected_nodes:
                raise PortRefusal(
                    "runtime callable dependency is outside the implementation slice: " + name
                )
            expected = actual  # definition code/globals/defaults checked by the owner below
        if actual is not expected:
            raise PortRefusal(
                "runtime consumed import or alias was rebound: " + module_name + "." + name
            )
        active.remove(key)
        checked[key] = expected
        return expected

    for module_name, name in uses:
        resolve(module_name, name)
    for module_name, name, members in attribute_uses:
        value = resolve(module_name, name)
        for member in members:
            if not isinstance(value, ModuleType) or value.__name__ not in modules:
                raise PortRefusal(
                    "runtime attribute needs an explicit acquired correspondence: "
                    + name
                    + "."
                    + member
                )
            value = resolve(value.__name__, member)


@dataclass(frozen=True)
class NativeCommandCompletion:
    """A returned native effect receipt, never a payload-shaped stand-in."""

    operation: str
    result: RoleValue
    receipt_id: str
    derivation_id: str


@dataclass(frozen=True)
class ResolvedPublicationPort:
    """Publication command boundary; transaction/receipt authority stays native."""

    storage: Any
    request_kind: str
    result_kind: str

    def invoke_json(self, value: RoleValue) -> NativeCommandCompletion:
        if value.role != "request" or value.kind_contract != self.request_kind:
            raise PortRefusal("publication command requires its captured nominal request")
        result = self.storage.invoke("publish_data_derivation", value.value())
        if (
            type(result.get("receipt_id")) is not str
            or not result["receipt_id"]
            or type(result.get("derivation_id")) is not str
            or not result["derivation_id"]
            or type(result.get("replayed")) is not bool
        ):
            raise PortRefusal("native publication did not return its required effect receipt")
        from .data_operation_identity import semantic_value

        return NativeCommandCompletion(
            "data.publish_data_derivation",
            RoleValue(
                "result",
                self.result_kind,
                canonical_bytes(result),
                canonical_bytes(semantic_value(result)),
            ),
            result["receipt_id"],
            result["derivation_id"],
        )
