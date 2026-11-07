"""Bounded structural candidate evidence for model reviews, without binding claims."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import tokenize
from hashlib import sha256
from io import BytesIO
from pathlib import Path


def locate_consumers(root: Path, head: str, identifiers: set[str]) -> dict:
    paths = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", "python/corpus-structure/src",
         "python/corpus-structure/tests"],
        capture_output=True, timeout=20, check=True,
    ).stdout.decode().split("\0")
    paths = [path for path in paths if path.endswith(".py") and "/_model/" not in path]
    found: list[dict] = []
    inspected: dict[str, str] = {}
    skipped: dict[str, str] = {}
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
            source = raw.decode(encoding)
            tree = ast.parse(source, filename=path, type_comments=True)
        except (OSError, SyntaxError, UnicodeError) as error:
            skipped[path] = type(error).__name__
            continue
        inspected[path] = sha256(raw).hexdigest()
        matched = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            elif isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                name = node.name
            elif isinstance(node, ast.alias):
                name = node.asname or node.name.rsplit(".", 1)[-1]
            else:
                continue
            if name in tokens:
                matched = True
                if len(found) < 200:
                    found.append({
                        "path": path, "name": name, "node": type(node).__name__,
                        "line": node.lineno, "utf8_column": node.col_offset,
                        "source": (ast.get_source_segment(source, node) or "")[:180],
                    })
        if matched and len(selected) < 40:
            selected.append(path)
    rule = {
        "id": "model-consumer-name", "language": "Python", "severity": "hint",
        "message": "model consumer candidate",
        "rule": {"all": [{"kind": "identifier"}, {"regex": "^(" + "|".join(
            re.escape(token) for token in tokens
        ) + ")$"}]},
    }
    structural = []
    structural_status = "no_ast_candidates"
    if selected:
        try:
            cmd = ["ast-grep", "scan", "--json=stream", "--max-results", "200", "--threads", "2",
                   "--inline-rules", json.dumps(rule),
                   *selected]
            result = subprocess.run(cmd, cwd=root, capture_output=True, timeout=20, check=False)
            if result.returncode:
                structural_status = "failed"
            else:
                structural_status = "inspected"
                for line in result.stdout.splitlines()[:200]:
                    row = json.loads(line)
                    path = Path(row["file"]).as_posix()
                    if sha256((root / path).read_bytes()).hexdigest() == inspected.get(path):
                        structural.append({
                            "path": path, "rule": row["ruleId"], "utf8_bytes": row["range"]["byteOffset"],
                        })
                    else:
                        structural_status = "source_changed"
        except (OSError, subprocess.TimeoutExpired, ValueError, KeyError):
            structural_status = "unavailable"
    return {
        "head": head, "identifiers": tokens, "inspected": inspected, "skipped": skipped,
        "unscanned_files": max(0, len(paths) - 400), "ast": found,
        "ast_truncated": len(found) == 200 or len(tokens) != len(identifiers),
        "ast_grep": structural, "ast_grep_scope": selected,
        "ast_grep_status": structural_status, "ast_grep_truncated": len(structural) == 200,
        "semantic_coverage": "unknown",
    }
