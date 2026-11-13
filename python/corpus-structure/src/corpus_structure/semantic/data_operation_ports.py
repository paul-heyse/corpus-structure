"""Direct original-callable ports for the admitted closed Python function profile.

Extraction is static. Runtime acquisition checks the complete source/recipe and
asks the acquired execution owner for permission. Structural values never grant
native publication authority; effects require a separately admitted implementation.
"""

from __future__ import annotations

import ast
import builtins
import copy
import importlib
import inspect
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import CodeType
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from .data_operation_bindings import BindingResult

from pydantic import BaseModel, ConfigDict, TypeAdapter

from .data_operation_model import EffectiveDataOperationModel, EffectiveOperation
from .identity import canonical_bytes
from .python_operation_sources import PythonSourceCollection


class PortRefusal(ValueError):
    """The selected representation has not established this execution capability."""


class DataOperationWireValue(BaseModel):
    """Strict external values; field reads detach nested caller-owned structures."""

    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", validate_default=True, revalidate_instances="always"
    )

    def model_post_init(self, context: Any) -> None:
        for name in type(self).model_fields:
            object.__setattr__(self, name, copy.deepcopy(object.__getattribute__(self, name)))

    def __getattribute__(self, name: str) -> Any:
        value = super().__getattribute__(name)
        if name in type(self).model_fields:
            return copy.deepcopy(value)
        return value


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


@dataclass(frozen=True)
class RoleValue:
    """An immutable nominal role value, independent of product/effect authority."""

    role: str
    kind_contract: str
    content: bytes

    def __post_init__(self) -> None:
        if type(self.content) is not bytes or not self.role or not self.kind_contract:
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


@dataclass(frozen=True)
class ResolvedPythonPort:
    identity: PythonPortIdentity
    operation: EffectiveOperation
    kind_contracts: tuple[tuple[str, str], ...]
    function: Callable[..., Any]
    signature: inspect.Signature
    authorize: Callable[[PythonPortIdentity], None]
    verify_runtime: Callable[[], None]

    def invoke_python(
        self, values: tuple[PythonRoleValue, ...], *, binding: BindingResult | None = None
    ) -> PortCompletion:
        return self._invoke(values, route="python", binding=binding)

    def invoke_json(
        self, values: tuple[RoleValue, ...], *, binding: BindingResult | None = None
    ) -> PortCompletion:
        return self._invoke(values, route="json", binding=binding)

    def _invoke(
        self, values: tuple[PythonRoleValue, ...] | tuple[RoleValue, ...], *, route: Literal["python", "json"], binding: BindingResult | None
    ) -> PortCompletion:
        # Recheck the acquired authority per invocation. A retained port is not a
        # durable permission after the target or source has changed.
        if binding is not None and (binding.operation != self.identity.operation or not binding.sufficient):
            raise PortRefusal("resolved binding is insufficient or belongs to another operation")
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
            parameter = self.signature.parameters[role.parameter]
            adapter = TypeAdapter(parameter.annotation)
            if name in supplied:
                value = supplied[name]
                if route == "json":
                    assert isinstance(value, RoleValue)
                    checked = adapter.validate_json(value.content, strict=True)
                else:
                    assert isinstance(value, PythonRoleValue)
                    checked = adapter.validate_python(_untrusted_value(value.value), strict=True)
            elif parameter.default is not inspect.Parameter.empty:
                checked = adapter.validate_python(_untrusted_value(parameter.default), strict=True)
            else:
                raise PortRefusal("missing callable input role: " + name)
            if role.collection != "scalar":
                length = len(checked)
                if length < role.minimum or (role.maximum is not None and length > role.maximum):
                    raise PortRefusal("input role cardinality differs: " + name)
            arguments[role.parameter] = copy.deepcopy(checked)
        # Parameters without data roles are semantic parameters owned by the
        # original signature. Only its validated defaults are admitted here.
        for name, parameter in self.signature.parameters.items():
            if name not in arguments:
                if parameter.default is inspect.Parameter.empty:
                    raise PortRefusal("unbound callable parameter: " + name)
                arguments[name] = TypeAdapter(parameter.annotation).validate_python(
                    _untrusted_value(parameter.default), strict=True
                )
        positional = tuple(
            arguments[p.name] for p in self.signature.parameters.values()
            if p.kind == inspect.Parameter.POSITIONAL_ONLY
        )
        keywords = {
            name: value for name, value in arguments.items()
            if self.signature.parameters[name].kind != inspect.Parameter.POSITIONAL_ONLY
        }
        bound = self.signature.bind(*positional, **keywords)
        result = self.function(*bound.args, **bound.kwargs)
        checked = TypeAdapter(self.signature.return_annotation).validate_python(_untrusted_value(result), strict=True)
        outputs = [role for role in self.operation.roles if role.direction == "output"]
        # There is deliberately no guessed tuple/attribute/outcome interpreter.
        # A multi-output or effectful implementation needs its own admitted
        # completion correspondence, not an accidental Python return convention.
        if len(outputs) != 1 or outputs[0].collection != "scalar":
            raise PortRefusal("direct function result requires one declared scalar output")
        output = outputs[0]
        encoded = TypeAdapter(self.signature.return_annotation).dump_json(checked)
        return PortCompletion(self.operation.semantic_id, (RoleValue(output.name, contracts[output.kind], encoded),))


