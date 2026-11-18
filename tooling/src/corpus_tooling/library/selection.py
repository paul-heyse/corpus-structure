"""`tooling library selection DIST...`: whether the project selects each distribution, and how.

uv is the authority (D4). The command runs `uv tree --format json` once over the whole project
and reads the graph; it never parses `uv.lock`. In uv's preview schema the document has
`members[]` (`name`, `id`) and a `resolution` map from node id to node. A node has `name`,
`version`, `source`, `kind` and `dependencies[]` of `{id, marker?}`. `kind` is `"package"`,
`{"extra": E}` for a selected extra of a package (its own node, with an edge to the base
package), `{"group": G}` for a dependency group of a member, or `"workspace"` (the container,
ignored). Edges run from the dependent to its dependency. The full graph is read and walked
upward here instead of one `--invert --package X` run per distribution: one subprocess serves
every requested name, and a name absent from the graph is "not selected", not a uv error.

A **member-owned** node is a workspace member's package node or one of its extra or group nodes.
Selection is direct when a member-owned node has an edge to the distribution (or to one of its
extra nodes); paths are walks up the graph from the distribution to the first member-owned node.

Scope: uv is always run with `--frozen --universal`, the only form that does not execute an
interpreter (strace on a cold uv cache, uv 0.13.7: `--locked`, `uv lock --check` and a
current-platform `--frozen` each run the project environment's `python`, whose `site` would
execute `.pth` lines; D2 forbids running the target). So the graph covers every platform, edges
keep their markers (a conditional edge is shown as `>[marker]`, never filtered to this
machine), and the lock is read as it stands, not verified against the `pyproject.toml` files;
every result says both. Without a group option the default groups are covered. `UV_PYTHON` and
the variables that would change the lock handling or the groups are removed from uv's
environment.
"""

from __future__ import annotations

import difflib
import heapq
import json
import os
import re
import shutil
import subprocess
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cached_property
from typing import Annotated, Any, ClassVar, Literal

import typer

from corpus_tooling.envelope import Column, Item
from corpus_tooling.library.context import library_envelope, library_state
from corpus_tooling.library.installed import normalize_name
from corpus_tooling.library.target import Project
from corpus_tooling.output import (
    DEFAULT_LIMIT,
    JsonOpt,
    LimitOpt,
    OffsetOpt,
    StrictOpt,
    ToolFailure,
    emit,
)

NodeKind = Literal["package", "extra", "group"]

# Environment variables that would silently change the lock check or the group selection the
# command states; the command's own flags are the only source of those choices.
_UV_OVERRIDES = (
    "UV_LOCKED",
    "UV_FROZEN",
    "UV_PROJECT",
    "UV_NO_DEV",
    "UV_NO_GROUP",
    "UV_NO_DEFAULT_GROUPS",
    "UV_PYTHON",
    "UV_SYSTEM_PYTHON",
    "UV_PROJECT_ENVIRONMENT",
)
_PATH_SEARCH_LIMIT = 50_000
"""Partial paths examined per distribution before path enumeration stops."""


# --- options ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class SelectionOptions:
    """The dependency groups a selection is read for. Platform and lock handling are fixed:
    every platform, lock read as it stands (see the module docstring)."""

    all_groups: bool = False
    groups: tuple[str, ...] = ()
    no_dev: bool = False

    def uv_arguments(self) -> list[str]:
        arguments = ["--frozen", "--universal"]
        if self.all_groups:
            arguments.append("--all-groups")
        for group in self.groups:
            arguments += ["--group", group]
        if self.no_dev:
            arguments.append("--no-dev")
        return arguments

    @property
    def group_selection(self) -> str:
        if self.all_groups:
            return "all"
        selection = "default" + "".join(f"+{group}" for group in self.groups)
        return selection + ("-dev" if self.no_dev else "")

    def describe(self) -> str:
        return f"platform=universal groups={self.group_selection} lock=unverified"

    def notes(self) -> list[str]:
        return [
            f"selection scope: {self.describe()} (every platform: edges keep their markers and "
            "are not filtered to this machine)",
            "uv.lock was read as it stands (`uv tree --frozen`) and not verified against the "
            "pyproject.toml files: uv verifies a lock only by running the project environment's "
            "interpreter, which this tool never does (D2); run `uv lock --check` yourself to "
            "verify it",
        ]


