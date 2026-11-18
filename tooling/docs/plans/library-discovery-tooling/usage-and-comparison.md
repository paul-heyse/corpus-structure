# Usage and comparison — LDT-04, LDT-05

**Status:** Proposed. Part of the
[library-discovery tooling series](../library-discovery-tooling_2026-11-17.md), which owns the
envelope, evidence classes, symbol identity and the join. This companion owns the usage census,
including the choice of its attribution engine, and the comparison. Sources:
[review O04](../../../../docs/functional_reviews/library-discovery-tooling_2026-11-17.md#O04) and
[O05](../../../../docs/functional_reviews/library-discovery-tooling_2026-11-17.md#O05).

## Why this work exists

Every existing account qualifies its usage statements as a "scoped no-hit" or a "representative
read". The census replaces those with a stated scope, attributed rows and an explicit list of
what could not be attributed. The comparison then gives the agent complete candidates to
interpret.

## LDT-04 — `census ROOT... --scope PATH...`

`ROOT` names one or more import roots (`pydantic`, or `typer rich`). `--scope` names the
directories to scan and is required; `--exclude` removes globs.

### Two layers

1. **Exact pass, every file in scope.** `ast` reads import statements and their context and
   finds the files that touch the roots. It is cheap: 710 product files in about 1.4 s
   (*probe*, `usage_ast.py`).
2. **Attributed pass, hit files only.** An engine resolves the base name of each call, attribute
   chain, base class and decorator to an imported module or name, honoring aliases and
   shadowing.

### Opening slice: choose the attribution engine

**Question.** Can `ast` with `symtable` do the attributed pass well enough to replace LibCST?

**Why it matters.** With LibCST the pass costs about 0.2 s per file: 47 s for the 239 files
mentioning pydantic (*probe*, `usage_libcst_census.py`), which calls for worker processes. With
`ast` and `symtable` it would run at parse speed in one process.

**What is known.**

- LibCST `QualifiedNameProvider` resolves `import a as b`, `from a import b as c` and
  function-local imports per file, without `FullRepoManager`. It returns a set of names where a
  binding is conditional. It does not follow assignment aliases, and it assigns members reached
  through an instance or a repository subclass to the local name (*probe*,
  `usage_libcst_attribution.py`;
  [libcst.md](../../../../docs/libraries/python_introspection/libcst.md) §5.1–5.6).
- `symtable` classifies each name once per scope (`is_imported`, `is_local`, `is_parameter`,
  `is_global`, `is_free`) but gives no positions and no link from an AST node to its table.
  Pairing means walking `get_children()` beside the AST and matching scope-creating nodes by
  type, name and line
  ([ast.md](../../../../docs/libraries/python_introspection/ast.md) §10.1; addendum §5).
- Pitfalls *observed* on Python 3.14.10:
  - inlined comprehensions (PEP 709) erase the shadowing of a comprehension target in function
    and class scopes, so `[t.Y for t in items]` looks like a use of a module-level `t`;
  - annotated definitions add `__annotate__` scopes, and generic classes resolve bases in a
    type-parameter scope;
  - same-line lambdas need ordered matching;
  - names inside string annotations are invisible to `symtable`.

**Method.** This is the first slice of the package, not a separate investigation, and it leaves
no evidence record. Write the census fixture (below) first, with the expected attribution of
every call, attribute chain, base and decorator written by hand. Implement both engines behind
the one engine function and run each against the fixture. The hand-written expectations are the
oracle; neither engine is treated as ground truth.

**Decision rule.**

- Adopt `ast` with `symtable` if every expected attribution is either produced or reported as an
  unresolved row. The census then needs no worker processes and LibCST is not declared as a
  dependency.
- Keep LibCST otherwise.
- A silent wrong attribution is disqualifying for either engine. The comprehension-target case
  is the one most likely to produce it on the `ast` side.

The chosen engine and the reason are recorded in this section when the slice completes, and the
losing engine's code is removed.

**Outcome, 2026-11-17: LibCST is kept.** Both engines ran through the same census logic on the
hand-written fixture. `ast` with `symtable` attributed a comprehension variable to an imported
name of the same spelling, with nothing marking the row as uncertain, whenever that name was
also used outside the comprehension in the same function, class body or module (PEP 709; on
Python 3.14.10 `symtable` reports the name as global with no comprehension flag). That is a
silent wrong attribution and disqualifies it. LibCST produced or reported every expected
attribution. The `ast` and `symtable` engine was removed; hit files run in worker processes.
The engine uses LibCST's `ScopeProvider` referents, the layer `QualifiedNameProvider` is built
on, because the alias, instance and subclass rows need the binding node.

### Behavior

Items, each with path, line, UTF-8 byte offset and the uv project the file belongs to:

| Item kind | Content |
|---|---|
| Import | Statement form, written module and names, alias, relative level, context (module level, function-local, under `try`, under `TYPE_CHECKING`) |
| Call | `written_paths` of the callee, positional count, keyword names, whether `*args` or `**kwargs` is passed |
| Subclass | `written_paths` of each attributed base |
| Instantiation | A call whose callee is an attributed class; recorded so `compare` knows instances exist |
| Decorator | `written_paths` |
| Reference | Attributed attribute access that is none of the above |
| Mention | The root named in `pyproject.toml` or a YAML file; never mixed with code use |

Two views, each a declared item kind: a per-symbol summary (counts and number of files), which
is the default, and per-site rows with `--sites`.

Coverage:

- `scanned`: files read, by scope root and uv project;
- `no_hit_scopes`: roots where the import root was not found, so "none in this scope" is a
  recorded fact about a stated scope;
- `excluded`: globs and generated paths left out;
- `skipped_inputs`: files that failed to parse;
- `unresolved`, by kind:
  - assignment alias (`alias = t.Option`);
  - member reached through an instance or a repository subclass (`app.command`,
    `MyModel.model_validate`);
  - `getattr`, `importlib.import_module`, `__import__`;
  - string reference: a dotted family path inside a string literal, such as a factory name or an
    entry-point value;
  - a repository re-export followed for more than one hop;
  - any kind the opening slice adds for the chosen engine.

### Mechanism

**Scope.** Directories are resolved against the target project. Each file is tagged with the uv
project that owns it. The repository holds tens of thousands of Python files outside the product
(`build/`, evidence probes), so no default scope is assumed.

**Exact pass.** `ast.Import` and `ast.ImportFrom` nodes anywhere in the tree, not only at module
level: 4,550 of the product's 10,343 import statements are below module level (*probe*). The
same pass records `getattr`, `import_module` and `__import__` calls and string literals that
start with a root name as unresolved candidates, and builds a table of repository modules that
re-export names from the roots, so files that reach a root through such a module join the hit
set (ast.md §4.3, §5.1–5.2; addendum §1.3, §7.1).

**Attributed pass.** One function: source text in, attributed rows and unresolved rows out. If
LibCST is kept: `MetadataWrapper(module, unsafe_skip_copy=True)` with `QualifiedNameProvider`
and `PositionProvider`, visiting `Call`, `Arg`, `ClassDef.bases`, `Decorator` and `Attribute`
(libcst.md §5.1–5.6; addendum §3.4, §5), with hit files processed in a `ProcessPoolExecutor`.
There is no result cache: the workload is one run per family per refresh, and `compare` accepts
a saved census.

**Members through instances and subclasses.** When the base of an attribute chain is a local
name bound to an instance of an attributed class, or is a repository class with an attributed
base, the row is unresolved with that kind and names the class. The engine does not guess the
member's owner; `compare` uses the row to avoid a false `unreferenced`.

**Re-exports inside the repository.** A relative written path (`.models.Field`) is joined to the
exact pass's re-export table. One hop is followed and reported as such; deeper chains are
unresolved.

**Validity.** Whether a file is valid Python is judged by `ast.parse`, with
`feature_version=(3, minor)` when the target's Python is older than the tool's. Python documents
`feature_version` as best-effort, so for an older target the result notes that validity was
approximated. LibCST is not the judge; it accepted a statement Python 3.14 rejects (*probe*).
A file that fails is a skipped input, and the attributed pass does not run on it.

**Positions.** `ast` columns are UTF-8 bytes and LibCST's are characters. Rows are normalized to
line and UTF-8 byte offset.

**Mentions.** `tomllib` for `pyproject.toml` dependency tables; a plain text search for YAML.
They are a separate item kind with no attribution claim.

### Alternatives considered

- ast-grep-py as the census engine: about a second for the whole product and equal counts for
  pydantic, but it cannot tell one `Field` from another, and an unknown language name raises a
  panic that `except Exception` does not catch (*probe*). It remains LDT-C2's mechanism.
- `FullRepoManager`: about 5% more time and nothing this job needs.
- A per-file result cache: machinery for a workload that runs once per refresh.
- Type-checker references for members reached through instances: that is O08, not planned here.

### Tests and completion

- A fixture repository written for the purpose, with hand-written expected rows, covering:
  - each item kind and each unresolved kind;
  - aliased and dotted imports, a relative import, a function-local import;
  - shadowing by a parameter, a later assignment, a class-body assignment and a comprehension
    target; `global` and `nonlocal`;
  - a `try`/`except ImportError` double binding and a `TYPE_CHECKING` double binding, each
    yielding two written paths;
  - a generic class, same-line lambdas and a string annotation;
  - a subclass of a root class with an inherited method called on the subclass and on an
    instance;
  - a file with a syntax error, a one-hop repository re-export and an empty scope.
- A scope with no use of the root exits 0 with the scope in `no_hit_scopes`.
- Demonstration: the pydantic census over `python/corpus-structure/src` is compared with the
  retained probe (`Field` 883 calls, `min_length` 314 keyword uses, `BaseModel` 303 bases at
  `d71291f67`; the tree has moved, so differences are explained, not required to be zero), and
  the structlog census finds the importing product files.

## LDT-05 — `compare ROOT... --scope PATH...`

### Behavior

Runs the inventory loader and the census for the roots, or reads a saved census with
`--census FILE`, and reports, grouped by module:

| Row | From |
|---|---|
| Public symbols `unreferenced in scope` | Inventory left-joined to census |
| Parameters and configuration keys of referenced callables that are never passed | Inventory signatures and `TypedDict` keys against census call rows |
| Extension points with no repository subclass or registration | Inventory markers against census subclass and decorator rows |
| Extras advertised but not selected | `metadata` against `selection` |
| Entry-point groups the library reads that no installed distribution populates | Inventory source scan against the installation reader |
| Deprecated symbols the repository uses | Deprecated-use authority below |
| Written paths `not in inventory` | Census rows with no match |

Each row carries only a mechanical state, as defined in the coordinator. When the scope spans
several uv projects, the comparison is reported per project, each against its own environment.

### The join

Defined in the [coordinator](../library-discovery-tooling_2026-11-17.md#shared-contracts) and
implemented here. The command loads the roots with the LDT-03 loader and keeps the Griffe
collection in memory. For each written path it resolves the path in the collection and takes
`canonical_path`; if the full path does not resolve it retries on shorter prefixes and records
the unmatched tail. `typer.Option` and `typer.params.Option` therefore count as one symbol, and
`pydantic.RootModel.model_validate` joins to `pydantic.main.BaseModel.model_validate`
(*observed*). A row with several written paths marks every symbol they resolve to as referenced.

Rules that keep the states honest:

- A member of a root class is `unresolved` when the census has a subclass, instantiation or
  instance-member row for that class and no direct reference to the member.
- A parameter is "never passed" only when every call to the callable binds without it.
  Positional arguments are bound to parameters in signature order; a call with `*args` or
  `**kwargs` makes that callable's parameters `unresolved`.
- A row touching any unresolved census kind is `unresolved`.

### Deprecated use (D3)

**Selected:** pyrefly, run as an executable against the scope:

```
pyrefly check --python-interpreter-path <target python> --error deprecated --only deprecated \
        --output-format json --summary=none <scope…>
```

Each record has a location and a description such as
"`pydantic.main.BaseModel.parse_obj` is deprecated" (*observed*, pyrefly 1.4.0). The declaring
path in the description is the join key. pyrefly reports this check only when it is raised to
error; with `--only` alone it prints nothing (*observed*), so the flags are part of the contract.
It sees uses the census cannot attribute, such as `m.dict()` on an instance of a subclass.

The description format is not a documented interface. A contract test pins it, and a record
whose description does not parse is kept as an unresolved row with its raw text.

**Fallback:** ty, `ty check --python <env> --project <project> --ignore all --warn deprecated
--output-format gitlab`. Its rule is stable and it reports the same uses, but its record carries
only a short name, a message and a location (*observed*, 0.0.102), so rows would join by
location against census spans. A renamed or unknown rule yields an `unknown-rule` record, which
must be treated as a failure, not as zero findings
([ty.md](../../../../docs/libraries/python_introspection/ty.md) addendum §6.4;
[rule reference](https://docs.astral.sh/ty/reference/rules/#deprecated)).

The package opens by running both on the deprecated fixture and confirming the choice. If
pyrefly's description cannot be relied on, ty is used and the coordinator's D3 is updated.

A pyrefly row stands on its own. Where the inventory did not mark the symbol deprecated (the
Griffe extension skips attributes and aliases), the row is still reported and the disagreement
is noted. The census is never a source for deprecation.

### Limits to state in the result

`compare` serves roots used through their Python API by direct reference. When most census rows
for a root are unresolved (string names, registries, instances, subclasses), the result says so
in its notes and does not present the surface as unreferenced.

### Tests and completion

- A fixture pair (package and repository) with hand-written expected states:
  - a symbol defined in a private module, exposed at the top level and used through both paths:
    one referenced symbol;
  - an inherited method called on a repository subclass and on an instance: `unresolved`, not
    `unreferenced`;
  - a callable called with a positional argument for its second parameter: that parameter is
    passed;
  - a callable called once with `**kwargs`: its parameters are `unresolved`;
  - a written path absent from the package: `not in inventory`;
  - a deprecated fixture method used through an instance: reported and joined to the inventory
    symbol.
- Contract test on the pyrefly JSON fields and description pattern.
- Demonstration: `compare typer` and `compare pydantic` over the product source, read by the
  author for plausibility and recorded in the completion note.
