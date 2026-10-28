# Rich 15.0.0 — Comprehensive Python Library Overview

Research date: October 28, 2026 · Primary library: Rich 15.0.0 · Integration focus: Typer 0.27.3

## 1. Executive orientation

Rich is a terminal presentation and rendering framework for Python, providing a unified engine for styled text, structured output, dynamic displays, diagnostic information, and terminal-aware rendering.

Its value extends considerably beyond colored console output. Rich provides a composable rendering architecture that can replace substantial custom machinery for terminal formatting, tabular presentation, progress reporting, interactive status displays, debugging, and output adaptation.

Rich also serves as an important presentation layer within the Python CLI ecosystem, particularly alongside Typer, which provides command definitions, typed parameters, validation, command dispatch, and shell completion.

The relationship between the libraries is complementary:

- Typer owns the command interface: command structure, arguments, options, parsing, help semantics, and invocation.
- Rich owns the presentation mechanisms: styled content, layout, console rendering, progress, tracebacks, and other terminal displays.
- Typer's Rich integration connects the two: automatic Rich-formatted help, errors, and exception presentation, plus configurable help markup and grouping.

A significant version-specific distinction is that Typer 0.26.0 and later vendor Click internally, rather than relying on a separately installed Click package. That changes the integration boundary for extensions that previously assumed ordinary Click command objects or Click internals. Typer 0.27.3 continues this architecture.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



### Capability map

| Capability family     | Principal mechanisms                                                                  |
| --------------------- | ------------------------------------------------------------------------------------- |
| Text and styling      | `Console`, `Text`, `Style`, `Theme`, markup, highlighting                             |
| Structured output     | `Table`, `Columns`, `Panel`, `Tree`, `Rule`, `Padding`, `Align`                       |
| Dynamic presentation  | `Progress`, `Live`, `Status`, `Spinner`, `Layout`                                     |
| Developer diagnostics | `Traceback`, `RichHandler`, `Pretty`, `inspect`, `Syntax`                             |
| Document rendering    | `Markdown`, `JSON`, syntax highlighting                                               |
| Terminal adaptation   | Color negotiation, width measurement, TTY detection, wrapping and overflow            |
| Custom presentation   | Console protocol, measurements, renderable composition, custom progress columns       |
| Output capture        | Text, HTML and SVG exports, capture contexts, alternate output streams                |
| CLI integration       | Typer help panels, Rich markup, exception formatting, application-owned Rich consoles |

Version baseline. Rich 15.0.0 was released April 12, 2026, and requires Python 3.9 or newer. Its major-version change removed Python 3.8 support. Typer 0.27.3 was released October 6, 2026, and requires Python 3.10 or newer. The discussion below targets these released versions, rather than features visible only on development branches.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



## 2. Rendering architecture and extensibility

### 2.1 `Console` as the central rendering engine

`rich.console.Console` is the principal abstraction. It translates Python objects and Rich renderables into terminal-compatible output, handling:

- Output destination: stdout, stderr, arbitrary text streams, or notebook output.
- Terminal capabilities: color systems, Unicode and terminal detection.
- Presentation geometry: available width, wrapping, overflow, justification, and cropping.
- Formatting: markup parsing, automatic highlighting, named styles, and theme resolution.
- Rendering lifecycle: screen control, output capture, recording, and exports.

A `Console` therefore acts as more than an enhanced `print()` function. It is a reusable presentation context through which otherwise independent components can share rendering behavior.

A configured Console may be supplied to higher-level objects, including `Progress`, `Live`, and `RichHandler`. This allows them to use consistent terminal settings and helps coordinate output while displays are active.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation+2



Core configuration surface

```
from rich.console import Consolefrom rich.theme import Themeconsole = Console(    color_system="auto",    force_terminal=None,    width=None,    theme=Theme({        "info": "cyan",        "success": "bold green",        "warning": "yellow",        "error": "bold red",    }),    markup=True,    highlight=True,    record=False,)
```

The significant distinctions are:

| Setting                 | Behavior                                                               |
| ----------------------- | ---------------------------------------------------------------------- |
| `color_system`          | Automatic, 16-color, 256-color, truecolor, Windows legacy, or disabled |
| `force_terminal`        | Overrides terminal capability detection                                |
| `force_interactive`     | Controls whether interactive features are enabled                      |
| `force_jupyter`         | Overrides notebook detection                                           |
| `width`, `height`       | Override detected console dimensions                                   |
| `theme`                 | Supplies application-specific named styles                             |
| `highlighter`           | Controls automatic syntax and pattern highlighting                     |
| `markup`, `emoji`       | Control string interpretation                                          |
| `soft_wrap`, `no_color` | Affect wrapping and color handling                                     |
| `stderr`, `file`        | Select an output stream                                                |
| `record`                | Enables subsequent output export                                       |

Source: `https://rich.readthedocs.io/en/stable/reference/console.html`

### 2.2 The console rendering protocol

One of Rich's most consequential capabilities is its object-based rendering protocol. A domain object can expose its own presentation without requiring the caller to understand its internal fields or manually assemble tables and strings.

There are three principal levels:

| Protocol                             | Responsibility                                        | Distinction                                          |
| ------------------------------------ | ----------------------------------------------------- | ---------------------------------------------------- |
| `__rich__()`                         | Return one Rich-compatible renderable                 | Simplest integration for domain objects              |
| `__rich_console__(console, options)` | Yield a sequence of renderables or low-level segments | Supports composition and context-dependent rendering |
| `__rich_measure__(console, options)` | Return a `Measurement(minimum, maximum)`              | Supports width negotiation inside tables and layouts |

