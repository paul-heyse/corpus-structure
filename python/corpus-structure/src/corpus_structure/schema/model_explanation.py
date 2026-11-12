"""Bounded explanations of retained model-change facts, without executing authored SQL."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class NativeOperationExplanation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    ordinal: int
    identity: dict[str, JsonValue]
    action: Literal["create", "change", "retire", "recreate"]
    changed_properties: tuple[str, ...]
    before_owner: str | None
    after_owner: str | None
    before_source: str | None
    after_source: str | None
    owner_bindings: dict[str, JsonValue]
    before_acl: JsonValue
    after_acl: JsonValue
    dependencies: dict[str, JsonValue]


class NativeOperationPage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal["native-operation-explanation-1"] = "native-operation-explanation-1"
    candidate_id: str
    binding: dict[str, JsonValue] = Field(default_factory=dict)
    total: int
    items: tuple[NativeOperationExplanation, ...]
    next_after: int | None


def explain_native_operations(
    raw: bytes, candidate_id: str, *, after: int = 0, limit: int = 20, binding=None
):
    if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("invalid native operation page selection")
    payload = json.loads(raw)
    if payload.get("version") != 1 or not isinstance(payload.get("operations"), list):
        raise ValueError("unsupported frozen native operation artifact")
    operations = payload["operations"]
    if after > len(operations):
        raise ValueError("native operation continuation is outside its population")
    output = []
    for ordinal, item in enumerate(operations[after : after + limit], after + 1):
        before, current = item.get("before"), item.get("after")
        old = before.get("catalog", {}) if before else {}
        new = current.get("catalog", {}) if current else {}
        selected = current or before
        if item.get("version") not in {1, 2} or not selected:
            raise ValueError("unsupported frozen native transition")
        output.append(
            NativeOperationExplanation(
                ordinal=ordinal,
                identity=selected["identity"],
                action="recreate"
                if item.get("recreate")
                else "create"
                if before is None
                else "retire"
                if current is None
                else "change",
                changed_properties=tuple(
                    sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
                ),
                before_owner=old.get("owner"),
                after_owner=new.get("owner"),
                before_source=before.get("source") if before else None,
                after_source=current.get("source") if current else None,
                owner_bindings={
                    "before": before.get("role_bindings", {}) if before else None,
                    "after": current.get("role_bindings", {}) if current else None,
                },
                before_acl=old.get("acl"),
                after_acl=new.get("acl"),
                dependencies={
                    "before": old.get("dependencies"),
                    "after": new.get("dependencies"),
                    "basis": "frozen catalog observations; null means unrecorded",
                },
            )
        )
    page = NativeOperationPage(
        candidate_id=candidate_id,
        binding=binding or {},
        total=len(operations),
        items=tuple(output),
        next_after=after + len(output) if after + len(output) < len(operations) else None,
    )
    if len(page.model_dump_json().encode()) > 128 * 1024:
        raise ValueError("native operation explanation exceeds byte bound; narrow the page")
    return page


class SQLStatementFact(BaseModel):
    ordinal: int
    kind: str
    start: int | None
    end: int | None
    excerpt: str
    excerpt_truncated: bool
    node_kinds: tuple[str, ...]


class SQLSourceFact(BaseModel):
    source: str
    sha256: str
    text: str
    parser_version: str | None = None
    status: Literal["parsed", "refused", "unavailable"]
    statements: tuple[SQLStatementFact, ...] = ()
    reason: str | None = None
    position: int | None = None


class SQLChangeFact(BaseModel):
    identity: str
    before: SQLSourceFact | None = None
    after: SQLSourceFact | None = None
    structural_edits: tuple[dict[str, JsonValue], ...] = ()
    structural_status: str = "unavailable"


class ModelChangeExplanation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal["model-change-explanation-1"] = "model-change-explanation-1"
    source_basis: str
    custody: dict[str, JsonValue] = Field(default_factory=dict)
    changes: tuple[SQLChangeFact, ...] = ()
    diagnostics: tuple[dict[str, JsonValue], ...] = ()
    impact: dict[str, JsonValue] | None = None
    native_observation: str = "not_observed"


def sql_source_fact(source: str, text: str) -> SQLSourceFact:
    """Inspect a private syntax clone; no query execution or native binding claim."""
    from hashlib import sha256

    from pglast.visitors import Visitor

    from corpus_structure.semantic.prepared_sql import SQLSyntaxError, prepare_sql

    digest = sha256(text.encode()).hexdigest()
    if len(text.encode()) > 4 * 1024 * 1024:
        return SQLSourceFact(
            source=source,
            sha256=digest,
            text=text,
            status="unavailable",
            reason="source exceeds syntax-inspection byte bound",
        )
    try:
        prepared = prepare_sql(text, source=source)
    except SQLSyntaxError as error:
        # Captured SQL templates are not rendered statements. Preserve their original bytes.
        import re

        template = re.search(r"\{[a-z_]+\}", text) is not None
        return SQLSourceFact(
            source=source,
            sha256=digest,
            text=text,
            status="unavailable" if template else "refused",
            reason="unexpanded source template" if template else str(error),
            position=error.position,
        )

    class Kinds(Visitor):
        def __init__(self):
            super().__init__()
            self.kinds = set()
            self.visit = self.observe

        def observe(self, ancestors, node):
            self.kinds.add(type(node).__name__)

    facts = []
    for ordinal, (tree, span) in enumerate(
        zip(prepared.private_tree(), prepared.slices, strict=True), 1
    ):
        kinds = Kinds()
        kinds(tree)
        excerpt = prepared.excerpt(ordinal - 1)
        facts.append(
            SQLStatementFact(
                ordinal=ordinal,
                kind=type(tree.stmt).__name__,
                start=span.start,
                end=span.stop,
                excerpt=excerpt[:3000],
                excerpt_truncated=len(excerpt) > 3000,
                node_kinds=tuple(sorted(kinds.kinds)),
            )
        )
    return SQLSourceFact(
        source=source,
        sha256=digest,
        text=text,
        status="parsed",
        parser_version=prepared.parser_version,
        statements=tuple(facts),
    )


def sql_change(identity: str, before: str | None, after: str | None) -> SQLChangeFact:
    old = sql_source_fact(identity + ":before", before) if before is not None else None
    new = sql_source_fact(identity + ":after", after) if after is not None else None
    edits = []
    status = "unavailable: structural diff supports single parsed SELECTs"
    if (
        old
        and new
        and old.status == new.status == "parsed"
        and len(old.statements) == len(new.statements) == 1
        and old.statements[0].kind == new.statements[0].kind == "SelectStmt"
    ):
        import sqlglot

        try:
            source_tree = sqlglot.parse_one(old.text, read="postgres")
            target_tree = sqlglot.parse_one(new.text, read="postgres")
            for edit in sqlglot.diff(source_tree, target_tree, delta_only=True):
                # Rendered expressions describe structural edits, never original source coordinates.
                row = {"kind": type(edit).__name__, "coordinate_space": "structural_expression"}
                for name in ("source", "target", "expression"):
                    expression = getattr(edit, name, None)
                    if expression is not None:
                        row[name] = expression.sql(dialect="postgres")[:3000]
                        # Stable argument/index paths distinguish equal expressions. The namespace
                        # identifies the captured side; runtime object IDs are never retained.
                        parts = []
                        root = expression
                        while root.parent is not None:
                            part = root.arg_key
                            if root.index is not None:
                                part += f"[{root.index}]"
                            parts.append(part)
                            root = root.parent
                        side = (
                            "before"
                            if root is source_tree
                            else "after"
                            if root is target_tree
                            else None
                        )
                        row[name + "_reference"] = (
                            identity
                            + ":"
                            + side
                            + ":$"
                            + ("." + ".".join(reversed(parts)) if parts else "")
                            if side
                            else "unavailable"
                        )
                edits.append(row)
            status = "available; edit descriptions do not establish equivalence"
        except sqlglot.errors.SqlglotError as error:
            status = "unavailable: " + str(error)[:1000]
    return SQLChangeFact(
        identity=identity,
        before=old,
        after=new,
        structural_edits=tuple(sorted(edits, key=lambda item: json.dumps(item, sort_keys=True))),
        structural_status=status,
    )


def capture_sql_changes(root, baseline: str, packs=()) -> ModelChangeExplanation:
    """Capture changed source text at preparation, never at later inspection."""
    import re
    import subprocess
    from pathlib import Path

    from corpus_structure.schema import preparation

    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name) for name in packs):
        raise ValueError("SQL explanation packs must be direct named domains")
    prefix = preparation.PACKAGE_PATH / "semantic" / "sql"
    roots = [str(prefix), *(str(Path("domains") / name) for name in packs)]
    command = ["git", "-C", str(root)]
    resolved = subprocess.run(
        [*command, "rev-parse", "--verify", "--end-of-options", f"{baseline}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    if resolved.returncode:
        raise ValueError("SQL explanation baseline is unavailable")
    baseline = resolved.stdout.decode().strip()
    names = (
        subprocess.run([*command, "ls-files", "-z", "--", *roots], capture_output=True, check=True)
        .stdout.decode()
        .split("\0")
    )
    names.extend(
        subprocess.run(
            [*command, "ls-tree", "-r", "--name-only", "-z", baseline, "--", *roots],
            capture_output=True,
            check=True,
        )
        .stdout.decode()
        .split("\0")
    )
    names.extend(
        str(path.relative_to(root))
        for selected in roots
        for path in (root / selected).rglob("*.sql")
        if path.is_file() and path.resolve().is_relative_to(root)
    )
    changes = []
    for name in sorted({n for n in names if n.endswith(".sql")}):
        old = subprocess.run(
            [*command, "show", f"{baseline}:{name}"], capture_output=True, check=False
        )
        before = old.stdout.decode() if old.returncode == 0 else None
        path = root / name
        after = path.read_bytes().decode("utf-8") if path.is_file() else None
        if before != after:
            changes.append(sql_change(name, before, after))
    return ModelChangeExplanation(
        source_basis=f"captured baseline {baseline}/worktree SQL at preparation",
        changes=tuple(changes),
    )


def explanation_from_native(raw: bytes, previous: ModelChangeExplanation | None = None):
    from corpus_structure.semantic.native_objects import native_sql_script

    payload = json.loads(raw)
    changes = list(previous.changes if previous else ())
    for ordinal, item in enumerate(payload.get("operations", ()), 1):
        sides = []
        for side in ("before", "after"):
            obj = item.get(side)
            sides.append(native_sql_script(obj.get("statements", ())) if obj is not None else None)
        changes.append(sql_change(f"frozen-operation:{ordinal}", *sides))
    return ModelChangeExplanation(
        source_basis="retained preview source plus frozen native transitions",
        custody=previous.custody if previous else {},
        changes=tuple(changes),
        diagnostics=previous.diagnostics if previous else (),
        impact=previous.impact if previous else None,
        native_observation="rollback-only candidate catalog observation; not deployment",
    )


class SQLExplanationPage(BaseModel):
    version: Literal["model-change-explanation-1"] = "model-change-explanation-1"
    result_id: str
    source_basis: str
    custody: dict[str, JsonValue]
    total: int
    items: tuple[dict[str, JsonValue], ...]
    diagnostics: tuple[dict[str, JsonValue], ...]
    impact: dict[str, JsonValue] | None
    native_observation: str
    next_after: int | None


def retained_text_changes(change: SQLChangeFact) -> dict[str, JsonValue]:
    """Focus display on actual changed text in retained bytes, without reanalysis."""
    from difflib import SequenceMatcher
    from itertools import accumulate

    old = change.before.text if change.before else ""
    new = change.after.text if change.after else ""
    old_lines, new_lines = old.splitlines(keepends=True), new.splitlines(keepends=True)
    basis = "textual line edits in retained source; not semantic analysis"
    if max(len(old_lines), len(new_lines)) > 20_000:
        return dict(
            basis=basis,
            status="unavailable",
            reason="text display line bound exceeded",
            items=[],
            truncated=True,
        )
    offsets = tuple(
        tuple(accumulate((len(line) for line in lines), initial=0))
        for lines in (old_lines, new_lines)
    )
    output = []
    total = 0
    for kind, i1, i2, j1, j2 in SequenceMatcher(None, old_lines, new_lines).get_opcodes():
        if kind == "equal":
            continue
        total += 1
        if len(output) == 8:
            continue
        left, right = "".join(old_lines[i1:i2]), "".join(new_lines[j1:j2])
        common = next(
            (
                index
                for index, pair in enumerate(zip(left, right, strict=False))
                if pair[0] != pair[1]
            ),
            min(len(left), len(right)),
        )

        def excerpt(text, start, end, side, common=common):
            # A long unchanged line prefix must not hide the actual changed token.
            focus = max(0, min(common, len(text)) - 120)
            shown = text[focus:].encode("utf-8")[:2000].decode("utf-8", errors="ignore")
            return dict(
                start_line_1based=start + 1,
                end_line_exclusive_1based=end + 1,
                changed_start_character=offsets[side][start],
                changed_end_character=offsets[side][end],
                excerpt_start_character=offsets[side][start] + focus,
                excerpt_end_character=offsets[side][start] + focus + len(shown),
                excerpt=shown,
                omitted_before=focus > 0,
                omitted_after=focus + len(shown) < len(text),
            )

        output.append(
            dict(kind=kind, before=excerpt(left, i1, i2, 0), after=excerpt(right, j1, j2, 1))
        )
    return dict(
        basis=basis,
        status="available",
        coordinate_space="original_source_text",
        total=total,
        items=output,
        truncated=total > len(output),
    )


def comparison_summary(comparison):
    """Keep detail inventories in their retained owner, with explicit display coverage."""
    if comparison is None:
        return None
    changes = comparison.get("changes", ())
    return {
        "before_release": comparison.get("before_release"),
        "after_release": comparison.get("after_release"),
        "total_changes": len(changes),
        "changes": [
            {key: str(item.get(key, ""))[:256] for key in ("kind", "model_ref")}
            for item in changes[:8]
        ],
        "truncated": len(changes) > 8,
    }


def explanation_page(
    explanation: ModelChangeExplanation, result_id: str, *, after: int = 0, limit: int = 20
):
    if (
        type(after) is not int
        or after < 0
        or not 1 <= limit <= 100
        or after > len(explanation.changes)
    ):
        raise ValueError("invalid SQL explanation page selection")
    items = []
    for ordinal, change in enumerate(explanation.changes[after : after + limit], after + 1):
        row = change.model_dump(mode="json")
        row["text_changes"] = retained_text_changes(change)
        for side in ("before", "after"):
            if row[side] is not None:
                row[side].pop("text")
                statements = row[side]["statements"]
                row[side]["statement_total"] = len(statements)
                row[side]["statements"] = statements[:8]
                row[side]["statements_truncated"] = len(statements) > 8
        items.append(dict(ordinal=ordinal, **row))
    report = SQLExplanationPage(
        version=explanation.version,
        result_id=result_id,
        source_basis=explanation.source_basis,
        custody=explanation.custody,
        total=len(explanation.changes),
        items=tuple(items),
        diagnostics=explanation.diagnostics,
        impact=comparison_summary(explanation.impact),
        native_observation=explanation.native_observation,
        next_after=after + len(items) if after + len(items) < len(explanation.changes) else None,
    )
    # The requested entry limit is an upper bound. Large retained SQL facts may
    # require a smaller page; the continuation still addresses the exact inventory.
    while len(report.model_dump_json().encode()) > 128 * 1024 and len(report.items) > 1:
        items = list(report.items[:-1])
        report = report.model_copy(update={"items": tuple(items), "next_after": after + len(items)})
    if len(report.model_dump_json().encode()) > 128 * 1024:
        raise ValueError("SQL explanation exceeds byte bound; narrow the page")
    return report
