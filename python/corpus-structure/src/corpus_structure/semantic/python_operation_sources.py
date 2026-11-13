"""Closed supplied-source extraction, with no target imports or loader discovery.

Griffe owns exposed callable shape and inherited declaration ownership. LibCST
owns lexical references and a conservative syntax projection. Static dispatch is
admitted by explicit forms; inference cardinality is never a completeness proof.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Never

import astroid.builder
import astroid.manager
import astroid.nodes
import astroid.transforms
import griffe
import libcst as cst
import libcst.matchers as matchers
from libcst.helpers import filter_node_fields
from libcst.metadata import (
    ExpressionContext,
    ExpressionContextProvider,
    MetadataWrapper,
    ParentNodeProvider,
    PositionProvider,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)

from .data_operation_model import (
    CallableParameter,
    CallableSurface,
    FactOrigin,
    ImplementationSlice,
    OpaqueBoundary,
    SemanticEdge,
    SemanticNode,
    SourceUnknown,
)
from .identity import canonical_bytes
from .types import Diagnostic, PreparationError, SourceArtifact

# Deliberately bounded static profile. Callback-taking/reflection/code-loading
# builtins require an explicit complete opaque model rather than successful inference.
_SUPPORTED_BUILTIN_CALLS = frozenset(
    {
        "abs",
        "all",
        "any",
        "bool",
        "bytes",
        "dict",
        "enumerate",
        "float",
        "frozenset",
        "int",
        "isinstance",
        "issubclass",
        "len",
        "list",
        "max",
        "min",
        "range",
        "reversed",
        "round",
        "set",
        "slice",
        "sorted",
        "str",
        "sum",
        "tuple",
        "zip",
        "ValueError",
        "TypeError",
        "RuntimeError",
        "ArithmeticError",
        "OverflowError",
        "ZeroDivisionError",
        "AssertionError",
        "NotImplementedError",
        "KeyError",
        "IndexError",
        "StopIteration",
    }
)


@dataclass(frozen=True)
class PythonSource:
    module: str
    content: bytes
    filename: str
    stub: bytes | None = None


@dataclass(frozen=True)
class PythonSourceCollection:
    sources: tuple[PythonSource, ...]
    interpreter: str = "python-3.14"
    interpretation: str = "closed-python-operations-v1"
    stub_policy: str = "source-authoritative"
    boundary_contracts: tuple[SourceArtifact, ...] = ()
    generated_interfaces: tuple[str, ...] = ()


@dataclass(frozen=True)
class PythonOperationFacts:
    metadata: bytes
    surfaces: tuple[CallableSurface, ...]
    origins: tuple[FactOrigin, ...]
    implementation: ImplementationSlice


@dataclass
class _Module:
    source: PythonSource
    wrapper: MetadataWrapper
    names: Mapping[cst.CSTNode, Any]
    positions: Mapping[cst.CSTNode, Any]
    scopes: Mapping[cst.CSTNode, Any]
    contexts: Mapping[cst.CSTNode, Any]
    parent_nodes: Mapping[cst.CSTNode, Any]
    model: griffe.Module
    bindings: astroid.nodes.Module


class _ClosedAstroidManager(astroid.manager.AstroidManager):
    """Structural model only: own every cache/transform, never bootstrap runtime objects."""

    def __init__(self) -> None:
        self.astroid_cache = {}
        self._mod_file_cache = {}
        self._failed_import_hooks = []
        self.extension_package_whitelist = set()
        self.module_denylist = set()
        self._transform = astroid.transforms.TransformVisitor()

    def bootstrap(self) -> None:
        # No inference/builtin lookup is used by this profile. A structural sentinel
        # satisfies AstroidBuilder without InspectBuilder's runtime bootstrapping.
        self.astroid_cache["builtins"] = astroid.nodes.Module("builtins")


class _ClosedAstroidBuilder(astroid.builder.AstroidBuilder):
    def _post_build(self, module, builder, encoding):
        module.file_encoding = encoding
        self._manager.cache_module(module)
        for from_node, global_names in builder._import_from_nodes:
            if from_node.modname == "__future__":
                module.future_imports.update(symbol for symbol, _ in from_node.names)
            if all(name != "*" for name, _ in from_node.names):
                self.add_from_names_to_locals(from_node, global_names)
        # delayed_assattr invokes node.infer even with transforms disabled. This
        # model deliberately leaves that runtime-like refinement to a later profile.
        return module


def _fail(location: str, message: str, code: str = "python_operation_source") -> Never:
    raise PreparationError((Diagnostic(code, location, message),))


def _literal(module: cst.Module, node: cst.CSTNode, location: str) -> Any:
    try:
        expression = ast.parse(module.code_for_node(node), mode="eval")
        for record in ast.walk(expression):
            if isinstance(record, ast.Dict):
                keys = []
                for key in record.keys:
                    if key is None:
                        _fail(location, "operation metadata cannot unpack a dynamic mapping")
                    value = ast.literal_eval(key)
                    if value in keys:
                        _fail(location, "duplicate semantic metadata field " + repr(value))
                    keys.append(value)
        return ast.literal_eval(expression)
    except PreparationError:
        raise
    except ValueError, SyntaxError, TypeError:
        _fail(location, "operation metadata must be static literal records")


def _syntax(value: Any) -> Any:
    """Keep syntax/control/literals, discard whitespace/comments and source positions."""
    if isinstance(value, cst.CSTNode):
        return {
            "node": type(value).__name__,
            "fields": {
                field.name: _syntax(getattr(value, field.name))
                for field in filter_node_fields(
                    value, show_defaults=True, show_syntax=True, show_whitespace=False
                )
            },
        }
    if isinstance(value, (list, tuple)):
        return [_syntax(item) for item in value]
    if isinstance(value, cst.MaybeSentinel):
        return {"sentinel": value.name}
    return value


class ClosedPythonSources:
    """One preparation lifetime; no module, inference-manager or target-runtime cache."""

    def __init__(self, inputs: PythonSourceCollection):
        if inputs.stub_policy != "source-authoritative":
            _fail("python/stub_policy", "unsupported source/stub policy")
        selected = inputs.generated_interfaces
        if len(selected) != len(set(selected)) or set(selected) - {
            "dataclasses",
            "dataclasses-runtime",
            "unpack-typeddict",
            "unpack-typeddict-runtime",
        }:
            _fail(
                "python/generated_interfaces",
                "unsupported or duplicate generated interface profile",
            )
        self.inputs = inputs
        self.generated: dict[str, griffe.Function] = {}
        self.generated_unknowns: dict[str, str] = {}
        self.boundary_surfaces: dict[str, CallableSurface] = {}
        self.source_fields: dict[str, dict[str, griffe.Object | griffe.Alias]] = {}
        self.binding_manager = _ClosedAstroidManager()
        self.binding_builder = _ClosedAstroidBuilder(self.binding_manager, apply_transforms=False)
        contract_names = [item.name for item in inputs.boundary_contracts]
        if len(contract_names) != len(set(contract_names)):
            _fail(
                "python/boundary_contracts", "duplicate supplied boundary interpretation contract"
            )
        self.boundary_contracts = {item.name: item for item in inputs.boundary_contracts}
        self.collection = griffe.ModulesCollection()
        self.modules: dict[str, _Module] = {}
        self.definitions: dict[str, tuple[str, cst.CSTNode]] = {}
        self.parents: dict[str, str] = {}
        self.metadata: dict[str, dict] = {}
        self.metadata_lines: dict[str, int] = {}
        self._validate_sources()
        # Seed the entire logical package hierarchy before visiting any supplied module.
        for source in sorted(
            inputs.sources, key=lambda item: (item.module.count("."), item.module)
        ):
            parts = source.module.split(".")
            for n in range(1, len(parts)):
                name = ".".join(parts[:n])
                if name not in self.collection:
                    parent = self.collection.get_member(".".join(parts[: n - 1])) if n > 1 else None
                    model = griffe.Module(parts[n - 1], parent=parent)
                    self.collection.set_member(name, model)
            parent = self.collection.get_member(".".join(parts[:-1])) if len(parts) > 1 else None
            model = griffe.visit(
                parts[-1],
                Path(source.filename),
                source.content.decode("utf-8"),
                parent=parent,
                modules_collection=self.collection,
            )
            previous = (
                self.collection.get_member(source.module)
                if source.module in self.collection
                else None
            )
            if previous is not None:
                # A supplied package initializer replaces its synthetic parent only once.
                for name, child in previous.members.items():
                    if name not in model.members:
                        model.set_member(name, child)
            self.collection.set_member(source.module, model)
            wrapper = MetadataWrapper(cst.parse_module(source.content))
            providers = wrapper.resolve_many(
                (
                    QualifiedNameProvider,
                    PositionProvider,
                    ScopeProvider,
                    ExpressionContextProvider,
                    ParentNodeProvider,
                )
            )
            module = _Module(
                source,
                wrapper,
                providers[QualifiedNameProvider],
                providers[PositionProvider],
                providers[ScopeProvider],
                providers[ExpressionContextProvider],
                providers[ParentNodeProvider],
                model,
                self.binding_builder.string_build(
                    source.content.decode("utf-8"), source.module, source.filename
                ),
            )
            self.modules[source.module] = module
            self._index(module, wrapper.module.body, source.module)
            if source.stub is not None:
                stub = griffe.visit(
                    parts[-1],
                    Path(source.filename + "i"),
                    source.stub.decode("utf-8"),
                    parent=parent,
                    modules_collection=self.collection,
                )
                self._check_stub(model, stub)
        loader = griffe.GriffeLoader(
            modules_collection=self.collection, search_paths=[], allow_inspection=False
        )
        self.unresolved_aliases, self.alias_iterations = loader.resolve_aliases(
            implicit=True, external=False, max_iterations=max(1, len(inputs.sources) + 1)
        )
        self._enrich_interfaces()

    def _enrich_interfaces(self) -> None:
        """Run selected trusted model hooks only after the supplied tree is resolved.

        Expanded Unpack parameters describe a wire boundary, not Python's actual
        **kwargs signature. Restore source functions after recording that view.
        """
        if not self.inputs.generated_interfaces:
            return
        classes = []
        functions = []

        def collect(obj):
            for member in tuple(obj.members.values()):
                if isinstance(member, griffe.Class):
                    classes.append(member)
                    self.source_fields[member.path] = dict(member.members)
                    collect(member)
                elif isinstance(member, griffe.Function):
                    functions.append(member)
                elif isinstance(member, griffe.Module):
                    collect(member)

        roots = [model for model in self.collection.members.values()]
        for model in roots:
            collect(model)
        if {"dataclasses", "dataclasses-runtime"} & set(self.inputs.generated_interfaces):
            extensions = griffe.Extensions(griffe.DataclassesExtension())
            for model in roots:
                extensions.call("on_package", pkg=model)
        if {"unpack-typeddict", "unpack-typeddict-runtime"} & set(self.inputs.generated_interfaces):
            extensions = griffe.load_extensions("unpack_typeddict")
            for cls in classes:
                extensions.call("on_class", cls=cls, loader=None)
            for func in functions:
                original_parameters = func.parameters
                original_docstring = func.docstring
                # The extension mutates both parameters and parsed documentation.
                # Use a separate parameter container and omit docs in this view.
                func.parameters = griffe.Parameters(*original_parameters)
                func.docstring = None
                try:
                    extensions.call("on_function", func=func, loader=None)
                    if tuple(func.parameters) != tuple(original_parameters):
                        self.boundary_surfaces[func.path] = self._surface(func.path, func)
                except KeyError, griffe.AliasResolutionError:
                    _fail(func.path, "Unpack boundary requires a supplied resolved TypedDict")
                finally:
                    func.parameters = original_parameters
                    func.docstring = original_docstring
        for cls in classes:
            init = cls.members.get("__init__")
            # Griffe 2.4.1 models init=False incorrectly; retain an explicit unknown.
            if (
                isinstance(init, griffe.Function)
                and init.path not in self.definitions
                and any(
                    isinstance(decorator.value, griffe.ExprCall)
                    and decorator.value.canonical_path == "dataclasses.dataclass"
                    and any(
                        isinstance(argument, griffe.ExprKeyword)
                        and argument.name == "init"
                        and str(argument.value) == "False"
                        for argument in decorator.value.arguments
                    )
                    for decorator in cls.decorators
                )
            ):
                cls.del_member("__init__")
                self.generated_unknowns[cls.path] = (
                    "selected dataclass constructor model does not support init=False"
                )
                continue
            if isinstance(init, griffe.Function) and init.path not in self.definitions:
                self.generated[init.path] = init

    def _runtime_typeddict(self, path: str) -> bool:
        if (
            "unpack-typeddict-runtime" not in self.inputs.generated_interfaces
            or path not in self.definitions
        ):
            return False
        module_name, node = self.definitions[path]
        if (
            not isinstance(node, cst.ClassDef)
            or node.decorators
            or node.keywords
            or len(node.bases) != 1
        ):
            return False
        for statement in node.body.body:
            if not isinstance(statement, cst.SimpleStatementLine):
                return False
            for value in statement.body:
                if isinstance(value, cst.AnnAssign) and value.value is None:
                    continue
                if isinstance(value, cst.Pass) or (
                    isinstance(value, cst.Expr)
                    and isinstance(value.value, (cst.SimpleString, cst.ConcatenatedString))
                ):
                    continue
                return False
        module = self.modules[module_name]
        names = module.names.get(node.bases[0].value, set())
        names = names() if callable(names) else names
        return {name.name for name in names} == {"typing.TypedDict"}

    def _runtime_dataclass(self, path: str) -> bool:
        if (
            "dataclasses-runtime" not in self.inputs.generated_interfaces
            or path not in self.definitions
        ):
            return False
        module_name, node = self.definitions[path]
        if not isinstance(node, cst.ClassDef) or node.keywords:
            return False
        module = self.modules[module_name]
        for statement in node.body.body:
            if isinstance(statement, cst.FunctionDef):
                if statement.decorators or statement.name.value.startswith("__"):
                    return False
                continue
            if not isinstance(statement, cst.SimpleStatementLine):
                return False
            for value in statement.body:
                if isinstance(value, (cst.AnnAssign, cst.Pass)):
                    continue
                if isinstance(value, cst.Expr) and isinstance(
                    value.value, (cst.SimpleString, cst.ConcatenatedString)
                ):
                    continue
                return False
        if any(
            parent == path
            and isinstance(self.definitions[name][1], cst.FunctionDef)
            and name.rsplit(".", 1)[-1].startswith("__")
            for name, parent in self.parents.items()
        ):
            return False
        if len(node.decorators) != 1:
            return False
        decorator = node.decorators[0].decorator
        function = decorator.func if isinstance(decorator, cst.Call) else decorator
        names = module.names.get(function, set())
        names = names() if callable(names) else names
        if {name.name for name in names} != {"dataclasses.dataclass"}:
            return False
        if isinstance(decorator, cst.Call):
            for arg in decorator.args:
                if arg.keyword is None or arg.keyword.value not in {"kw_only", "frozen", "init"}:
                    return False
                if not isinstance(arg.value, cst.Name) or arg.value.value not in {"True", "False"}:
                    return False
                if arg.keyword.value == "init" and arg.value.value != "True":
                    return False
        return True

    def _runtime_dataclass_field(self, path: str, value) -> bool:
        if not self._runtime_dataclass(path.rsplit(".", 1)[0]) or not isinstance(value, cst.Call):
            return False
        module_name, _ = self.definitions[path]
        module = self.modules[module_name]
        names = module.names.get(value.func, set())
        names = names() if callable(names) else names
        return {name.name for name in names} == {"dataclasses.field"} and all(
            arg.keyword is not None
            and arg.keyword.value in {"default", "default_factory", "kw_only"}
            for arg in value.args
        )

    @staticmethod
    def _expression(value: str | griffe.Expr | None) -> Any:
        if value is None or isinstance(value, str):
            return value
        if isinstance(value, griffe.ExprName):
            return {
                "expression": type(value).__name__,
                "source": str(value),
                "reference": value.reference_path,
            }
        return {
            "expression": type(value).__name__,
            "parts": [ClosedPythonSources._expression(part) for part in value.iterate(flat=False)],
        }

    def _generated_record(self, func: griffe.Function) -> dict:
        return {
            "declaration": func.path,
            "origin": "modeled",
            "parameters": [
                {
                    "name": parameter.name,
                    "kind": parameter.kind.value if parameter.kind is not None else None,
                    "annotation": self._expression(parameter.annotation),
                    "default": self._expression(parameter.default),
                }
                for parameter in func.parameters
            ],
            "returns": self._expression(func.returns),
        }

    def _validate_sources(self) -> None:
        names = [source.module for source in self.inputs.sources]
        if len(names) != len(set(names)):
            _fail("python/sources", "duplicate supplied logical module")
        for source in self.inputs.sources:
            if not source.module or not all(
                part.isidentifier() for part in source.module.split(".")
            ):
                _fail(source.filename, "invalid logical Python module")
            try:
                source.content.decode("utf-8")
            except UnicodeDecodeError:
                _fail(source.filename, "supplied sources must use UTF-8")

    def _check_stub(self, source: griffe.Object, stub: griffe.Object) -> None:
        for name, member in stub.members.items():
            actual = source.members.get(name)
            if actual is None:
                _fail(stub.path + "." + name, "stub member is absent from authoritative source")
            if isinstance(member, griffe.Function) and isinstance(actual, griffe.Function):
                left = self._surface(actual.path, actual)
                right = self._surface(actual.path, member)
                if (left.parameters, left.returns) != (right.parameters, right.returns):
                    _fail(actual.path, "source/stub callable disagreement")
            elif isinstance(member, griffe.Class) and isinstance(actual, griffe.Class):
                self._check_stub(actual, member)

    def _index(self, module: _Module, body, prefix: str) -> None:
        for statement in body:
            if isinstance(statement, (cst.ClassDef, cst.FunctionDef)):
                path = prefix + "." + statement.name.value
                self.definitions[path] = (module.source.module, statement)
                self.parents[path] = prefix
                nested = (
                    statement.body.body if isinstance(statement.body, cst.IndentedBlock) else ()
                )
                self._index(
                    module,
                    nested,
                    path + (".<locals>" if isinstance(statement, cst.FunctionDef) else ""),
                )
            if isinstance(statement, cst.SimpleStatementLine):
                for small in statement.body:
                    if isinstance(small, cst.AnnAssign) and isinstance(small.target, cst.Name):
                        name = small.target.value
                        if name == "__data_operation__" or name.endswith("__data_operation__"):
                            owner = (
                                prefix
                                if name == "__data_operation__"
                                else prefix + "." + name.removesuffix("__data_operation__")
                            )
                            if owner in self.metadata or small.value is None:
                                _fail(owner, "operation metadata requires one literal value")
                            self.metadata[owner] = _literal(
                                module.wrapper.module, small.value, owner
                            )
                            self.metadata_lines[owner] = module.positions[small].start.line
                            continue
                        assignment_path = prefix + "." + small.target.value
                        self.definitions[assignment_path] = (module.source.module, small)
                        self.parents[assignment_path] = prefix
                    if not isinstance(small, cst.Assign):
                        continue
                    for target in small.targets:
                        if isinstance(target.target, cst.Name):
                            path = prefix + "." + target.target.value
                            if target.target.value == "__data_operation__":
                                self.metadata[prefix] = _literal(
                                    module.wrapper.module, small.value, path
                                )
                                self.metadata_lines[prefix] = module.positions[small].start.line
                            elif target.target.value.endswith("__data_operation__"):
                                owner = (
                                    prefix
                                    + "."
                                    + target.target.value.removesuffix("__data_operation__")
                                )
                                if owner in self.metadata:
                                    _fail(owner, "duplicate operation metadata owner")
                                self.metadata[owner] = _literal(
                                    module.wrapper.module, small.value, owner
                                )
                                self.metadata_lines[owner] = module.positions[small].start.line
                            else:
                                self.definitions[path] = (module.source.module, small)
                                self.parents[path] = prefix
                        elif isinstance(target.target, cst.Attribute) and matchers.matches(
                            target.target,
                            matchers.Attribute(attr=matchers.Name("__data_operation__")),
                        ):
                            owner = module.wrapper.module.code_for_node(target.target.value)
                            path = prefix + "." + owner
                            if path in self.metadata:
                                _fail(path, "duplicate operation metadata owner")
                            self.metadata[path] = _literal(module.wrapper.module, small.value, path)
                            self.metadata_lines[path] = module.positions[small].start.line
        for path, metadata in self.metadata.items():
            if not isinstance(metadata, dict):
                _fail(path, "operation metadata must be a mapping")

    def resolve(self, path: str) -> griffe.Object:
        try:
            module_name = self._module_for(path)
            obj = self.modules[module_name].model
            suffix = path.removeprefix(module_name).removeprefix(".")
            for name in suffix.split(".") if suffix else ():
                if isinstance(obj, griffe.Alias):
                    obj = obj.final_target
                obj = obj.all_members[name] if isinstance(obj, griffe.Class) else obj.members[name]
            return obj.final_target if isinstance(obj, griffe.Alias) else obj
        except (KeyError, griffe.AliasResolutionError, griffe.CyclicAliasError) as exc:
            _fail(path, "reference is outside the supplied source collection: " + str(exc))

    def _surface(self, exposed: str, obj: griffe.Function) -> CallableSurface:
        return CallableSurface(
            exposed,
            obj.path,
            tuple(
                CallableParameter(
                    p.name,
                    p.kind.value if p.kind is not None else "positional or keyword",
                    str(p.annotation) if p.annotation is not None else None,
                    str(p.default) if p.default is not None else None,
                )
                for p in obj.parameters
            ),
            str(obj.returns) if obj.returns is not None else None,
            tuple(
                canonical_bytes(
                    {
                        "parameters": [
                            {
                                "name": p.name,
                                "kind": p.kind.value
                                if p.kind is not None
                                else "positional or keyword",
                                "annotation": str(p.annotation) if p.annotation else None,
                                "default": str(p.default) if p.default is not None else None,
                            }
                            for p in overload.parameters
                        ],
                        "returns": str(overload.returns) if overload.returns else None,
                    }
                )
                for overload in obj.overloads or ()
            ),
        )

    def kind_facts(self, reference: str) -> dict:
        obj = self.resolve(reference)
        if not isinstance(obj, griffe.Class):
            _fail(reference, "Python kind owner must be a supplied typed class")
        lineage = []
        unknowns = []
        seen = set()
        active = set()

        def ancestors(cls):
            if cls.path in active:
                _fail(cls.path, "cyclic inherited Python kind")
            if cls.path in seen:
                return
            seen.add(cls.path)
            active.add(cls.path)
            lineage.append(cls)
            for base in cls.bases:
                target = getattr(base, "canonical_path", None) or str(base)
                if target in {"object", "builtins.object"} or (
                    self._runtime_typeddict(cls.path) and target == "typing.TypedDict"
                ):
                    continue
                if "." not in target:
                    target = self._module_for(cls.path) + "." + target
                try:
                    parent = self.resolve(target)
                except PreparationError:
                    unknowns.append(
                        {
                            "source": reference,
                            "location": cls.path,
                            "reason": "required inherited kind base is unavailable: " + target,
                            "required": True,
                        }
                    )
                    continue
                if not isinstance(parent, griffe.Class):
                    unknowns.append(
                        {
                            "source": reference,
                            "location": cls.path,
                            "reason": "unsupported inherited kind base: " + target,
                            "required": True,
                        }
                    )
                    continue
                ancestors(parent)
            active.remove(cls.path)

        ancestors(obj)
        if not unknowns:
            try:
                lineage = [obj] if self._runtime_typeddict(obj.path) else [obj, *obj.mro()]
            except (ValueError, griffe.AliasResolutionError) as exc:
                _fail(reference, "unsupported inherited Python kind MRO: " + str(exc))
        else:
            lineage = [obj]  # Explicit partial local evidence, never an admitted effective kind.
        effective = {}
        seen_members = set()
        for cls in lineage:
            fields = (
                self.source_fields.get(cls.path, cls.members)
                if "typed-dict" in cls.labels
                else cls.members
            )
            for name, member in sorted(fields.items()):
                if name in seen_members:
                    continue
                seen_members.add(name)
                try:
                    actual = member.final_target if isinstance(member, griffe.Alias) else member
                except griffe.AliasResolutionError:
                    unknowns.append(
                        {
                            "source": reference,
                            "location": cls.path + "." + name,
                            "reason": "required kind member alias is unresolved",
                            "required": True,
                        }
                    )
                    continue
                if isinstance(actual, griffe.Attribute) and "property" in actual.labels:
                    unknowns.append(
                        {
                            "source": reference,
                            "location": actual.path,
                            "reason": "computed descriptor kind field requires "
                            "a declared analysis model",
                            "required": True,
                        }
                    )
                    continue
                if isinstance(actual, griffe.Attribute) and not name.startswith("_"):
                    effective[name] = {
                        "name": name,
                        "annotation": (
                            str(actual.annotation)
                            .removeprefix("NotRequired[")
                            .removeprefix("Required[")[:-1]
                            if self._runtime_typeddict(cls.path)
                            and str(actual.annotation).startswith(("NotRequired[", "Required["))
                            else str(actual.annotation)
                            if actual.annotation
                            else None
                        ),
                        "default": str(actual.value) if actual.value is not None else None,
                        "owner": actual.path,
                        **(
                            {
                                "annotation_expression": self._expression(actual.annotation),
                                "default_expression": self._expression(actual.value),
                                "labels": sorted(actual.labels),
                            }
                            if self.inputs.generated_interfaces
                            else {}
                        ),
                    }
        kind_surfaces = tuple(
            self._surface(cls.path + "." + name, member)
            for cls in lineage
            for name, member in sorted(cls.members.items())
            if isinstance(member, griffe.Function)
        )
        source_slice = self.implementation_slice(reference, kind_surfaces, (), ())
        unknowns.extend(
            {
                "source": item.source,
                "location": item.location,
                "reason": item.reason,
                "required": item.required,
            }
            for item in source_slice.unknowns
        )
        generated = {}
        if reference in self.generated_unknowns:
            unknowns.append(
                {
                    "source": reference,
                    "location": reference,
                    "reason": self.generated_unknowns[reference],
                    "required": True,
                }
            )
        if self.inputs.generated_interfaces:
            constructor = next(
                (cls.members["__init__"] for cls in lineage if "__init__" in cls.members), None
            )
            generated = {
                "generated_interfaces": sorted(self.inputs.generated_interfaces),
                "constructor": self._generated_record(constructor)
                if isinstance(constructor, griffe.Function) and constructor.path in self.generated
                else None,
            }
        return {
            **generated,
            "python": reference,
            "fields": [effective[name] for name in sorted(effective)],
            "owned_definition": source_slice.semantic_records(),
            "bases": [str(base) for base in obj.bases],
            "decorators": [str(d.value) for d in obj.decorators],
            "complete": not unknowns,
            "unknowns": unknowns,
        }

    def operations(self) -> tuple[PythonOperationFacts, ...]:
        results = []
        for exposed in sorted(self.metadata):
            obj = self.resolve(exposed)
            metadata: dict = {}
            field_owners: dict[str, str] = {}
            if isinstance(obj, griffe.Class):
                try:
                    for base in reversed(obj.mro()):
                        metadata.update(self.metadata.get(base.path, {}))
                        field_owners.update(
                            {field: base.path for field in self.metadata.get(base.path, {})}
                        )
                except griffe.AliasResolutionError, ValueError:
                    pass  # Unsupported bases are visible to slice admission below.
            metadata.update(self.metadata[exposed])
            field_owners.update({field: exposed for field in self.metadata[exposed]})
            if metadata.get("abstract", False):
                continue
            surfaces = []
            if isinstance(obj, griffe.Function):
                if "entrypoints" in metadata:
                    _fail(
                        exposed,
                        "a function operation supplies its own callable; entrypoints are redundant",
                    )
                surfaces.append(self._surface(exposed, obj))
            elif isinstance(obj, griffe.Class):
                for name in metadata.get("entrypoints", ("run",)):
                    member = self.resolve(exposed + "." + name)
                    if not isinstance(member, griffe.Function):
                        _fail(exposed + "." + name, "operation entrypoint must be callable")
                    surfaces.append(self._surface(exposed + "." + name, member))
            else:
                _fail(exposed, "metadata must attach to a function or class definition")
            origins = tuple(
                FactOrigin(
                    field,
                    "authored",
                    self.modules[self._module_for(field_owners[field])].source.filename,
                    field_owners[field],
                    exposed,
                    self.metadata_lines.get(field_owners[field]),
                )
                for field in metadata
            )
            origins += tuple(
                FactOrigin(
                    "callable",
                    "modeled" if s.declaration in self.generated else "extracted",
                    self.modules[self._module_for(s.declaration)].source.filename,
                    s.declaration,
                    s.exposed,
                    self.resolve(s.declaration).lineno,
                )
                for s in surfaces
            )
            # Asset custody uses only the same explicitly supplied immutable contracts
            # as opaque implementation boundaries; a name is never ambient authority.
            if "assets" in metadata:
                metadata["assets"] = [
                    {
                        **asset,
                        **(
                            {"content_digest": self.boundary_contracts[asset["contract"]].digest}
                            if asset.get("content_digest") is None
                            and asset.get("contract") in self.boundary_contracts
                            else {}
                        ),
                    }
                    for asset in metadata["assets"]
                ]
            boundaries = tuple(
                OpaqueBoundary(**boundary) for boundary in metadata.get("opaque", ())
            )
            boundaries = tuple(
                replace(boundary, content_digest=self.boundary_contracts[boundary.contract].digest)
                if boundary.content_digest is None and boundary.contract in self.boundary_contracts
                else boundary
                for boundary in boundaries
            )
            bound_inputs = tuple(metadata.get("bound_inputs", ()))
            supplied_parameters = {
                parameter.name for surface in surfaces for parameter in surface.parameters
            }
            if not set(bound_inputs) <= supplied_parameters:
                _fail(exposed, "bound input declarations must name actual callable parameters")
            implementation = self.implementation_slice(
                exposed, tuple(surfaces), boundaries, bound_inputs
            )
            role_parameters = {
                role.get("parameter")
                for role in metadata.get("roles", ())
                if role.get("direction") == "input"
            }
            unbound = tuple(
                SourceUnknown(
                    exposed,
                    exposed,
                    "bound object input lacks a canonical semantic input role: " + name,
                )
                for name in bound_inputs
                if name not in role_parameters
            )
            if unbound:
                implementation = replace(
                    implementation, unknowns=(*implementation.unknowns, *unbound)
                )
            results.append(
                PythonOperationFacts(
                    canonical_bytes(metadata), tuple(surfaces), origins, implementation
                )
            )
        return tuple(results)

    def _closed_alias_binding(self, path: str) -> bool:
        """Refine only direct single-assignment aliases using Astroid's native protocol."""
        module_name = self._module_for(path)
        scope = self.modules[module_name].bindings
        parts = path.removeprefix(module_name + ".").split(".")
        for part in parts[:-1]:
            declarations = scope.locals.get(part, ())
            if len(declarations) != 1 or not isinstance(
                declarations[0], (astroid.nodes.ClassDef, astroid.nodes.FunctionDef)
            ):
                return False
            scope = declarations[0]

        def terminal(name: str, active: set[str]) -> bool:
            if name in active:
                return False
            declarations = scope.locals.get(name, ())
            if len(declarations) != 1:
                return False
            binding = declarations[0]
            if isinstance(
                binding,
                (
                    astroid.nodes.FunctionDef,
                    astroid.nodes.ClassDef,
                    astroid.nodes.Import,
                    astroid.nodes.ImportFrom,
                ),
            ):
                return True  # The supplied definition/import boundary is independently closed.
            if not isinstance(binding, astroid.nodes.AssignName):
                return False
            assignment = binding.parent
            if not isinstance(assignment, (astroid.nodes.Assign, astroid.nodes.AnnAssign)):
                return False
            if isinstance(assignment, astroid.nodes.Assign) and (
                len(assignment.targets) != 1 or assignment.targets[0] is not binding
            ):
                return False
            if isinstance(assignment.value, astroid.nodes.Name):
                targets = tuple(binding.assigned_stmts())
                if len(targets) != 1 or not isinstance(targets[0], astroid.nodes.Name):
                    return False
                target = targets[0].name
                if target in scope.locals:
                    return terminal(target, active | {name})
                return target in _SUPPORTED_BUILTIN_CALLS

            def immutable(node):
                return isinstance(node, astroid.nodes.Const) or (
                    isinstance(node, astroid.nodes.Tuple)
                    and all(immutable(item) for item in node.elts)
                )

            return immutable(assignment.value)

        return terminal(parts[-1], set())

    def _module_for(self, path: str) -> str:
        candidates = [name for name in self.modules if path == name or path.startswith(name + ".")]
        if not candidates:
            _fail(path, "reference is outside the supplied source collection")
        return max(candidates, key=len)

    def implementation_slice(
        self,
        exposed: str,
        surfaces: tuple[CallableSurface, ...],
        boundaries: tuple[OpaqueBoundary, ...],
        bound_inputs: tuple[str, ...],
    ) -> ImplementationSlice:
        root = "python:" + exposed
        nodes: dict[str, SemanticNode] = {}
        edges: set[SemanticEdge] = set()
        unknowns: set[SourceUnknown] = set()
        used_boundaries: set[OpaqueBoundary] = set()
        todo = [surface.declaration for surface in surfaces]
        receiver = self.resolve(exposed)
        if isinstance(receiver, griffe.Class):
            todo.append(exposed)
        else:
            nodes[root] = SemanticNode(
                root, "implementation_entry", canonical_bytes({"entry": exposed})
            )
        for surface in surfaces:
            edges.add(
                SemanticEdge(
                    root, "python:" + surface.declaration, "resolved_definition", surface.exposed
                )
            )

        def boundary_for(reference: str) -> OpaqueBoundary | None:
            matches = [
                b
                for b in boundaries
                if reference == b.reference or reference.startswith(b.reference + ".")
            ]
            return max(matches, key=lambda b: len(b.reference)) if matches else None

        def reference(path: str, target: str, relation: str, location: str) -> None:
            if "unpack-typeddict-runtime" in self.inputs.generated_interfaces and target in {
                "typing.TypedDict",
                "typing.Unpack",
                "typing.NotRequired",
                "typing.Required",
            }:
                return
            boundary = boundary_for(target)
            if boundary is not None:
                if not boundary.contract or not boundary.role:
                    _fail(
                        location,
                        "opaque dependencies require an explicit contract and semantic role",
                    )
                used_boundaries.add(boundary)
                if boundary.content_digest is None:
                    unknowns.add(
                        SourceUnknown(
                            path,
                            location,
                            "opaque contract lacks a supplied immutable revision: "
                            + boundary.contract,
                        )
                    )
                target_id = "opaque:" + boundary.reference
                nodes[target_id] = SemanticNode(
                    target_id,
                    "opaque_dependency",
                    canonical_bytes(
                        {
                            "reference": boundary.reference,
                            "contract": boundary.contract,
                            "role": boundary.role,
                            "content_digest": boundary.content_digest,
                        }
                    ),
                )
                edges.add(SemanticEdge("python:" + path, target_id, relation, target))
                return
            try:
                obj = self.resolve(target)
                target = obj.path
            except PreparationError:
                unknowns.add(
                    SourceUnknown(path, location, "unresolved required reference " + target)
                )
                return
            if target in self.definitions:
                todo.append(target)
                edges.add(SemanticEdge("python:" + path, "python:" + target, relation))
            else:
                unknowns.add(
                    SourceUnknown(path, location, "definition has no supplied body " + target)
                )

        visited: set[str] = set()

        def process_definition(path: str) -> None:
            node_id = "python:" + path
            if path in visited:
                return
            visited.add(path)
            if path in self.generated:
                nodes[node_id] = SemanticNode(
                    node_id,
                    "modeled_generated_callable",
                    canonical_bytes(self._generated_record(self.generated[path])),
                )
                owner = path.rsplit(".", 1)[0]
                todo.append(owner)
                edges.add(SemanticEdge(node_id, "python:" + owner, "implementation_determinant"))
                if not (self._runtime_dataclass(owner) or self._runtime_typeddict(owner)):
                    unknowns.add(
                        SourceUnknown(
                            path,
                            path,
                            "generated constructor runtime behavior requires "
                            "an admitted analysis model",
                        )
                    )
                return
            if path not in self.definitions:
                unknowns.add(SourceUnknown(path, path, "entrypoint body is not supplied"))
                return
            module_name, node = self.definitions[path]
            module = self.modules[module_name]
            location = module.source.filename + ":" + str(module.positions[node].start.line)
            if isinstance(node, cst.ClassDef):
                # Class configuration and bases are determinants.
                # Methods enter through calls or declared entrypoints.
                payload = {
                    "name": node.name.value,
                    "bases": _syntax(node.bases),
                    "decorators": _syntax(node.decorators),
                    "keywords": _syntax(node.keywords),
                }
                if self.inputs.generated_interfaces:
                    init = self.generated.get(path + ".__init__")
                    if init is not None:
                        payload["generated_constructor"] = self._generated_record(init)
                nodes[node_id] = SemanticNode(node_id, "python_class", canonical_bytes(payload))
                for child, parent in self.parents.items():
                    if parent == path and not isinstance(
                        self.definitions[child][1], (cst.ClassDef, cst.FunctionDef)
                    ):
                        todo.append(child)
                        edges.add(
                            SemanticEdge(node_id, "python:" + child, "implementation_determinant")
                        )

                runtime_dataclass = self._runtime_dataclass(path)

                class HeaderReferences(cst.CSTVisitor):
                    def visit_Name(self, node: cst.Name) -> None:
                        candidates = module.names.get(node, set())
                        candidates = candidates() if callable(candidates) else candidates
                        for candidate in candidates:
                            if candidate.source == QualifiedNameSource.BUILTIN:
                                continue
                            target = (
                                candidate.name
                                if candidate.source == QualifiedNameSource.IMPORT
                                else module_name + "." + candidate.name
                            )
                            if target != path and not (
                                runtime_dataclass and target == "dataclasses.dataclass"
                            ):
                                reference(path, target, "implementation_determinant", location)

                for header in (*node.decorators, *node.bases, *node.keywords):
                    header.visit(HeaderReferences())
                if (node.decorators or node.keywords) and not self._runtime_dataclass(path):
                    unknowns.add(
                        SourceUnknown(
                            path,
                            location,
                            "class decorator/metaclass transformation requires "
                            "an admitted analysis model",
                        )
                    )
                try:
                    cls = self.resolve(path)
                    assert isinstance(cls, griffe.Class)
                    for base in cls.bases:
                        target = getattr(base, "canonical_path", None) or str(base)
                        if self._runtime_typeddict(path) and target == "typing.TypedDict":
                            continue
                        reference(
                            path,
                            target if "." in target else module_name + "." + target,
                            "inherits",
                            location,
                        )
                except PreparationError, griffe.AliasResolutionError, ValueError:
                    unknowns.add(SourceUnknown(path, location, "unresolved class base"))
                return
            nodes[node_id] = SemanticNode(
                node_id, "python_definition", canonical_bytes(_syntax(node))
            )
            if isinstance(node, cst.FunctionDef) and node.decorators:
                unknowns.add(
                    SourceUnknown(
                        path,
                        location,
                        "function decorator requires an admitted "
                        "callable-surface transformation model",
                    )
                )
            if isinstance(node, (cst.Assign, cst.AnnAssign)) and node.value is not None:
                try:
                    constant = ast.literal_eval(module.wrapper.module.code_for_node(node.value))

                    def immutable(value):
                        return isinstance(
                            value, (str, bytes, int, float, complex, bool, type(None))
                        ) or (isinstance(value, tuple) and all(immutable(item) for item in value))

                    admitted_constant = immutable(constant)
                except ValueError, SyntaxError:
                    # An explicitly modeled external definition is a closed boundary;
                    # arbitrary constructor results and aliases are not frozen values.
                    candidates = module.names.get(node.value, set())
                    candidates = candidates() if callable(candidates) else candidates
                    admitted_constant = bool(candidates) and all(
                        boundary_for(candidate.name) is not None for candidate in candidates
                    )
                    if isinstance(node.value, cst.Name):
                        admitted_constant = self._closed_alias_binding(path)
                        # Supplied definition aliases are checked through their own nodes;
                        # unsupported builtin aliases cannot hide a dynamic call target.
                admitted_constant = admitted_constant or self._runtime_dataclass_field(
                    path, node.value
                )
                if not admitted_constant:
                    unknowns.add(
                        SourceUnknown(
                            path,
                            location,
                            "captured global/class value is not known immutable; "
                            "requires an explicit boundary",
                        )
                    )
            seen_names: set[tuple[str, str]] = set()

            extractor = self
            value_methods = {
                "builtins.str": {
                    **dict.fromkeys(
                        (
                            "lower",
                            "upper",
                            "casefold",
                            "strip",
                            "lstrip",
                            "rstrip",
                            "replace",
                            "join",
                            "removeprefix",
                            "removesuffix",
                            "capitalize",
                            "title",
                            "swapcase",
                            "format",
                            "format_map",
                        ),
                        "builtins.str",
                    ),
                    **dict.fromkeys(
                        (
                            "startswith",
                            "endswith",
                            "isalpha",
                            "isalnum",
                            "isdigit",
                            "isspace",
                            "isdecimal",
                            "isnumeric",
                            "islower",
                            "isupper",
                        ),
                        "builtins.bool",
                    ),
                    **dict.fromkeys(("find", "rfind", "index", "rindex", "count"), "builtins.int"),
                    **dict.fromkeys(("split", "rsplit", "splitlines"), "builtins.list"),
                    "partition": "builtins.tuple",
                    "rpartition": "builtins.tuple",
                    "encode": "builtins.bytes",
                },
                "builtins.bytes": {
                    "decode": "builtins.str",
                    "hex": "builtins.str",
                    "count": "builtins.int",
                    "find": "builtins.int",
                },
                "builtins.int": {
                    "bit_count": "builtins.int",
                    "bit_length": "builtins.int",
                    "to_bytes": "builtins.bytes",
                },
                "builtins.float": {
                    "hex": "builtins.str",
                    "is_integer": "builtins.bool",
                    "as_integer_ratio": "builtins.tuple",
                },
                "builtins.tuple": {"count": "builtins.int", "index": "builtins.int"},
                "builtins.list": {
                    "count": "builtins.int",
                    "index": "builtins.int",
                    "copy": "builtins.list",
                },
                "builtins.dict": {
                    "get": None,
                    "items": None,
                    "keys": None,
                    "values": None,
                    "copy": "builtins.dict",
                },
                "builtins.set": {
                    "issubset": "builtins.bool",
                    "issuperset": "builtins.bool",
                    "isdisjoint": "builtins.bool",
                    "union": "builtins.set",
                    "intersection": "builtins.set",
                    "difference": "builtins.set",
                },
            }

            def annotated_value(annotation) -> tuple[str, tuple[str, ...]]:
                """Nominal data provenance, distinct from class/function objects."""
                if annotation is None:
                    return "unknown", ()
                if isinstance(annotation, cst.Annotation):
                    annotation = annotation.annotation
                if isinstance(annotation, cst.CSTNode):
                    lookup = (
                        annotation.value if isinstance(annotation, cst.Subscript) else annotation
                    )
                    candidates = module.names.get(lookup, set())
                    candidates = candidates() if callable(candidates) else candidates
                    names = [
                        candidate.name
                        if candidate.source != QualifiedNameSource.LOCAL
                        else module_name + "." + candidate.name
                        for candidate in candidates
                    ]
                    if not names:
                        text = module.wrapper.module.code_for_node(annotation)
                        with suppress(ValueError, SyntaxError):
                            text = ast.literal_eval(text)
                        names = [text] if isinstance(text, str) else []
                else:
                    names = [getattr(annotation, "canonical_path", None) or str(annotation)]
                outcomes = []
                for name in names:
                    name = name.removeprefix("builtins.")
                    # Generic containers retain container operations, not arbitrary
                    # attributes of an unknown element returned by indexing/get.
                    primitive = name.split("[", 1)[0]
                    if primitive in {
                        "str",
                        "int",
                        "float",
                        "bool",
                        "bytes",
                        "tuple",
                        "list",
                        "dict",
                        "set",
                        "frozenset",
                    }:
                        outcomes.append(("value", ("builtins." + primitive,)))
                        continue
                    try:
                        obj = extractor.resolve(name if "." in name else module_name + "." + name)
                    except PreparationError:
                        return "unknown", ()
                    if not isinstance(obj, griffe.Class):
                        return "unknown", ()
                    outcomes.append(("instance", (obj.path,)))
                return (
                    outcomes[0]
                    if outcomes and all(item == outcomes[0] for item in outcomes)
                    else ("unknown", ())
                )

            def expression_binding(expression, active=frozenset()):
                """Resolve supported receiver provenance, never arbitrary object inference.

                Lexical referents identify direct local aliases. Attribute semantics are
                admitted separately: knowing a function does not admit reading its code.
                """
                if id(expression) in active:
                    return "unknown", ()
                active = active | {id(expression)}
                if isinstance(expression, cst.Name):
                    candidates = module.names.get(expression, set())
                    candidates = candidates() if callable(candidates) else candidates
                    targets = []
                    kinds = set()
                    for candidate in candidates:
                        if candidate.source == QualifiedNameSource.BUILTIN:
                            kinds.add("builtin")
                            continue
                        target = (
                            candidate.name
                            if candidate.source == QualifiedNameSource.IMPORT
                            else module_name + "." + candidate.name
                        )
                        if ".<locals>." in target:
                            scope = module.scopes.get(expression)
                            accesses = (
                                [a for a in scope.accesses if a.node is expression] if scope else []
                            )
                            referents = {r for a in accesses for r in a.referents}
                            if len(referents) != 1:
                                kinds.add("unknown")
                                continue
                            declaration = next(iter(referents)).node
                            if isinstance(declaration, cst.Param):
                                kind, refs = annotated_value(declaration.annotation)
                                kinds.add(kind)
                                targets.extend(refs)
                                continue
                            parent = module.parent_nodes.get(declaration)
                            if isinstance(parent, cst.AssignTarget):
                                parent = module.parent_nodes.get(parent)
                            if (
                                isinstance(parent, (cst.Assign, cst.AnnAssign))
                                and parent.value is not None
                            ):
                                kind, refs = expression_binding(parent.value, active)
                                kinds.add(kind)
                                targets.extend(refs)
                            else:
                                kinds.add("unknown")
                            continue
                        if boundary_for(target):
                            kinds.add("opaque")
                            targets.append(target)
                            continue
                        if target in self.modules:
                            kinds.add("module")
                            targets.append(target)
                            continue
                        definition = self.definitions.get(target)
                        if definition is not None and isinstance(
                            definition[1], (cst.Assign, cst.AnnAssign)
                        ):
                            kind, refs = expression_binding(definition[1].value, active)
                            kinds.add(kind)
                            targets.extend(refs)
                            continue
                        try:
                            obj = self.resolve(target)
                        except PreparationError:
                            kinds.add("unknown")
                        else:
                            kinds.add(
                                "class"
                                if isinstance(obj, griffe.Class)
                                else "callable"
                                if isinstance(obj, griffe.Function)
                                else "value"
                            )
                            targets.append(obj.path)
                    if expression.value in {"self", "cls"} and isinstance(receiver, griffe.Class):
                        return "receiver", (exposed,)
                    if not kinds:
                        return (
                            ("value", ()) if expression.value in bound_inputs else ("unknown", ())
                        )
                    return (
                        (next(iter(kinds)), tuple(targets)) if len(kinds) == 1 else ("unknown", ())
                    )
                if isinstance(expression, cst.Attribute):
                    kind, targets = expression_binding(expression.value, active)
                    if kind == "opaque":
                        return kind, targets
                    if kind == "instance":
                        results = []
                        for target in targets:
                            try:
                                cls = extractor.resolve(target)
                                member = cls.all_members.get(expression.attr.value)
                                if isinstance(member, griffe.Alias):
                                    member = member.final_target
                            except PreparationError, griffe.AliasResolutionError:
                                return "unknown", ()
                            if isinstance(member, griffe.Function):
                                unknowns.add(
                                    SourceUnknown(
                                        path,
                                        location,
                                        "nominal input method dispatch requires "
                                        "an admitted concrete receiver model",
                                    )
                                )
                                results.append(("callable", (member.path,)))
                            elif (
                                isinstance(member, griffe.Attribute)
                                and "property" not in member.labels
                            ):
                                reference(path, member.path, "implementation_determinant", location)
                                results.append(annotated_value(member.annotation))
                            else:
                                return "unknown", ()
                        return (
                            results[0]
                            if results and all(item == results[0] for item in results)
                            else ("unknown", ())
                        )
                    if kind in {"module", "class", "receiver"}:
                        results = []
                        for target in targets:
                            member = target + "." + expression.attr.value
                            if boundary_for(member):
                                return "opaque", (member,)
                            try:
                                obj = self.resolve(member)
                            except PreparationError:
                                return "unknown", ()
                            results.append(
                                (
                                    "class"
                                    if isinstance(obj, griffe.Class)
                                    else "callable"
                                    if isinstance(obj, griffe.Function)
                                    else "value",
                                    obj.path,
                                )
                            )
                        categories = {k for k, _ in results}
                        return (
                            (next(iter(categories)), tuple(t for _, t in results))
                            if len(categories) == 1
                            else ("unknown", ())
                        )
                    if kind == "value" and targets:
                        returns = [
                            value_methods.get(target, {}).get(expression.attr.value, "unsupported")
                            for target in targets
                        ]
                        if any(result == "unsupported" for result in returns):
                            return "unknown", ()
                        return "value-callable", tuple(
                            result for result in returns if result is not None
                        )
                    return "unknown", ()
                if isinstance(expression, cst.Call):
                    kind, targets = expression_binding(expression.func, active)
                    # Only the actual opaque receiver's contract covers its returned
                    # object. A boundary name nested inside an argument is irrelevant.
                    if kind == "opaque":
                        return "opaque", targets
                    return ("value", targets) if kind == "value-callable" else ("unknown", ())
                for syntax, typename in (
                    (cst.Integer, "int"),
                    (cst.Float, "float"),
                    (cst.SimpleString, "str"),
                    (cst.Tuple, "tuple"),
                ):
                    if isinstance(expression, syntax):
                        return "value", ("builtins." + typename,)
                return "unknown", ()

            extractor = self

            class References(cst.CSTVisitor):
                def visit_Name(self, node: cst.Name) -> None:
                    candidates = module.names.get(node, set())
                    candidates = candidates() if callable(candidates) else candidates
                    parent = module.parent_nodes.get(node)
                    imported_name = isinstance(
                        parent, (cst.ImportAlias, cst.ImportFrom, cst.Import)
                    )
                    if (
                        not candidates
                        and module.contexts.get(node) == ExpressionContext.LOAD
                        and not imported_name
                        and node.value not in {"None", "True", "False", "Ellipsis"}
                    ):
                        unknowns.add(
                            SourceUnknown(
                                path, location, "unresolved required load name " + node.value
                            )
                        )
                    if module.contexts.get(node) == ExpressionContext.LOAD:
                        kind, _ = expression_binding(node)
                        allowed = (
                            (isinstance(parent, cst.Attribute) and parent.value is node)
                            or (isinstance(parent, cst.Call) and parent.func is node)
                            or (
                                isinstance(parent, (cst.Assign, cst.AnnAssign))
                                and parent.value is node
                            )
                        )
                        ancestor_for_use = parent
                        while ancestor_for_use is not None and not isinstance(
                            ancestor_for_use, (cst.SimpleStatementLine, cst.FunctionDef)
                        ):
                            if isinstance(ancestor_for_use, cst.Annotation):
                                allowed = True
                                break
                            ancestor_for_use = module.parent_nodes.get(ancestor_for_use)
                        if (
                            kind
                            in {
                                "callable",
                                "class",
                                "module",
                                "opaque",
                                "receiver",
                                "value-callable",
                            }
                            and not allowed
                            and not isinstance(parent, cst.Arg)
                        ):
                            unknowns.add(
                                SourceUnknown(
                                    path,
                                    location,
                                    "callable/object escape requires an admitted use model",
                                )
                            )
                    relation = "resolved_definition"
                    ancestor = parent
                    while ancestor is not None:
                        if isinstance(ancestor, cst.Annotation):
                            relation = "type_reference"
                            break
                        if isinstance(
                            ancestor, (cst.FunctionDef, cst.ClassDef, cst.SimpleStatementLine)
                        ):
                            break
                        ancestor = module.parent_nodes.get(ancestor)
                    for candidate in candidates:
                        if candidate.source == QualifiedNameSource.BUILTIN:
                            continue
                        target = candidate.name
                        if candidate.source == QualifiedNameSource.LOCAL:
                            target = module_name + "." + target
                        if (
                            ".<locals>." in target
                            or target == path
                            or (target, relation) in seen_names
                        ):
                            continue
                        seen_names.add((target, relation))
                        reference(path, target, relation, location)

                def visit_Attribute(self, node: cst.Attribute) -> None:
                    if module.contexts.get(node) in {
                        ExpressionContext.STORE,
                        ExpressionContext.DEL,
                    }:
                        receiver_kind, _ = expression_binding(node.value)
                        if receiver_kind in {"callable", "class", "module", "opaque"}:
                            unknowns.add(
                                SourceUnknown(
                                    path,
                                    location,
                                    "captured object mutation requires an admitted model",
                                )
                            )
                    if module.contexts.get(node) == ExpressionContext.LOAD:
                        kind, targets = expression_binding(node)
                        if kind == "unknown":
                            unknowns.add(
                                SourceUnknown(
                                    path,
                                    location,
                                    "unsupported observable attribute access "
                                    + module.wrapper.module.code_for_node(node),
                                )
                            )
                        if kind != "value-callable":
                            for target in targets:
                                if not target.startswith("builtins."):
                                    reference(path, target, "implementation_determinant", location)
                    if (
                        isinstance(node.value, cst.Name)
                        and node.value.value in {"self", "cls"}
                        and isinstance(receiver, griffe.Class)
                    ):
                        reference(
                            path,
                            exposed + "." + node.attr.value,
                            "implementation_determinant",
                            location,
                        )

                def visit_Call(self, node: cst.Call) -> bool | None:
                    if extractor._runtime_dataclass_field(path, node):
                        for arg in node.args:
                            assert arg.keyword is not None
                            if arg.keyword.value == "default_factory":
                                names = module.names.get(arg.value, set())
                                names = names() if callable(names) else names
                                if len(names) != 1:
                                    unknowns.add(
                                        SourceUnknown(
                                            path,
                                            location,
                                            "dataclass factory requires one captured target",
                                        )
                                    )
                                for candidate in names:
                                    target = (
                                        candidate.name
                                        if candidate.source == QualifiedNameSource.IMPORT
                                        else module_name + "." + candidate.name
                                    )
                                    reference(path, target, "implementation_determinant", location)
                            else:
                                try:
                                    ast.literal_eval(module.wrapper.module.code_for_node(arg.value))
                                except ValueError, SyntaxError:
                                    unknowns.add(
                                        SourceUnknown(
                                            path,
                                            location,
                                            "dataclass field option requires a literal",
                                        )
                                    )
                        return False
                    expression = node.func
                    text = module.wrapper.module.code_for_node(expression)
                    first = text.split(".")[0]
                    if any(argument.star == "**" for argument in node.args):
                        unknowns.add(
                            SourceUnknown(
                                path,
                                location,
                                "expanded keyword call arguments require an admitted "
                                "static binding model",
                            )
                        )
                    if any(
                        argument.keyword is not None and argument.keyword.value == "key"
                        for argument in node.args
                    ):
                        unknowns.add(
                            SourceUnknown(
                                path,
                                location,
                                "callback-bearing key argument requires an admitted argument model",
                            )
                        )
                    callee_kind, _ = expression_binding(expression)

                    class ArgumentUses(cst.CSTVisitor):
                        def visit_Call(self, node):
                            # The nested call has its own argument admission below;
                            # its callee is invoked, not passed as an object here.
                            return False

                        def visit_Attribute(self, node):
                            kind, _ = expression_binding(node)
                            if kind in {
                                "callable",
                                "class",
                                "module",
                                "opaque",
                                "receiver",
                                "value-callable",
                                "instance",
                            }:
                                unknowns.add(
                                    SourceUnknown(
                                        path,
                                        location,
                                        "callable/object escape requires "
                                        "an admitted argument model",
                                    )
                                )
                            return False

                        def visit_Name(self, node):
                            if module.contexts.get(node) != ExpressionContext.LOAD:
                                return
                            kind, _ = expression_binding(node)
                            if kind == "receiver" and callee_kind == "opaque":
                                # The explicit prepared bridge owns this receiver's
                                # resource/configuration contract; this is not a
                                # callable escape into an arbitrary observer.
                                return
                            if kind in {
                                "callable",
                                "class",
                                "module",
                                "opaque",
                                "receiver",
                                "value-callable",
                                "instance",
                            }:
                                # Class predicates have an explicit, nonescaping type argument.
                                if text in {"isinstance", "issubclass"} and kind == "class":
                                    return
                                unknowns.add(
                                    SourceUnknown(
                                        path,
                                        location,
                                        "callable/object escape requires "
                                        "an admitted argument model",
                                    )
                                )

                    for argument in node.args:
                        argument.value.visit(ArgumentUses())
                    if isinstance(expression, cst.Name):
                        candidates = module.names.get(expression, set())
                        candidates = candidates() if callable(candidates) else candidates
                        if not candidates:
                            unknowns.add(
                                SourceUnknown(
                                    path, location, "unresolved required call target " + text
                                )
                            )
                        for candidate in candidates:
                            if (
                                candidate.source == QualifiedNameSource.BUILTIN
                                and candidate.name.rsplit(".", 1)[-1]
                                not in _SUPPORTED_BUILTIN_CALLS
                            ):
                                unknowns.add(
                                    SourceUnknown(
                                        path,
                                        location,
                                        "unsupported builtin call target " + candidate.name,
                                    )
                                )
                        local_kind, local_targets = expression_binding(expression)
                        if (
                            any(".<locals>." in candidate.name for candidate in candidates)
                            and local_kind != "callable"
                        ):
                            unknowns.add(
                                SourceUnknown(
                                    path,
                                    location,
                                    "unbound or unsupported implementation callable input " + text,
                                )
                            )
                        for target in local_targets:
                            if local_kind == "callable":
                                reference(path, target, "possible_call", location)
                        for candidate in candidates:
                            if (
                                candidate.source == QualifiedNameSource.BUILTIN
                                or ".<locals>." in candidate.name
                            ):
                                continue
                            target = (
                                candidate.name
                                if candidate.source == QualifiedNameSource.IMPORT
                                else module_name + "." + candidate.name
                            )
                            reference(path, target, "possible_call", location)
                    elif isinstance(expression, cst.Attribute):
                        if (
                            isinstance(expression.value, cst.Call)
                            and isinstance(expression.value.func, cst.Name)
                            and expression.value.func.value == "super"
                            and not expression.value.args
                            and isinstance(receiver, griffe.Class)
                        ):
                            owner = path.rsplit(".", 1)[0]
                            lineage = [receiver, *receiver.mro()]
                            index = next(
                                (n for n, cls in enumerate(lineage) if cls.path == owner), -1
                            )
                            target = next(
                                (
                                    cls.path + "." + expression.attr.value
                                    for cls in lineage[index + 1 :]
                                    if expression.attr.value in cls.members
                                ),
                                None,
                            )
                            if target is None:
                                unknowns.add(
                                    SourceUnknown(
                                        path,
                                        location,
                                        "unresolved super member " + expression.attr.value,
                                    )
                                )
                            else:
                                reference(path, target, "possible_call", location)
                            return
                        member_kind, member_targets = expression_binding(expression)
                        if member_kind == "callable":
                            for target in member_targets:
                                reference(path, target, "possible_call", location)
                        candidates = module.names.get(expression, set())
                        candidates = candidates() if callable(candidates) else candidates
                        imported = [c for c in candidates if c.source == QualifiedNameSource.IMPORT]
                        if imported:
                            for candidate in imported:
                                reference(path, candidate.name, "possible_call", location)
                        elif first not in {"self", "cls"} and first not in bound_inputs:
                            kind, targets = expression_binding(expression)
                            if kind not in {"opaque", "callable", "value-callable"}:
                                unknowns.add(
                                    SourceUnknown(
                                        path, location, "unsupported member dispatch " + text
                                    )
                                )
                            if kind != "value-callable":
                                for target in targets:
                                    reference(path, target, "possible_call", location)
                    else:
                        unknowns.add(
                            SourceUnknown(
                                path,
                                location,
                                "unsupported dynamic call target form " + type(expression).__name__,
                            )
                        )

                def visit_Global(self, node: cst.Global) -> None:
                    unknowns.add(SourceUnknown(path, location, "mutable global binding"))

                def visit_Nonlocal(self, node: cst.Nonlocal) -> None:
                    unknowns.add(SourceUnknown(path, location, "mutable closure binding"))

            node.visit(References())

        while todo:
            process_definition(todo.pop())

        # Expanded boundaries are derived views of source callables, never replacement
        # runtime signatures. Their meaning contributes to the admitted implementation.
        for surface in surfaces:
            expanded = self.boundary_surfaces.get(surface.declaration)
            if expanded is not None:
                boundary_id = "python:" + surface.declaration + "/unpack-boundary"
                nodes[boundary_id] = SemanticNode(
                    boundary_id,
                    "modeled_unpack_boundary",
                    canonical_bytes(
                        {
                            "parameters": [
                                {
                                    "name": p.name,
                                    "kind": p.kind,
                                    "annotation": p.annotation,
                                    "default": p.default,
                                }
                                for p in expanded.parameters
                            ]
                        }
                    ),
                )
                edges.add(SemanticEdge(root, boundary_id, "implementation_determinant"))

        # The interpretation contract bootstraps extraction semantics without inspecting itself.
        interpretation_id = "interpretation:" + self.inputs.interpretation
        nodes[interpretation_id] = SemanticNode(
            interpretation_id,
            "interpretation_contract",
            canonical_bytes(
                {
                    "contract": self.inputs.interpretation,
                    "interpreter": self.inputs.interpreter,
                    "stub_policy": self.inputs.stub_policy,
                    **(
                        {"generated_interfaces": sorted(self.inputs.generated_interfaces)}
                        if self.inputs.generated_interfaces
                        else {}
                    ),
                    "normalization": "python-cst-v1",
                    "binding_model": "astroid-structural-assignments-no-transforms-or-inference-v1",
                }
            ),
        )
        edges.add(SemanticEdge(root, interpretation_id, "implementation_determinant"))
        if bound_inputs:
            assumptions_id = root + "/bound-inputs"
            nodes[assumptions_id] = SemanticNode(
                assumptions_id,
                "bound_input_contract",
                canonical_bytes(
                    {
                        "parameters": sorted(bound_inputs),
                        "interpretation": self.inputs.interpretation,
                        "surfaces": [
                            {
                                "exposed": surface.exposed,
                                "parameters": [
                                    {"name": p.name, "annotation": p.annotation}
                                    for p in surface.parameters
                                    if p.name in bound_inputs
                                ],
                            }
                            for surface in surfaces
                        ],
                    }
                ),
            )
            edges.add(SemanticEdge(root, assumptions_id, "implementation_determinant"))
        return ImplementationSlice(
            root,
            tuple(nodes[key] for key in sorted(nodes)),
            tuple(sorted(edges, key=lambda e: (e.source, e.target, e.relation, e.role))),
            tuple(sorted(used_boundaries, key=lambda b: b.reference)),
            tuple(sorted(unknowns, key=lambda u: (u.source, u.location, u.reason))),
        )