Rich's low-level rendering representation is `Segment`: text plus optional style and control information. Custom renderables can yield segments directly when they need tighter control than ordinary `Text`, `Panel`, or `Table` composition offers.

`ConsoleOptions` carries environmental constraints such as available width and height, wrapping, markup settings, and terminal characteristics. Width-aware rendering therefore does not require every domain object to independently inspect the terminal.

Why this matters: presentation can become an extension capability of domain objects, while layout and terminal adaptation remain centralized. It can reduce custom formatter hierarchies, string concatenation, fixed-width formatting, and special-case output code.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation+1



Source: `https://rich.readthedocs.io/en/stable/protocol.html`

### 2.3 Renderables compose recursively

Rich's high-level objects generally accept other renderables rather than merely plain strings.

For example, a `Table` cell can contain a `Panel`, `Syntax` object, `Tree`, or custom renderable. A `Layout` region can contain a `Table`; the table can contain styled `Text`; that text can contain named styles or terminal hyperlinks.

This establishes a useful separation:

1. Semantic representation: application objects and their data.
2. Presentation composition: renderables describing how information should appear.
3. Device-specific output: Console measurement and terminal rendering.

The model is not a browser DOM or an automatically maintained application state tree. Mutable renderables and `Live` provide refresh behavior, but application state and updates remain the caller's responsibility.

### 2.4 Rich representations versus console renderables

A separate protocol, `__rich_repr__()`, controls how objects appear in pretty-printed representations.

It supports positional fields, named fields, and default-value suppression. `rich.repr.auto` can generate representations from constructors and attributes, with conventional and angle-bracket representations.

This is distinct from `__rich__()`:

- `__rich_repr__()` is suited to compact structural inspection, nested data structures, and debugging.
- `__rich__()` is suited to an object's primary human-readable presentation.
- `__rich_console__()` is suited to sophisticated presentation with multiple components or width-dependent behavior.

The distinction is particularly useful for avoiding a single overloaded string representation that must simultaneously serve logging, debugging, and human-oriented CLI output.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation



Source: `https://rich.readthedocs.io/en/stable/pretty.html`

## 3. Text, structured data, and document presentation

### 3.1 Styled text and themes

Rich supports declarative styling through strings, `Style`, `Text`, and `Theme`.

`Text` holds textual content together with style spans. It provides operations such as `append()`, `stylize()`, `highlight_words()`, `highlight_regex()`, and `from_ansi()`.

Because the style spans remain distinct from the underlying text, Rich can measure, wrap, and restyle content without application code manually managing ANSI sequences.

`Theme` assigns semantic names to styles. A style may specify colors, boldness, dimming, underlining, links, or other supported terminal attributes.

This allows diagnostic categories such as `warning`, `success`, and `error` to be expressed independently of their color definitions. It does not, by itself, establish those categories as application-level status types or logging levels.

Rich also supports terminal hyperlinks through styles and markup where the terminal recognizes the relevant escape sequences.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation+1



Sources:

`https://rich.readthedocs.io/en/stable/text.html`

`https://rich.readthedocs.io/en/stable/style.html`

### 3.2 Tables as structured renderable containers

`rich.table.Table` is substantially more capable than a tabular string formatter.

| Capability         | Mechanism and significance                                       |
| ------------------ | ---------------------------------------------------------------- |
| Automatic sizing   | Determines column widths from content and available space        |
| Width constraints  | `width`, `min_width`, `max_width`, `ratio`, `expand`             |
| Alignment          | Horizontal justification and vertical positioning                |
| Overflow control   | Per-column wrapping, cropping, or ellipsis                       |
| Styling            | Column, row, header, footer, and border styles                   |
| Structure          | Headers, footers, captions, section separators, optional borders |
| Dense presentation | `Table.grid()`, custom padding, and borderless layouts           |
| Nested content     | Cells contain arbitrary Rich renderables                         |

A particularly useful distinction is between a regular `Table`, which emphasizes tabular data, and `Table.grid()`, which can serve as a lightweight layout mechanism without displaying a conventional table grid.

Rich tables are presentation structures, not analytical DataFrames. They do not provide relational query execution, typed column storage, filtering, aggregation, or a general-purpose tabular data model. Such operations belong upstream; Rich handles the formatted display.

Source: `https://rich.readthedocs.io/en/stable/tables.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation



### 3.3 Other structural renderables

Rich provides a family of interoperable layout primitives.

| Renderable          | Principal role                                                                |
| ------------------- | ----------------------------------------------------------------------------- |
| `Panel`             | Bordered or titled region around a renderable                                 |
| `Columns`           | Arrange multiple renderables across available width                           |
| `Tree`              | Hierarchical representation with expandable branches at construction time     |
| `Rule`              | Labeled horizontal separator                                                  |
| `Padding`           | Add controlled space around a renderable                                      |
| `Align`             | Horizontal and vertical positioning                                           |
| `Layout`            | Named regions with horizontal/vertical splits, ratios, and sizing constraints |
| `Group` / `group()` | Combine several renderables into one composition                              |

`Layout` is especially important for terminal dashboards. It enables nested splits, named regions, resizing, and replacement of region content without requiring manual terminal-coordinate calculations.

It does not perform data aggregation or application-state management. Its principal concern is the spatial organization of renderables.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation



Sources:

`https://rich.readthedocs.io/en/stable/layout.html`

`https://rich.readthedocs.io/en/stable/tree.html`

`https://rich.readthedocs.io/en/stable/panel.html`

### 3.4 Markdown, syntax highlighting, and JSON

Rich includes specialized renderers for common developer-facing content.

