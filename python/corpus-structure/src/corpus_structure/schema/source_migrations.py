"""Finite explicit source changes prepared without delegating file publication."""

from __future__ import annotations

import ast
import symtable
from hashlib import sha256
from importlib.metadata import version
from importlib.util import resolve_name
from io import BytesIO
from pathlib import Path
from tokenize import detect_encoding
from typing import Literal

import libcst as cst
from libcst.codemod import (
    CodemodContext,
    ContextAwareTransformer,
    TransformSuccess,
    transform_module,
)
from libcst.codemod.commands.rename import RenameCommand
from libcst.codemod.visitors import ApplyTypeAnnotationsVisitor, RemoveImportsVisitor
from libcst.helpers import get_full_name_for_node
from libcst.metadata import (
    MetadataWrapper,
    ParentNodeProvider,
    QualifiedNameProvider,
    QualifiedNameSource,
    ScopeProvider,
)
from pydantic import BaseModel, ConfigDict


class SourceRoot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    module: str


class AuthoredSourceChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    module: str
    before: str
    after: str


class CallContextChange(BaseModel):
    """One explicit source call correspondence; context is supplied, never inferred."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    before: str
    after: str
    context_names: tuple[str, ...]


class SourceMigration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["symbol_move", "annotations", "call_context"]
    owner: str
    new_owner: str | None = None
    sources: tuple[AuthoredSourceChange, ...]
    roots: tuple[SourceRoot, ...]
    excluded: tuple[str, ...] = ()
    old_name: str | None = None
    new_name: str | None = None
    overwrite_annotations: bool = False
    calls: tuple[CallContextChange, ...] = ()


class ConsumerOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    state: Literal[
        "changed", "already_satisfied", "excluded", "ambiguous", "unsupported", "unresolved"
    ]
    warnings: tuple[str, ...] = ()


class SourceCallProof(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    owner: str
    callable: str
    path: str
    source_digest: str
    signature: str


class SourceMigrationPreview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    roots: tuple[SourceRoot, ...]
    membership: tuple[str, ...]
    inputs: dict[str, str]
    implementation: str
    preparation: str
    outcomes: tuple[ConsumerOutcome, ...]
    after: dict[str, str]
    call_proofs: tuple[SourceCallProof, ...] = ()

    @property
    def ready(self) -> bool:
        return all(
            item.state in {"changed", "already_satisfied", "excluded"} for item in self.outcomes
        )


def _path(root: Path, name: str) -> Path:
    path = root / name
    if (
        not name
        or Path(name).is_absolute()
        or path.resolve() != path
        or not path.is_relative_to(root)
    ):
        raise ValueError(f"unsafe source migration path: {name}")
    return path


def source_members(root: Path, roots: tuple[SourceRoot, ...]) -> dict[str, str]:
    """Include untracked callers and reject overlapping logical module assignments."""
    found: dict[str, str] = {}
    for selected in roots:
        directory = _path(root, selected.path)
        if not directory.is_dir():
            raise ValueError(f"source migration root unavailable: {selected.path}")
        for path in sorted(directory.rglob("*.py")):
            name = path.relative_to(root).as_posix()
            _path(root, name)
            relative = path.relative_to(directory).with_suffix("")
            parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
            module = ".".join((selected.module, *parts)).strip(".")
            if name in found and found[name] != module:
                raise ValueError(f"ambiguous logical module: {name}")
            found[name] = module
    return found


def utf8_source(content: bytes) -> str:
    encoding, _ = detect_encoding(BytesIO(content).readline)
    if encoding.lower().replace("_", "-") not in {"utf-8", "utf-8-sig"}:
        raise ValueError("source migrations support UTF-8 Python only")
    if encoding == "utf-8-sig":
        raise ValueError("UTF-8 BOM source requires an explicit byte-preserving route")
    return content.decode("utf-8")


def preparation_identity() -> str:
    # Readiness custody, never a result-recipe salt. Include implicit trusted inputs
    # and set membership; check fresh bytes even within one long-lived process.
    package = Path(__file__).resolve().parents[1]
    digest = sha256()
    for dependency in (
        "libcst",
        "astroid",
        "griffe",
        "linkml-runtime",
        "pydantic",
        "sqlalchemy",
        "networkx",
    ):
        digest.update((dependency + "=" + version(dependency)).encode())
    for directory in (package / "semantic", package / "model" / "semantic"):
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix in {".py", ".yaml", ".json", ".sql"}:
                digest.update(path.relative_to(package).as_posix().encode())
                digest.update(sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def implementation_identity() -> str:
    return sha256(Path(__file__).read_bytes() + version("libcst").encode()).hexdigest()


class _Eligibility(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (QualifiedNameProvider,)

    def __init__(self, old: str, package: str):
        self.old = old
        self.package = package
        self.matched = False
        self.ambiguous = False
        self.unresolved = False

    def on_visit(self, node):
        if isinstance(node, (cst.Name, cst.Attribute)):
            names = self.get_metadata(QualifiedNameProvider, node, set())
            absolute = {
                resolve_name(n.name, self.package) if n.name.startswith(".") else n.name
                for n in names
            }
            eligible = {n for n in absolute if n == self.old or n.startswith(self.old + ".")}
            if (
                isinstance(node, cst.Attribute)
                and node.attr.value == self.old.rsplit(".", 1)[-1]
                and not eligible
            ):
                self.unresolved = True
            if (
                isinstance(node, cst.Name)
                and node.value == self.old.rsplit(".", 1)[-1]
                and names
                and not eligible
                and any(n.source == QualifiedNameSource.IMPORT for n in names)
            ):
                self.unresolved = True
            self.matched = self.matched or bool(eligible)
            if eligible and len(names) != 1:
                self.ambiguous = True
        return True


class _AbsoluteImports(cst.CSTTransformer):
    """Normalize only relative import modules before the native rename command."""

    def __init__(self, package: str, targets: tuple[str, ...]):
        self.package = package
        self.targets = targets
        self.originals = {}

    def leave_ImportFrom(self, original_node, updated_node):
        if not original_node.relative:
            return updated_node
        name = get_full_name_for_node(original_node.module) if original_node.module else ""
        absolute = resolve_name("." * len(original_node.relative) + (name or ""), self.package)
        if not any(
            target == absolute or target.startswith(absolute + ".") for target in self.targets
        ):
            return updated_node
        self.originals[absolute] = (original_node.module, original_node.relative)
        return updated_node.with_changes(module=cst.parse_expression(absolute), relative=())


class _RestoreImports(cst.CSTTransformer):
    def __init__(self, originals):
        self.originals = originals

    def leave_ImportFrom(self, original_node, updated_node):
        name = get_full_name_for_node(original_node.module) if original_node.module else ""
        if not original_node.relative and name in self.originals:
            module, relative = self.originals[name]
            return updated_node.with_changes(module=module, relative=relative)
        return updated_node


class _CallContextCommand(ContextAwareTransformer):
    METADATA_DEPENDENCIES = (QualifiedNameProvider, ScopeProvider, ParentNodeProvider)

    def __init__(self, context, old, changes):
        super().__init__(context)
        self.old = old
        self.changes = changes
        self.seen = set()

    def _check_reference(self, node):
        names = self.get_metadata(QualifiedNameProvider, node, set())
        package = self.context.full_package_name or ""
        qualified = {
            resolve_name(item.name, package) if item.name.startswith(".") else item.name
            for item in names
        }
        if self.old not in qualified:
            return
        parent = self.get_metadata(ParentNodeProvider, node, None)
        if isinstance(parent, cst.Call) and parent.func is node:
            return
        while isinstance(parent, (cst.Attribute, cst.ImportAlias)):
            parent = self.get_metadata(ParentNodeProvider, parent, None)
        if isinstance(parent, (cst.Import, cst.ImportFrom)):
            return
        raise ValueError("owned callable escapes the finite call-context correspondence")

    def visit_Name(self, node):
        self._check_reference(node)

    def visit_Attribute(self, node):
        self._check_reference(node)

    def leave_Call(self, original_node, updated_node):
        names = self.get_metadata(QualifiedNameProvider, original_node.func, set())
        package = self.context.full_package_name or ""
        qualified = {
            resolve_name(name.name, package) if name.name.startswith(".") else name.name
            for name in names
        }
        spelling = self.module.code_for_node(original_node)
        matches = [item for item in self.changes if item.before == spelling]
        if matches and qualified != {self.old}:
            raise ValueError("call-context receiver is not the exact declared owner")
        if self.old not in qualified:
            return updated_node
        if len(names) != 1 or len(matches) != 1:
            raise ValueError("required owned call has no unambiguous explicit correspondence")
        change = matches[0]
        if change.before in self.seen:
            raise ValueError("call-context correspondence matches more than one call")
        scope = self.get_metadata(ScopeProvider, original_node)
        if any(not scope[item] for item in change.context_names):
            raise ValueError("call-context lacks supplied context in the call lexical scope")
        self.seen.add(change.before)
        return cst.parse_expression(change.after)


def _prepare_call_context(parsed, source, name, context, request):
    changes = tuple(item for item in request.calls if item.path == name)
    tree = ast.parse(source)
    for change in changes:
        before, after = ast.parse(change.before, mode="eval"), ast.parse(change.after, mode="eval")
        if not isinstance(before.body, ast.Call) or not isinstance(after.body, ast.Call):
            raise ValueError("call-context correspondence must contain call expressions")
        if not change.context_names or any(
            not item.isidentifier() for item in change.context_names
        ):
            raise ValueError("call-context requires explicit context identifiers")
        loaded = {node.id for node in ast.walk(after) if isinstance(node, ast.Name)}
        if not set(change.context_names) <= loaded:
            raise ValueError("call-context lacks explicitly supplied context")
    old = request.old_name
    assert old is not None
    eligibility = _Eligibility(old, context.full_package_name or "")
    MetadataWrapper(parsed).visit(eligibility)
    if eligibility.ambiguous or eligibility.unresolved:
        raise ValueError("call-context receiver is ambiguous or unresolved")
    if any(
        isinstance(node, ast.Name)
        and node.id in {"getattr", "eval", "exec", "globals", "locals", "__import__"}
        for node in ast.walk(tree)
    ):
        raise ValueError("dynamic source consumers require explicit resolution")
    module, _, symbol = old.rpartition(".")
    RemoveImportsVisitor.remove_unused_import(context, module, symbol)
    command = _CallContextCommand(context, old, changes)
    result = transform_module(command, source)
    if not isinstance(result, TransformSuccess):
        raise ValueError("call-context transformation refused: " + str(result))
    cleaned = RemoveImportsVisitor(context).transform_module(cst.parse_module(result.code))
    result = TransformSuccess(code=cleaned.code, warning_messages=result.warning_messages)
    if command.seen != {item.before for item in changes}:
        raise ValueError("required call-context source is absent or changed")
    # Verify the declared destination resolves from the proposed consumer source.
    rewritten = cst.parse_module(result.code)
    destination = _Eligibility(request.new_name, context.full_package_name or "")
    MetadataWrapper(rewritten).visit(destination)
    if changes and (not destination.matched or destination.ambiguous or destination.unresolved):
        raise ValueError("call-context destination is not the exact declared owner")
    return result


def _selection_call_proofs(root, request, members, inputs):
    """Prove a declaration-owned former selector without admitting its body."""
    import griffe

    proofs = []
    for path, module in members.items():
        if not request.old_name or not request.old_name.startswith(module + "."):
            continue
        suffix = request.old_name.removeprefix(module + ".").split(".")
        if len(suffix) != 2:
            continue
        class_name, method = suffix
        source = utf8_source(_path(root, path).read_bytes())
        tree = ast.parse(source)
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or node.name != class_name:
                continue
            declarations = []
            for item in node.body:
                if (
                    isinstance(item, ast.AnnAssign)
                    and isinstance(item.target, ast.Name)
                    and item.target.id == "__selection_operation__"
                ) or (isinstance(item, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "__selection_operation__"
                    for target in item.targets
                )):
                    declarations.append(ast.literal_eval(item.value))
            if len(declarations) != 1 or declarations[0].get("id") != request.owner:
                continue
            parsed = griffe.visit(module.rsplit(".", 1)[-1], Path(path), source)
            owner = parsed.members[class_name]
            supplied = owner.members.get(method)
            if not isinstance(supplied, griffe.Function):
                raise ValueError("former selection callable is not directly captured")
            proofs.append(
                SourceCallProof(
                    owner=request.owner,
                    callable=request.old_name,
                    path=path,
                    source_digest=inputs[path],
                    signature=str(supplied.signature()),
                )
            )
    if len(proofs) > 1:
        raise ValueError("former selection callable has ambiguous captured owners")
    return tuple(proofs)


def prepare_source_migration(root: Path, request: SourceMigration) -> SourceMigrationPreview:
    if not request.owner or not request.sources or not request.roots:
        raise ValueError("source migration requires an owner, authored changes and explicit roots")
    if request.kind in {"symbol_move", "call_context"} and (
        not request.old_name or not request.new_name
    ):
        raise ValueError("source move requires an explicit old/new correspondence")
    if request.new_owner is not None and request.kind != "call_context":
        raise ValueError(
            "semantic owner correspondence is supported only for call-context migrations"
        )
    if request.kind == "call_context" and not request.calls:
        raise ValueError("call-context migration requires explicit call correspondences")
    members = source_members(root, request.roots)
    if len({item.path for item in request.sources}) != len(request.sources):
        raise ValueError("duplicate authored source change")
    if any(item.path not in members for item in request.calls):
        raise ValueError("call-context path lies outside the acquired consumer universe")
    if len({(item.path, item.before) for item in request.calls}) != len(request.calls):
        raise ValueError("duplicate call-context correspondence")
    inputs = {name: sha256(_path(root, name).read_bytes()).hexdigest() for name in members}
    call_proofs = (
        _selection_call_proofs(root, request, members, inputs)
        if request.kind == "call_context"
        else ()
    )
    after: dict[str, str] = {}
    outcomes: list[ConsumerOutcome] = []
    for owner in request.sources:
        if members.get(owner.path) != owner.module or inputs.get(owner.path) != owner.before:
            raise ValueError(f"authored source revision/module differs: {owner.path}")
        utf8_source(owner.after.encode())
        compile(owner.after, owner.path, "exec", dont_inherit=True)
        if request.kind != "annotations":
            after[owner.path] = owner.after
    if not set(request.excluded) <= members.keys() or set(request.excluded) & {
        item.path for item in request.sources
    }:
        raise ValueError("source exclusions must name acquired non-owner files")
    for name, module_name in members.items():
        if name in request.excluded:
            outcomes.append(ConsumerOutcome(path=name, state="excluded"))
            continue
        try:
            source = after.get(name, utf8_source(_path(root, name).read_bytes()))
            parsed = cst.parse_module(source)
            tree = ast.parse(source)
            context = CodemodContext(
                filename=name,
                full_module_name=module_name,
                full_package_name=module_name
                if name.endswith("/__init__.py")
                else module_name.rpartition(".")[0],
            )
            owners = []
            if request.kind == "call_context":
                try:
                    result = _prepare_call_context(parsed, source, name, context, request)
                except ValueError as error:
                    outcomes.append(
                        ConsumerOutcome(path=name, state="unresolved", warnings=(str(error),))
                    )
                    continue
                code = result.code
                compile(code, name, "exec", dont_inherit=True)
                changed = code != utf8_source(_path(root, name).read_bytes())
                if changed:
                    after[name] = code
                outcomes.append(
                    ConsumerOutcome(path=name, state="changed" if changed else "already_satisfied")
                )
                continue
            if request.kind == "symbol_move":
                old = request.old_name
                assert old is not None and request.new_name is not None
                eligibility = _Eligibility(old, context.full_package_name or "")
                MetadataWrapper(parsed).visit(eligibility)
                if eligibility.ambiguous:
                    outcomes.append(ConsumerOutcome(path=name, state="ambiguous"))
                    continue
                if eligibility.unresolved:
                    outcomes.append(ConsumerOutcome(path=name, state="unresolved"))
                    continue
                dynamic_names = {
                    "getattr",
                    "setattr",
                    "hasattr",
                    "eval",
                    "exec",
                    "__import__",
                    "globals",
                    "locals",
                    "vars",
                }
                dynamic = any(
                    (isinstance(node, ast.Name) and node.id in dynamic_names)
                    or (isinstance(node, ast.Attribute) and node.attr in dynamic_names)
                    or (
                        isinstance(node, ast.ImportFrom)
                        and node.module == "builtins"
                        and any(alias.name in dynamic_names for alias in node.names)
                    )
                    for node in ast.walk(tree)
                )
                indirect_import = any(
                    isinstance(node, ast.ImportFrom)
                    and any(alias.name == old.rsplit(".", 1)[-1] for alias in node.names)
                    and resolve_name(
                        "." * node.level + (node.module or ""), context.full_package_name or ""
                    )
                    != old.rpartition(".")[0]
                    for node in ast.walk(tree)
                )
                stars = any(
                    isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names)
                    for node in ast.walk(tree)
                )
                if dynamic or stars or indirect_import:
                    outcomes.append(ConsumerOutcome(path=name, state="unresolved"))
                    continue
                target_import = any(
                    isinstance(node, ast.ImportFrom)
                    and any(
                        resolve_name(
                            "." * node.level + (node.module or ""), context.full_package_name or ""
                        )
                        + "."
                        + alias.name
                        == old
                        for alias in node.names
                    )
                    for node in ast.walk(tree)
                )
                if not eligibility.matched and not target_import:
                    outcomes.append(
                        ConsumerOutcome(
                            path=name,
                            state="changed"
                            if source != utf8_source(_path(root, name).read_bytes())
                            else "already_satisfied",
                        )
                    )
                    continue
                destination = request.new_name.rsplit(".", 1)[-1]
                tables = [symtable.symtable(source, name, "exec")]
                collision = False
                while tables:
                    table = tables.pop()
                    collision = collision or destination in table.get_identifiers()
                    tables.extend(table.get_children())
                if name not in {item.path for item in request.sources} and collision:
                    outcomes.append(ConsumerOutcome(path=name, state="ambiguous"))
                    continue
                command = RenameCommand(context, old, request.new_name)
            else:
                owners = [owner for owner in request.sources if owner.module == module_name]
                if len(owners) != 1:
                    outcomes.append(ConsumerOutcome(path=name, state="already_satisfied"))
                    continue
                # A transient stub is derived from the explicitly authored after-source.
                ApplyTypeAnnotationsVisitor.store_stub_in_context(
                    context,
                    cst.parse_module(owners[0].after),
                    overwrite_existing_annotations=request.overwrite_annotations,
                    strict_posargs_matching=True,
                    strict_annotation_matching=True,
                )
                command = ApplyTypeAnnotationsVisitor(context)
            normalized = _AbsoluteImports(
                context.full_package_name or "",
                tuple(name for name in (request.old_name, request.new_name) if name is not None),
            )
            candidate = parsed.visit(normalized).code if request.kind == "symbol_move" else source
            result = transform_module(command, candidate)
            if not isinstance(result, TransformSuccess):
                outcomes.append(
                    ConsumerOutcome(
                        path=name, state="unsupported", warnings=tuple(result.warning_messages)
                    )
                )
                continue
            code = (
                cst.parse_module(result.code).visit(_RestoreImports(normalized.originals)).code
                if request.kind == "symbol_move"
                else result.code
            )
            compile(code, name, "exec", dont_inherit=True)
            if (
                request.kind == "annotations"
                and owners
                and ast.dump(ast.parse(code)) != ast.dump(ast.parse(owners[0].after))
            ):
                outcomes.append(
                    ConsumerOutcome(
                        path=name,
                        state="unsupported",
                        warnings=("annotation stage cannot realize the requested authored change",),
                    )
                )
                continue
            changed = code != utf8_source(_path(root, name).read_bytes())
            if changed:
                after[name] = code
            outcomes.append(
                ConsumerOutcome(
                    path=name,
                    state="changed" if changed else "already_satisfied",
                    warnings=tuple(result.warning_messages),
                )
            )
        except (SyntaxError, UnicodeError, ValueError, cst.ParserSyntaxError) as error:
            outcomes.append(ConsumerOutcome(path=name, state="unsupported", warnings=(str(error),)))
    return SourceMigrationPreview(
        roots=request.roots,
        membership=tuple(sorted(members)),
        inputs=inputs,
        implementation=implementation_identity(),
        preparation=preparation_identity(),
        outcomes=tuple(outcomes),
        after=after,
        call_proofs=call_proofs,
    )


def check_source_migration(root: Path, preview: SourceMigrationPreview) -> None:
    if not preview.ready:
        raise ValueError("source migration has required unresolved consumers")
    if preview.preparation != preparation_identity():
        raise ValueError(
            "semantic preparation implementation or implicit inputs changed after preview"
        )
    if preview.implementation != implementation_identity():
        raise ValueError("source transformation implementation changed after preview")
    if tuple(sorted(source_members(root, preview.roots))) != preview.membership:
        raise ValueError("source consumer membership changed after preview")
