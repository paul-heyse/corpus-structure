# Environment and offered surface — LDT-02, LDT-03

**Status:** Proposed. Part of the
[library-discovery tooling series](../library-discovery-tooling_2026-11-17.md), which owns the
envelope, evidence classes and symbol identity. This companion owns the selection, installation
and offered-surface commands. Sources:
[review O02](../../../../docs/functional_reviews/library-discovery-tooling_2026-11-17.md#O02) and
[O03](../../../../docs/functional_reviews/library-discovery-tooling_2026-11-17.md#O03).

## Why this work exists

Selection and installation are the facts all four existing accounts rebuilt by hand. The offered
surface is the fact none of them had: a list of what the library exposes, with the markers that
point discovery at configuration and extension points.

Both packages consume the target, installation reader and envelope from LDT-01 and nothing from
each other.

## LDT-02 — `selection` and `metadata`

### `selection DIST...`

For each distribution: whether the project selects it, directly or transitively; the dependency
paths from workspace members; the extras and dependency groups through which it is selected; and
platform markers on those edges.

**Mechanism.** uv is the authority. The command runs

```
uv tree --project P --locked --offline --no-python-downloads \
        --format json --preview-features json-output --invert --package X
```

and reads the graph. In uv 0.13.7 the output has `members[]` and a `resolution` map of nodes,
each with `name`, `version`, `source`, `kind` and `dependencies[]` carrying an optional `marker`.
A selected extra is its own node (`pydantic[email]`) with an edge to the base package; a group is
a node of the member (`corpus-structure-dev:dev`). Direct selection is an edge from a member node
or from one of its extra or group nodes; paths are walks up the inverted graph (*observed*;
[uv tree reference](https://docs.astral.sh/uv/reference/cli/#uv-tree)).

Conditions and limits:

- The JSON schema is marked preview and may change. The package pins the fields it reads with a
  contract test against the root project and records the uv version in `tool`.
- Without `--universal` the tree is filtered to the current platform, and without a group option
  it covers the default groups only. The command reports the platform mode and the group
  selection it used and passes `--universal`, `--all-groups`, `--group` and `--no-dev` through.
- uv is a host binary with no pinned version here; the result records the uv version it ran.
- `--locked` fails on a stale lock, which is the right default: a stale lock means selection is
  not established. The failure is exit 3 with that explanation. `--frozen` reads the lock as it
  stands; if offered, the result must say the lock was not verified. Which of the two a dirty
  `pyproject.toml` should lead to is settled in this package.
- uv documents `uv.lock` as internal to uv. The tool does not parse it; it only hashes it for the
  baseline.

**Not selected** is a result, not an error: the item says `selected: false` for the stated
project, groups and platform mode.

### `metadata DIST...`

For each distribution installed in the target:

- version, `Requires-Python`, license expression;
- `Provides-Extra` beside the extras `selection` found selected, so advertised-but-unselected
  extras are explicit;
- `Requires-Dist` with markers;
- entry points it declares, by group;
- `Project-URL` values, which give the version-matched documentation and source addresses for a
  Context7 or primary-source lookup;
- typing: `py.typed` present, stub files present, a separate `*-stubs` distribution installed;
- import names it provides;
- **companions**: installed distributions whose `Requires-Dist` names this one, and installed
  distributions that declare entry points in groups this one declares or reads. Uninstalled
  companions are a documentation question and are out of the tool's reach.

**Mechanism.** The
[installation reader](foundation-and-envelope.md#installation-reader) from LDT-01. A requested
name that matches no installed distribution is reported in `unavailable_metadata`, with close
matches listed (one account wrote `term-validator` for `linkml-term-validator`). Typing presence
is a check of the distribution's file list. Companions are computed across all installed
distributions: reverse `Requires-Dist`, and entry-point groups shared with this distribution.

A distribution that provides several import packages, and an import package provided by several
distributions (for example `onnxruntime` and `onnxruntime-gpu`), are both reported as they are.

### Tests and completion

- Contract test: the fields read from `uv tree --format json` exist for the root project.
- A fixture site-packages directory with hand-written `.dist-info` folders checks extras,
  entry points, companions, the unmatched-name report and a multi-owner import name.
- Demonstration: `selection` and `metadata` for typer, rich and structlog reproduce the
  mechanical facts of the `cli-and-logging` baseline, with structlog 26.1.0 selected and
  installed.

## LDT-03 — `inventory PACKAGE`

### Behavior

For an import package installed in the target, the command lists its public modules, classes,
functions and attributes. Each item carries the symbol identity defined in the coordinator
(distribution, import root, exposed paths, declared path) and:

- publicity as two separate facts: `in_all` (named in `__all__`) and `public` (public by
  convention or by re-export);
- kind; signature with parameter kinds, defaults and annotations; overloads;
- first docstring line, and parameter descriptions where the library documents them;
- bases and decorators;
- markers, each a separate boolean with its reason:
  - `deprecated`, with the message;
  - `extension_point`: a Protocol or abstract base class, a class with abstract methods, a
    class named by one of the distribution's entry-point groups, or a registration function
    (a decorator or `register`-style callable that takes a user class or function);
  - `configuration`: a `TypedDict` whose keys configure behavior, a settings class, or a symbol
    through which the library reads environment variables;
  - `extra_gated`: defined or imported under `try`/`except ImportError`.
- For the package as a whole: the environment-variable names and entry-point group names its
  source reads.

Views bound the output: `--depth`, `--kind`, `--match`, `--marker`, `--limit`. The default view
is the top-level public surface; deeper views are requested.

Coverage follows the coordinator's split. **Skipped inputs**: compiled modules without stubs and
modules that failed to parse. **Unresolved rows**: aliases Griffe could not resolve, typically
re-exports from another distribution; pydantic has seven (*observed*), so these must not trip
`--strict`.

### Mechanism

**Static load.** `griffe.GriffeLoader(allow_inspection=False, search_paths=[site-packages…],
extensions=…)`, `load(package, try_relative_path=False)`, then
`resolve_aliases(external=False)`, which returns the aliases it could not resolve. The load does
not import the package and takes a fraction of a second for typer and pydantic (*probe*,
`api_griffe.py`). It parses with the tool's Python grammar, so a target for an older Python is
read correctly unless the tool's interpreter is older than the target's syntax
([griffe.md](../../../../docs/libraries/python_introspection/griffe.md) §2.4, §4.1–4.4;
addendum §1–2).

**Identity.** `Alias.target_path` and `final_target` give the declared path of a re-export;
`Object.aliases` gives the reverse map from a declaration to the paths that expose it
(griffe.md addendum §1.3–1.4). Items carry both. The loader that builds the collection is a
function LDT-05 calls directly: `compare` joins against the loaded collection, not against this
command's bounded output, because member and inherited paths exist only by navigating it.

**Publicity** (D1). `griffe-public-redundant-aliases` sets an alias public when it is imported
as `from .x import Y as Y`. Without it Griffe reports 13 public names at typer's top level and
marks `Typer` and `Option` non-public; with it, 40, including them (*observed*).
`griffe-public-wildcard-imports` is the matching extension for `from .x import *` and is added
only if a family needs it.

**Deprecation** (D1). `griffe-warnings-deprecated` sets `obj.deprecated` and a `deprecated`
label for functions and classes decorated with `warnings.deprecated` or
`typing_extensions.deprecated`. Limits: the message must be a literal, and attributes and
aliases are not covered (source read, 1.1.2).

**Parameter documentation** (D1). `griffe-typingdoc` reads `Annotated[..., Doc(...)]` and adds
parameter sections to `function.docstring.parsed`. Those sections exist only on that parsed list;
re-parsing the docstring text loses them, so the inventory reads `docstring.parsed` from the
loaded object once (source read, 0.3.2). typer 0.28 documents its parameters this way.

Extensions are enabled with `griffe.load_extensions("griffe_public_redundant_aliases",
"griffe_warnings_deprecated", "griffe_typingdoc")`. A dotted name that imports a module holding
no extension class loads nothing and raises nothing, so the package asserts that each requested
extension is present in the loaded set
([official extensions](https://mkdocstrings.github.io/griffe/extensions/official/)).

`griffe-pydantic` is not adopted now. It describes models that a library defines, adds nothing to
an inventory of pydantic itself, and stores `functools.partial` values that may not survive
`as_json`. Revisit when a family's offered surface is mainly Pydantic models.

**Markers the tool derives.**

- Extension point: from `resolved_bases` and decorators on the Griffe objects (`typing.Protocol`,
  `abc.ABC`, `abc.abstractmethod`), and from the entry-point groups in the distribution's
  metadata.
- Configuration: classes whose resolved bases include `typing.TypedDict` or a settings base, and
  an `ast` scan of the package's own source for `os.environ[...]`, `os.getenv(...)` and
  `entry_points(group=...)` string arguments. Non-literal arguments are reported as unresolved.
- Extra-gated: `ast` `Try` nodes whose handler catches `ImportError` or `ModuleNotFoundError`.

**Compiled modules.** A scan of the package directory for `.so` and `.pyd` files with no
matching `.pyi`. Under static loading these are silently absent from Griffe's result (*probe*),
so each is a skipped input. D2: the tool does not import the package to fill the gap.

**Assignment aliases.** A name the library binds by assignment from another distribution loads
as an attribute of the assigning module: `pydantic.ValidationError` is
`pydantic_core.ValidationError` (*observed*). Its declared path is the assigning module's, and
the item notes the right-hand side so the reader knows the definition is elsewhere.

**Namespace packages.** A root that is a namespace package has no `__init__` and may span
several distributions; Griffe models it as a namespace package (griffe.md addendum §4). The
inventory lists the portions found and their distributions and does not present them as one
package.

### Limits to state in the result

- Packages that export lazily through a module `__getattr__` are covered only where they also
  carry `TYPE_CHECKING` imports, as pydantic does. Whether a given package is covered is checked
  by comparing the public count with `__all__` where both exist; a shortfall is a note.
- A surface generated at import time (metaclass-built members) is not visible.
- Annotation expressions are recorded as written in the source.

### Alternatives considered

- Astroid, as the engine or as a cross-check on publicity: partial inference, no Pydantic
  fields, tied to the running interpreter, and it would be a dependency for this alone. The
  hand-written fixture is what validates the publicity rule.
- ty or pyrefly as inventory: neither exports a model of a library's surface.
- Hand-written publicity and deprecation rules: workable, but the extensions are maintained with
  Griffe and were observed to produce the wanted result.

### Tests and completion

- A fixture package written for the purpose, with: `__all__`; a redundant-alias re-export without
  `__all__`; a re-export from a second fixture distribution that stays unresolved; an assignment
  alias; a registration decorator; a private-module definition exposed publicly; a deprecated function; a Protocol and
  an abstract base; a `TypedDict` configuration; an `os.getenv` read; a `try`/`except
  ImportError` block; an empty `.so` file without a stub. The expected inventory is written by
  hand.
- The loaded-extension assertion is exercised with a misspelt extension name.
- Demonstration: the typer inventory lists `Typer`, `Option` and `Argument` as public with their
  declared paths under `typer.main` and `typer.params`, and `Option` parameters carry their
  `Doc` text; the pydantic inventory reports 153 exports and marks its deprecated functions.
