"""Pure selections of existing located evidence; never validate the diagnosed input again."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import Any, Literal

from .correction_detail import _detail_limits
from .identity import canonical_bytes

DiagnosticView = Literal["summary", "correction", "document"]


def decode_diagnostic_document(document: Any) -> dict:
    """Decode the supported custody envelope and declared report version, without preparation."""
    from jsonschema import Draft202012Validator

    from .operation_reporting import report_schema

    if not isinstance(document, dict) or set(document) != {"version", "report", "members"}:
        raise ValueError("unsupported diagnostic artifact")
    if type(document["version"]) is not int or document["version"] != 1:
        raise ValueError("unsupported diagnostic artifact version")
    if not isinstance(document["report"], dict) or document["report"].get("report_version") != 5:
        raise ValueError("unsupported located report version")
    from jsonschema.exceptions import ValidationError

    try:
        Draft202012Validator(report_schema("LocatedValidationReport")).validate(document["report"])
    except ValidationError as error:
        raise ValueError("retained report differs from its supported schema") from error
    names = set()
    if not isinstance(document["members"], list):
        raise ValueError("diagnostic members must be a list")
    for member in document["members"]:
        if not isinstance(member, dict) or not all(
            isinstance(member.get(key), str)
            for key in ("name", "media_type", "sensitivity", "content", "digest")
        ):
            raise ValueError("invalid diagnostic member")
        if member["name"] in names or member["sensitivity"] not in {"safe", "raw"}:
            raise ValueError("invalid diagnostic member identity or sensitivity")
        names.add(member["name"])
        if sha256(member["content"].encode()).hexdigest() != member["digest"]:
            raise ValueError("diagnostic member digest differs")
    return document


def _provenance(document: dict) -> dict:
    member = next((m for m in document.get("members", ()) if m["name"] == "provenance"), None)
    if member is None:
        return {
            "sources": [],
            "contributors": [],
            "contributors_status": "unavailable",
            "reason": "Source provenance was not retained.",
        }
    value = json.loads(member["content"])
    if not isinstance(value, dict) or not isinstance(value.get("sources"), list):
        raise ValueError("invalid source provenance")
    return value


def source_excerpt(
    document: dict, module: str, *, raw_evidence: bool, start_line=1, lines=20, max_bytes=16384
) -> dict:
    """Read exact retained UTF-8 bytes; logical declaration paths never become physical lines."""
    if (
        type(start_line) is not int
        or start_line < 1
        or type(lines) is not int
        or not 1 <= lines <= 100
        or type(max_bytes) is not int
        or not 1024 <= max_bytes <= 65536
    ):
        raise ValueError("unsupported source excerpt bounds")
    records = [item for item in _provenance(document)["sources"] if item.get("module") == module]
    if len(records) != 1:
        return dict(
            module=module,
            availability="unavailable",
            reason="Exact retained source module is unavailable.",
        )
    record = records[0]
    base = dict(module=module, digest=record["digest"], availability=record["availability"])
    if not raw_evidence:
        return dict(
            base,
            availability="withheld",
            reason="Source excerpts require --raw-evidence and raw collection.",
        )
    member = next((m for m in document["members"] if m["name"] == record.get("member")), None)
    if member is None:
        return dict(base, reason=record.get("reason", "Source bytes were not collected."))
    content = member["content"]
    if sha256(content.encode()).hexdigest() != record["digest"]:
        raise ValueError("source member differs from its acquired digest")
    selected = []
    used = 0
    all_lines = content.splitlines(keepends=True)
    for line in all_lines[start_line - 1 : start_line - 1 + lines]:
        size = len(line.encode())
        if used + size > max_bytes:
            break
        selected.append(line)
        used += size
    return dict(
        base,
        availability="available",
        start_line=start_line,
        lines=len(selected),
        content="".join(selected),
        omitted=(start_line - 1 + len(selected) < len(all_lines)),
        location_basis="explicit source line; no line inferred from a logical declaration path",
    )


def select_diagnostic(
    document: dict,
    view: DiagnosticView,
    *,
    result_id: str | None = None,
    invocation: dict | None = None,
    max_errors=100,
    max_depth=8,
    max_bytes=262144,
    source: str | None = None,
    raw_evidence=False,
    source_line=1,
    source_lines=20,
    source_bytes=16384,
) -> dict:
    """Select already captured facts, preserving original outcome, bindings and unknowns."""
    _detail_limits(max_errors, max_depth, max_bytes)
    if view == "document":
        if source is not None:
            raise ValueError("source excerpts require the correction view")
        return document
    if view not in {"summary", "correction"}:
        raise ValueError("unknown diagnostic view")
    if source is not None and view != "correction":
        raise ValueError("source excerpts require the correction view")
    report = document["report"]
    evidence = {key: value for key, value in report.get("evidence", {}).items() if key != "content"}
    projection = {
        key: deepcopy(report[key])
        for key in (
            "report_version",
            "report_schema_digest",
            "validation_outcome",
            "release_id",
            "model_id",
            "complete",
            "presentation",
        )
        if key in report
    }
    projection["evidence"] = evidence
    selection: dict[str, Any] = dict(
        view=view,
        report=projection,
        result_id=result_id,
        invocation=invocation,
        captured_observations=len(report["observations"]),
        provenance=_provenance(document),
        omissions=[],
        next_reads=[],
    )
    bindings = {(item.get("operation"), item.get("scope")) for item in report["observations"]}
    known = {operation for operation, _scope in bindings if operation is not None}
    selection["operation_bindings"] = dict(
        standing="unavailable" if not known else "multiple" if len(bindings) > 1 else "recorded",
        basis="captured_observations_only",
        values=[
            dict(operation=operation, scope=scope)
            for operation, scope in sorted(bindings, key=lambda item: canonical_bytes(item))
        ],
    )
    if result_id:
        selection["next_reads"] = [
            f"ci schema diagnostic {result_id} --view document --json"
            + (" --raw-evidence" if raw_evidence else "")
        ]
    if view == "correction":
        nodes = report.get("correction_detail", {}).get("nodes", [])
        kept, depths, kept_ordinals = [], {}, set()
        for node in nodes:
            parent = node.get("parent")
            depth = 0 if parent is None else depths.get(parent, max_depth + 1) + 1
            depths[node["ordinal"]] = depth
            if (
                len(kept) >= max_errors
                or depth > max_depth
                or (parent is not None and parent not in kept_ordinals)
            ):
                selection["omissions"].append(
                    dict(ordinal=node["ordinal"], reason="requested count/depth selection")
                )
            else:
                kept.append(deepcopy(node))
                kept_ordinals.add(node["ordinal"])
        if nodes:
            roots = {
                node["ordinal"]: index
                for index, node in enumerate(n for n in nodes if n.get("parent") is None)
            }
            projection["observations"] = [
                deepcopy(report["observations"][roots[node["ordinal"]]])
                for node in kept
                if node.get("parent") is None
                and roots[node["ordinal"]] < len(report["observations"])
            ]
        else:
            projection["observations"] = deepcopy(report["observations"][:max_errors])
        if len(report["observations"]) > max_errors:
            selection["omissions"].append(dict(reason="observation count selection"))
        if "correction_detail" in report:
            projection["correction_detail"] = dict(
                deepcopy(report["correction_detail"]), nodes=kept
            )
        if source is not None:
            selection["source_excerpt"] = source_excerpt(
                document,
                source,
                raw_evidence=raw_evidence,
                start_line=source_line,
                lines=source_lines,
                max_bytes=source_bytes,
            )
    # Bound one selected forest by serialized prefix search, never re-normalizing it.
    if selection["omissions"]:
        selection["omissions"] = [
            dict(reason="requested count/depth selection", omitted=len(selection["omissions"]))
        ]
        projection["presentation"]["render_complete"] = False
        if "correction_detail" in projection:
            projection["correction_detail"]["render_complete"] = False
    if len(canonical_bytes(selection)) <= max_bytes:
        return selection
    selected_nodes = projection.get("correction_detail", {}).get("nodes", [])
    selected_observations = projection.get("observations", [])
    total = len(selected_nodes) if selected_nodes else len(selected_observations)

    def prefix(count):
        candidate = deepcopy(selection)
        body = candidate["report"]
        if selected_nodes:
            body["correction_detail"]["nodes"] = selected_nodes[:count]
            roots = sum(node.get("parent") is None for node in selected_nodes[:count])
            body["observations"] = selected_observations[:roots]
        elif "observations" in body:
            body["observations"] = selected_observations[:count]
        candidate["omissions"] = [
            *selection["omissions"],
            dict(
                reason="byte selection omitted captured detail",
                omitted=total - count,
                first_omitted_ordinal=selected_nodes[count]["ordinal"]
                if selected_nodes and count < total
                else None,
            ),
        ]
        body["presentation"]["render_complete"] = False
        if "correction_detail" in body:
            body["correction_detail"]["render_complete"] = False
        return candidate

    minimal = prefix(0)
    while len(canonical_bytes(minimal)) > max_bytes:
        if selection.get("source_excerpt", {}).get("content"):
            excerpt = selection["source_excerpt"]
            excerpt.pop("content")
            excerpt.update(
                availability="omitted", reason="source excerpt exceeds selection byte budget"
            )
        elif selection["provenance"].get("contributors") or selection["provenance"].get("sources"):
            selection["provenance"] = dict(
                sources=[],
                contributors=[],
                contributors_status="omitted",
                reason="provenance exceeds selection byte budget",
            )
        else:
            raise ValueError("diagnostic binding exceeds requested selection byte limit")
        minimal = prefix(0)
    low, high, best = 0, total + 1, minimal
    while low + 1 < high:
        middle = (low + high) // 2
        candidate = prefix(middle)
        if len(canonical_bytes(candidate)) <= max_bytes:
            low, best = middle, candidate
        else:
            high = middle
    return best
