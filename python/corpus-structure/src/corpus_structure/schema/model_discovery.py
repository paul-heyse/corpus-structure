"""Captured-source structural candidates with separately attributed lexical evidence."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import cast

import libcst as cst
from ast_grep_py import Rule, SgRoot
from libcst.metadata import MetadataWrapper, PositionProvider, QualifiedNameProvider

from .source_migrations import utf8_source


class _Bindings(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider, QualifiedNameProvider)

    def __init__(self):
        self.names = {}

    def visit_Name(self, node):
        location = self.get_metadata(PositionProvider, node, None)
        assert location is not None
        point = location.start
        names = self.get_metadata(QualifiedNameProvider, node, set())
        self.names[point.line, point.column] = sorted(
            (name.name, name.source.name) for name in names
        )


def discover_source_consumers(
    sources: dict[str, bytes], identifiers: set[str], *, modules: dict[str, str] | None = None
) -> dict:
    """Examine the complete supplied universe; candidates never establish caller closure.

    ast-grep indexes Python character offsets. Convert them through the original
    Unicode source to exact UTF-8 byte spans, including CRLF and astral characters.
    LibCST owns lexical attribution; the interpreter independently owns validity.
    """
    tokens = sorted(identifiers)
    regex = "^(?:" + "|".join(re.escape(token) for token in tokens) + ")$"
    base = {"all": [{"kind": "identifier"}, {"regex": regex}]}
    categories = (
        ("import", {"any": [{"kind": "import_statement"}, {"kind": "import_from_statement"}]}),
        ("annotation", {"kind": "type"}),
        ("call", {"kind": "call"}),
        ("declaration", {"any": [{"kind": "function_definition"}, {"kind": "class_definition"}]}),
    )
    rules: list[tuple[str, Rule]] = [
        (
            category,
            cast(
                Rule,
                {
                    "all": [
                        base,
                        {
                            "inside": {
                                **parent,
                                **({"stopBy": "end"} if category != "declaration" else {}),
                            }
                        },
                    ]
                },
            ),
        )
        for category, parent in categories
    ]
    rules.append(("reference", cast(Rule, base)))
    candidates, inspected, skipped, compiled = [], {}, {}, {}
    for path, raw in sorted(sources.items()):
        try:
            source = utf8_source(raw)
            compiled[path] = {"outcome": "passed"}
            try:
                compile(source, path, "exec", dont_inherit=True)
            except (SyntaxError, RecursionError) as error:
                compiled[path] = {"outcome": "failed", "line": getattr(error, "lineno", None)}
            parsed = SgRoot(source, "python").root()
            wrapped = MetadataWrapper(cst.parse_module(raw))
            lexical = _Bindings()
            wrapped.visit(lexical)
        except (
            UnicodeError,
            SyntaxError,
            ValueError,
            cst.ParserSyntaxError,
            RecursionError,
        ) as error:
            skipped[path] = type(error).__name__
            continue
        inspected[path] = sha256(raw).hexdigest()
        seen = set()
        for category, rule in rules:
            for node in parsed.find_all({"rule": rule}) if tokens else ():
                span = node.range()
                key = (span.start.index, span.end.index)
                if key in seen:
                    continue
                seen.add(key)
                start = len(source[: span.start.index].encode())
                end = len(source[: span.end.index].encode())
                line, column = span.start.line + 1, span.start.column
                names = lexical.names.get((line, column), [])
                candidates.append(
                    dict(
                        path=path,
                        module=(modules or {}).get(path),
                        category=category,
                        name=node.text(),
                        node=node.kind(),
                        source=node.text(),
                        source_digest=inspected[path],
                        utf8_bytes=dict(start=start, end=end),
                        line=line,
                        utf8_column=len(source[: span.start.index].rsplit("\n", 1)[-1].encode()),
                        qualified_names=[dict(name=name, origin=origin) for name, origin in names],
                        lexical_status="ambiguous"
                        if len(names) > 1
                        else "qualified"
                        if names
                        else "unresolved",
                    )
                )
    candidates.sort(key=lambda item: (item["path"], item["utf8_bytes"]["start"], item["category"]))
    return dict(
        candidates=candidates,
        identifiers=tokens,
        inspected=inspected,
        skipped=skipped,
        compile=compiled,
        unscanned_files=len(skipped),
        coverage="complete-syntax-examination" if not skipped else "partial-syntax-examination",
        backend="ast-grep-py",
        backend_version=version("ast-grep-py"),
        query_sha256=sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest(),
        semantic_coverage=dict(
            status="candidate_evidence",
            unknowns=["Structural matches do not establish complete semantic callers."],
        ),
    )


def locate_consumers(
    root: Path,
    head: str,
    identifiers: set[str],
    *,
    comparison: dict | None = None,
    proposed: dict[str, str] | None = None,
    sources: dict[str, bytes] | None = None,
    modules: dict[str, str] | None = None,
) -> dict:
    """Acquire checkout sources once, or use an already acquired explicit snapshot."""
    excluded, acquisition_skipped = [], {}
    if sources is None:
        sources = {}
        for directory in (
            root / "python/corpus-structure/src",
            root / "python/corpus-structure/tests",
        ):
            for path in sorted(directory.rglob("*.py")):
                name = path.relative_to(root).as_posix()
                if "/_model/" in name:
                    excluded.append(name)
                elif path.resolve() == path:
                    sources[name] = path.read_bytes()
                else:
                    acquisition_skipped[name] = "symlink source requires explicit captured bytes"
    sources = dict(sources)
    sources.update({path: content.encode() for path, content in (proposed or {}).items()})
    report = discover_source_consumers(sources, identifiers, modules=modules)
    report["skipped"].update(acquisition_skipped)
    report["unscanned_files"] = len(report["skipped"])
    if acquisition_skipped:
        report["coverage"] = "partial-syntax-examination"
    declared = (comparison or {}).get("changes", ())
    report.update(head=head, excluded_generated=excluded)
    report["semantic_coverage"].update(
        status="declared_partial" if declared else "unknown",
        consumers={change["model_ref"]: change.get("consumers", ()) for change in declared},
        unknowns=(comparison or {}).get("unknowns", report["semantic_coverage"]["unknowns"]),
    )
    return report
