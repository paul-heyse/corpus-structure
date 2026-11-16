"""Public pytest hooks supplement reportlog; reports remain the outcome authority."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any, TextIO

import pytest
from hypothesis import settings

_stream: TextIO | None = None
_identity: dict[str, object] = {}
_current_nodeid: str | None = None
_logical_nodeid = pytest.StashKey[str]()
_requested_worker_selection = pytest.StashKey[object]()


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_cmdline_main(config: pytest.Config) -> Generator[None, Any, Any]:
    # Capture parsed CLI/ini/environment selection before xdist resolves auto/logical.
    config.stash[_requested_worker_selection] = config.getoption("numprocesses", None)
    return (yield)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--qualification-evidence",
        choices=("ordinary", "providers"),
        default="ordinary",
        help="Select ordinary controls or explicitly required provider evidence.",
    )


def _explicit_provider(item: pytest.Item, config: pytest.Config) -> bool:
    logical = item.stash[_logical_nodeid]
    _, _, suffix = logical.partition("::")
    for selector in config.args:
        filename, separator, selected = selector.partition("::")
        if (
            separator
            and Path(filename).resolve() == item.path.resolve()
            and (
                suffix == selected
                or suffix.startswith(selected + "::")
                or suffix.startswith(selected + "[")
            )
        ):
            return True
    return False


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> Generator[None]:
    # Preserve identities before xdist adds group suffixes, then apply evidence selection
    # after normal keyword and lane filters. Excluded providers are never required nodes.
    for item in items:
        item.stash[_logical_nodeid] = item.nodeid
    private = os.environ.get("CORPUS_CI_NATIVE_HOST", "shared") == "private"
    explicit_incompatible = [
        item.stash[_logical_nodeid]
        for item in items
        if private
        and item.get_closest_marker("shared_cluster_fault")
        and _explicit_provider(item, config)
    ]
    yield
    incompatible = [
        item.stash[_logical_nodeid]
        for item in items
        if private
        and (
            item.get_closest_marker("shared_cluster_fault")
            or item.get_closest_marker("private_host_incompatible")
        )
    ]
    if explicit_incompatible or incompatible:
        message = (
            "private native host is incompatible with shared-host/authentication or durability controls: "
            + ", ".join(sorted(set(explicit_incompatible + incompatible)))
        )
        _emit("selection_refusal", message=message)
        raise pytest.UsageError(message)
    mode = config.getoption("qualification_evidence")
    providers = [item for item in items if item.get_closest_marker("provider_evidence")]
    if mode == "ordinary":
        explicit = [
            item.stash[_logical_nodeid] for item in providers if _explicit_provider(item, config)
        ]
        if explicit:
            message = "provider evidence requires ci test --providers-only: " + ", ".join(explicit)
            _emit("selection_refusal", message=message)
            raise pytest.UsageError(message)
    elif any(item.get_closest_marker("shared_cluster_fault") for item in items):
        message = "provider evidence is incompatible with the exclusive fault lane"
        _emit("selection_refusal", message=message)
        raise pytest.UsageError(message)
    selected = []
    excluded = []
    for item in items:
        target = (
            selected
            if bool(item.get_closest_marker("provider_evidence")) == (mode == "providers")
            else excluded
        )
        target.append(item)
    if excluded:
        config.hook.pytest_deselected(items=excluded)
        items[:] = selected


def native_context_active() -> bool:
    """Whether an actual receipt sink can currently consume optional native observations."""
    return _stream is not None and not _stream.closed


def _emit(event: str, **values: object) -> None:
    if native_context_active():
        assert _stream is not None
        _stream.write(
            json.dumps({"event": event, "time": time.time(), **_identity, **values}) + "\n"
        )
        _stream.flush()


def record_native_context(
    context: dict[str, object], *, scope: str = "test", nodeid: str | None = None
) -> None:
    """Record requested and acquired native context in the current pytest event stream.

    Completeness denotes item-bound acquired identity; deployment/policy metadata is optional.
    Test-scoped records default to the item whose fixture/setup is currently running. Session
    records are explicitly unbound to an item; they describe a resource that may serve many
    tests, and cannot by themselves attest any one test's exercise.
    """
    if scope not in {"test", "session"}:
        raise ValueError("native context scope must be 'test' or 'session'")
    associated = None if scope == "session" else (nodeid or _current_nodeid)
    _emit("native_context", context=context, scope=scope, nodeid=associated)


def logical_nodeid(item: pytest.Item) -> str:
    """The collection owner's identity, before any xdist scheduling suffix."""
    if _logical_nodeid in item.stash:
        return item.stash[_logical_nodeid]
    if native_context_active():
        raise RuntimeError("managed SQL selection has no authoritative logical identity")
    return item.nodeid