# --- the graph -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Edge:
    target: str
    marker: str | None


@dataclass(frozen=True)
class Node:
    id: str
    name: str
    version: str | None
    kind: NodeKind
    qualifier: str | None
    """The extra or group name for an extra or group node."""
    source: str | None
    dependencies: tuple[Edge, ...]


class UvSchemaChanged(ValueError):
    """The uv document lacks a field this reader relies on."""


def _require(mapping: Any, key: str, where: str) -> Any:
    if not isinstance(mapping, dict) or key not in mapping:
        raise UvSchemaChanged(f"{where} has no `{key}`")
    return mapping[key]


def _kind(raw: Any, where: str) -> tuple[NodeKind | Literal["workspace"] | None, str | None]:
    if raw in ("package", "workspace"):
        return raw, None
    if isinstance(raw, dict) and len(raw) == 1:
        ((key, value),) = raw.items()
        if key in ("extra", "group") and isinstance(value, str):
            return key, value
    return None, json.dumps(raw)


@dataclass(frozen=True)
class SelectionGraph:
    """uv's resolved graph for one project and scope, walked upward from distributions."""

    members: frozenset[str]
    nodes: Mapping[str, Node]
    unknown_kinds: tuple[str, ...] = ()
    cycles_cut: set[str] = field(default_factory=set, compare=False)
    """Distributions whose path count met a dependency cycle (filled in while counting)."""

    @classmethod
    def from_document(cls, document: Any) -> SelectionGraph:
        """Read the fields this module relies on; `UvSchemaChanged` names a missing one."""
        members = _require(document, "members", "the uv tree document")
        resolution = _require(document, "resolution", "the uv tree document")
        if not isinstance(members, list) or not isinstance(resolution, dict):
            raise UvSchemaChanged("`members` is not a list or `resolution` is not a map")
        member_names = frozenset(
            normalize_name(_require(member, "name", "a member")) for member in members
        )
        nodes: dict[str, Node] = {}
        unknown: set[str] = set()
        for node_id, raw in resolution.items():
            where = f"resolution node {node_id}"
            kind, qualifier = _kind(_require(raw, "kind", where), where)
            dependencies = _require(raw, "dependencies", where)
            if kind == "workspace":
                continue
            if kind is None:
                unknown.add(qualifier or "")
                continue
            source = _require(raw, "source", where)
            nodes[node_id] = Node(
                id=node_id,
                name=normalize_name(_require(raw, "name", where)),
                version=_require(raw, "version", where),
                kind=kind,
                qualifier=qualifier,
                source=next(iter(source), None) if isinstance(source, dict) else None,
                dependencies=tuple(
                    Edge(
                        target=_require(edge, "id", f"a dependency of {node_id}"),
                        marker=edge.get("marker"),
                    )
                    for edge in dependencies
                ),
            )
        return cls(members=member_names, nodes=nodes, unknown_kinds=tuple(sorted(unknown)))

    @cached_property
    def parents(self) -> Mapping[str, tuple[Edge, ...]]:
        """Node id -> the edges into it, each naming the dependent (`Edge.target` is the
        dependent here). Edges to ids missing from the graph are dropped."""
        incoming: defaultdict[str, list[Edge]] = defaultdict(list)
        for node in self.nodes.values():
            for edge in node.dependencies:
                if edge.target in self.nodes:
                    incoming[edge.target].append(Edge(target=node.id, marker=edge.marker))
        return {
            node_id: tuple(sorted(edges, key=lambda e: (self.label(e.target), e.marker or "")))
            for node_id, edges in incoming.items()
        }

    @cached_property
    def _by_name(self) -> Mapping[str, tuple[Node, ...]]:
        grouped: defaultdict[str, list[Node]] = defaultdict(list)
        for node in self.nodes.values():
            grouped[node.name].append(node)
        return {name: tuple(nodes) for name, nodes in grouped.items()}

    def member_owned(self, node_id: str) -> bool:
        return self.nodes[node_id].name in self.members

    def label(self, node_id: str) -> str:
        """`name`, `name[extra]` or `member:group`; `==version` when a name has several
        package versions in the graph (a universal resolution with forks)."""
        node = self.nodes[node_id]
        versions = {n.version for n in self._by_name[node.name] if n.kind == "package"}
        pinned = f"=={node.version}" if len(versions) > 1 else ""
        if node.kind == "extra":
            return f"{node.name}[{node.qualifier}]{pinned}"
        if node.kind == "group":
            return f"{node.name}:{node.qualifier}"
        return f"{node.name}{pinned}"

    def packages(self, name: str) -> tuple[Node, ...]:
        """The package nodes of a distribution (one per selected version)."""
        nodes = self._by_name.get(normalize_name(name), ())
        return tuple(sorted((n for n in nodes if n.kind == "package"), key=lambda n: n.id))

    def is_selected(self, name: str) -> bool:
        return bool(self.packages(name))

    def selected_extras(self, name: str, version: str | None = None) -> tuple[str, ...]:
        """The extras of a distribution that the resolution selects (their own nodes)."""
        nodes = self._by_name.get(normalize_name(name), ())
        return tuple(
            sorted(
                {
                    n.qualifier or ""
                    for n in nodes
                    if n.kind == "extra" and (version is None or n.version == version)
                }
            )
        )

    def close_names(self, name: str) -> tuple[str, ...]:
        return tuple(difflib.get_close_matches(normalize_name(name), self._by_name, n=5))

    # --- walks ---------------------------------------------------------------------------

    def reach_nodes(self, package: Node) -> list[str]:
        """The package node and its extra nodes of the same version: what a member reaches."""
        return [
            n.id
            for n in self._by_name[package.name]
            if n.version == package.version and n.kind in ("package", "extra")
        ]

    def ancestors(self, package: Node) -> set[str]:
        """Every node with a path to the package, not walking past member-owned nodes."""
        seen: set[str] = set()
        stack = list(self.reach_nodes(package))
        while stack:
            current = stack.pop()
            for edge in self.parents.get(current, ()):
                if edge.target not in seen:
                    seen.add(edge.target)
                    if not self.member_owned(edge.target):
                        stack.append(edge.target)
        return seen

    @cached_property
    def _member_distance(self) -> Mapping[str, int]:
        """Shortest number of edges from a member-owned node down to each node."""
        distance = {node_id: 0 for node_id in self.nodes if self.member_owned(node_id)}
        frontier = sorted(distance)
        while frontier:
            following = []
            for node_id in frontier:
                for edge in self.nodes[node_id].dependencies:
                    if edge.target in self.nodes and edge.target not in distance:
                        distance[edge.target] = distance[node_id] + 1
                        following.append(edge.target)
            frontier = following
        return distance

    def shortest_paths(self, package: Node, count: int) -> list[str]:
        """Up to `count` simple paths from a member-owned node to the package, shortest
        first (best-first search with the exact distance to a member as its estimate),
        rendered member first; `a >[marker] b` marks a conditional edge."""
        if count == 0:
            return []
        distance = self._member_distance
        start = package.id
        found: list[tuple[int, tuple[str, ...], str]] = []
        # (estimated length, labels, node ids from the package upward, marker of each edge)
        queue: list[tuple[int, tuple[str, ...], tuple[str, ...], tuple[str | None, ...]]] = [
            (distance.get(start, 0), (self.label(start),), (start,), ())
        ]
        examined = 0
        while queue and len(found) < count and examined < _PATH_SEARCH_LIMIT:
            _, labels, path, markers = heapq.heappop(queue)
            examined += 1
            head = path[-1]
            if head != start and self.member_owned(head):
                found.append((len(path), labels, self._render(path, markers)))
                continue
            for edge in self.parents.get(head, ()):
                if edge.target in path or edge.target not in distance:
                    continue
                heapq.heappush(
                    queue,
                    (
                        len(path) + distance[edge.target],
                        (*labels, self.label(edge.target)),
                        (*path, edge.target),
                        (*markers, edge.marker),
                    ),
                )
        return [text for _, _, text in sorted(found)]

    def _render(self, path: tuple[str, ...], markers: tuple[str | None, ...]) -> str:
        """`path` runs from the package up to a member; `markers[i]` is on the edge from
        `path[i + 1]` to `path[i]`."""
        text = self.label(path[-1])
        for index in range(len(path) - 2, -1, -1):
            marker = markers[index]
            text += f" >[{marker}] " if marker else " > "
            text += self.label(path[index])
        return text

    def path_count(self, package: Node) -> int:
        """Simple paths from member-owned nodes to the package; an edge closing a dependency
        cycle is not followed (the package is then recorded in `cycles_cut`)."""
        memo: dict[str, int] = {}

        def count(node_id: str, stack: frozenset[str]) -> int:
            if node_id != package.id and self.member_owned(node_id):
                return 1
            if node_id in memo:
                return memo[node_id]
            total = 0
            for edge in self.parents.get(node_id, ()):
                if edge.target in stack:
                    self.cycles_cut.add(package.name)
                    continue
                total += count(edge.target, stack | {edge.target})
            memo[node_id] = total
            return total

        return count(package.id, frozenset({package.id}))

    def unconditional(self, package: Node) -> bool:
        """Whether some path from a member-owned node reaches the package with no marker on
        any edge."""
        seen: set[str] = set()
        stack = [package.id]
        while stack:
            current = stack.pop()
            for edge in self.parents.get(current, ()):
                if edge.marker or edge.target in seen:
                    continue
                if self.member_owned(edge.target):
                    return True
                seen.add(edge.target)
                stack.append(edge.target)
        return False