Markdown (`rich.markdown.Markdown`). Renders headings, lists, tables, emphasis, rules, and syntax-highlighted code blocks into terminal-compatible output. It uses `markdown-it-py` for Markdown parsing. It is a terminal renderer, not a complete HTML/browser presentation engine.

Syntax (`rich.syntax.Syntax`). Uses Pygments for syntax highlighting. Supports language selection, themes, line numbers, line ranges, highlighted lines, wrapping, and background controls. Suitable for source previews, snippets, and diagnostics.

JSON (`rich.json.JSON`, `Console.print_json()`). Formats and colors JSON, including nested structures and primitive values. It is a presentation tool rather than a replacement for schema validation or a JSON serialization library.

Pretty (`rich.pretty.Pretty`, `pprint`). Pretty-prints Python containers, dataclasses, and objects with suitable representations, adapting structure to available width. It can limit depth and the amount of content displayed.

Highlighters (`rich.highlighter`). Built-in or custom highlighters identify recognizable text patterns, while `RegexHighlighter` provides a straightforward extension point for application-specific tokens.

These features can be composed: a traceback contains syntax-rendered source, a table can display highlighted values, and a Markdown document can embed syntax-highlighted code.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation+3



Sources:

`https://rich.readthedocs.io/en/stable/markdown.html`

`https://rich.readthedocs.io/en/stable/syntax.html`

`https://rich.readthedocs.io/en/stable/highlighting.html`

## 4. Dynamic presentation and progress tracking

Rich provides three complementary dynamic mechanisms: `Status`, `Progress`, and `Live`.

### 4.1 Different mechanisms for different execution states

| Mechanism  | Best-suited problem                     | Important properties                                       |
| ---------- | --------------------------------------- | ---------------------------------------------------------- |
| `Status`   | Indeterminate activity                  | Spinner and message, context-managed                       |
| `Progress` | Task-oriented activity                  | Multiple tasks, counters, rates, elapsed time, ETA         |
| `Live`     | Continuously changing arbitrary content | Refreshable renderables, screen management, custom layouts |

All three concern presentation. They do not execute jobs, schedule work, or provide a distributed task engine.

### 4.2 Advanced `Progress` capabilities

`rich.progress.Progress` supports considerably more than an automatically advancing progress bar.

Multi-task state. Each task has an identifier and independently maintained completion, total, visibility, timing, description, and custom fields. Tasks can represent nested phases, independent concurrent activities, or separate units of a long-running operation.

Determinate and indeterminate states. Tasks can have known totals or `total=None`, enabling pulsing indicators where progress cannot yet be quantified.

Custom columns. Available components include `SpinnerColumn`, `TextColumn`, `BarColumn`, `TaskProgressColumn`, `TimeElapsedColumn`, `TimeRemainingColumn`, `TransferSpeedColumn`, `DownloadColumn`, and `RenderableColumn`.

Extensibility. Custom `ProgressColumn` implementations can render additional task information. `task.fields` can carry application-specific values into column formatters.

Refresh control. `auto_refresh`, `refresh_per_second`, `refresh()`, and `transient` permit different tradeoffs between output smoothness and rendering work.

Coordination. Progress supports updates from concurrent tasks and can display information from threaded or multiprocess workloads. For separate processes, the application must still coordinate and communicate progress data to the renderer.

`Progress` automatically builds its display from a Rich table and uses the live-rendering infrastructure. This means its columns, sizing, console destination, and refresh behavior compose with other Rich mechanisms rather than requiring a separate presentation system.

Source: `https://rich.readthedocs.io/en/stable/progress.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation+1



### 4.3 `Live` for dashboards and continuously refreshed views

`rich.live.Live` accepts any renderable and can refresh it periodically or on demand.

Important capabilities include:

- `update(renderable, refresh=...)` for replacing displayed content.
- `auto_refresh=False` for explicit refresh control.
- `screen=True` for alternate-screen presentation.
- `transient=True` for removing the live display at completion.
- `vertical_overflow` policies for content exceeding terminal height.
- `redirect_stdout` and `redirect_stderr` to reduce interference from ordinary prints.
- Nested Live displays, supported in the 14.x line and available in 15.0.0.

`Live` combined with `Layout`, `Table`, `Panel`, and `Progress` can implement terminal dashboards without introducing a full terminal application framework.

Its limitations become more important when applications need rich keyboard interaction, focus management, persistent widgets, asynchronous UI events, or navigation among views. Those responsibilities are better served by a dedicated TUI framework such as Textual.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation+1



Source: `https://rich.readthedocs.io/en/stable/live.html`

## 5. Diagnostics, logging, interactive input, and output capture

### 5.1 Exception rendering and debugging

Rich supplies several ways to render Python exceptions, each with a different integration boundary.

| Mechanism                            | Behavior                                                             |
| ------------------------------------ | -------------------------------------------------------------------- |
| `Console.print_exception()`          | Renders the current exception explicitly                             |
| `Traceback.from_exception()`         | Builds a reusable traceback renderable                               |
| `rich.traceback.install()`           | Installs Rich as the process-level uncaught-exception renderer       |
| `RichHandler(rich_tracebacks=True)`  | Uses Rich tracebacks for exceptions sent through Python logging      |
| Typer's pretty-exception integration | Uses Rich to display uncaught exceptions from Typer-invoked commands |

Rich traceback rendering supports source-code context, syntax highlighting, line wrapping, suppressed framework frames, exception chaining, and configurable treatment of local variables.

Options such as `show_locals`, `locals_max_length`, `locals_max_string`, `locals_max_depth`, `suppress`, and `max_frames` allow the developer to control the amount and kind of diagnostic information displayed.

