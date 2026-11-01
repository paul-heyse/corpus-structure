"""The tree printer (D1 §6.2; ingest and math §3.7 "Tree printer").

It prints what the grammar read for a value in the token form's normalization, so the tree/token
property can compare it with `core/tex.py`'s token form of the value as given. It serves only that
property: keys and symbol names come from the token form, never from a tree. When the two
disagree the token form is right and the printer is the side that changes (KEYS-01); S5-A made
three such changes, kept here:

- **T1 trimmed reading.** A value read only after dropping trailing sentence punctuation
  (`partial`) has a tree over the trimmed input; the dropped tail is printed after it.
- **T2 outer environment.** The token form strips one outer pair of math delimiters, an outer
  `align`/`equation`/... environment included; printing through the token form's normalization
  strips it from the leaves the same way.
- **T3 text-mode arguments.** The braced argument of a text-mode command (`core/tex.py`
  `TEXT_MODE`) is printed from the source, so whitespace the grammar's `%ignore` skipped inside it
  is kept and collapsed as the token form collapses it.

Leaf text retains source whitespace between positioned leaves. Joining adds only the separator
needed to keep a control word and a following letter distinct; arbitrary separators can become
content inside an opaque text-mode argument whose closing brace is escaped in TeX.
"""

from __future__ import annotations

from collections.abc import Mapping

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef
from corpus_structure.methods.math import _tree


def leaf_texts(tree: _tree.Node, source: str) -> list[str]:
    """Leaf texts, original whitespace gaps and text-mode argument source slices (T3)."""
    leaves = _tree.leaves(tree)
    out: list[str] = []
    position = 0

    def append(value: str, start: int | None, end: int | None) -> None:
        nonlocal position
        if start is not None:
            whitespace = "".join(c for c in source[position:start] if c.isspace())
            if whitespace:
                out.append(whitespace)
        out.append(value)
        if end is not None:
            position = end

    i = 0
    while i < len(leaves):
        leaf = leaves[i]
        opening = leaves[i + 1] if i + 1 < len(leaves) else None
        if str(leaf) in tex.TEXT_MODE and opening is not None and str(opening) == "{":
            depth, j = 0, i + 1
            while j < len(leaves):
                depth += str(leaves[j]) == "{"
                depth -= str(leaves[j]) == "}"
                if depth == 0:
                    break
                j += 1
            start, end = opening.start_pos, leaves[j].end_pos if j < len(leaves) else None
            if start is not None and end is not None:
                append(str(leaf), leaf.start_pos, leaf.end_pos)
                append(source[start:end], start, end)
                i = j + 1
                continue
        append(str(leaf), leaf.start_pos, leaf.end_pos)
        i += 1
    whitespace = "".join(c for c in source[position:] if c.isspace())
    if whitespace:
        out.append(whitespace)
    return out


def _join_leaves(parts: list[str]) -> str:
    out: list[str] = []
    previous: tex.Token | None = None
    for part in parts:
        if not part:
            continue
        if (
            previous is not None
            and previous.kind == "word"
            and part[0] in ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
        ):
            out.append(" ")
            previous = None
        out.append(part)
        # The final token can cross a grammar-leaf boundary (e.g. a bare backslash).
        previous = tex.tokens((previous.text if previous is not None else "") + part)[-1]
    return "".join(out)


def print_tree(tree: _tree.Node, source: str, table: Mapping[str, MacroDef], tail: str = "") -> str:
    """The printed form of a reading of `source`, with the dropped `tail` after it (T1)."""
    reading = source[: -len(tail)] if tail else source
    return tex.token_form(_join_leaves([*leaf_texts(tree, reading), tail]), table)
