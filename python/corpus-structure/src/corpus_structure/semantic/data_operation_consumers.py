"""Immutable handoff from admitted relational binding to target consumer selection.

Selection has already happened in the binding owner. This representation exposes its
exact role pins to an admitted consumer without opening a reader or selecting again.
It grants no native publication, hydration or effect permission.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from dataclasses import dataclass
from hashlib import sha256

from .data_operation_bindings import BindingResult
from .data_operation_model import MODEL_VERSION, BoundRoleMember, ResolvedRoleBinding
from .python_operation_sources import PythonSource
from .types import SourceArtifact


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


def consumer_selection_declarations(
    sources: tuple[PythonSource, ...],
) -> tuple[SourceArtifact, ...]:
    """Extract only colocated literal selection contracts from captured source bytes.

    This explicit declaration route never imports target implementations. The
    ordinary closed compiler owns their validation and resulting semantic meaning.
    """
    import ast

    import libcst as cst

    from .identity import canonical_bytes

    class Contracts(cst.CSTVisitor):
        def __init__(self, module: cst.Module, source: PythonSource) -> None:
            self.module = module
            self.source = source
            self.operations: list[dict] = []

        def visit_ClassDef(self, node: cst.ClassDef) -> None:
            body = node.body.body if isinstance(node.body, cst.IndentedBlock) else ()
            values = []
            for statement in body:
                if not isinstance(statement, cst.SimpleStatementLine):
                    continue
                for small in statement.body:
                    if isinstance(small, cst.Assign) and any(
                        isinstance(target.target, cst.Name)
                        and target.target.value == "__selection_operation__"
                        for target in small.targets
                    ):
                        values.append(ast.literal_eval(self.module.code_for_node(small.value)))
                    elif (
                        isinstance(small, cst.AnnAssign)
                        and isinstance(small.target, cst.Name)
                        and small.target.value == "__selection_operation__"
                    ):
                        if small.value is None:
                            raise ValueError("consumer selection contract lacks a literal value")
                        values.append(ast.literal_eval(self.module.code_for_node(small.value)))
            if len(values) > 1:
                raise ValueError("one class cannot declare conflicting selection contracts")
            if values:
                operation = values[0]
                if not isinstance(operation, dict) or operation.get("profile") != "selection":
                    raise ValueError("consumer selection contract requires selection profile")
                methods = [member for member in body if isinstance(member, cst.FunctionDef) and member.name.value == "select_hydrated"]
                if len(methods) != 1:
                    raise ValueError("selection owner requires one explicit select_hydrated implementation")
                operation["consumer_selection"] = {"entrypoint": self.source.module + "." + node.name.value + ".select_hydrated", "source_digest": sha256(self.source.content).hexdigest()}
                self.operations.append(operation)

    declarations = []
    for source in sources:
        module = cst.parse_module(source.content)
        contracts = Contracts(module, source)
        module.visit(contracts)
        if contracts.operations:
            declarations.append(
                SourceArtifact(
                    "consumer-selection:" + source.module,
                    canonical_bytes(
                        {"version": MODEL_VERSION, "operations": contracts.operations}
                    ),
                )
            )
    return tuple(declarations)


@dataclass(frozen=True)
class SelectedConsumerValue:
    """Exact selected native member plus detached, already admitted semantic body."""

    member: BoundRoleMember
    content: bytes

    def value(self):
        import json

        return json.loads(self.content)


@dataclass(frozen=True)
class HydratedConsumerSelection:
    selection: BoundConsumerSelection
    values: tuple[tuple[str, tuple[SelectedConsumerValue, ...]], ...]

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
    connection, model, selection, *, demand_id, read_id, trust_snapshot, max_bytes
):
    """Hydrate only retained role pins under the same authenticated native read.

    This is not a new selector. No unselected body or mutable latest/default query
    can supply an input. Native custody and purpose remain enforced by its owner.
    """
    from sqlalchemy import select

    from .data_operation_identity import decode_semantic_value
    from .data_operation_json import json_context_equal, json_loads
    from .data_operation_storage import admitted_data_projection
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
    if context is None or context.subject != binding.subject:
        raise ValueError("native consumer hydration requires its acquired subject context")
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("native hydration requires explicit positive packet capacity")
    projections = admitted_data_projection(
        connection,
        demand_id,
        binding.operation,
        trust_snapshot,
        model,
        read_id=read_id,
        subject=context.subject,
        original_source=context.original_source,
        analyzed_scope=json_loads(context.analyzed_scope),
    )
    if set(binding.admission_evidence) != {
        projection.admission_evidence for projection in projections
    }:
        raise ValueError("retained consumer binding belongs to a different native read boundary")
    by_kind = {projection.kind: projection for projection in projections}
    declaration = model.operation(binding.operation)
    result, used = [], 0
    for role in binding.roles:
        definition = next(item for item in declaration.roles if item.name == role.role)
        relation = by_kind[definition.kind].relation
        values = []
        for member in role.members:
            query = select(relation.c.meaning_body).where(
                relation.c.product == member.product,
                relation.c.member.is_not_distinct_from(member.member),
                relation.c.kind_contract == member.kind_contract,
                relation.c.subject == member.subject,
                relation.c.original_source == member.original_source,
                json_context_equal(relation.c.analyzed_scope, json_loads(member.analyzed_scope)),
                relation.c.support_evidence == json_loads(member.support_evidence),
                relation.c.support_episodes == list(member.support_episodes),
                relation.c.support_references
                == support_reference_records(member.support_references),
                relation.c.position.is_not_distinct_from(member.position),
                relation.c.multiplicity == member.multiplicity,
            )
            rows = connection.execute(query).scalars().all()
            if len(rows) != 1:
                raise ValueError("retained consumer member no longer has one admitted body")
            content = canonical_bytes(decode_semantic_value(rows[0]))
            used += len(content) * member.multiplicity
            if used > max_bytes:
                raise ValueError("complete consumer inputs exceed owned packet capacity")
            values.extend(
                SelectedConsumerValue(member, content) for _ in range(member.multiplicity)
            )
        result.append((role.role, tuple(values)))
    return HydratedConsumerSelection(selection, tuple(result))


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
    candidates = [source for source in sources.sources if capability.entrypoint.startswith(source.module + ".")]
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
        if path.read_bytes() != source.content or sha256(source.content).hexdigest() != capability.source_digest:
            raise PortRefusal("consumer source differs from captured capability")
        if Path(inspect.getfile(module)).resolve() != path or not inspect.ismethod(function):
            raise PortRefusal("consumer runtime differs from captured source")
        actual = inspect.getattr_static(owner, method_name)
        if actual is not function.__func__ or actual is not entry[2] or actual.__code__ != entry[3] or actual.__globals__ is not module.__dict__:
            raise PortRefusal("consumer implementation was rebound")

    verify()
    authorize()
    return ResolvedConsumerSelection(operation, function, verify, authorize)


def resolve_prepared_factory(model, sources, operation):
    """Resolve the compiled original static acquisition method, never an ambient registry."""
    import ast
    import importlib
    import inspect
    from pathlib import Path

    from .data_operation_ports import PortRefusal, _runtime_members

    if model.version != MODEL_VERSION:
        raise PortRefusal("historical model cannot acquire current prepared capabilities")
    capability = model.operation(operation).capabilities.prepared_factory
    if capability is None:
        raise PortRefusal("operation has no captured prepared acquisition")
    candidates = [source for source in sources.sources if capability.entrypoint.startswith(source.module + ".")]
    if not candidates:
        raise PortRefusal("prepared acquisition is outside acquired source")
    source = max(candidates, key=lambda value: len(value.module))
    module = importlib.import_module(source.module)
    path = Path(source.filename).resolve()
    expected = compile(source.content, str(path), "exec", dont_inherit=True)
    entries = tuple(_runtime_members(ast.parse(source.content).body, module, expected, source.module))
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
            module_name = importlib.util.resolve_name(reference, package) if node.level else reference
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
        if (Path(inspect.getfile(owner_module)).resolve() != Path(original.filename).resolve()
                or Path(original.filename).read_bytes() != original.content):
            raise PortRefusal("prepared callable source differs from acquired bytes")
        _verify_prepared_callable(expected_owner, actual)

    def verify_bindings():
        for name in called:
            if name in imports:
                supplying_module, member_name = imports[name]
                actual = inspect.getattr_static(importlib.import_module(supplying_module), member_name)
                if inspect.isfunction(actual):
                    verify_callable(supplying_module + "." + member_name, actual)
            elif name in module.__dict__ and inspect.isfunction(module.__dict__[name]):
                verify_callable(source.module + "." + name, module.__dict__[name])

    def acquire(*args, **kwargs):
        if path.read_bytes() != source.content or sha256(source.content).hexdigest() != capability.source_digest:
            raise PortRefusal("prepared acquisition source differs from admitted bytes")
        actual = module
        for name in capability.entrypoint.removeprefix(source.module + ".").split("."):
            actual = inspect.getattr_static(actual, name)
        if not isinstance(actual, staticmethod) or actual.__func__ is not function or function.__code__ != entry[3] or function.__globals__ is not module.__dict__ or Path(inspect.getfile(module)).resolve() != path:
            raise PortRefusal("prepared acquisition runtime was rebound")
        verify_bindings()
        result = function(*args, **kwargs)
        verify_bindings()
        from .data_operation_pdf_effect import PdfCaptureEffectPort
        implementation = result.wrapped if isinstance(result, PdfCaptureEffectPort) else result
        if hasattr(implementation, "plan_python"):
            method = implementation.plan_python
            verify_callable(type(implementation).__module__ + "." + type(implementation).__qualname__ + ".plan_python", method)
        return result

    return acquire
