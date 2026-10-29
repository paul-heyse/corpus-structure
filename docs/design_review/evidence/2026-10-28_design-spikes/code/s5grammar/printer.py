r"""The tree printer with S5-A's tree-side fixes (KEYS-01: the token form wins every disagreement;
the tree printer is the side that changes).

``read_canonical(result, table)`` is the printed form of what the grammar read for a value, to be
compared with the token form of the value as given. It is ``mathgrammar.printer.tree_canonical``
(rules 3-6 over the leaf tokens) with three fixes:

- **T1 trimmed reading.** ``api`` reads a value that fails whole after dropping trailing sentence
  punctuation (``.``, ``,``, ``;``) and reports it ``partial`` (or ``ambiguous``). The tree then
  covers the trimmed input only, so the printer appends the dropped tail's tokens: the printed
  form is the whole value's, as the token form's is. (6 of 6 corpus disagreements before any
  S5 extension.)
- **T2 outer environment.** Rule 1 (one outer pair of math delimiters removed, including an outer
  ``align``/``equation``/... environment) applies to the leaf tokens too, so a value the grammar
  reads as a whole ``\begin{align}…\end{align}`` (S5-19) prints as the token form does.
- **T3 text-mode arguments.** The braced argument of a text-mode command (``\text``, ``\mathrm``,
  ``\textrm``, ``\mbox``, ``\operatorname``: ``printer.TEXT_MODE``) is printed from the source slice
  from its ``{`` leaf to the matching ``}`` leaf, so whitespace the grammar's ``%ignore`` skipped
  inside it is kept and collapsed to one space by rule 5, as in the token form. This covers the
  S5-18 ``text_group``, the operator names ``\text{var}``/``\operatorname{cov}`` and
  ``\mathrm{A}``. (Corpus: 36 S5-34 spans with ``\text{ as }``-style connectives; generated
  strings: ``\text{ AA}``, ``\mathrm{AA }``, found by the Hypothesis layer.)
"""

from __future__ import annotations

from lark import Token, Tree

from mathgrammar.printer import TEXT_MODE, expand, normalize, strip_outer, tex_tokens


def dropped_tail(result) -> str:
    """The trailing punctuation ``api._parse`` dropped before the tree was read ('' if none)."""
    if result.tree is None or result.reason is None:
        return ""
    inner = result.latex
    trimmed = inner.rstrip().rstrip(".,;").rstrip()
    return inner[len(trimmed):] if trimmed != inner.strip() else ""


def _leaves(node, out: list[Token]) -> None:
    if isinstance(node, Token):
        out.append(node)
        return
    if node.data == "_ambig":  # every reading covers the same input; take the first
        _leaves(node.children[0], out)
        return
    for c in node.children:
        _leaves(c, out)


def tree_tokens(tree, source: str) -> list[str]:
    """TeX tokens of the tree's leaves; a text-mode command's braced argument from the source (T3)."""
    leaves: list[Token] = []
    _leaves(tree, leaves)
    out: list[str] = []
    i = 0
    while i < len(leaves):
        leaf = leaves[i]
        if (str(leaf) in TEXT_MODE and i + 1 < len(leaves) and str(leaves[i + 1]) == "{"
                and getattr(leaves[i + 1], "start_pos", None) is not None):
            depth, j = 0, i + 1
            while j < len(leaves):
                depth += str(leaves[j]) == "{"
                depth -= str(leaves[j]) == "}"
                if depth == 0:
                    break
                j += 1
            if j < len(leaves) and leaves[j].end_pos is not None:
                out.extend(tex_tokens(str(leaf)))
                out.extend(tex_tokens(source[leaves[i + 1].start_pos:leaves[j].end_pos]))
                i = j + 1
                continue
        out.extend(tex_tokens(str(leaf)))
        i += 1
    return out


def read_canonical(result, table: dict) -> str:
    toks = tree_tokens(result.tree, result.latex) + tex_tokens(dropped_tail(result))
    return normalize(expand(strip_outer(toks), table))


def tree_canonical(tree, table: dict, source: str = "") -> str:
    """For a bare tree (no trimmed tail): T2 and T3 only."""
    return normalize(expand(strip_outer(tree_tokens(tree, source)), table))


__all__ = ["Tree", "dropped_tail", "read_canonical", "tree_canonical", "tree_tokens"]
