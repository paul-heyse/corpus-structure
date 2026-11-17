"""Original prepared scalar calls using shared admission, wire and physical owners."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

from .data_operation_model import EffectiveDataOperationModel, EffectiveOperation
from .data_operation_ports import (
    BatchPortCompletion,
    PortCompletion,
    PortRefusal,
    ResolvedPythonPort,
    logical_batch_signature,
)
from .data_operation_prepared_products import verify_prepared_product
from .python_operation_sources import PythonSourceCollection
from .types import SourceArtifact


@dataclass(frozen=True)
class PreparedCallResult:
    value: Any
    cpu_execution_evidence: bytes | None = None
    execution_evidence: bytes | None = None
    outcome: str | None = None
    provider_execution_evidence: bytes | None = None
    cpu_execution_reply: bytes | None = None


@dataclass(frozen=True)
class PreparedBatchCallResult:
    """One original whole CPU reply/receipt, never independently minted member receipts."""

    content: bytes
    cpu_execution_evidence: bytes


@dataclass
class PreparedOriginalCallPort:
    """A captured family factory supplies resources and an existing physical plan.

    This adapter owns no executor or policy. The original callable's annotations
    and the effective roles retain nominal ingress and completion meaning; the
    physical plan uses the caller's existing CPU/provider ownership.
    """

    identity: Any
    model: EffectiveDataOperationModel
    operation: EffectiveOperation
    sources: PythonSourceCollection
    custody: tuple[SourceArtifact, ...]
    original: Callable[..., Any]
    physical_plan: Callable[..., Any]
    plan_owner: str
    authorize: Callable[[Any], None]
    assets: tuple[SourceArtifact, ...]
    required_sources: PythonSourceCollection
    functions: tuple[tuple[str, Callable[..., Any]], ...] = ()
    native_selections: tuple = ()
    requires_prepared_schema: bool = False
    completion_type: Any = None
    retain_cpu_reply: bool = False
    _port: ResolvedPythonPort = field(init=False, repr=False)

    def __post_init__(self):
        if self.operation != self.model.operation(self.identity.operation):
            raise PortRefusal("prepared call differs from its exact effective operation")
        native_publication = (
            self.operation.profile == "command"
            and self.operation.capabilities.preparation == "native-publication"
            and bool(self.operation.effects)
        )
        if self.operation.capabilities.forms not in (("scalar",), ("batch",)) or (
            self.operation.effects and not native_publication
        ):
            raise PortRefusal(
                "prepared original-call adapter requires an explicit scalar/batch computation or native publication command"
            )
        if self.operation.capabilities.preparation == "none":
            raise PortRefusal("prepared original-call adapter requires declared preparation")
        batch = self.operation.capabilities.forms == ("batch",)
        if batch and (self.operation.effects or not self.retain_cpu_reply):
            raise PortRefusal(
                "prepared batch requires effect-free computation and its original whole CPU authority reply"
            )
        signature = inspect.signature(self.original, eval_str=True)
        surface = self.operation.callable_surfaces
        if len(surface) != 1:
            raise PortRefusal("prepared original call requires one captured callable")
        parameters = tuple(item.name for item in surface[0].parameters)
        if inspect.ismethod(self.original):
            parameters = parameters[1:]
        if (
            tuple(signature.parameters) != parameters
            or signature.return_annotation is inspect.Signature.empty
            or any(
                parameter.annotation is inspect.Parameter.empty
                or parameter.kind
                in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
                for parameter in signature.parameters.values()
            )
        ):
            raise PortRefusal("prepared original call differs from its fixed typed signature")
        from .data_operation_prepared_products import authenticated_prepared_product
        functions = ((self.identity.declaration, self.original), (self.plan_owner, self.physical_plan), *self.functions)
        verify_prepared_product(
            self.identity, self.model, self.operation, self.sources, self.custody,
            assets=self.assets, functions=functions, authorize=self.authorize,
            required_sources=self.required_sources,
        )
        self._port = ResolvedPythonPort(
            self.identity,
            self.model,
            self.operation,
            tuple(
                (item.owner, item.key) for item in self.model.identities if item.domain == "kind"
            ),
            self.original,
            signature,
            self.authorize,
            self._verify,
            logical_batch_signature(signature) if batch else None,
        )
        self._verification = authenticated_prepared_product(self.sources, functions)
        self._basis = tuple((name, getattr(self, name)) for name in ("identity", "model", "operation", "sources", "custody", "assets", "original", "physical_plan", "functions", "required_sources"))
        self._verify()

    @property
    def consumer_receiver(self):
        return self.original.__self__ if inspect.ismethod(self.original) else None

    @property
    def logical_signature(self):
        return self._port.logical_signature or self._port.signature

    def _verify(self):
        if any(getattr(self, name) is not value for name, value in self._basis):
            raise PortRefusal("prepared port correspondence changed after acquisition")
        try:
            self._verification.check()
        except ValueError as error:
            raise PortRefusal(str(error)) from error
        self.authorize(self.identity)

    def plan_cpu_reply(
        self,
        kernel,
        bound: inspect.BoundArguments,
        captured: PythonSourceCollection,
        *,
        prepared_release_id: str | None = None,
        asset_custody: tuple = (),
        verify=None,
        check_active,
        execution_owner,
    ):
        """Execute a family-bound kernel using the existing physical CPU owner.

        The family owns binding, resources and domain validation. This owner
        constructs the fixed source descriptor and keeps admission verification
        attached through submission and collection; it acquires no resources.
        """
        from .data_operation_cpu import PythonCPUDescriptor, plan_cpu_call

        def verify_call():
            self._verify()
            if verify is not None:
                verify()

        descriptor = PythonCPUDescriptor(
            tuple((source.module, source.filename, source.content) for source in captured.sources),
            kernel.__module__ + "." + kernel.__qualname__,
            (),
            verification="prepared-kernel",
            control_parameter="check_active",
            prepared_parameter="prepared" if prepared_release_id is not None else None,
            prepared_release_id=prepared_release_id,
            asset_custody=asset_custody,
        )
        return (
            yield from plan_cpu_call(
                descriptor,
                bound,
                bound.signature,
                verify=verify_call,
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )

    def plan_cpu(self, kernel, bound, captured, **options):
        """Complete the common JSON kernel shape with its authentic CPU receipt."""
        import json

        from .identity import canonical_bytes

        reply = yield from self.plan_cpu_reply(kernel, bound, captured, **options)
        if self.retain_cpu_reply:
            from .data_operation_cpu_basis import cpu_authority_value

            value = cpu_authority_value(
                reply.content, expected_basis=bound.arguments["input_basis"]
            )
        else:
            value = json.loads(reply.content)
        return PreparedCallResult(
            value,
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
            cpu_execution_reply=reply.content if self.retain_cpu_reply else None,
        )

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        if self.operation.capabilities.forms != ("scalar",):
            raise PortRefusal("prepared batch requires explicit member invocation")
        check_active()
        self._verify()
        arguments = self._port._arguments(
            values, route="python", binding=binding, signature=self._port.signature
        )
        # The acquired family plan owns physical submission. No hidden callback
        # pool, Reader, native claim or publication is introduced here.
        result = yield from self.physical_plan(
            arguments,
            binding=binding,
            check_active=check_active,
            execution_owner=execution_owner,
        )
        check_active()
        self._verify()
        if isinstance(result, PreparedCallResult):
            if (
                self.retain_cpu_reply
                and result.cpu_execution_evidence is not None
                and result.cpu_execution_reply is None
            ):
                raise PortRefusal(
                    "prepared authority boundary requires its actual retained CPU reply"
                )
            if result.outcome in {"failed", "empty"}:
                if result.outcome not in self.operation.outcomes or result.value is not None:
                    raise PortRefusal(
                        "terminal prepared result differs from its declared output policy"
                    )
                completion = PortCompletion(self.operation.semantic_id, (), outcome=result.outcome)
            else:
                completion = self._port._complete(
                    result.value, self.completion_type or self._port.signature.return_annotation
                )
                if result.outcome is not None and result.outcome != completion.outcome:
                    raise PortRefusal(
                        "successful prepared result differs from its declared outcome"
                    )
            return replace(
                completion,
                cpu_execution_evidence=result.cpu_execution_evidence,
                execution_evidence=result.execution_evidence,
                provider_execution_evidence=result.provider_execution_evidence,
                cpu_execution_reply=result.cpu_execution_reply,
            )
        return self._port._complete(
            result, self.completion_type or self._port.signature.return_annotation
        )

    def plan_batch_python(self, members, *, check_active=lambda: None, execution_owner):
        import json

        from .data_operation_cpu_basis import (
            cpu_authority_batch_values,
            cpu_input_basis_from_binding,
        )

        if self.operation.capabilities.forms != ("batch",):
            raise PortRefusal("prepared scalar cannot accept a batch invocation")
        members = tuple(members)
        if not members or len({member.member for member in members}) != len(members):
            raise PortRefusal("prepared batch requires distinct ordered logical members")
        self._verify()
        expected = []
        roles = {role.name: role for role in self.operation.roles if role.direction == "input"}
        for member in members:
            if member.binding is None or member.producer is None:
                raise PortRefusal(
                    "prepared CPU batch requires its actual binding and original native producer"
                )
            arguments = self._port._arguments(
                member.values,
                route="python",
                binding=member.binding,
                signature=self.logical_signature,
            )
            bodies = {
                name: (arguments.arguments[role.parameter],)
                if role.collection == "scalar"
                else tuple(arguments.arguments[role.parameter])
                for name, role in roles.items()
            }
            expected.append(
                dict(
                    member=member.member,
                    producer=json.loads(member.producer),
                    input_basis=cpu_input_basis_from_binding(
                        self.identity.recipe, member.binding, bodies
                    ),
                )
            )
        result = yield from self.physical_plan(
            tuple(expected), check_active=check_active, execution_owner=execution_owner
        )
        if not isinstance(result, PreparedBatchCallResult):
            raise PortRefusal("prepared batch requires its actual whole reply/receipt")
        values = cpu_authority_batch_values(result.content, expected_members=expected)
        check_active()
        self._verify()
        return BatchPortCompletion(
            tuple(
                (
                    member.member,
                    replace(
                        self._port._complete(
                            value, self.completion_type or self.logical_signature.return_annotation
                        ),
                        cpu_execution_evidence=result.cpu_execution_evidence,
                        cpu_execution_reply=result.content,
                    ),
                )
                for member, value in zip(members, values, strict=True)
            )
        )
