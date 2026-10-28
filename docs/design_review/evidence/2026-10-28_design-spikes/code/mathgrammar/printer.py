r"""The token form for keys (D1 §6.2, ADR-0012 and its amendment), and the tree printer.

**Token form** (``token_form``, ``tokens_canonical``): the canonical form of every math value for
keys and tier-1 comparison, total and independent of the grammar:

1. one outer pair of math delimiters is removed: ``\(…\)``, ``\[…\]``, or a math environment's
   ``\begin{env}…\end{env}`` (``MATH_ENVIRONMENTS``); never ``$`` (the source's delimiters are
   ``\(`` and ``\[``); inner delimiters stay;
2. tokens are TeX's (``TEX_TOKEN``): a control word is ``\`` + letters (a ``*`` is never part of
   it), a control symbol ``\`` + one other character, anything else one character;
3. macros expand from the effective macro table by whole command name, at most ``MACRO_DEPTH``
   (16) nested expansions; a deeper macro token is kept unexpanded and reported;
4. the commands of ``DROP_LIST`` are removed: every ``%ignore`` literal of SymPy 1.14's
   ``latex.lark`` (lines 1–11) and the sizing commands ``\big \Big \bigg \Bigg`` with their
   ``l``/``r``/``m`` forms;
5. whitespace is removed, except inside a text-mode argument (``TEXT_MODE``), where each
   whitespace run becomes one space;
6. braces around a single token are dropped (``b^{2}`` -> ``b^2``; a group holding only a space
   keeps its braces); a space is written after a control word followed by a letter, so
   ``\mu x`` stays distinct from ``\mux``.

**Tree printer** (``tree_canonical``): the same normalization over a parse tree's leaf tokens. It
is used for validation and symbol names, and is checked against the token form (the tree/token
property, ``api.tree_token_agreement``); it never writes keys. ``build`` generates the grammar's
added ``%ignore`` from ``DROP_LIST`` and refuses a grammar whose ``%ignore`` set it does not cover.
"""

from __future__ import annotations

import re

from lark import Token, Tree

TEX_TOKEN = re.compile(r"\\[A-Za-z]+|\\.|.", re.S)
_CW = re.compile(r"\\[A-Za-z]+$")

# Every %ignore literal of SymPy 1.14.0's latex.lark, lines 3-11 (line 1 ignores whitespace, which
# rule 5 handles), in file order. build.check_ignores asserts the shipped grammar matches.
SYMPY_IGNORE_LITERALS: tuple[str, ...] = (
    "\\,", "\\thinspace", "\\:", "\\medspace", "\\;","\\thickspace",
    "\\quad", "\\qquad",
    "\\!", "\\negthinspace", "\\negmedspace", "\\negthickspace",
    "\\vrule", "\\vcenter", "\\vbox", "\\vskip", "\\vspace", "\\hfill",
    "\\*", "\\-", "\\.", "\\/", "\\(", "\\=",
    "\\left", "\\right",
    "\\limits", "\\nolimits",
    "\\displaystyle",
)
SIZING_COMMANDS: tuple[str, ...] = tuple(f"\\{b}{s}" for b in ("big", "Big", "bigg", "Bigg") for s in ("", "l", "r", "m"))
DROP_LIST: tuple[str, ...] = SYMPY_IGNORE_LITERALS + SIZING_COMMANDS
DROP = frozenset(DROP_LIST)
TEXT_MODE = frozenset({"\\text", "\\mathrm", "\\textrm", "\\mbox", "\\operatorname"})
# Environments that open math mode, so they delimit a math value as \[ … \] does. Inner
# environments (cases, array, aligned, matrix, …) are content and stay.
MATH_ENVIRONMENTS = frozenset({
    "equation", "equation*", "align", "align*", "alignat", "alignat*", "flalign", "flalign*",
    "gather", "gather*", "multline", "multline*", "eqnarray", "eqnarray*", "displaymath", "math",
})
MACRO_DEPTH = 16


def tex_tokens(s: str) -> list[str]:
    return TEX_TOKEN.findall(s)


def macro_table(macros: dict | None) -> dict[str, tuple[int, str]]:
    """An effective macro table ``{name: {"nargs", "body"}}`` (or ``name: body``) as
    ``name -> (nargs, body)``; names must be control words."""
    out = {}
    for name, spec in (macros or {}).items():
        if isinstance(spec, str):
            spec = {"nargs": 0, "body": spec}
        name = name.strip()
        if re.fullmatch(r"\\[A-Za-z]+", name):
            out[name] = (int(spec.get("nargs") or 0), spec.get("body", ""))
    return out