def record_sql_batch(report: dict[str, Any], *, directory: str, nodeids: list[str]) -> None:
    """Diagnostic observations only; each pytest member gates its own qualification."""
    _emit("sql_batch", report=report, directory=directory, nodeids=nodeids)


def pytest_configure(config: pytest.Config) -> None:
    global _stream, _identity
    config.addinivalue_line("markers", "provider_evidence: opt-in actual provider evidence")
    config.addinivalue_line("markers", "prerequisite(name): collection-time external prerequisite")
    config.addinivalue_line(
        "markers", "sql_family(family, case, assertions): finite native SQL family member"
    )
    config.addinivalue_line(
        "markers",
        "private_host_incompatible: requires shared host, peer authentication or durability semantics",
    )
    directory = os.environ.get("QUALIFICATION_RECEIPT_DIR")
    if directory is None:
        return
    worker = os.environ.get("PYTEST_XDIST_WORKER", "controller")
    _identity = {"pid": os.getpid(), "worker": worker}
    _stream = (Path(directory) / f"events-{worker}-{os.getpid()}.jsonl").open("x")
    config.add_cleanup(_close)
    _emit("process_start", invocation_args=list(config.invocation_params.args))


def _close() -> None:
    global _stream
    if _stream is not None:
        _stream.close()
        _stream = None


def pytest_sessionstart(session: pytest.Session) -> None:
    _emit(
        "session_start",
        hypothesis_profile=settings.get_current_profile_name(),
        hypothesis_settings=str(settings.default),
        faulthandler_timeout=session.config.getini("faulthandler_timeout"),
        faulthandler_exit_on_timeout=session.config.getini("faulthandler_exit_on_timeout"),
        xdist_numprocesses=session.config.getoption("numprocesses"),
        xdist_dist=session.config.getoption("dist"),
        xdist_loadgroup=session.config.getoption("loadgroup", False),
        invocation_args=list(session.config.invocation_params.args),
        requested_worker_selection=session.config.stash.get(_requested_worker_selection, None),
        effective_worker_count=int(os.environ.get("PYTEST_XDIST_WORKER_COUNT", "0")),
        math_pool_cap=8,
        evidence_selection=session.config.getoption("qualification_evidence"),
        native_host=os.environ.get("CORPUS_CI_NATIVE_HOST", "shared"),
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    # xdist can finish its controller with NO_TESTS_COLLECTED after a worker
    # refuses an invalid selector. Preserve each actual session's exit status.
    _emit("session_finish", exitstatus=exitstatus)


def pytest_collection_finish(session: pytest.Session) -> None:
    aliases: dict[str, str] = {}
    originals: set[str] = set()
    for item in session.items:
        original = item.stash[_logical_nodeid]
        if item.nodeid in aliases or original in originals:
            raise pytest.UsageError(f"ambiguous collected node identity: {item.nodeid}")
        aliases[item.nodeid] = original
        originals.add(original)
    _emit(
        "collection_finish",
        nodeid_aliases=aliases,
        affinity_groups={
            item.nodeid: sorted(
                {
                    str(mark.args[0] if mark.args else mark.kwargs.get("name", "default"))
                    for mark in item.iter_markers("xdist_group")
                }
            )
            for item in session.items
        },
        selected=[item.nodeid for item in session.items],
        evidence_selection=session.config.getoption("qualification_evidence"),
        native_host=os.environ.get("CORPUS_CI_NATIVE_HOST", "shared"),
        provider_evidence=[
            item.nodeid for item in session.items if item.get_closest_marker("provider_evidence")
        ],
        native_required=[
            item.nodeid for item in session.items if item.get_closest_marker("db") is not None
        ],
    )


def pytest_deselected(items: list[pytest.Item]) -> None:
    _emit("deselected", nodes=[item.nodeid for item in items])


def pytest_runtest_logstart(nodeid: str, location: object) -> None:
    global _current_nodeid
    _current_nodeid = nodeid
    _emit("logstart", nodeid=nodeid, location=location)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> Generator[None, Any, Any]:
    _emit("phase_start", nodeid=item.nodeid, phase="setup")
    return (yield)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None, Any, Any]:
    _emit("phase_start", nodeid=item.nodeid, phase="call")
    return (yield)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_teardown(item: pytest.Item) -> Generator[None, Any, Any]:
    _emit("phase_start", nodeid=item.nodeid, phase="teardown")
    return (yield)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    error = call.excinfo.value if call.excinfo is not None else None
    grouped = _exception_group_messages(error) if isinstance(error, BaseExceptionGroup) else None
    report = yield
    if call.excinfo is not None:
        # Import lazily: pure test collection never acquires application/native settings.
        from test_prerequisites import PrerequisiteUnavailable

        error = call.excinfo.value
        if grouped is not None:
            report.user_properties.append(("qualification_exception_group", grouped))
        if isinstance(error, PrerequisiteUnavailable):
            report.user_properties.extend(
                [
                    ("qualification_prerequisite", error.category),
                    ("qualification_reason", error.reason),
                ]
            )
    return report