A key distinction is frame suppression versus error suppression. Removing framework internals from the displayed traceback makes the failure easier to inspect; it does not change the underlying exception or repair the error.

Displaying locals is valuable during debugging, but may expose passwords, tokens, configuration secrets, personal data, or large in-memory objects. It is therefore an explicit capability rather than a safe default.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation+1



Source: `https://rich.readthedocs.io/en/stable/traceback.html`

### 5.2 Standard-library logging integration

`rich.logging.RichHandler` integrates with Python's `logging` architecture as a standard logging handler.

It can display log time, severity, source file and line, highlighted messages, and formatted exceptions. It also supports per-handler control over timestamps, file hyperlinks, highlighters, and traceback formatting.

```
import loggingfrom rich.console import Consolefrom rich.logging import RichHandlerdiagnostics = Console(stderr=True)logging.basicConfig(    level=logging.INFO,    format="%(message)s",    handlers=[        RichHandler(            console=diagnostics,            rich_tracebacks=True,            tracebacks_show_locals=False,            show_path=True,        )    ],)logger = logging.getLogger(__name__)logger.info("Processing started")
```

`Console.log()` and `RichHandler` should not be confused:

- `Console.log()` is a direct convenience method for annotated terminal messages.
- `RichHandler` participates in the standard logging system, preserving logger names, levels, filters, handlers, propagation, and structured `LogRecord` metadata.

This distinction matters when a system needs console output alongside file logs, structured JSON logs, or centralized log collection. Rich can be one presentation sink without replacing the logging architecture.

`RichHandler` leaves markup processing off by default, because arbitrary log strings may contain square brackets that should remain literal. Markup can be enabled globally on the handler or per record using `extra={"markup": True}`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation



Source: `https://rich.readthedocs.io/en/stable/logging.html`

### 5.3 Prompts and interactive input

Rich includes `Prompt`, `IntPrompt`, `FloatPrompt`, and `Confirm`.

They provide styled prompts, default values, choice restrictions, retry behavior, case sensitivity settings, and password-input support. The prompt classes are customizable through inheritance.

The boundary with Typer is important: Rich prompts are interactive input widgets; Typer options and arguments are part of the CLI's declared command interface.

A Typer option can have its own prompt, type, default, environment-variable behavior, and validation. A Rich prompt invoked inside the command body is independent of Typer's parameter definition and does not automatically participate in Typer's help or argument parsing.

Source: `https://rich.readthedocs.io/en/stable/prompt.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation



### 5.4 Capture, export, and alternate output destinations

Rich's output handling supports several less obvious uses.

| Feature                         | Capability                                     |
| ------------------------------- | ---------------------------------------------- |
| `Console.capture()`             | Captures rendered output as text               |
| `Console(file=...)`             | Renders into an arbitrary text stream          |
| `Console(record=True)`          | Retains rendering information for later export |
| `export_text()` / `save_text()` | Produces text output                           |
| `export_html()` / `save_html()` | Produces formatted HTML                        |
| `export_svg()` / `save_svg()`   | Produces scalable terminal-rendered graphics   |
| `Console.pager()`               | Presents long output through a pager           |
| `Console.input()`               | Reads input with Rich-styled prompts           |

HTML and SVG export are useful for preserving terminal presentations in reports, documentation, or test evidence. The exported representation is a rendering artifact, not a lossless serialization of the original Python object or dataset.

SVG export supports terminal themes, so its appearance need not exactly match the theme of the terminal where the content was originally displayed.

Source: `https://rich.readthedocs.io/en/stable/console.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation



## 6. Terminal adaptation, execution characteristics, and operational limits

### 6.1 Terminal capability detection

Rich automatically adapts to supported terminal capabilities. This includes color depth, terminal width, Unicode characters, cursor-control support, and interactivity.

Useful environment controls include:

| Variable            | Effect                                                          |
| ------------------- | --------------------------------------------------------------- |
| `NO_COLOR`          | Disables Rich colors; some non-color text attributes may remain |
| `FORCE_COLOR`       | Requests color output, subject to `NO_COLOR` taking precedence  |
| `TTY_COMPATIBLE=1`  | Tells Rich the output accepts terminal escape sequences         |
| `TTY_COMPATIBLE=0`  | Treats output as not terminal-compatible                        |
| `TTY_INTERACTIVE=0` | Disables interactive behavior                                   |
| `TTY_INTERACTIVE=1` | Enables interactive behavior                                    |
| `COLUMNS`, `LINES`  | Can influence detected terminal dimensions                      |

Rich's documentation specifically identifies `TTY_COMPATIBLE=1` together with `TTY_INTERACTIVE=0` as useful for CI output where styling is desirable but live animation is not.

These mechanisms are preferable to assuming every invocation has an interactive, color-capable terminal.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation+1



Source: `https://rich.readthedocs.io/en/stable/console.html`

### 6.2 Performance and resource behavior

Rich's performance characteristics depend principally on how much content must be rendered and how often rendering occurs.

Static output. Rich adds formatting, width measurement, and presentation work compared with plain strings. For modest human-facing output, this can replace substantial custom formatting without introducing a separate service or runtime.

Large tables and deeply nested renderables. Layout calculations and string/segment production can become material. Rendering a large dataset is not equivalent to performing a relational or columnar operation on that dataset.

Live displays. Refresh frequency, renderable complexity, terminal bandwidth, and the cost of rebuilding the displayed content affect overhead. `auto_refresh=False` or a lower refresh rate can avoid unnecessary rendering when updates are infrequent.

Logging. Rich formatting occurs at the logging presentation layer; it does not change the fundamental performance or concurrency characteristics of Python's logging architecture.