def _untrusted_value(value: Any) -> Any:
    """Model instances can have bypassed validation; reconstruct their public fields."""
    if isinstance(value, BaseModel):
        return {name: _untrusted_value(getattr(value, name)) for name in type(value).model_fields}
    if isinstance(value, Mapping):
        return {key: _untrusted_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_untrusted_value(item) for item in value)
    if isinstance(value, list):
        return [_untrusted_value(item) for item in value]
    return copy.deepcopy(value)


def python_port_identity(
    model: EffectiveDataOperationModel, sources: PythonSourceCollection, operation: str
) -> PythonPortIdentity:
    """Prepare a correspondence statically; no import and no execution permission."""
    from dataclasses import asdict

    from .data_operation_compilation import compile_data_operations

    selected = model.operation(operation)
    if len(selected.callable_surfaces) != 1 or selected.implementation_root is None:
        raise PortRefusal("operation has no single closed original callable surface")
    # Re-extract the exact supplied source instead of trusting a caller-created
    # EffectiveOperation or a matching signature alone.
    observed = compile_data_operations(python_sources=sources)
    expected = {(i.owner, i.domain): i.key for i in model.identities}
    actual = {(i.owner, i.domain): i.key for i in observed.identities}
    required = ((operation, "definition"), (operation, "recipe"), (selected.implementation_root, "implementation-slice"))
    if any(key not in expected or actual.get(key) != expected[key] for key in required):
        raise PortRefusal("complete source/definition/recipe correspondence is unavailable or differs")
    if observed.operation(operation) != selected:
        # Origins are evidence, so filenames must also correspond for this runtime
        # archive. A broader model may still contain independent operations/kinds.
        raise PortRefusal("supplied operation facts differ from the compiled model")
    return PythonPortIdentity(
        sha256(model.content).hexdigest(), operation, expected[required[0]], expected[required[1]],
        expected[required[2]], selected.callable_surfaces[0].declaration,
        sha256(canonical_bytes(tuple((s.module, sha256(s.content).hexdigest()) for s in sources.sources))).hexdigest(),
        canonical_bytes(asdict(selected.capabilities)),
    )


def resolve_python_port(
    model: EffectiveDataOperationModel,
    sources: PythonSourceCollection,
    operation: str,
    *,
    authorize: Callable[[PythonPortIdentity], None],
) -> ResolvedPythonPort:
    """Acquire the original callable after explicit execution-owner authorization.

    `authorize` must be supplied by the acquired execution-admission owner.
    A pure call-correspondence/context check is not such authority.

    This closed direct-function profile has no effects, preparation resource,
    streaming or batch completion mapping. Other declared forms are preserved in
    the model and refuse here until their implementation capability is admitted.
    There is no scalar fallback for them and no ambient Reader parameter.
    """
    identity = python_port_identity(model, sources, operation)
    selected = model.operation(operation)
    if selected.effects or selected.capabilities.forms != ("scalar",) or selected.capabilities.preparation != "none" or selected.capabilities.cancellation not in ("none", "call-boundary"):
        raise PortRefusal("the declared effects/form/preparation/cancellation need an explicit admitted implementation capability")
    if len([r for r in selected.roles if r.direction == "output"]) != 1:
        raise PortRefusal("multi-output completion requires an explicit admitted result correspondence")
    authorize(identity)
    for source in sources.sources:
        # An archive records exact acquired paths, not a module search fallback.
        path = Path(source.filename)
        if not path.is_file() or path.read_bytes() != source.content:
            raise PortRefusal("runtime source differs from supplied archive: " + source.module)
    modules = {}
    for source in sources.sources:
        path = Path(source.filename)
        modules[source.module] = importlib.import_module(source.module)
        if Path(inspect.getfile(modules[source.module])).resolve() != path.resolve():
            raise PortRefusal("runtime module resolved to a different acquired source")
    module_name = max((name for name in modules if identity.declaration.startswith(name + ".")), key=len)
    member = identity.declaration.removeprefix(module_name + ".")
    if "." in member:
        raise PortRefusal("bound methods require an explicit admitted owner capability")
    function = getattr(modules[module_name], member)
    if not inspect.isfunction(function):
        raise PortRefusal("original declaration is not a Python function")
    if hasattr(function, "__signature__") or hasattr(function, "__wrapped__"):
        raise PortRefusal("runtime signature override needs an admitted callable transformation")
    signature = inspect.signature(function, eval_str=True)
    if any(p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD) or p.annotation is inspect.Parameter.empty for p in signature.parameters.values()) or signature.return_annotation is inspect.Signature.empty:
        raise PortRefusal("direct callable requires a complete fixed annotated signature")
    if tuple(signature.parameters) != tuple(p.name for p in selected.callable_surfaces[0].parameters):
        raise PortRefusal("runtime callable signature differs from compiled declaration")
    def verify_runtime() -> None:
        _verify_runtime_sources(model, selected, sources, modules)
    verify_runtime()
    contracts = tuple((i.owner, i.key) for i in model.identities if i.domain == "kind")
    # Invalid defaults must fail at acquisition, even when the caller would supply
    # that argument and conceal the invalid default.
    for parameter in signature.parameters.values():
        if parameter.default is not inspect.Parameter.empty:
            TypeAdapter(parameter.annotation).validate_python(_untrusted_value(parameter.default), strict=True)
    return ResolvedPythonPort(identity, selected, contracts, function, signature, authorize, verify_runtime)


