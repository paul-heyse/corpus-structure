"""Output and exit contract shared by every `tooling` command.

- `--json`: stdout carries exactly one envelope (`model_dump_json`), nothing else.
- Otherwise stdout on a terminal gets a Rich projection; stdout that is not a terminal gets dense
  plain lines (one item per line, `# `-prefixed context lines, the truncation line last). Both
  are derived from the `columns` the item kind declares, so a command writes no rendering code.
- Diagnostics and progress go to stderr. Consoles are created per call, so a test runner's
  stream swap and `COLUMNS` reach them.
- Coverage row lists (skipped inputs, unresolved rows, unavailable metadata) are rendered grouped
  by reason, kind or field, with counts and the first few rows of each group; `--json` always
  carries every row.
- Exit codes: 0 delivered (zero hits and unresolved rows included); 2 usage (Typer's own, and
  a usage error raised in a command body; no envelope);
  3 `ToolFailure` (or an unexpected error), delivered as the same envelope with
  `status: failed`; 1 under `--strict` when `coverage.skipped_inputs` is not empty.
- Text from outside the tool is rendered literally with terminal control sequences removed.
"""

from __future__ import annotations

import os
import re
import shlex
import sys
import traceback
from collections.abc import Mapping, Sequence
from contextlib import suppress
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Annotated, Any, NoReturn, Protocol, runtime_checkable

import typer
from rich.console import Console, Group, RenderableType
from rich.progress import Progress
from rich.table import Table
from rich.text import Text
from typer.core import TyperCommand

from corpus_tooling.envelope import Baseline, Column, Envelope, ErrorInfo, failed_envelope

JsonOpt = Annotated[
    bool, typer.Option("--json", help="Write exactly one result envelope as JSON to stdout.")
]
LimitOpt = Annotated[
    int, typer.Option("--limit", min=0, help="Show at most this many items; 0 shows all.")
]
OffsetOpt = Annotated[
    int, typer.Option("--offset", min=0, help="Skip this many items (continue a truncated list).")
]
StrictOpt = Annotated[bool, typer.Option("--strict", help="Exit 1 when any input was skipped.")]
DEFAULT_LIMIT = 200

EXIT_STRICT = 1
EXIT_FAILURE = 3


class ToolFailure(Exception):
    """A tool or environment failure: exit 3 with a `status: failed` envelope.

    `kind` is a short stable token; `remedy` says what to pass or fix."""

    def __init__(self, kind: str, message: str, remedy: str) -> None:
        super().__init__(message)
        self.error = ErrorInfo(kind=kind, message=message, remedy=remedy)


# --- literal text ----------------------------------------------------------------------------

# Re-expressed from the product's diagnostic capture: OSC/CSI sequences, then C0/C1 controls
# other than tab and newline. No credential redaction: this tool reads no credentials.
_TERMINAL = re.compile(r"\x1b(?:\][^\x07\x1b]*(?:\x07|\x1b\\)|\[[0-?]*[ -/]*[@-~])")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def safe_text(value: object) -> str:
    """`value` as text with terminal control sequences and control characters removed."""
    return _CONTROL.sub("", _TERMINAL.sub("", str(value)))


def _cell(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list | tuple | set | frozenset):
        return ",".join(_cell(part) for part in value) or "-"
    if isinstance(value, dict):
        return ",".join(f"{_cell(key)}={_cell(part)}" for key, part in value.items()) or "-"
    # Cells are one line: tabs and newlines inside a value would break the plain format.
    return " ".join(safe_text(value).split()) if value != "" else "-"


# --- streams and broken pipes ----------------------------------------------------------------


def _discard_shutdown_output(descriptor: int) -> None:
    # A failed buffered flush is retried during interpreter shutdown.
    with suppress(OSError):
        fd = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(fd, descriptor)
        finally:
            os.close(fd)


def _undelivered(exit_code: int) -> NoReturn:
    """The reader closed stdout: end without a traceback, as `ci` does."""
    if sys.stdout is sys.__stdout__:
        _discard_shutdown_output(1)
    with suppress(OSError):
        sys.stderr.write("tooling: stdout closed before the result was delivered\n")
        sys.stderr.flush()
    raise typer.Exit(exit_code or 74)