Output export. Recording retains output history in memory until it is exported or cleared, so indefinite recording can increase memory use.

These are architectural consequences of Rich's rendering model, not claims of measured speedups or specific resource savings.

### 6.3 Markup safety and machine-readable output

Rich strings can contain markup such as `[red]...[/red]` and terminal links. If arbitrary user or external text is interpolated into such strings, it may be interpreted as formatting rather than literal content.

Use `rich.markup.escape()` when incorporating untrusted text into markup strings, or use `Text` with separate styled and unstyled segments.

For machine-readable CLI interfaces, it is usually advantageous to keep JSON, CSV, Arrow IPC, and other structured data outputs independent of Rich's decorative presentation. A common conceptual separation is stdout for structured output and stderr for diagnostics, progress, and human-readable status.

Source: `https://rich.readthedocs.io/en/stable/markup.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://rich.readthedocs.io\&sz=32)

Rich 14.1.0 documentation



## 7. Rich–Typer integration: architecture and configuration

### 7.1 What Typer integrates automatically

Typer 0.27.3 declares Rich as a dependency (`rich>=13.8.0`). Installing current Typer therefore normally installs Rich automatically. A separate Rich declaration is useful when an application directly uses Rich APIs and wants to manage that dependency explicitly.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



The integration occurs at distinct layers:

| Presentation concern            | Automatic through Typer? | Configuration mechanism                                               |
| ------------------------------- | ------------------------ | --------------------------------------------------------------------- |
| `--help` output                 | Yes                      | `rich_markup_mode`, `rich_help_panel`, command and parameter metadata |
| Argument/option errors          | Yes                      | Typer's built-in Rich error formatter                                 |
| Unknown-command suggestions     | Yes                      | `suggest_commands`                                                    |
| Uncaught command exceptions     | Yes                      | `pretty_exceptions_*` settings                                        |
| Application result formatting   | No                       | Explicit Rich `Console` or renderables                                |
| Tables and structured views     | No                       | Explicit `Table`, `Panel`, `Tree`, etc.                               |
| Progress bars and live displays | No                       | Explicit `Progress`, `Live`, `Status`                                 |
| Standard Python logging         | No                       | Explicit `RichHandler`                                                |
| Custom application theme        | No                       | Explicit Rich `Theme` and `Console`                                   |
| Shell completion                | Typer, not Rich          | Typer's completion mechanisms                                         |

This means that `typer.Typer()` does not automatically make every `print()` call Rich-formatted. Automatic formatting applies to the CLI interface Typer itself generates.

Source: `https://typer.tiangolo.com/tutorial/printing/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://typer.tiangolo.com\&sz=32)

Typer



### 7.2 Configuring the Typer application

Typer exposes its principal Rich behavior through constructor parameters.

```
import typerapp = typer.Typer(    rich_markup_mode="rich",    pretty_exceptions_enable=True,    pretty_exceptions_show_locals=False,    pretty_exceptions_short=True,    suggest_commands=True,)
```

| Parameter                       | Default in ordinary current Typer installations | Purpose                                                 |
| ------------------------------- | ----------------------------------------------- | ------------------------------------------------------- |
| `rich_markup_mode`              | `"rich"`                                        | Selects Rich markup, Markdown, or plain help formatting |
| `rich_help_panel`               | `None`                                          | Assigns the mounted command/group to a named help panel |
| `pretty_exceptions_enable`      | `True`                                          | Enables Typer's improved developer exception display    |
| `pretty_exceptions_show_locals` | `False`                                         | Includes local variable values in developer tracebacks  |
| `pretty_exceptions_short`       | `True`                                          | Controls intended traceback-frame reduction             |
| `suggest_commands`              | `True`                                          | Suggests similar names when a command is mistyped       |

There are no separate `rich_help_enable`, `rich_colors`, or `rich_theme` constructor arguments in Typer's documented application API.

The settings above are Typer configuration, not Rich `Console` settings. They control how Typer uses Rich to present CLI metadata and exceptions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://typer.tiangolo.com\&sz=32)

Typer



Source: `https://typer.tiangolo.com/reference/typer/`

### 7.3 Choosing help markup: Rich, Markdown, or plain output

The most important help-formatting setting is `rich_markup_mode`.

`"rich"`

Uses Rich's bracket-based markup, such as `[bold cyan]text[/]`, in help strings and command docstrings. Appropriate when precise inline styling is desired.

`"markdown"`

Parses help text as Markdown, supporting emphasis, lists, code formatting, and other Markdown constructs. Appropriate for more document-like descriptions.

`None`

Disables Typer's Rich help formatter and uses ordinary plain CLI help. It also disables Rich formatting for Typer's handled parameter and command-line usage errors. It does not necessarily disable Rich's separate uncaught-developer-exception handling.

These modes are not interchangeable. A docstring containing `[green]...[/]` should not be expected to behave as Rich markup when `rich_markup_mode="markdown"` is selected.

The mode is inherited through Typer's generated command structure, so it generally need not be declared separately on every command.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://typer.tiangolo.com\&sz=32)

Typer+2



Source: `https://typer.tiangolo.com/tutorial/commands/help/`

### 7.4 Help panels: commands versus arguments and options

Typer exposes `rich_help_panel` in multiple contexts. These contexts produce different sections of the generated help.

| Location                                           | Effect                                                         |
| -------------------------------------------------- | -------------------------------------------------------------- |
| `@app.command(rich_help_panel="Operations")`       | Groups that command in a named command panel                   |
| `typer.Option(..., rich_help_panel="Diagnostics")` | Groups an option within its command's help                     |
| `typer.Argument(..., rich_help_panel="Inputs")`    | Groups an argument within its command's help                   |
| `typer.Typer(rich_help_panel="Administration")`    | Groups the subapplication when it appears as a mounted command |

