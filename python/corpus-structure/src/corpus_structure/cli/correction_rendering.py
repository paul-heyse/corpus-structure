"""Literal human presentations of shared selections and the owned exception product."""

from __future__ import annotations

import json
from io import StringIO

from rich.console import Console, Group
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from corpus_structure._diagnostic_capture import safe_text
from corpus_structure.cli.exception_observations import ExceptionTrace, OmittedExceptionDetail


def _text(value) -> Text:
    return Text(safe_text(str(value)))


def _path(segments) -> str:
    return "#" + "".join(
        "/"
        + str(p.get("index") if p["kind"] == "index" else p.get("field", ""))
        .replace("~", "~0")
        .replace("/", "~1")
        for p in segments
    )


def render_correction(selection: dict) -> Group:
    report = selection["report"]
    table = Table.grid(padding=(0, 1))
    for name, value in (
        ("Outcome", report["validation_outcome"]),
        ("Release", report.get("release_id", "unavailable")),
        ("Model", report.get("model_id", "unavailable")),
        ("Assessment complete", report["complete"]),
        ("Presentation", json.dumps(report["presentation"], ensure_ascii=False)),
        ("Evidence", json.dumps(report.get("evidence", {}), ensure_ascii=False)),
    ):
        table.add_row(_text(name), _text(value))
    table.add_row(
        _text("Operation / scope bindings"),
        _text(json.dumps(selection["operation_bindings"], ensure_ascii=False)),
    )
    if selection.get("invocation"):
        table.add_row(_text("Invocation"), _text(json.dumps(selection["invocation"])))
    parts: list[Table | Tree | Text | Syntax] = [table]
    for index, item in enumerate(report.get("observations", ())):
        row = Table.grid(padding=(0, 1))
        row.add_row(_text(f"Observation {index}"), _text(f"{item['category']} · {item['code']}"))
        for label, key in (
            ("Instance", "input_path"),
            ("Declaration", "model_path"),
            ("Operation", "operation"),
            ("Scope", "scope"),
            ("Constraint", "native_constraint"),
            ("Message", "message"),
            ("Next inspection", "remedy"),
        ):
            if key in item:
                row.add_row(_text(label), _text(item[key]))
        parts.append(row)
    detail = report.get("correction_detail")
    if detail:
        tree = Tree(_text("Original-engine detail · " + detail["engine"]))
        branches = {}
        for node in detail["nodes"]:
            parent = node.get("parent")
            branch = branches.get(parent, tree).add(
                _text(f"{node['ordinal']} · {node['keyword']} · {node['message']}")
            )
            branches[node["ordinal"]] = branch
            branch.add(_text("Instance " + _path(node["input_path"])))
            branch.add(_text("Schema " + _path(node["schema_path"])))
            for key in ("rdf_json", "path_json"):
                if node.get(key) is not None:
                    branch.add(_text(node[key]))
        tree.add(_text("Coverage · " + detail["coverage_note"]))
        parts.append(tree)
    provenance = selection["provenance"]
    parts.append(
        _text("Source contributors · " + provenance.get("contributors_status", "unavailable"))
    )
    for contributor in provenance.get("contributors", ()):
        parts.append(_text(json.dumps(contributor, ensure_ascii=False)))
    for source in provenance.get("sources", ()):
        parts.append(
            _text(f"Source {source['module']} · {source['digest']} · {source['availability']}")
        )
    if provenance.get("reason"):
        parts.append(_text(provenance["reason"]))
    excerpt = selection.get("source_excerpt")
    if excerpt:
        parts.append(_text(f"Source excerpt {excerpt['module']} · {excerpt['availability']}"))
        if excerpt.get("content") is not None:
            parts.append(
                Syntax(
                    safe_text(excerpt["content"]),
                    "yaml",
                    line_numbers=True,
                    start_line=excerpt["start_line"],
                    word_wrap=True,
                )
            )
            parts.append(_text(excerpt["location_basis"]))
            if excerpt["omitted"]:
                parts.append(_text("Source excerpt omitted remaining lines."))
        elif excerpt.get("reason"):
            parts.append(_text(excerpt["reason"]))
    for omission in selection["omissions"]:
        parts.append(_text("Omitted · " + json.dumps(omission)))
    if not report["presentation"]["render_complete"]:
        parts.append(
            _text("Omitted detail · captured evidence or requested presentation is incomplete.")
        )
    for command in selection["next_reads"]:
        parts.append(_text("Next read · " + command))
    return Group(*parts)


def correction_text(selection: dict, *, width=100) -> str:
    stream = StringIO()
    Console(file=stream, width=width, color_system=None, force_terminal=False).print(
        render_correction(selection)
    )
    return stream.getvalue()


def render_exception(
    trace: ExceptionTrace, *, invocation: str | None = None, stage: str | None = None
) -> Group:
    """Consume the observation owner's exact typed trace; never classify it as validation."""
    tree = Tree(
        _text(
            f"Unexpected exception · invocation={invocation or 'unavailable'} "
            f"· stage={stage or 'unavailable'}"
        )
    )

    def omitted(branch, item):
        branch.add(_text(f"Omitted · {item.path}: {item.reason}"))

    def visit(product: ExceptionTrace, branch):
        branch.add(_text("Chain order · " + product.chain_order))
        for stack in product.stacks:
            if isinstance(stack, OmittedExceptionDetail):
                omitted(branch, stack)
                continue
            child = branch.add(
                _text(
                    f"{stack.exc_type}: {stack.exc_value}" + (" (cause)" if stack.is_cause else "")
                )
            )
            for note in stack.exc_notes:
                child.add(_text("Note · " + note))
            for frame in stack.frames:
                if isinstance(frame, OmittedExceptionDetail):
                    omitted(child, frame)
                else:
                    child.add(_text(f"{frame.filename}:{frame.lineno} · {frame.name}"))
            if stack.syntax_error:
                child.add(_text(json.dumps(stack.syntax_error, ensure_ascii=False)))
            for grouped in stack.exceptions:
                if isinstance(grouped, OmittedExceptionDetail):
                    omitted(child, grouped)
                else:
                    visit(grouped, child.add(_text("Grouped exception")))
            for item in stack.omissions:
                omitted(child, item)
        for item in product.omissions:
            omitted(branch, item)

    visit(trace, tree)
    return Group(tree)