class _ResultConsole(Console):
    def __init__(self, exit_code: int) -> None:
        super().__init__()
        self.exit_code = exit_code

    def on_broken_pipe(self) -> None:
        _undelivered(self.exit_code)


class _DiagnosticConsole(Console):
    def on_broken_pipe(self) -> None:
        self.quiet = True
        if sys.stderr is sys.__stderr__:
            _discard_shutdown_output(2)


def stderr_console() -> Console:
    return _DiagnosticConsole(stderr=True)


def write_stdout(body: str, *, exit_code: int = 0) -> None:
    try:
        sys.stdout.write(body)
        sys.stdout.flush()
    except BrokenPipeError:
        _undelivered(exit_code)


def diagnostic(message: str) -> None:
    """One literal line on stderr; never on the result channel."""
    try:
        stderr_console().print(Text(safe_text(message)), markup=False, highlight=False)
    except OSError:
        if sys.stderr is sys.__stderr__:
            _discard_shutdown_output(2)


def progress() -> Progress:
    """A stderr progress display, disabled (no output at all) when stderr is not a terminal."""
    console = stderr_console()
    return Progress(console=console, disable=not console.is_terminal, transient=True)


def stdout_is_terminal() -> bool:
    """Layout choice. `TTY_COMPATIBLE=1/0` overrides detection (Rich's own variable);
    `FORCE_COLOR` deliberately does not, so piped output stays plain."""
    forced = os.environ.get("TTY_COMPATIBLE", "")
    if forced in {"0", "1"}:
        return forced == "1"
    try:
        return sys.stdout.isatty()
    except ValueError:
        return False


# --- normalized invocation -------------------------------------------------------------------


def normalized_command(ctx: typer.Context) -> str:
    """The invocation as `tooling <group> <command>` plus every explicitly given parameter in
    declaration order, options in their first long form, arguments last."""
    chain: list[typer.Context] = []
    current: Any = ctx
    while current is not None:
        chain.append(current)
        current = current.parent
    tokens = ["tooling"]
    for context in reversed(chain):
        if context.parent is not None:
            tokens.append(context.info_name or "")
        arguments: list[str] = []
        for param in context.command.params:
            name = param.name or ""
            source = context.get_parameter_source(name)
            if source is None or source.name in {"DEFAULT", "DEFAULT_MAP"}:
                continue
            value = context.params.get(name)
            values = list(value) if isinstance(value, list | tuple) else [value]
            if param.param_type_name == "argument":
                arguments.extend(str(part) for part in values)
                continue
            long_forms = [opt for opt in param.opts if opt.startswith("--")] or param.opts
            if getattr(param, "is_flag", False) and isinstance(value, bool):
                negative = getattr(param, "secondary_opts", [])
                if value:
                    tokens.append(long_forms[0])
                elif negative:
                    tokens.append(negative[0])
                continue
            for part in values:
                tokens.extend([long_forms[0], str(part)])
        if any(argument.startswith("-") for argument in arguments):
            tokens.append("--")
        tokens.extend(arguments)
    return shlex.join(tokens)


def next_page_command(command: str, offset: int) -> str:
    tokens = shlex.split(command)
    kept: list[str] = []
    skip = False
    for token in tokens:
        if skip:
            skip = False
            continue
        if token == "--offset":
            skip = True
            continue
        if token == "--json" or token.startswith("--offset="):
            continue
        kept.append(token)
    at = kept.index("--") if "--" in kept else len(kept)  # options precede `--` and arguments
    return shlex.join([*kept[:at], "--offset", str(offset), *kept[at:]])


# --- rendering -------------------------------------------------------------------------------


def _columns(envelope: Envelope[Any, Any]) -> tuple[Column, ...]:
    return type(envelope).item_type().columns


def _offset(envelope: Envelope[Any, Any]) -> int:
    tokens = shlex.split(envelope.command)
    for index, token in enumerate(tokens[:-1]):
        if token == "--offset":
            with suppress(ValueError):
                return int(tokens[index + 1])
    return 0