# --- running uv ------------------------------------------------------------------------------


@dataclass(frozen=True)
class UvTree:
    graph: SelectionGraph
    uv_version: str
    options: SelectionOptions
    project: Project


def _uv_environment() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key not in _UV_OVERRIDES}


def _uv() -> str:
    uv = shutil.which("uv")
    if uv is None:
        raise ToolFailure(
            "uv_not_found",
            "uv is not on PATH; selection facts come from `uv tree`",
            "Install uv or put it on PATH, then run the command again.",
        )
    return uv


def uv_version(uv: str | None = None) -> str:
    completed = subprocess.run(
        [uv or _uv(), "--version"], capture_output=True, text=True, check=False
    )
    match = re.match(r"uv (\S+)", completed.stdout.strip())
    return match[1] if match else "unknown"


def uv_tree_command(uv: str, project: Project, options: SelectionOptions) -> list[str]:
    return [
        uv,
        "tree",
        "--project",
        str(project.root),
        *options.uv_arguments(),
        "--offline",
        "--no-python-downloads",
        "--color",
        "never",
        "--format",
        "json",
        "--preview-features",
        "json-output",
    ]


def run_uv_tree(project: Project, options: SelectionOptions) -> tuple[Any, str]:
    """Run `uv tree --format json` for the project; the parsed document and uv's version.
    A uv failure is a `ToolFailure`."""
    uv = _uv()
    version = uv_version(uv)
    completed = subprocess.run(
        uv_tree_command(uv, project, options),
        capture_output=True,
        text=True,
        check=False,
        env=_uv_environment(),
    )
    message = " ".join(
        line.strip()
        for line in completed.stderr.splitlines()
        if line.strip().startswith(("error", "hint", "Caused by", "warning"))
    )
    if completed.returncode != 0:
        raise ToolFailure(
            "uv_failed",
            f"`uv tree` failed in {project.root.as_posix()} (uv {version}, exit "
            f"{completed.returncode}): {message or completed.stderr.strip()[-500:]}",
            "Fix the condition uv reports; the full uv command is "
            + " ".join(uv_tree_command("uv", project, options)),
        )
    try:
        document = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ToolFailure(
            "uv_schema_changed",
            f"`uv tree --format json` (uv {version}) did not print JSON: {error}",
            "Check the uv version; the json-output preview format may have changed.",
        ) from error
    return document, version


