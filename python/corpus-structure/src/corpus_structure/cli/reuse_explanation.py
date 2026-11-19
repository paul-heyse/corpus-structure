"""Terminal rendering of the same bounded local explanation delivered as JSON."""

from rich.console import Group
from rich.text import Text
from rich.tree import Tree


def render_reuse_explanation(report):
    if report.availability == "unavailable":
        return Text(report.reason or "Reuse explanation unavailable")
    root = Tree("Code reuse")
    for record in report.reports:
        node = root.add(
            f"{record.entry_point} · {record.tier} · {record.outcome} · process {record.process_id}"
        )
        node.add("eligible" if record.eligible else "reuse withheld")
        for fact in record.facts:
            site = fact.module or fact.semantic_owner
            if fact.line is not None:
                site += ":" + str(fact.line)
            item = node.add(f"{fact.standing} · {site} · {fact.reason}")
            if fact.dependency_path:
                item.add(" → ".join(fact.dependency_path))
        if record.omitted:
            node.add(str(record.omitted) + " facts omitted")
        if record.next_action:
            node.add(record.next_action)
    return root


def with_reuse(renderable, report):
    return renderable if report is None else Group(renderable, render_reuse_explanation(report))


def emit_selected_result(result, *, json: bool, explain: bool):
    from typing import Any

    from pydantic import RootModel

    from corpus_structure.cli.output import emit, write_report_text
    from corpus_structure.semantic.code_reuse import ReuseExplanationReport
    from corpus_structure.semantic.data_operation_json import json_bytes

    if json or not explain:
        write_report_text(json_bytes(result).decode() + "\n")
        return

    def render(value):
        report = ReuseExplanationReport.model_validate(value.root["reuse_explanation"])
        body = {key: item for key, item in value.root.items() if key != "reuse_explanation"}
        return Group(Text(json_bytes(body).decode()), render_reuse_explanation(report))

    emit(RootModel[dict[str, Any]](result), json=False, render=render)
