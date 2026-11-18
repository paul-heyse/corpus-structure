"""LibCST engine of the attributed pass (`attribution.attribute`).

One `MetadataWrapper` per file, without `FullRepoManager`. Names are resolved through
`ScopeProvider`'s accesses and their referents, the bindings `QualifiedNameProvider` itself is
computed from: an access sees only the bindings of its own scope that precede it (and every
binding of an enclosing scope), comprehensions and class bodies are scopes of their own, and
string annotations are parsed. The referents also give the binding node, which the alias,
instance and subclass rows need and qualified names alone do not carry.

Two bindings `ScopeProvider` does not order the way Python does are added here, so a site that
may not refer to the import becomes `mixed_binding` instead of a silent wrong attribution:

- a `match` capture (`case Field:`, `case [*rest]`, `case {**rest}`, `case ... as name`) binds
  the name in its scope, which `ScopeProvider` does not record;
- in a function, a name bound anywhere in the body is local for the whole body (an earlier use
  raises `UnboundLocalError`), whereas `ScopeProvider` resolves a use before the binding to the
  enclosing scope's binding.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import cast

import libcst as cst
from libcst.metadata import (
    Assignment,
    BaseAssignment,
    CodeRange,
    ExpressionContext,
    ExpressionContextProvider,
    FunctionScope,
    ImportAssignment,
    MetadataWrapper,
    ParentNodeProvider,
    PositionProvider,
    Scope,
    ScopeProvider,
)

from corpus_tooling.library.attribution import (
    _MAX_DEPTH,
    OTHER,
    Attribution,
    CallShape,
    Candidate,
    FileContext,
    RowSink,
    call_shape,
    decide,
    value_candidate,
)
from corpus_tooling.library.census_rows import SiteUse

_CODE = cst.Module([])


def attribute(source: str, context: FileContext) -> Attribution:
    module = cst.parse_module(source)
    collector = _Collector(context, RowSink(context, source))
    MetadataWrapper(module, unsafe_skip_copy=True).visit(collector)
    return collector.sink.result


def _chain(expression: cst.BaseExpression) -> tuple[cst.BaseExpression, list[str]]:
    attributes: list[str] = []
    while isinstance(expression, cst.Attribute):
        attributes.append(expression.attr.value)
        expression = expression.value
    attributes.reverse()
    return expression, attributes


def _leftmost(node: cst.CSTNode) -> cst.CSTNode:
    while isinstance(node, cst.Attribute):
        node = node.value
    return node


def _shape(call: cst.Call) -> CallShape:
    return call_shape(
        (argument.keyword.value if argument.keyword else None, argument.star)
        for argument in call.args
    )


def _outer_chains(node: cst.CSTNode) -> Iterator[cst.BaseExpression]:
    """Outermost names and attribute chains of a parsed annotation expression."""
    if isinstance(node, cst.Name | cst.Attribute):
        yield node
        return
    for child in node.children:
        yield from _outer_chains(child)


class _Collector(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (
        ScopeProvider,
        PositionProvider,
        ParentNodeProvider,
        ExpressionContextProvider,
    )

    def __init__(self, context: FileContext, sink: RowSink) -> None:
        super().__init__()
        self.context = context
        self.sink = sink
        self.consumed: set[int] = set()
        self.annotations = 0
        self.active: set[int] = set()
        self.captures: set[tuple[int, str]] = set()
        """(id of a scope, name) for every `match` capture."""
        self.capture_names: set[int] = set()

    def visit_Module(self, node: cst.Module) -> None:
        finder = _Captures()
        node.visit(finder)
        for name in finder.names:
            scope = self.get_metadata(ScopeProvider, name, None)
            if scope is not None:
                self.captures.add((id(scope), name.value))
            self.capture_names.add(id(name))

    # --- sites --------------------------------------------------------------------------

    def visit_Import(self, node: cst.Import) -> bool:
        return False  # import statements are rows of the exact pass

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
        return False

    def visit_Decorator(self, node: cst.Decorator) -> None:
        expression = node.decorator
        call = expression if isinstance(expression, cst.Call) else None
        target = call.func if call is not None else expression
        self.consumed.add(id(target))
        if call is not None:
            self.consumed.add(id(call))
        self._site("decorator", target, expression, call)

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        for argument in node.bases:
            value = argument.value
            if isinstance(value, cst.Subscript):
                value = value.value  # a generic base: `Base[T]`
            self.consumed.add(id(value))
            self._site("subclass", value, value, None)

    def visit_Call(self, node: cst.Call) -> None:
        if id(node) in self.consumed or self._getattr(node):
            return
        self.consumed.add(id(node.func))
        self._site("call", node.func, node, node)

    def visit_Name(self, node: cst.Name) -> None:
        self._reference(node)

    def visit_Attribute(self, node: cst.Attribute) -> None:
        self._reference(node)

    def visit_Annotation(self, node: cst.Annotation) -> None:
        self.annotations += 1

    def leave_Annotation(self, original_node: cst.Annotation) -> None:
        self.annotations -= 1

    def visit_SimpleString(self, node: cst.SimpleString) -> None:
        if self.annotations:
            self._string_annotation(node)

    def _reference(self, node: cst.Name | cst.Attribute) -> None:
        if id(node) in self.consumed or id(node) in self.capture_names:
            return
        parent = self.get_metadata(ParentNodeProvider, node, None)
        if isinstance(parent, cst.Attribute) and (parent.value is node or parent.attr is node):
            return  # inside a longer chain, or the member name itself
        if isinstance(parent, cst.Arg) and parent.keyword is node:
            return
        context = self.get_metadata(ExpressionContextProvider, node, None)
        if context is None or (isinstance(node, cst.Name) and context != ExpressionContext.LOAD):
            return
        self._site("reference", node, node, None)

    def _site(
        self,
        use: SiteUse,
        target: cst.BaseExpression,
        anchor: cst.CSTNode,
        call: cst.Call | None,
    ) -> None:
        base, attributes = _chain(target)
        candidates = self._candidates(base, attributes, 0)
        decision = decide(candidates, member=bool(attributes))
        if decision is None:
            return
        line, column = self._position(anchor)
        self.sink.emit(
            use,
            decision,
            line=line,
            column=column,
            subject=_CODE.code_for_node(target),
            call=_shape(call) if call is not None else None,
        )

    def _getattr(self, node: cst.Call) -> bool:
        """`getattr(<family object>, ...)`: an unresolved row instead of a reference."""
        function = node.func
        if not (isinstance(function, cst.Name) and function.value == "getattr"):
            return False
        if len(node.args) < 2 or any(
            isinstance(referent, Assignment)
            for referent, _ in self._referents(function, ["getattr"])
        ):
            return False
        target = node.args[0].value
        base, attributes = _chain(target)
        decision = decide(self._candidates(base, attributes, 0), member=bool(attributes))
        if decision is None:
            return False
        member = node.args[1].value
        literal = member.evaluated_value if isinstance(member, cst.SimpleString) else None
        paths = decision.paths
        if decision.kind == "attributed" and isinstance(literal, str):
            paths = tuple(f"{path}.{literal}" for path in paths)
        self.consumed.update({id(target), id(function)})
        line, column = self._position(node)
        self.sink.unresolved(
            "getattr",
            line=line,
            column=column,
            subject=_CODE.code_for_node(node),
            paths=paths,
            owner=decision.owner,
        )
        return True

    def _string_annotation(self, node: cst.SimpleString) -> None:
        text = node.evaluated_value
        if not isinstance(text, str):
            return
        try:
            expression = cst.parse_expression(text.strip())
        except cst.ParserSyntaxError:
            return
        scope = self.get_metadata(ScopeProvider, node, None)
        if scope is None:
            return
        line, column = self._position(node)
        for chain in _outer_chains(expression):
            base, attributes = _chain(chain)
            if not isinstance(base, cst.Name):
                continue
            parts = [base.value, *attributes]
            candidates: list[Candidate] = []
            for length in range(len(parts), 0, -1):
                name = ".".join(parts[:length])
                if name in scope:
                    for assignment in scope[name]:
                        candidates += self._from_referent(assignment, parts, length, 0)
                    break
            decision = decide(candidates, member=bool(attributes))
            self.sink.emit(
                "reference", decision, line=line, column=column, subject=_CODE.code_for_node(chain)
            )

    def _position(self, node: cst.CSTNode) -> tuple[int, int]:
        start = cast(CodeRange, self.get_metadata(PositionProvider, node)).start
        return start.line, self.sink.byte_column(start.line, start.column)

    # --- resolution -----------------------------------------------------------------------

    def _referents(self, base: cst.Name, parts: Sequence[str]) -> list[tuple[BaseAssignment, int]]:
        """The bindings the access at `base` may refer to, with the length of the dotted
        prefix the access was recorded under (`import a.b` records `a.b`)."""
        scope: Scope | None = self.get_metadata(ScopeProvider, base, None)
        if scope is None:
            return []
        for length in range(len(parts), 0, -1):
            name = ".".join(parts[:length])
            found = [
                (referent, length)
                for access in scope.accesses[name]
                if _leftmost(access.node) is base
                for referent in access.referents
            ]
            if found:
                return found
        return []

    def _candidates(
        self, base: cst.BaseExpression, attributes: Sequence[str], depth: int
    ) -> list[Candidate]:
        if depth > _MAX_DEPTH:
            return [OTHER]
        if isinstance(base, cst.Name):
            parts = [base.value, *attributes]
            referents = self._referents(base, parts)
            candidates = [
                candidate
                for referent, length in referents
                for candidate in self._from_referent(referent, parts, length, depth)
            ]
            if candidates and self._rebound(base, referents):
                candidates.append(OTHER)
            return candidates
        if isinstance(base, cst.Call):
            callee, tail = _chain(base.func)
            candidates = self._candidates(callee, tail, depth + 1)
            decision = decide(candidates, member=bool(tail))
            owner = _CODE.code_for_node(base.func) + "()"
            return [
                value_candidate(decision, candidates, call=True, member=bool(tail), owner=owner)
            ]
        return []

    def _rebound(self, base: cst.Name, referents: Sequence[tuple[BaseAssignment, int]]) -> bool:
        """Whether the name at `base` may be bound by something its referents leave out: a
        `match` capture in its scope or an enclosing one, or a binding of a function's own
        scope that the use precedes."""
        scope: Scope | None = self.get_metadata(ScopeProvider, base, None)
        name = base.value
        if scope is None:
            return False
        if isinstance(scope, FunctionScope):
            seen = {id(referent) for referent, _ in referents}
            if any(id(binding) not in seen for binding in scope.assignments[name]):
                return True
        current: Scope | None = scope
        while current is not None:
            if (id(current), name) in self.captures:
                return True
            parent = current.parent
            current = None if parent is current else parent
        return False

    def _from_referent(
        self, referent: BaseAssignment, parts: Sequence[str], length: int, depth: int
    ) -> list[Candidate]:
        if isinstance(referent, ImportAssignment):
            return [
                self.context.imported(qualified.name)
                for qualified in referent.get_qualified_names_for(".".join(parts))
            ]
        if isinstance(referent, Assignment):
            if id(referent) in self.active:
                return [OTHER]
            self.active.add(id(referent))
            try:
                bound = self._bound(referent, depth)
            finally:
                self.active.discard(id(referent))
            return [bound.extended(parts[length:])]
        return [OTHER]  # a builtin

    def _bound(self, assignment: Assignment, depth: int) -> Candidate:
        """What a local binding (not an import) stands for."""
        node = assignment.node
        if isinstance(node, cst.ClassDef):
            paths: set[str] = set()
            for argument in node.bases:
                value = argument.value
                if isinstance(value, cst.Subscript):
                    value = value.value
                base, attributes = _chain(value)
                candidates = self._candidates(base, attributes, depth + 1)
                decision = decide(candidates, member=bool(attributes))
                if decision is not None and decision.kind == "attributed":
                    paths.update(decision.paths)
                elif not attributes:
                    paths.update(p for c in candidates if c.kind == "repo_class" for p in c.paths)
            if not paths:
                return OTHER
            return Candidate("repo_class", tuple(sorted(paths)), owner=node.name.value)
        if isinstance(node, cst.Name):
            value = self._bound_value(node)
            if value is None:
                return OTHER
            call = isinstance(value, cst.Call)
            expression = value.func if isinstance(value, cst.Call) else value
            base, attributes = _chain(expression)
            candidates = self._candidates(base, attributes, depth + 1)
            decision = decide(candidates, member=bool(attributes))
            return value_candidate(
                decision, candidates, call=call, member=bool(attributes), owner=node.value
            )
        return OTHER

    def _bound_value(self, name: cst.Name) -> cst.BaseExpression | None:
        """The value a name is bound to by `name = v`, `name: T = v`, `(name := v)` or
        `with v(...) as name`; None for any other binding."""
        parent = self.get_metadata(ParentNodeProvider, name, None)
        if isinstance(parent, cst.AssignTarget) and parent.target is name:
            statement = self.get_metadata(ParentNodeProvider, parent, None)
            return statement.value if isinstance(statement, cst.Assign) else None
        if isinstance(parent, cst.AnnAssign | cst.NamedExpr) and parent.target is name:
            return parent.value
        if isinstance(parent, cst.AsName) and parent.name is name:
            item = self.get_metadata(ParentNodeProvider, parent, None)
            if isinstance(item, cst.WithItem) and isinstance(item.item, cst.Call):
                return item.item
        return None


class _Captures(cst.CSTVisitor):
    """The names `match` patterns capture."""

    def __init__(self) -> None:
        super().__init__()
        self.names: list[cst.Name] = []

    def visit_MatchAs(self, node: cst.MatchAs) -> None:
        if node.name is not None:
            self.names.append(node.name)

    def visit_MatchStar(self, node: cst.MatchStar) -> None:
        if node.name is not None:
            self.names.append(node.name)

    def visit_MatchMapping(self, node: cst.MatchMapping) -> None:
        if node.rest is not None:
            self.names.append(node.rest)
