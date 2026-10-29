"""The math methods' pure functions (ingest and math §3.7-§3.10; P0-I-2a; ADR-0012).

- `grammar`: the one math grammar (assembly, parser cache, `parse`, ambiguity, failures,
  occurrences) that every reader of math in the product uses;
- `transform`: the parse tree to SymPy (`to_sympy`);
- `printer`: the tree printer, which serves only the tree/token property (keys come from
  `core/tex.py`'s token form, never from a tree);
- `spans`: M11's grammar part and M09 over a rendition's math spans;
- `scope`: M13, binding sites and scopes from M09's and M11's output;
- `context`: a unit's standing context from M13's scopes.

The grammar raises when called off a process's main thread (its deadline is a `SIGALRM` timer), so
these functions run in single-threaded worker processes, never in an MCP server's threads.
"""