def _env_name(tokens: list[str], i: int) -> tuple[str | None, int]:
    """``{name}`` at ``tokens[i]`` -> (name, index after the closing brace)."""
    if i >= len(tokens) or tokens[i] != "{":
        return None, i
    for k in range(i + 1, len(tokens)):
        if tokens[k] == "}":
            return "".join(tokens[i + 1: k]).strip(), k + 1
        if tokens[k] == "{":
            return None, i
    return None, i


def strip_outer(tokens: list[str]) -> list[str]:
    """Rule 1: remove one outer pair of math delimiters, if the whole value is wrapped in one."""
    i, j = 0, len(tokens)
    while i < j and tokens[i].isspace():
        i += 1
    while j > i and tokens[j - 1].isspace():
        j -= 1
    t = tokens[i:j]
    for o, c in (("\\(", "\\)"), ("\\[", "\\]")):
        if len(t) >= 2 and t[0] == o and t[-1] == c and c not in t[1:-1]:
            return t[1:-1]
    if t and t[0] == "\\begin":
        name, k = _env_name(t, 1)
        if name in MATH_ENVIRONMENTS:
            depth, m = 0, 0
            while m < len(t):
                if t[m] in ("\\begin", "\\end"):
                    nm, after = _env_name(t, m + 1)
                    if nm == name:
                        depth += 1 if t[m] == "\\begin" else -1
                        if depth == 0:
                            return t[k:m] if after == len(t) else t
                        m = after
                        continue
                m += 1
    return t


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


def expand(tokens: list[str], table: dict[str, tuple[int, str]], unexpanded: list[str] | None = None,
           depth: int = 0) -> list[str]:
    """Rule 3: expand macros (name -> (nargs, body)) by whole command name; arguments are read as
    TeX reads undelimited arguments (a group or one token) and substituted as a group. A macro met
    at nesting depth ``MACRO_DEPTH`` is kept unexpanded and appended to ``unexpanded``."""
    out: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        spec = table.get(t)
        if spec is None:
            out.append(t)
            i += 1
            continue
        if depth >= MACRO_DEPTH:
            if unexpanded is not None:
                unexpanded.append(t)
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
        out.extend(expand(sub, table, unexpanded, depth + 1))
        i = j
    return out


def _spaces(tokens: list[str]) -> list[str]:
    """Rules 4 and 5: drop-list commands removed; whitespace removed outside text-mode arguments
    and collapsed to one space inside them."""
    toks = [t for t in tokens if t not in DROP]
    out: list[str] = []
    stack: list[bool] = []  # per open group: is it a text-mode argument?
    pending_text = False  # the previous significant token was a text-mode command
    for t in toks:
        in_text = bool(stack) and stack[-1]
        if t.isspace():
            if in_text and not (out and out[-1] == " "):
                out.append(" ")
            continue
        if t == "{":
            stack.append(pending_text or in_text)
        elif t == "}" and stack:
            stack.pop()
        pending_text = t in TEXT_MODE
        out.append(t)
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
            single = len(inner) == 1 and isinstance(inner[0], str) and not inner[0].isspace()
            out.append(inner[0] if single else inner)
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
    """Rules 4-6 over expanded tokens."""
    toks = _spaces(tokens)
    tree = _tree(toks)
    return serialize(toks if tree is None else _flatten(_simplify(tree)))


def token_form(latex: str, table: dict[str, tuple[int, str]]) -> tuple[str, list[str]]:
    """D1 §6.2 token form of ``latex`` under the effective macro table ``table``
    (name -> (nargs, body)), with the macro tokens left unexpanded at the depth bound."""
    unexpanded: list[str] = []
    return normalize(expand(strip_outer(tex_tokens(latex)), table, unexpanded)), unexpanded


def tokens_canonical(latex: str, table: dict[str, tuple[int, str]]) -> str:
    """The token form (the key form of every math value)."""
    return token_form(latex, table)[0]


def strip_delimiters(latex: str) -> str:
    r"""The parser's input: math delimiters removed as the grammar reader has always done
    (``$$``, ``$``, ``\(``, ``\[``). Reading only; keys use ``strip_outer`` (rule 1)."""
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
    """The tree printer: rules 3-6 over the tree's leaf tokens. ``table``: name -> (nargs, body)
    (``MacroClass.table()``). Validation and symbol names only; never keys."""
    toks: list[str] = []
    for leaf in leaves(node):
        toks.extend(tex_tokens(str(leaf)))
    return normalize(expand(toks, table))


def node_text(node, source: str) -> str:
    """Source text of a node (positions propagated by the parser)."""
    if isinstance(node, Token):
        return source[node.start_pos: node.end_pos]
    if isinstance(node, Tree) and not node.meta.empty:
        return source[node.meta.start_pos: node.meta.end_pos]
    return "".join(source[t.start_pos: t.end_pos] for t in leaves(node))