For example:

```
from typing import Annotatedimport typerapp = typer.Typer(rich_markup_mode="rich")@app.command(rich_help_panel="Inspection")def inspect(    source: Annotated[        str,        typer.Argument(help="Source to inspect"),    ],    verbose: Annotated[        bool,        typer.Option(            "--verbose",            "-v",            help="Show additional diagnostics",            rich_help_panel="Diagnostics",        ),    ] = False,):    print(source, verbose)@app.command(rich_help_panel="Utilities")def status():    """Display the current status."""    print("Ready")
```

At the top level, Typer groups `inspect` and `status` under separate named command panels. Within `inspect --help`, the `--verbose` option appears in the Diagnostics panel.

Help panels are presentation groups, not additional command namespaces. They do not change command dispatch, parameter parsing, nesting, or command names.

For genuine command namespaces, Typer's separate `add_typer()` mechanism provides nested subcommands; Rich then formats that resulting hierarchy.

Source: `https://typer.tiangolo.com/tutorial/commands/help/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://typer.tiangolo.com\&sz=32)

Typer



### 7.5 Rich-formatted usage errors versus developer exceptions

This distinction is particularly important for CLI diagnostics.

A. Invalid CLI invocation

Missing argument · invalid parameter type · unknown option

Typer parser and validation

Rich error panel + usage hint

B. Uncaught Python exception in a command

Unexpected runtime error · failed operation · programming defect

Typer exception hook

Rich traceback + source context

The first path is controlled primarily by Typer's Rich help/error formatting behavior. The second is controlled by `pretty_exceptions_enable` and related exception settings.

`pretty_exceptions_show_locals=True` is especially relevant to the second path, not ordinary argument validation.

There is also a subtle version-specific qualification: Typer's documentation describes `pretty_exceptions_short=False` as enabling a longer traceback, but inspection of the 0.27.3 tagged Rich traceback implementation shows that this flag is not passed into `rich.traceback.Traceback.from_exception()`. The Rich path always supplies its internal framework paths through the `suppress` argument. The flag is consulted in Typer's non-Rich traceback path.

Consequently, the documented Rich-specific effect of `pretty_exceptions_short=False` should not be assumed without verification for that release. This is an observed source/documentation discrepancy, not a claim that the entire exception-formatting system is broken.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



Sources:

`https://typer.tiangolo.com/tutorial/exceptions/`

`https://raw.githubusercontent.com/fastapi/typer/0.27.3/typer/rich_utils.py`

### 7.6 Configuring Rich output inside Typer commands

Typer does not provide the application's normal Rich `Console` automatically. It is created explicitly.

```
from rich.console import Consolefrom rich.theme import Themetheme = Theme({    "success": "bold green",    "warning": "bold yellow",    "detail": "dim cyan",})console = Console(theme=theme)diagnostics = Console(stderr=True, theme=theme)
```

The two Consoles can be used for different output channels and supplied to individual Rich components.

```
from rich.progress import Progressfrom rich.table import Tabletable = Table(title="Inspection results")table.add_column("Name")table.add_column("Value")with Progress(console=diagnostics) as progress:    task = progress.add_task("Inspecting", total=10)    for item in range(10):        table.add_row(str(item), str(item * item))        progress.advance(task)console.print(table)
```

In this example, progress is directed to stderr and the final table to stdout. Typer continues to manage argument parsing and help generation independently.

This also illustrates a valuable composition: one `Console` can serve as the presentation context for several Rich components.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://typer.tiangolo.com\&sz=32)

Typer+1



### 7.7 Can a custom Rich theme control Typer's `--help` colors?

Not through the application's `Console(theme=...)` alone.

Typer 0.27.3 constructs separate internal Rich Consoles for help, usage errors, and exception formatting. Its `typer.rich_utils` module defines formatter-specific style constants such as:

`STYLE_OPTION`, `STYLE_SWITCH`, `STYLE_USAGE`, `STYLE_COMMANDS_PANEL_BORDER`, `STYLE_ERRORS_PANEL_BORDER`, and other layout/style settings.

The internal `_get_rich_console()` function constructs its own `Console`, `Theme`, and highlighter from those settings.

These constants provide insight into how Typer's formatting works, but they are internal implementation details rather than a documented stable public theming contract. Changing them programmatically may work for a specific release, but such customization requires version-specific maintenance and testing.

There is no documented `typer.Typer(console=my_console)` parameter that transparently unifies Typer's built-in help theme with the application's Rich Console.

This is arguably the most important limitation to understand when seeking a single globally configured Rich presentation system.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Source: `https://raw.githubusercontent.com/fastapi/typer/0.27.3/typer/rich_utils.py`

### 7.8 Environment controls and disabling Rich in Typer

The tagged Typer implementation contains several relevant controls.

| Configuration                    | Effect and scope                                                                 |
| -------------------------------- | -------------------------------------------------------------------------------- |
| `rich_markup_mode=None`          | Public configuration: plain Typer help and handled usage errors                  |
| `pretty_exceptions_enable=False` | Public configuration: standard uncaught Python exception formatting              |
| `TYPER_USE_RICH=0`               | Source-verified environment switch disabling Typer's built-in Rich formatting    |
| `TYPER_STANDARD_TRACEBACK=1`     | Source-verified override to use standard exception tracebacks                    |
| `NO_COLOR`                       | General Rich color suppression                                                   |
| `FORCE_COLOR`                    | General color request; Typer also detects it when constructing internal Consoles |
| `TERMINAL_WIDTH`                 | Consulted by Typer's internal Rich formatter for its maximum width               |