def _truncation_lines(envelope: Envelope[Any, Any]) -> list[str]:
    lines = []
    for entry in envelope.truncated:
        line = f"truncated {entry.list}: shown {entry.shown} of {entry.total}"
        following = _offset(envelope) + entry.shown
        if entry.list == "items" and following < entry.total:
            line += f"; next: {next_page_command(envelope.command, following)}"
        lines.append(line)
    return lines


def _baseline_fields(envelope: Envelope[Any, Any]) -> list[tuple[str, str]]:
    fields = [("view", _cell(envelope.view)), ("status", envelope.status)]
    baseline = envelope.baseline
    if baseline is not None:
        python = baseline.python
        fields += [
            ("project", _cell(baseline.project)),
            ("python", _cell(python.version if python else None)),
            ("environment", _cell(python.environment if python else None)),
            ("platform", _cell(baseline.platform)),
            ("revision", _cell(baseline.revision)),
            ("dirty", str(len(baseline.dirty_paths))),
            ("lock", _cell(baseline.lock_digest)),
        ]
    return fields


def _coverage_fields(envelope: Envelope[Any, Any]) -> list[tuple[str, str]]:
    coverage = envelope.coverage
    return [
        ("scanned", str(coverage.scanned)),
        ("no_hit_scopes", _cell(coverage.no_hit_scopes)),
        ("excluded", _cell(coverage.excluded)),
        ("skipped", str(len(coverage.skipped_inputs))),
        ("unresolved", str(len(coverage.unresolved))),
        ("unavailable_metadata", str(len(coverage.unavailable_metadata))),
    ]


def _row_cells(row: Any) -> list[str]:
    return [_cell(getattr(row, name)) for name in type(row).model_fields]


RENDERED_PER_GROUP = 3
"""Coverage rows a rendering shows per group (kind, reason or field); `--json` shows all."""


@dataclass(frozen=True)
class _CoverageList:
    label: str
    """The plain-format line tag and the Rich table title."""
    group_field: str
    rows: Sequence[Any]

    def groups(self) -> list[tuple[str, list[Any]]]:
        grouped: dict[str, list[Any]] = {}
        for row in self.rows:
            grouped.setdefault(_cell(getattr(row, self.group_field)), []).append(row)
        return sorted(grouped.items(), key=lambda entry: (-len(entry[1]), entry[0]))

    def shown(self) -> list[Any]:
        return [row for _, rows in self.groups() for row in rows[:RENDERED_PER_GROUP]]

    def summary(self) -> str | None:
        """One line of counts per group, and how to get every row, when rows are hidden."""
        groups = self.groups()
        if not any(len(rows) > RENDERED_PER_GROUP for _, rows in groups):
            return None
        counts = " ".join(f"{name}={len(rows)}" for name, rows in groups)
        return (
            f"{self.label} by {self.group_field}: {counts}; showing up to {RENDERED_PER_GROUP} "
            "of each (--json lists every row)"
        )


def _coverage_lists(envelope: Envelope[Any, Any]) -> list[_CoverageList]:
    coverage = envelope.coverage
    return [
        _CoverageList("skipped", "reason", coverage.skipped_inputs),
        _CoverageList("unresolved", "kind", coverage.unresolved),
        _CoverageList("unavailable", "field", coverage.unavailable_metadata),
    ]


def render_plain(envelope: Envelope[Any, Any]) -> str:
    """Dense lines for a pipe: tab-separated items; context lines start with `# `."""
    columns = _columns(envelope)
    lines = [f"# {envelope.schema_} {' '.join(f'{k}={v}' for k, v in _baseline_fields(envelope))}"]
    lines.append("# columns\t" + "\t".join(column.title for column in columns))
    lines += ["\t".join(_cell(getattr(item, c.field)) for c in columns) for item in envelope.items]
    lines.append("# coverage " + " ".join(f"{k}={v}" for k, v in _coverage_fields(envelope)))
    for listing in _coverage_lists(envelope):
        summary = listing.summary()
        if summary is not None:
            lines.append(f"# {summary}")
        lines += [f"# {listing.label}\t" + "\t".join(_row_cells(row)) for row in listing.shown()]
    lines += [f"# note\t{_cell(note)}" for note in envelope.notes]
    lines += [f"# {line}" for line in _truncation_lines(envelope)]
    return "\n".join(lines) + "\n"


