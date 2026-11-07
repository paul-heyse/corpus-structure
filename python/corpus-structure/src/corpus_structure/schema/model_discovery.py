"""Bounded structural candidate evidence for model reviews, without binding claims."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import symtable
import sys
import tokenize
from hashlib import sha256
from io import BytesIO
from pathlib import Path


def _scopes(table: symtable.SymbolTable, name: str, line: int) -> list[dict]:
    result = []
    if name in table.get_identifiers() and table.get_lineno() <= line:
        symbol = table.lookup(name)
        result.append(
            {
                "name": table.get_name(),
                "line": table.get_lineno(),
                "type": str(table.get_type()),
                "imported": symbol.is_imported(),
                "local": symbol.is_local(),
                "global": symbol.is_global(),
                "free": symbol.is_free(),
            }
        )
    for child in table.get_children():
        result.extend(_scopes(child, name, line))
    return result


def _source_point(raw: bytes, offset: int) -> tuple[int, int]:
    prefix = raw[:offset]
    return prefix.count(b"\n") + 1, len(prefix.rsplit(b"\n", 1)[-1])


def locate_consumers(
    root: Path, head: str, identifiers: set[str], *, comparison: dict | None = None
) -> dict:
    paths = (
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "-z",
                "--",
                "python/corpus-structure/src",
                "python/corpus-structure/tests",
            ],
            capture_output=True,
            timeout=20,
            check=True,
        )
        .stdout.decode()
        .split("\0")
    )
    excluded = [path for path in paths if path.endswith(".py") and "/_model/" in path]
    paths = [path for path in paths if path.endswith(".py") and path not in excluded]
    found: list[dict] = []
    inspected: dict[str, str] = {}
    skipped: dict[str, str] = {}
    compiled: dict[str, dict] = {}
    selected: list[str] = []
    tokens = sorted(identifiers)[:64]
    for path in paths[:400]:
        try:
            file = root / path
            if file.resolve() != file or file.stat().st_size > 256_000:
                skipped[path] = "symlink or outside byte bound"
                continue
            raw = file.read_bytes()
            encoding, _ = tokenize.detect_encoding(BytesIO(raw).readline)
            source = raw.decode(encoding).replace("\r\n", "\n")
            tree = ast.parse(source, filename=path, type_comments=True)
        except (OSError, SyntaxError, UnicodeError, RecursionError) as error:
            skipped[path] = type(error).__name__
            continue
        inspected[path] = sha256(raw).hexdigest()
        matches: list[tuple[ast.expr | ast.stmt | ast.alias, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            elif isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                name = node.name
            elif isinstance(node, ast.alias):
                names = {node.name.rsplit(".", 1)[-1], node.asname}
                matches.extend(
                    (node, name) for name in names if name is not None and name in tokens
                )
                continue
            else:
                continue
            if name in tokens:
                matches.append((node, name))
        if not matches:
            continue
        try:
            compile(source, path, "exec", dont_inherit=True)
            compiled[path] = {"outcome": "passed"}
        except (SyntaxError, RecursionError) as error:
            compiled[path] = {"outcome": "failed", "line": getattr(error, "lineno", None)}
        try:
            symbols = symtable.symtable(source, path, "exec")
        except SyntaxError, RecursionError:
            symbols = None
        for node, name in matches[: max(200 - len(found), 0)]:
            scopes = (
                _scopes(symbols, name, node.lineno)
                if symbols and isinstance(node, ast.Name)
                else []
            )
            found.append(
                {
                    "path": path,
                    "name": name,
                    "node": type(node).__name__,
                    "line": node.lineno,
                    "utf8_column": node.col_offset,
                    "source": (ast.get_source_segment(source, node) or "")[:180],
                    "scope_candidates": scopes,
                    "lexical_status": "ambiguous"
                    if len(scopes) > 1
                    else "candidate"
                    if scopes
                    else "unresolved",
                }
            )
        if encoding == "utf-8" and len(selected) < 40:
            selected.append(path)
    rule = {
        "id": "model-consumer-name",
        "language": "Python",
        "severity": "hint",
        "message": "model consumer candidate",
        "rule": {
            "all": [
                {"kind": "identifier"},
                {"regex": "^(" + "|".join(re.escape(token) for token in tokens) + ")$"},
            ]
        },
    }
    structural = []
    structural_status = "no_ast_candidates"
    ast_grep_version = None
    if selected:
        try:
            ast_grep_version = subprocess.run(
                ["ast-grep", "--version"], capture_output=True, text=True, timeout=5, check=True
            ).stdout.strip()
            cmd = [
                "ast-grep",
                "scan",
                "--json=stream",
                "--max-results",
                "200",
                "--threads",
                "2",
                "--inline-rules",
                json.dumps(rule),
                *selected,
            ]
            result = subprocess.run(cmd, cwd=root, capture_output=True, timeout=20, check=False)
            if result.returncode == 1 and not result.stdout and not result.stderr:
                structural_status = "inspected_no_hit"
            elif result.returncode:
                structural_status = "failed"
            else:
                structural_status = "inspected"
                for line in result.stdout.splitlines()[:200]:
                    row = json.loads(line)
                    path = Path(row["file"]).as_posix()
                    raw = (root / path).read_bytes()
                    if sha256(raw).hexdigest() == inspected.get(path):
                        span = row["range"]["byteOffset"]
                        line, column = _source_point(raw, span["start"])
                        structural.append(
                            {
                                "path": path,
                                "rule": row["ruleId"],
                                "utf8_bytes": span,
                                "line": line,
                                "utf8_column": column,
                            }
                        )
                    else:
                        structural_status = "source_changed"
        except OSError, subprocess.SubprocessError, ValueError, KeyError:
            structural_status = "unavailable"
    declared = (comparison or {}).get("changes", ())
    return {
        "head": head,
        "identifiers": tokens,
        "inspected": inspected,
        "skipped": skipped,
        "excluded_generated": excluded,
        "compile": compiled,
        "python": sys.version,
        "unscanned_files": max(0, len(paths) - 400),
        "ast": found,
        "ast_truncated": len(found) == 200 or len(tokens) != len(identifiers),
        "ast_grep": structural,
        "ast_grep_scope": selected,
        "ast_grep_status": structural_status,
        "ast_grep_version": ast_grep_version,
        "ast_grep_rule_sha256": sha256(json.dumps(rule, sort_keys=True).encode()).hexdigest(),
        "ast_grep_truncated": len(structural) == 200,
        "semantic_coverage": {
            "status": "declared_partial" if declared else "unknown",
            "consumers": {change["model_ref"]: change.get("consumers", ()) for change in declared},
            "unknowns": (comparison or {}).get("unknowns", ()),
        },
    }
