# Library-discovery tooling: capability probes — 2026-11-17

**Question.** What can the installed introspection libraries establish about a third-party Python
package and about this repository's use of it, at what fidelity and cost, and how do Typer and
Rich behave for an agent-facing CLI?

**Consumer.** [Tooling for library-led discovery](../../../functional_reviews/library-discovery-tooling_2026-11-17.md).
No record is finalized: these are capability observations behind `Proposed` opportunities, not an
accepted result.

## Conditions

Run on 2026-11-17 at `d71291f67` (plus unrelated uncommitted work) from the repository root with
the root environment: Python 3.14.10, griffe 2.4.1, astroid 4.3.4, libcst 1.9.0, ast-grep-py
0.51.2, tree-sitter 0.26.0 with tree-sitter-python 0.25.0, ty 0.0.102, typer 0.28.0, rich 15.0.0.
Read-only; nothing imports the inspected packages except where stated. Timings are single
wall-clock runs on a shared machine, some overlapping, and are indicative only. The census scope
is `python/corpus-structure/src` (710 files).

```console
uv run --no-sync python -B docs/design_review/evidence/2026-11-17_library-discovery-tooling/<script>.py
```

## Probes and observations

| Script | Observation |
|---|---|
| `api_griffe.py` | Static load, no import: typer 0.06 s, pydantic 0.23 s, structlog 0.04 s. typer has 13 public top-level names and `Typer`, `Option`, `Argument`, `Context`, `run` report `is_public=False`; Astroid `wildcard_import_names()` gives 28 including `Typer`. pydantic: 153 exports; 33 functions decorated `@deprecated`, `.deprecated` set on none. |
| `usage_ast.py` | 710 files parsed, no failures, 1.4 s; 10,343 import statements, 4,550 below module level; 351 `getattr`, 25 `import_module`, 1 `__import__`. `packages_distributions()` maps `yaml` to PyYAML and returns nothing for the editable `corpus_structure`. |
| `usage_libcst_census.py` | Per-file `QualifiedNameProvider`: 124 s for all files, 47 s for the 239 mentioning pydantic, identical results. `pydantic.Field` 883 calls, `ConfigDict` 239, `BaseModel` bases 303, `Field.min_length` 314. |
| `usage_libcst_attribution.py` | Import aliases resolve (`import typer as t; t.Typer`); assignment aliases and instance-bound decorators (`@app.command`) come back `LOCAL`. LibCST parses `lazy import x`, which `ast.parse` rejects on 3.14. |
| `usage_libcst_fullrepo.py` | On 40 files, `FullRepoManager` with `FullyQualifiedNameProvider` 7.3 s against 6.95 s per-file. |
| `usage_ast_grep.py` | 256 pydantic import statements (equal to `ast`); `Field($$$ARGS)` 885 matches; keyword counts equal to LibCST; about 1 s. An unsupported language name raises a Rust panic not caught by `except Exception`. |
| `usage_ast_grep_relational.py` | `keyword_argument inside call` returns 0 with the default `stopBy`; nesting through `argument_list` returns the matches. |
| `ty_lsp.py`, `ty_workspace/` | `ty server` pointed at the root environment: `references` on `Option` finds the import, the call, the attribute access and the import in an unopened file, but not the call through `as Opt`; `definition` lands in `site-packages/typer/params.py`; `workspace/symbol` returns nothing for library names. |
| `cli_typer_rich.py` | `import typer` about 21 ms without loading Rich; root options must precede the subcommand; `Table` cells default to `overflow="ellipsis"` and truncate long paths; `Progress` on a non-terminal still prints a final line unless disabled; `rich.json` emits `NaN`. |

## Limits

- Several observations in the review (Griffe over a foreign Python 3.12 site-packages,
  `importlib.metadata.distributions(path=…)`, compiled modules without stubs, Tree-sitter grammar
  coverage, `ty check` output formats) were made with inline one-off commands whose source was
  not retained. `api_griffe.py` was rerun by the coordinator; the other scripts are the workers'
  sources as run, and `ty_lsp.py` and `ty_workspace/ty.toml` carry this machine's absolute paths.
- One ty release, one machine. Very large packages were not measured.
