"""Canonical LaTeX (D1 §6.2) written from a parse tree.

The tree's leaf tokens are taken in order. The grammar has already dropped whitespace, spacing
commands and ``\\left``/``\\right`` (``%ignore``). Macro tokens (GEN_SET, GEN_OP, GEN_STYLE) are
replaced by their bodies from the macro table. Each leaf is split into TeX tokens (control word,
control symbol, character), braces around single tokens are dropped (``b^{2}`` -> ``b^2``), and a
space is kept only after a control word followed by a letter (``\\mu x`` stays distinct from
``\\mux``).

``tokens_canonical`` applies the same normalization to raw LaTeX with no parse (used only when a
value does not parse, so every value still has a canonical form). On parsed input the two agree by
construction; ``results/mathgrammar/`` records the check over the S0 values.
"""

from __future__ import annotations

import re

from lark import Token, Tree

_TEX = re.compile(r"\\[A-Za-z]+\*?|\\.|\s+|.", re.S)
_CW = re.compile(r"\\[A-Za-z]+\*?$")
def _ignored() -> set[str]:
    """Commands the shipped grammar ``%ignore``s (spacing, ``\\left``/``\\right``, ...)."""
    from .build import BASE_GRAMMAR

    out = set()
    for line in BASE_GRAMMAR.read_text(encoding="utf-8").splitlines():
        if line.startswith("%ignore"):
            out.update("\\" + m for m in re.findall(r'"\\\\([^"]+)"', line))
    return out


_DROP = _ignored()


def tex_tokens(s: str) -> list[str]:
    return _TEX.findall(s)


def _read_arg(tokens: list[str], j: int) -> tuple[list[str], int]:
    while j < len(tokens) and tokens[j].isspace():
        j += 1
    if j >= len(tokens):
        return [], j
    if tokens[j] != "{":
        return [tokens[j]], j + 1
    depth = 0
    for k in range(j, len(tokens)):
        depth += tokens[k] == "{"
        depth -= tokens[k] == "}"
        if depth == 0:
            return tokens[j + 1: k], k + 1
    return tokens[j + 1:], len(tokens)


def _expand(tokens: list[str], table: dict[str, tuple[int, str]], depth: int = 0) -> list[str]:
    """Expand macros (name -> (nargs, body)); arguments are read as TeX does (group or token)."""
    out: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        spec = table.get(t)
        if spec is None or depth > 10:
            out.append(t)
            i += 1
            continue
        nargs, body = spec
        args, j = [], i + 1
        for _ in range(nargs):
            a, j = _read_arg(tokens, j)
            args.append(a)
        sub: list[str] = []
        bt = tex_tokens(body)
        k = 0
        while k < len(bt):
            if bt[k] == "#" and k + 1 < len(bt) and bt[k + 1].isdigit():
                n = int(bt[k + 1]) - 1
                sub.extend(["{", *(args[n] if n < len(args) else []), "}"])
                k += 2
            else:
                sub.append(bt[k])
                k += 1
        out.extend(_expand(sub, table, depth + 1))
        i = j
    return out


def _tree(tokens: list[str]):
    stack: list[list] = [[]]
    for t in tokens:
        if t == "{":
            stack.append([])
        elif t == "}":
            if len(stack) == 1:
                return None
            g = stack.pop()
            stack[-1].append(g)
        else:
            stack[-1].append(t)
    return stack[0] if len(stack) == 1 else None


def _simplify(items: list) -> list:
    out = []
    for it in items:
        if isinstance(it, list):
            inner = _simplify(it)
            out.append(inner[0] if len(inner) == 1 and isinstance(inner[0], str) else inner)
        else:
            out.append(it)
    return out


def _flatten(items: list) -> list[str]:
    out: list[str] = []
    for it in items:
        if isinstance(it, list):
            out.extend(["{", *_flatten(it), "}"])
        else:
            out.append(it)
    return out


def serialize(tokens: list[str]) -> str:
    out, prev = [], ""
    for t in tokens:
        if prev and _CW.match(prev) and t[:1].isalpha():
            out.append(" ")
        out.append(t)
        prev = t
    return "".join(out)


def normalize(tokens: list[str]) -> str:
    toks = [t for t in tokens if not t.isspace() and t not in _DROP]
    tree = _tree(toks)
    return serialize(toks if tree is None else _flatten(_simplify(tree)))


def strip_delimiters(latex: str) -> str:
    s = latex.strip()
    for o, c in (("$$", "$$"), ("$", "$"), ("\\(", "\\)"), ("\\[", "\\]")):
        if s.startswith(o) and s.endswith(c) and len(s) >= len(o) + len(c):
            return s[len(o): len(s) - len(c)].strip()
    return s


def leaves(node) -> list[Token]:
    if isinstance(node, Token):
        return [node]
    if node.data == "_ambig":  # every reading has the same leaves; take the first
        return leaves(node.children[0])
    out: list[Token] = []
    for c in node.children:
        out.extend(leaves(c))
    return out


def tree_canonical(node, table: dict[str, tuple[int, str]]) -> str:
    """``table``: name -> (nargs, body) (``MacroClass.table()``)."""
    toks: list[str] = []
    for leaf in leaves(node):
        toks.extend(tex_tokens(str(leaf)))
    return normalize(_expand(toks, table))


def tokens_canonical(latex: str, table: dict[str, tuple[int, str]]) -> str:
    """Same normalization on raw LaTeX (fallback for values that do not parse)."""
    return normalize(_expand(tex_tokens(strip_delimiters(latex)), table))


def node_text(node, source: str) -> str:
    """Source text of a node (positions propagated by the parser)."""
    if isinstance(node, Token):
        return source[node.start_pos: node.end_pos]
    if isinstance(node, Tree) and not node.meta.empty:
        return source[node.meta.start_pos: node.meta.end_pos]
    return "".join(source[t.start_pos: t.end_pos] for t in leaves(node))