def load_selection(project: Project, options: SelectionOptions | None = None) -> UvTree:
    """uv's graph for a locked project and scope; reusable by other commands (`metadata`,
    `compare`). Raises `ToolFailure` when uv cannot establish it."""
    options = options or SelectionOptions()
    document, version = run_uv_tree(project, options)
    try:
        graph = SelectionGraph.from_document(document)
    except UvSchemaChanged as error:
        raise ToolFailure(
            "uv_schema_changed",
            f"`uv tree --format json` (uv {version}, preview schema) changed: {error}",
            "Update the selection reader to the new schema and its contract test.",
        ) from error
    return UvTree(graph=graph, uv_version=version, options=options, project=project)


def selected_extras(graph: SelectionGraph, distribution: str) -> tuple[str, ...]:
    """The extras of `distribution` that the project's resolution selects."""
    return graph.selected_extras(distribution)


# --- the command -----------------------------------------------------------------------------


class SelectionItem(Item):
    kind: Literal["selection"] = "selection"
    distribution: str
    version: str | None
    selected: bool
    direct: bool
    """A member (or one of its extras or groups) depends on it, or on one of its extras."""
    workspace_member: bool
    source: str | None
    selected_extras: list[str]
    required_by: list[str]
    """The immediate dependents, labelled as in `paths`."""
    via_groups: list[str]
    """Member dependency groups from which a path reaches the distribution."""
    via_extras: list[str]
    """Other packages' selected extras through which a path reaches the distribution."""
    markers: list[str]
    """Distinct markers on the edges into the distribution and its extras."""
    unconditional: bool | None
    """Whether some path from a member has no marker on any edge; null when not selected."""
    path_count: int
    paths: list[str]
    """The shortest paths, member first; `a >[marker] b` marks a conditional edge."""
    scope: str

    columns: ClassVar = (
        Column("distribution"),
        Column("version"),
        Column("selected"),
        Column("direct"),
        Column("selected_extras", "extras"),
        Column("via_groups", "groups"),
        Column("required_by", "required by"),
        Column("path_count", "paths"),
        Column("paths", "shortest paths"),
    )
    sort_fields: ClassVar = ("distribution", "version")