def _verify_runtime_sources(model, operation, sources, modules) -> None:
    implementation = next(s for s in model.implementation_slices if s.root == operation.implementation_root)
    expected_nodes = {n.id.removeprefix("python:") for n in implementation.nodes if n.id.startswith("python:")}
    for source in sources.sources:
        module = modules[source.module]
        if Path(source.filename).read_bytes() != source.content:
            raise PortRefusal("runtime source changed after acquisition")
        code = compile(source.content, source.filename, "exec", dont_inherit=True)
        functions = {item.co_name: item for item in code.co_consts if isinstance(item, CodeType)}
        tree = ast.parse(source.content)
        for node in tree.body:
            name = node.name if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else node.targets[0].id if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) else node.target.id if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) else None
            if name is None or source.module + "." + name not in expected_nodes:
                continue
            value = getattr(module, name)
            if isinstance(node, ast.FunctionDef):
                if not inspect.isfunction(value) or value.__code__ != functions.get(name):
                    raise PortRefusal("runtime callable implementation differs: " + name)
                if hasattr(value, "__signature__") or hasattr(value, "__wrapped__"):
                    raise PortRefusal("runtime signature transformation differs: " + name)
                runtime_signature = inspect.signature(value, eval_str=True)
                parameters = runtime_signature.parameters
                annotated = [(a.arg, a.annotation) for a in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)]
                annotated.append(("return", node.returns))
                for annotation_name, annotation in annotated:
                    if annotation is None:
                        continue
                    for dependency in ast.walk(annotation):
                        if isinstance(dependency, ast.Name) and hasattr(builtins, dependency.id) and dependency.id in module.__dict__ and module.__dict__[dependency.id] is not getattr(builtins, dependency.id):
                            raise PortRefusal("runtime annotation dependency differs: " + dependency.id)
                    expected_annotation = eval(compile(ast.Expression(annotation), source.filename, "eval"), module.__dict__)
                    if isinstance(expected_annotation, str):
                        expected_annotation = eval(expected_annotation, module.__dict__)
                    actual_annotation = runtime_signature.return_annotation if annotation_name == "return" else parameters[annotation_name].annotation
                    if actual_annotation != expected_annotation:
                        raise PortRefusal("runtime callable annotation differs: " + annotation_name)
                defaults = [
                    *zip(node.args.posonlyargs + node.args.args, [None] * (len(node.args.posonlyargs + node.args.args) - len(node.args.defaults)) + list(node.args.defaults)),
                    *zip(node.args.kwonlyargs, node.args.kw_defaults),
                ]
                for argument, default in defaults:
                    actual = parameters[argument.arg].default
                    if default is None:
                        if actual is not inspect.Parameter.empty:
                            raise PortRefusal("runtime parameter default differs: " + argument.arg)
                        continue
                    try:
                        expected = ast.literal_eval(default)
                    except (ValueError, TypeError):
                        raise PortRefusal("default requires an explicit acquired correspondence: " + argument.arg) from None
                    if type(actual) is not type(expected) or actual != expected:
                        raise PortRefusal("runtime parameter default differs: " + argument.arg)
                for global_name in value.__code__.co_names:
                    if hasattr(builtins, global_name) and global_name in value.__globals__ and value.__globals__[global_name] is not getattr(builtins, global_name):
                        raise PortRefusal("runtime builtin dependency was replaced: " + global_name)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                try:
                    expected = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    raise PortRefusal("runtime determinant needs an explicit acquired correspondence: " + name) from None
                if type(value) is not type(expected) or value != expected:
                    raise PortRefusal("runtime constant determinant differs: " + name)
            else:
                raise PortRefusal("runtime owner needs an explicit acquired correspondence: " + name)
