"""What a package's own source reads and guards, found by one `ast` pass per module.

Standard library only; nothing is imported or executed. For one module's source text this finds:

- environment-variable reads: `os.environ[...]`, `os.environ.get/setdefault/pop(...)`,
  `os.getenv(...)`, `"X" in os.environ`, through any local import alias of `os`;
- entry-point group reads: `importlib.metadata.entry_points(group=...)` (or
  `importlib_metadata`), `entry_points().select(group=...)`,
  `pkg_resources.iter_entry_points(...)`, and `<x>.group == "g"` comparisons made while
  iterating a distribution's entry points;
- bindings made under `try`/`except ImportError` (or `ModuleNotFoundError`) at module or class
  scope;
- registration functions: a module- or class-level function named `register`/`register_*`, or
  one that (directly or through a nested function) stores a parameter it never rebinds into a
  container (a mutating method call) or a subscript or attribute, and returns that same
  parameter: the shape of a registration decorator.

A name argument counts as literal when it is a string literal or a module-level name bound once
to one (`GROUP = "g"`). Any other argument keeps `name=None` and its source text, so the caller
reports it as unresolved. Each finding names the dotted path of the symbol it belongs to:
the enclosing function or class, a module- or class-level assignment target, or the module.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Literal

ReadCategory = Literal["env_var", "entry_point_group"]

_ENV_CALLS = {"os.getenv", "os.environ.get", "os.environ.setdefault", "os.environ.pop"}
_ENTRY_POINT_CALLS = {"importlib.metadata.entry_points", "importlib_metadata.entry_points"}
_ITER_ENTRY_POINTS = "pkg_resources.iter_entry_points"
_IMPORT_ERRORS = {"ImportError", "ModuleNotFoundError"}
_STORING_METHODS = {"append", "add", "insert", "extend", "update", "setdefault", "register", "put"}


@dataclass(frozen=True)
class SourceRead:
    category: ReadCategory
    name: str | None
    """The literal name or group; `None` when the argument is not a string literal."""
    expression: str
    """The argument as written (`"<no group argument>"` for a bare `entry_points()`)."""
    symbol: str
    line: int
    column: int


@dataclass(frozen=True)
class GatedBinding:
    path: str
    line: int


@dataclass(frozen=True)
class Registration:
    path: str
    line: int
    reason: str


@dataclass
class ModuleScan:
    reads: list[SourceRead] = field(default_factory=list)
    gated: list[GatedBinding] = field(default_factory=list)
    registrations: list[Registration] = field(default_factory=list)


def _literal(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _argument(call: ast.Call, keyword: str, position: int | None = None) -> ast.expr | None:
    """The argument passed as `keyword`, or at `position` when it can be passed positionally."""
    for item in call.keywords:
        if item.arg == keyword:
            return item.value
    if position is not None and len(call.args) > position:
        argument = call.args[position]
        return None if isinstance(argument, ast.Starred) else argument
    return None


def _catches_import_error(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return False
    caught = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    for node in caught:
        name = node.attr if isinstance(node, ast.Attribute) else getattr(node, "id", None)
        if name in _IMPORT_ERRORS:
            return True
    return False


def _bound_names(statements: list[ast.stmt]) -> list[tuple[str, int]]:
    """Names bound by these statements in their own scope (not inside nested functions)."""
    bound: list[tuple[str, int]] = []
    for statement in statements:
        match statement:
            case ast.Import(names=names):
                bound += [((a.asname or a.name.split(".")[0]), statement.lineno) for a in names]
            case ast.ImportFrom(names=names):
                bound += [((a.asname or a.name), statement.lineno) for a in names if a.name != "*"]
            case ast.FunctionDef() | ast.AsyncFunctionDef() | ast.ClassDef():
                bound.append((statement.name, statement.lineno))
            case ast.Assign(targets=targets):
                for target in targets:
                    bound += [(n.id, statement.lineno) for n in _target_names(target)]
            case ast.AnnAssign(target=target) | ast.AugAssign(target=target):
                bound += [(n.id, statement.lineno) for n in _target_names(target)]
            case ast.If(body=body, orelse=orelse):
                bound += _bound_names(body) + _bound_names(orelse)
            case (
                ast.Try(body=body, handlers=handlers, orelse=orelse, finalbody=final)
                | ast.TryStar(body=body, handlers=handlers, orelse=orelse, finalbody=final)
            ):
                inner = [s for handler in handlers for s in handler.body]
                bound += _bound_names(body + inner + orelse + final)
            case ast.With(body=body) | ast.AsyncWith(body=body):
                bound += _bound_names(body)
            case _:
                pass
    return bound


def _target_names(target: ast.expr) -> list[ast.Name]:
    if isinstance(target, ast.Name):
        return [target]
    if isinstance(target, ast.Tuple | ast.List):
        return [name for element in target.elts for name in _target_names(element)]
    return []


def _parameter_names(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    arguments = function.args
    names = [a.arg for a in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)]
    return set(names)


def _stores(function: ast.FunctionDef | ast.AsyncFunctionDef, parameter: str) -> bool:
    """Whether `parameter`, never rebound, is itself handed to a container-mutating method call
    (`registry.append(p)`, `self.items.append(Info(callback=p))`) or assigned into another
    object's subscript or attribute (`REGISTRY[name] = p`). Using one of its attributes
    (`p.inner = ...`, `f(p.x)`) does not count."""
    stored = False
    for node in ast.walk(function):
        if isinstance(node, ast.Assign | ast.AugAssign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(n.id == parameter for t in targets for n in _target_names(t)):
                return False  # rebound: what is returned is no longer the argument
            if (
                node.value is not None
                and any(
                    isinstance(t, ast.Subscript | ast.Attribute) and _root_name(t) != parameter
                    for t in targets
                )
                and _mentions(node.value, parameter)
            ):
                stored = True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _STORING_METHODS
            and _root_name(node.func) != parameter
            and any(
                _mentions(a, parameter) for a in (*node.args, *(k.value for k in node.keywords))
            )
        ):
            stored = True
    return stored


def _root_name(node: ast.expr) -> str | None:
    while isinstance(node, ast.Attribute | ast.Subscript):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _mentions(node: ast.AST, name: str) -> bool:
    """Whether `name` occurs as a value itself, not only as the object of an attribute or
    subscript access."""
    accessed = {
        id(n.value)
        for n in ast.walk(node)
        if isinstance(n, ast.Attribute | ast.Subscript) and isinstance(n.value, ast.Name)
    }
    return any(
        isinstance(n, ast.Name) and n.id == name and id(n) not in accessed for n in ast.walk(node)
    )


def _registration_reason(function: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    for node in ast.walk(function):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        parameters = _parameter_names(node)
        for statement in ast.walk(node):
            if (
                isinstance(statement, ast.Return)
                and isinstance(statement.value, ast.Name)
                and statement.value.id in parameters
                and _stores(node, statement.value.id)
            ):
                return (
                    "registration decorator: stores its argument "
                    f"`{statement.value.id}` and returns it"
                )
    if function.name == "register" or function.name.startswith("register_"):
        return f"registration function by name (`{function.name}`)"
    return None


class _Scanner(ast.NodeVisitor):
    def __init__(self, module: str) -> None:
        self.module = module
        self.result = ModuleScan()
        self.imports: dict[str, str] = {}
        self.scope: list[str] = []  # qualified-name parts below the module
        self.in_function = 0
        self.binding: str | None = None  # a module- or class-level assignment target
        self.select_receivers: set[int] = set()
        self.constants: dict[str, str] = {}  # module-level names bound once to a string literal

    # --- names --------------------------------------------------------------------------------

    def _path(self, *parts: str) -> str:
        return ".".join([self.module, *self.scope, *parts])

    def _symbol(self) -> str:
        if self.binding is not None:
            return self._path(self.binding)
        return self._path()

    def _dotted(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return self.imports.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            base = self._dotted(node.value)
            return f"{base}.{node.attr}" if base else None
        return None

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.asname:
                self.imports[alias.asname] = alias.name
            else:
                top = alias.name.split(".")[0]
                self.imports[top] = top

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level or not node.module:
            return
        for alias in node.names:
            if alias.name != "*":
                self.imports[alias.asname or alias.name] = f"{node.module}.{alias.name}"

    # --- scopes -------------------------------------------------------------------------------

    def _definition(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        if isinstance(node, ast.ClassDef):
            for base in (*node.bases, *(k.value for k in node.keywords)):
                self.visit(base)
        elif not self.in_function:
            reason = _registration_reason(node)
            if reason is not None:
                self.result.registrations.append(
                    Registration(path=self._path(node.name), line=node.lineno, reason=reason)
                )
        saved = self.binding
        self.binding = None
        self.scope.append(node.name)
        function = not isinstance(node, ast.ClassDef)
        self.in_function += int(function)
        if function:
            arguments = node.args
            for default in (*arguments.defaults, *arguments.kw_defaults):
                if default is not None:
                    self.visit(default)
        for statement in node.body:
            self.visit(statement)
        self.in_function -= int(function)
        self.scope.pop()
        self.binding = saved

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._definition(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._definition(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._definition(node)

    def _assignment(self, node: ast.Assign | ast.AnnAssign | ast.AugAssign) -> None:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names = [n.id for t in targets for n in _target_names(t)]
        if self.in_function or not names:
            self.generic_visit(node)
            return
        saved = self.binding
        self.binding = names[0]
        self.generic_visit(node)
        self.binding = saved

    def visit_Assign(self, node: ast.Assign) -> None:
        self._assignment(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._assignment(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._assignment(node)

    def _try(self, node: ast.Try | ast.TryStar) -> None:
        if not self.in_function and any(_catches_import_error(h) for h in node.handlers):
            statements = [*node.body, *(s for h in node.handlers for s in h.body), *node.orelse]
            for name, line in _bound_names(statements):
                self.result.gated.append(GatedBinding(path=self._path(name), line=line))
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._try(node)

    def visit_TryStar(self, node: ast.TryStar) -> None:
        self._try(node)

    # --- reads --------------------------------------------------------------------------------

    def _read(self, category: ReadCategory, argument: ast.expr | None, at: ast.AST) -> None:
        expression = "<no group argument>" if argument is None else ast.unparse(argument)
        self.result.reads.append(
            SourceRead(
                category=category,
                name=self._string(argument),
                expression=expression,
                symbol=self._symbol(),
                line=getattr(at, "lineno", 0),
                column=getattr(at, "col_offset", 0) + 1,
            )
        )

    def visit_Call(self, node: ast.Call) -> None:
        callee = self._dotted(node.func)
        if callee in _ENV_CALLS:
            self._read("env_var", _argument(node, "key", 0), node)
        elif callee in _ENTRY_POINT_CALLS:
            group = _argument(node, "group")
            if group is not None or id(node) not in self.select_receivers:
                self._read("entry_point_group", group, node)
        elif callee == _ITER_ENTRY_POINTS:
            self._read("entry_point_group", _argument(node, "group", 0), node)
        elif (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "select"
            and isinstance(node.func.value, ast.Call)
            and self._dotted(node.func.value.func) in _ENTRY_POINT_CALLS
        ):
            self.select_receivers.add(id(node.func.value))
            self._read("entry_point_group", _argument(node, "group"), node)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if isinstance(node.ctx, ast.Load) and self._dotted(node.value) == "os.environ":
            self._read("env_var", node.slice, node)
        self.generic_visit(node)

    def _string(self, node: ast.expr | None) -> str | None:
        """A string literal, or a module-level name bound once to one."""
        literal = _literal(node)
        if literal is None and isinstance(node, ast.Name):
            return self.constants.get(node.id)
        return literal

    def visit_Compare(self, node: ast.Compare) -> None:
        if len(node.ops) == 1:
            operator, left, right = node.ops[0], node.left, node.comparators[0]
            if isinstance(operator, ast.In | ast.NotIn) and self._dotted(right) == "os.environ":
                self._read("env_var", left, node)
            elif isinstance(operator, ast.Eq | ast.NotEq):
                # `entry_point.group == "g"` while iterating distributions' entry points.
                for attribute, other in ((left, right), (right, left)):
                    if (
                        isinstance(attribute, ast.Attribute)
                        and attribute.attr == "group"
                        and self._string(other) is not None
                    ):
                        self._read("entry_point_group", other, node)
                        break
        self.generic_visit(node)


def scan_module(source: str, module: str) -> ModuleScan:
    """Scan one module's source; `module` is its dotted path. Raises `SyntaxError`."""
    tree = ast.parse(source)
    scanner = _Scanner(module)
    # Imports anywhere in the module bind names the reads may use (a function-level `import os`).
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            scanner.visit_Import(node)
        elif isinstance(node, ast.ImportFrom):
            scanner.visit_ImportFrom(node)
    scanner.constants = _string_constants(tree)
    for statement in tree.body:
        scanner.visit(statement)
    return scanner.result


def _string_constants(tree: ast.Module) -> dict[str, str]:
    values: dict[str, str | None] = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            targets, value = statement.targets, statement.value
        elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
            targets, value = [statement.target], statement.value
        else:
            continue
        for target in targets:
            for name in _target_names(target):
                literal = _literal(value) if isinstance(target, ast.Name) else None
                values[name.id] = None if name.id in values else literal
    return {name: value for name, value in values.items() if value is not None}