def selection_items(
    graph: SelectionGraph, requested: Iterable[str], options: SelectionOptions, paths: int
) -> list[SelectionItem]:
    items = []
    for name in dict.fromkeys(normalize_name(name) for name in requested):
        packages = graph.packages(name)
        if not packages:
            items.append(
                SelectionItem(
                    distribution=name,
                    version=None,
                    selected=False,
                    direct=False,
                    workspace_member=name in graph.members,
                    source=None,
                    selected_extras=[],
                    required_by=[],
                    via_groups=[],
                    via_extras=[],
                    markers=[],
                    unconditional=None,
                    path_count=0,
                    paths=[],
                    scope=options.describe(),
                )
            )
            continue
        for package in packages:
            starts = graph.reach_nodes(package)
            incoming = [edge for start in starts for edge in graph.parents.get(start, ())]
            ancestors = graph.ancestors(package)
            own_extras = set(starts) - {package.id}
            items.append(
                SelectionItem(
                    distribution=name,
                    version=package.version,
                    selected=True,
                    direct=any(graph.member_owned(edge.target) for edge in incoming),
                    workspace_member=name in graph.members,
                    source=package.source,
                    selected_extras=list(graph.selected_extras(name, package.version)),
                    required_by=sorted(
                        {graph.label(edge.target) for edge in incoming}
                        - set(map(graph.label, own_extras))
                    ),
                    via_groups=sorted(
                        graph.label(n) for n in ancestors if graph.nodes[n].kind == "group"
                    ),
                    via_extras=sorted(
                        graph.label(n)
                        for n in ancestors - own_extras
                        if graph.nodes[n].kind == "extra"
                    ),
                    markers=sorted({edge.marker for edge in incoming if edge.marker}),
                    unconditional=graph.unconditional(package),
                    path_count=graph.path_count(package),
                    paths=graph.shortest_paths(package, paths),
                    scope=options.describe(),
                )
            )
    return items