`TYPER_USE_RICH` is read while Typer's core module is imported, so it must be set before the application process imports Typer. It disables Typer's internal Rich integration, not unrelated Rich formatting explicitly performed inside command functions.

The last three environment mechanisms should be distinguished from Typer's public constructor parameters. They are not interchangeable configuration interfaces, and the internal controls are more vulnerable to upstream implementation changes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



Source: `https://raw.githubusercontent.com/fastapi/typer/0.27.3/typer/core.py`

## 8. Combined configuration example

The following illustrative implementation demonstrates Typer's built-in Rich integration and separately configured Rich application output.

```
from typing import Annotatedimport typerfrom rich.console import Consolefrom rich.progress import Progressfrom rich.table import Tablefrom rich.theme import Themeapp = typer.Typer(    help="Operations for [bold cyan]artifacts[/].",    rich_markup_mode="rich",    no_args_is_help=True,    pretty_exceptions_enable=True,    pretty_exceptions_show_locals=False,)theme = Theme({    "success": "bold green",    "warning": "yellow",})console = Console(theme=theme)diagnostics = Console(stderr=True, theme=theme)@app.command(rich_help_panel="Inspection")def inspect(    name: Annotated[        str,        typer.Argument(            help="Artifact [cyan]identifier[/]"        ),    ],    verbose: Annotated[        bool,        typer.Option(
```

This example deliberately separates four concerns:

| Concern                                       | Owning component                        |
| --------------------------------------------- | --------------------------------------- |
| Commands, arguments, options, type conversion | Typer                                   |
| Help markup, help panels, usage errors        | Typer's Rich integration                |
| Tables and successful results                 | Application-owned Rich Console          |
| Progress reporting                            | Rich Progress on the diagnostic Console |

For structured-data commands, the same arrangement can be extended by selecting a plain or serialized output path instead of `console.print()`, without changing Typer's command model.

The example is illustrative and was not executed as part of this research.

## 9. Adjacent tooling, compatibility, and important distinctions

### 9.1 Typer and `rich-click`

`rich-click` is a separate package that adds Rich formatting and configurable themes to Click applications.

Typer historically shared much of Click's implementation and extension behavior, and `rich-click` offered experimental Typer patching through `patch_typer()`.

However, in Typer 0.26.0, Typer began vendoring Click internally. This introduced an important integration boundary.

The current rich-click documentation explicitly states that its experimental Typer patching does not work with Typer 0.26.0 or later. Consequently, rich-click should not be treated as a straightforward supported mechanism for customizing Typer 0.27.3's help theme.

This does not mean Rich itself is incompatible with Typer. Typer's own built-in Rich integration remains distinct from the external rich-click patching mechanism.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ewels.github.io\&sz=32)

rich-click+1



Sources:

`https://ewels.github.io/rich-click/latest/documentation/typer_support/`

`https://typer.tiangolo.com/release-notes/`

### 9.2 Relationship with Textual

Rich and Textual are complementary rather than competing implementations of the same abstraction.

| Rich                                                | Textual                                                            |
| --------------------------------------------------- | ------------------------------------------------------------------ |
| Rendering and presentation components               | Interactive terminal application framework                         |
| Tables, trees, panels, progress and live layouts    | Widgets, screens, focus and event handling                         |
| Works naturally within ordinary command execution   | Supports persistent event-driven application interfaces            |
| Application explicitly owns state and refresh logic | Framework provides a broader reactive UI and application lifecycle |

A Rich `Live` dashboard may eliminate the need for a full TUI framework when the display is primarily observational. A genuinely interactive application with complex navigation and input behavior is a different problem.

### 9.3 Jupyter, Pygments, and Markdown dependencies

Rich's integration ecosystem includes dependencies and optional features with distinct responsibilities.

| Component        | Relationship                                                          |
| ---------------- | --------------------------------------------------------------------- |
| Pygments         | Syntax lexing and source highlighting                                 |
| `markdown-it-py` | Markdown parsing                                                      |
| `ipywidgets`     | Optional Jupyter support, available through the `rich[jupyter]` extra |
| IPython/Jupyter  | Notebook rendering environment                                        |
| Python `logging` | Standard logging infrastructure into which `RichHandler` plugs        |
| Typer            | CLI framework that uses Rich for presentation                         |

Rich 15.0.0's tagged package metadata declares `pygments`, `markdown-it-py`, and the optional `ipywidgets` extra. These are separate from Typer's own dependencies and command handling.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Source: `https://raw.githubusercontent.com/Textualize/rich/v15.0.0/pyproject.toml`

### 9.4 Testing Rich–Typer behavior

Typer provides `typer.testing.CliRunner`, which supports application invocation and inspection of exit codes, output, and errors.

```
from typer.testing import CliRunnerrunner = CliRunner()result = runner.invoke(app, ["inspect", "sample", "--verbose"])assert result.exit_code == 0assert "sample" in result.outputassert "Length" in result.output
```

It is useful to distinguish tests of CLI semantics from tests of terminal presentation.

- CLI semantics: correct command routing, argument validation, error messages, exit codes, and stdout/stderr behavior.
- Presentation behavior: Rich styling, wrapping, tables, terminal width handling, and help layout.
- Terminal interaction: progress and live-display behavior under interactive and noninteractive conditions.

Rich's `Console(file=...)`, fixed `width`, capture, and recording APIs allow presentation to be tested without relying on the calling terminal's dimensions.