def _exception_group_messages(error: BaseExceptionGroup) -> dict[str, Any]:
    """Capture native messages and frame coordinates, without source, SQL or locals."""
    entries = []
    seen = set()
    omitted = 0
    remaining = 16384
    frame_remaining = 16384

    def visit(value: BaseException, path: str, depth: int) -> None:
        nonlocal omitted, remaining, frame_remaining
        if id(value) in seen:
            return
        seen.add(id(value))
        if len(entries) >= 32 or depth > 8:
            omitted += 1
            return
        try:
            # Driver details/SQL are subsequent lines. Never pre-clip credentials;
            # the managed CLI redacts complete captured messages before display.
            message = str(value).split("\n", 1)[0]
        except Exception:
            message = "exception message unavailable"
        try:
            message.encode("utf-8")
        except UnicodeError:
            message = "exception message encoding unavailable"
            omitted += 1
        message_size = len(json.dumps(message).encode())
        if message_size > remaining:
            message = "exception message exceeds capture limit"
            omitted += 1
        else:
            remaining -= message_size
        # Keep the innermost four actual frame coordinates. ExceptionGroup's
        # rendered traceback does not expose these as structured pytest entries.
        # Never retain a frame, locals or source lines in the serialized report.
        frames = []
        native = value.__traceback__
        visited = 0
        while native is not None and visited < 256:
            frames.append(
                dict(
                    path=native.tb_frame.f_code.co_filename,
                    lineno=native.tb_lineno,
                    function=native.tb_frame.f_code.co_name,
                )
            )
            frames = frames[-4:]
            native = native.tb_next
            visited += 1
        if native is not None:
            omitted += 1
        captured_frames = []
        for frame in frames:
            size = len(json.dumps(frame).encode())
            if size > frame_remaining:
                omitted += 1
                continue
            frame_remaining -= size
            captured_frames.append(frame)
        entries.append(
            dict(
                path=path,
                type=type(value).__module__ + "." + type(value).__qualname__,
                message=message,
                traceback=captured_frames,
            )
        )
        if isinstance(value, BaseExceptionGroup):
            for index, child in enumerate(value.exceptions):
                visit(child, path + f".exceptions[{index}]", depth + 1)
        if value.__cause__ is not None:
            visit(value.__cause__, path + ".__cause__", depth + 1)
        elif not value.__suppress_context__ and value.__context__ is not None:
            visit(value.__context__, path + ".__context__", depth + 1)

    visit(error, "$", 0)
    return dict(version=2, entries=entries, omitted=omitted)


def pytest_runtest_logfinish(nodeid: str, location: object) -> None:
    global _current_nodeid
    _emit("logfinish", nodeid=nodeid, location=location)
    if _current_nodeid == nodeid:
        _current_nodeid = None


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node: Any, error: object) -> None:
    _emit("worker_down", lost_worker=node.gateway.id, error=str(error) if error else None)


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_setupnodes(config: pytest.Config, specs: list[Any]) -> None:
    _emit("workers_created", count=len(specs), workers=[spec.id for spec in specs])


@pytest.hookimpl(optionalhook=True)
def pytest_testnodeready(node: Any) -> None:
    _emit("worker_ready", ready_worker=node.gateway.id)