def selection_notes(
    graph: SelectionGraph, items: Sequence[SelectionItem], options: SelectionOptions, paths: int
) -> list[str]:
    notes = options.notes()
    for item in items:
        if not item.selected:
            close = [
                name for name in graph.close_names(item.distribution) if name != item.distribution
            ]
            notes.append(
                f"{item.distribution}: not in the resolution for this scope"
                + (f"; names close to it: {', '.join(close)}" if close else "")
            )
    if any(item.path_count > len(item.paths) for item in items):
        notes.append(
            f"paths lists at most {paths} shortest paths per distribution (--paths); "
            "path_count is the total"
        )
    if graph.cycles_cut:
        notes.append(
            "dependency cycles met while counting paths for "
            f"{', '.join(sorted(graph.cycles_cut))}; edges closing a cycle were not followed"
        )
    if graph.unknown_kinds:
        notes.append(
            f"uv emitted node kinds this reader does not know, ignored: {', '.join(graph.unknown_kinds)}"
        )
    return notes


DistributionsArg = Annotated[
    list[str], typer.Argument(help="Distribution names, in any spelling (PEP 503 normalized).")
]


def selection(
    ctx: typer.Context,
    distributions: DistributionsArg,
    all_groups: Annotated[
        bool, typer.Option("--all-groups", help="Include every dependency group.")
    ] = False,
    group: Annotated[
        list[str] | None,
        typer.Option("--group", help="Include this dependency group (repeatable)."),
    ] = None,
    no_dev: Annotated[
        bool, typer.Option("--no-dev", help="Exclude the development dependency group.")
    ] = False,
    paths: Annotated[
        int,
        typer.Option("--paths", min=0, max=1000, help="Shortest paths shown per distribution."),
    ] = 5,
    json: JsonOpt = False,
    limit: LimitOpt = DEFAULT_LIMIT,
    offset: OffsetOpt = 0,
    strict: StrictOpt = False,
) -> None:
    """Direct or transitive selection, dependency paths, extras and groups, from uv: every
    platform (edges keep their markers), uv.lock read as it stands and not verified."""
    state = library_state(ctx)
    project = state.target.require_project()
    options = SelectionOptions(all_groups=all_groups, groups=tuple(group or ()), no_dev=no_dev)
    tree = load_selection(project, options)
    items = selection_items(tree.graph, distributions, options, paths)
    emit(
        library_envelope(
            ctx,
            SelectionItem,
            items,
            limit=limit,
            offset=offset,
            authorities={"uv": tree.uv_version},
            scanned=len(tree.graph.nodes),
            notes=selection_notes(tree.graph, items, options, paths),
        ),
        json=json,
        strict=strict,
    )


def register(group: typer.Typer) -> None:
    group.command("selection")(selection)