def _fields_grid(fields: Sequence[tuple[str, str]]) -> Table:
    grid = Table.grid(padding=(0, 1))
    grid.add_column(style="bold")
    grid.add_column(overflow="fold")
    for label, value in fields:
        grid.add_row(label, Text(value))
    return grid


def _rows_table(title: str, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> Table:
    table = Table(box=None, title=title, title_justify="left", header_style="bold")
    for header in headers:
        table.add_column(header, overflow="fold")
    for row in rows:
        table.add_row(*(Text(cell) for cell in row))
    return table


def render_rich(envelope: Envelope[Any, Any]) -> RenderableType:
    columns = _columns(envelope)
    parts: list[RenderableType] = [_fields_grid(_baseline_fields(envelope))]
    parts.append(
        _rows_table(
            f"{envelope.view} ({len(envelope.items)})",
            [column.title for column in columns],
            [[_cell(getattr(item, c.field)) for c in columns] for item in envelope.items],
        )
    )
    parts.append(_fields_grid(_coverage_fields(envelope)))
    for listing in _coverage_lists(envelope):
        rows = listing.shown()
        if rows:
            headers = list(type(rows[0]).model_fields)
            title = f"{listing.label} ({len(rows)} of {len(listing.rows)})"
            parts.append(_rows_table(title, headers, [_row_cells(row) for row in rows]))
        summary = listing.summary()
        if summary is not None:
            parts.append(Text(summary))
    parts += [Text(f"note: {_cell(note)}") for note in envelope.notes]
    # The next-page command stays on one line so it can be copied whole.
    parts += [Text(line, no_wrap=True, overflow="ignore") for line in _truncation_lines(envelope)]
    return Group(*parts)


def _failure_text(envelope: Envelope[Any, Any]) -> str:
    error = envelope.error
    if error is None:
        return "tooling: failed\n"
    lines = [
        f"tooling: {safe_text(error.message)} [{error.kind}]",
        f"  fix: {safe_text(error.remedy)}",
    ]
    lines += [f"  note: {safe_text(note)}" for note in envelope.notes]
    return "\n".join(lines) + "\n"


@dataclass
class _Delivery:
    delivered: bool = False


# Set by `EnvelopeCommand` for the duration of one command invocation.
_DELIVERY: ContextVar[_Delivery | None] = ContextVar("corpus_tooling_delivery", default=None)


def emit(envelope: Envelope[Any, Any], *, json: bool, strict: bool = False) -> None:
    """Deliver the command's one envelope; under `--strict` exit 1 when inputs were skipped.

    A second `emit` in the same invocation raises `RuntimeError` (exit 3, no second result)."""
    delivery = _DELIVERY.get()
    if delivery is not None:
        if delivery.delivered:
            raise RuntimeError("emit called twice: a command delivers exactly one envelope")
        delivery.delivered = True
    exit_code = EXIT_STRICT if strict and envelope.coverage.skipped_inputs else 0
    if json:
        write_stdout(envelope.model_dump_json() + "\n", exit_code=exit_code)
    elif stdout_is_terminal():
        _ResultConsole(exit_code).print(render_rich(envelope))
    else:
        write_stdout(render_plain(envelope), exit_code=exit_code)
    if exit_code:
        raise typer.Exit(exit_code)


def emit_failure(envelope: Envelope[Any, Any], *, json: bool) -> NoReturn:
    """A failed envelope: JSON on stdout under `--json`, otherwise a short report on stderr."""
    if json:
        write_stdout(envelope.model_dump_json() + "\n", exit_code=EXIT_FAILURE)
    else:
        with suppress(OSError):
            sys.stderr.write(_failure_text(envelope))
            sys.stderr.flush()
    raise typer.Exit(EXIT_FAILURE)


# --- the command class every envelope command runs under -------------------------------------


def _json_requested(command: TyperCommand, ctx: typer.Context) -> bool:
    for param in command.params:
        if "--json" in getattr(param, "opts", ()):
            return bool(ctx.params.get(param.name or ""))
    return False


@dataclass(frozen=True)
class FailureContext:
    """What a failed envelope can still carry from the group's state."""

    baseline: Baseline | None = None
    notes: tuple[str, ...] = ()
    authorities: Mapping[str, str] = field(default_factory=dict)


@runtime_checkable
class ProvidesFailureContext(Protocol):
    """Implemented by a group's `ctx.obj` (such as `LibraryState`) so a failure after target
    resolution keeps the baseline block and the target's notes."""

    def failure_context(self) -> FailureContext: ...


def _failure_context(ctx: typer.Context) -> FailureContext:
    if isinstance(ctx.obj, ProvidesFailureContext):
        with suppress(Exception):
            return ctx.obj.failure_context()
    return FailureContext()


EXIT_USAGE = 2


def _is_foreign_usage_error(error: Exception) -> bool:
    """A usage error from the standalone `click` package (installed beside Typer, which vendors
    its own copy): a `UsageError` subclass such as `BadParameter`."""
    return any(
        kind.__name__ == "UsageError" and kind.__module__.split(".", 1)[0] == "click"
        for kind in type(error).__mro__
    )


def _report_usage_error(error: Exception) -> NoReturn:
    """Report a usage error raised inside a command body as Typer reports its own: a message on
    stderr, exit 2, no envelope."""
    format_message = getattr(error, "format_message", None)
    message = format_message() if callable(format_message) else str(error)
    with suppress(OSError):
        sys.stderr.write(f"Error: {safe_text(message)}\n")
        sys.stderr.flush()
    raise typer.Exit(EXIT_USAGE)


class EnvelopeCommand(TyperCommand):
    """Turns a `ToolFailure` (or an unexpected exception, traceback on stderr) raised by the
    command into exit 3 with a `status: failed` envelope. A usage error raised in the body
    (`typer.BadParameter`, or a `click` usage error) exits 2 with no envelope, as one raised
    while parsing does. After the envelope was delivered, a later failure still exits 3,
    reported on stderr only: stdout never gets a second result."""

    def invoke(self, ctx: Any) -> Any:
        delivery = _Delivery()
        token = _DELIVERY.set(delivery)
        try:
            return super().invoke(ctx)
        except ToolFailure as failure:
            error = failure.error
        except typer.Exit, typer.Abort, typer.TyperException, KeyboardInterrupt:
            raise  # usage and parameter errors (Typer's vendored Click) keep Typer's handling
        except Exception as unexpected:
            if type(unexpected).__module__.startswith("typer"):
                raise
            if _is_foreign_usage_error(unexpected):
                _report_usage_error(unexpected)  # exit 2, never an envelope
            traceback.print_exc(file=sys.stderr)
            error = ErrorInfo(
                kind="internal_error",
                message=f"{type(unexpected).__name__}: {unexpected}",
                remedy="This is a defect in the tool; the traceback is on stderr.",
            )
        finally:
            _DELIVERY.reset(token)
        if delivery.delivered:
            with suppress(OSError):
                sys.stderr.write(
                    f"tooling: failed after the result was delivered: {safe_text(error.message)}"
                    f" [{error.kind}]\n"
                )
            raise typer.Exit(EXIT_FAILURE)
        context = _failure_context(ctx)
        envelope = failed_envelope(
            command=normalized_command(ctx),
            error=error,
            baseline=context.baseline,
            authorities=context.authorities,
            notes=context.notes,
        )
        emit_failure(envelope, json=_json_requested(self, ctx))


def envelope_commands(group: typer.Typer) -> None:
    """Run every command registered on `group` under `EnvelopeCommand`."""
    for info in group.registered_commands:
        if info.cls is None or info.cls is TyperCommand:  # `Typer.command` fills in the default
            info.cls = EnvelopeCommand
        elif not issubclass(info.cls, EnvelopeCommand):
            raise TypeError(f"command {info.name}: a custom cls must subclass EnvelopeCommand")