For stable automated assertions, semantic content is generally less brittle than byte-for-byte comparisons of ANSI sequences or complete layouts. Exact rendering tests remain useful where formatting itself is a product requirement.

Source: `https://typer.tiangolo.com/tutorial/testing/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://typer.tiangolo.com\&sz=32)

Typer



### 9.5 Cross-cutting architectural limitations

The most consequential boundaries are summarized below.

| Boundary                                                       | Consequence                                                               |
| -------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Rich is presentation, not computation                          | Data processing and validation remain upstream                            |
| Rich renderables are not automatically reactive state models   | Applications own updates and lifecycle                                    |
| Dynamic terminal output assumes suitable terminal capabilities | Non-TTY and redirected output need suitable fallback behavior             |
| Rich themes are scoped to Consoles                             | They do not automatically configure Typer's internal help                 |
| Typer owns CLI parsing                                         | Rich prompts and renderables do not replace typed CLI parameters          |
| Typer vendors Click                                            | Ordinary Click-specific extensions are no longer automatically compatible |
| Formatted output differs from structured serialization         | Machine-readable interfaces should preserve a distinct output path        |
| Rendering can expose information                               | Markup escaping and traceback-local controls matter                       |

## 10. Primary-source reference map

These sources are organized by the capability they document. All URLs are provided in full for direct reuse.

| Subject                                       | Primary source                                                               |
| --------------------------------------------- | ---------------------------------------------------------------------------- |
| Rich current release                          | `https://pypi.org/project/rich/`                                             |
| Rich tagged release                           | `https://github.com/Textualize/rich/releases/tag/v15.0.0`                    |
| Rich package dependencies and extras          | `https://raw.githubusercontent.com/Textualize/rich/v15.0.0/pyproject.toml`   |
| Console rendering and capture                 | `https://rich.readthedocs.io/en/stable/console.html`                         |
| Console API reference                         | `https://rich.readthedocs.io/en/stable/reference/console.html`               |
| Custom renderable protocol                    | `https://rich.readthedocs.io/en/stable/protocol.html`                        |
| Text and styled content                       | `https://rich.readthedocs.io/en/stable/text.html`                            |
| Styles                                        | `https://rich.readthedocs.io/en/stable/style.html`                           |
| Rich markup and escaping                      | `https://rich.readthedocs.io/en/stable/markup.html`                          |
| Tables                                        | `https://rich.readthedocs.io/en/stable/tables.html`                          |
| Layout                                        | `https://rich.readthedocs.io/en/stable/layout.html`                          |
| Progress                                      | `https://rich.readthedocs.io/en/stable/progress.html`                        |
| Live displays                                 | `https://rich.readthedocs.io/en/stable/live.html`                            |
| Tracebacks                                    | `https://rich.readthedocs.io/en/stable/traceback.html`                       |
| Logging                                       | `https://rich.readthedocs.io/en/stable/logging.html`                         |
| Syntax highlighting                           | `https://rich.readthedocs.io/en/stable/syntax.html`                          |
| Markdown rendering                            | `https://rich.readthedocs.io/en/stable/markdown.html`                        |
| Pretty printing                               | `https://rich.readthedocs.io/en/stable/pretty.html`                          |
| Prompts                                       | `https://rich.readthedocs.io/en/stable/prompt.html`                          |
| Typer current release                         | `https://pypi.org/project/typer/`                                            |
| Typer application configuration               | `https://typer.tiangolo.com/reference/typer/`                                |
| Typer command help and panels                 | `https://typer.tiangolo.com/tutorial/commands/help/`                         |
| Typer arguments/options reference             | `https://typer.tiangolo.com/reference/parameters/`                           |
| Typer exceptions                              | `https://typer.tiangolo.com/tutorial/exceptions/`                            |
| Typer printing and colors                     | `https://typer.tiangolo.com/tutorial/printing/`                              |
| Typer testing                                 | `https://typer.tiangolo.com/tutorial/testing/`                               |
| Typer release notes                           | `https://typer.tiangolo.com/release-notes/`                                  |
| Typer tagged Rich formatter implementation    | `https://raw.githubusercontent.com/fastapi/typer/0.27.3/typer/rich_utils.py` |
| Typer tagged command and error implementation | `https://raw.githubusercontent.com/fastapi/typer/0.27.3/typer/core.py`       |
| Typer tagged application implementation       | `https://raw.githubusercontent.com/fastapi/typer/0.27.3/typer/main.py`       |
| rich-click / Typer compatibility              | `https://ewels.github.io/rich-click/latest/documentation/typer_support/`     |

Documentation-version qualification: Rich's public Read the Docs pages still identify themselves as Rich 14.1.0 in portions of the site. This overview therefore uses the Rich 15.0.0 tagged release and package metadata to establish the target version, and the public documentation principally to explain established APIs and mechanisms. Consequential Typer integration behavior was additionally checked against the Typer 0.27.3 tagged source.

## 11. Architectural synthesis

Rich is best understood as a terminal rendering subsystem with a composable object protocol, not simply a collection of formatting helpers.

Its largest architectural benefits arise from using that rendering subsystem consistently: renderables encapsulate presentation, `Console` centralizes terminal adaptation, and specialized components provide tables, progress, diagnostics, and export without requiring custom terminal-control code.

For Typer applications, there are two complementary layers: Typer's built-in Rich formatting of the command interface, configured through Typer's public parameters, and application-owned Rich presentation, configured through Consoles, themes, and renderables.

The main integration limitation is that those layers do not share a single public, fully configurable theme or Console instance automatically. Recognizing that boundary allows the libraries' existing capabilities to be leveraged extensively without depending unnecessarily on Typer's private rendering internals.