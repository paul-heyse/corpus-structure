"""Private physical work ports; callbacks and reduction stay with their parent owner."""

from collections.abc import Callable, Generator
from concurrent.futures import FIRST_COMPLETED, Future, wait
from dataclasses import dataclass, field
from typing import Any, Protocol


class WorkHandle[T](Protocol):
    @property
    def future(self) -> Future[Any]: ...
    def collect(self) -> T: ...
    def cancel(self) -> None: ...
    def retire(self) -> bool: ...


@dataclass(frozen=True)
class PreparedWork[T]:
    """A parent-only submission factory; None is ordinary capacity backpressure."""

    try_submit: Callable[[], WorkHandle[T] | None]
    abandon: Callable[[], None] = lambda: None


@dataclass(frozen=True)
class ReadyGroup:
    """Independent child plans, bounded activation and stable result association."""

    plans: tuple[Generator[Any, Any, Any], ...]
    max_active: int | None = None

    def __post_init__(self):
        if self.max_active is not None and self.max_active < 1:
            raise ValueError("ready plan admission requires a positive window")


@dataclass
class _Node:
    plan: Generator[Any, Any, Any]
    yielded: Any = None
    started: bool = False
    done: bool = False
    value: Any = None
    error: BaseException | None = None
    children: dict[int, Any] = field(default_factory=dict)
    handles: dict[int, WorkHandle] = field(default_factory=dict)
    replies: dict[int, Any] = field(default_factory=dict)
    retiring: list[WorkHandle] = field(default_factory=list)

    def abandon_requests(self):
        if isinstance(self.yielded, tuple):
            for work in self.yielded:
                if isinstance(work, PreparedWork):
                    work.abandon()

    def advance(self, value=None, error=None):
        try:
            self.abandon_requests()
            if error is not None:
                self.yielded = self.plan.throw(error)
            elif not self.started:
                self.started = True
                self.yielded = next(self.plan)
            else:
                self.yielded = self.plan.send(value)
        except StopIteration as complete:
            self.done, self.value = True, complete.value
        except Exception as failure:
            self.done, self.error = True, failure
        self.children, self.handles, self.replies = {}, {}, {}

    def tick(self):
        self.retiring = [handle for handle in self.retiring if not handle.retire()]
        if self.done:
            return False
        if not self.started:
            self.advance()
            return True
        if isinstance(self.yielded, ReadyGroup):
            group = self.yielded
            active = sum(not child.done for child in self.children.values())
            for index, plan in enumerate(group.plans):
                if index not in self.children and active < (group.max_active or len(group.plans)):
                    self.children[index] = _Node(plan)
                    active += 1
            progress = False
            for child in tuple(self.children.values()):
                progress = child.tick() or progress
            if len(self.children) == len(group.plans) and all(
                c.done for c in self.children.values()
            ):
                failure = next((c.error for c in self.children.values() if c.error), None)
                values = tuple(self.children[i].value for i in range(len(group.plans)))
                for child in self.children.values():
                    self.retiring.extend(child.retiring)
                    child.retiring = []
                self.advance(values, failure)
                return True
            return progress
        group = self.yielded
        progress = False
        try:
            for index, work in enumerate(group):
                if index not in self.handles:
                    handle = work.try_submit()
                    if handle is not None:
                        self.handles[index] = handle
                        progress = True
            for index, handle in tuple(self.handles.items()):
                active = getattr(handle, "check_active", None)
                if active is not None:
                    active()
                if index not in self.replies and handle.future.done():
                    self.replies[index] = handle.collect()
                    progress = True
            if len(self.replies) == len(group):
                handles = tuple(self.handles.values())
                values = tuple(self.replies[i] for i in range(len(group)))
                # Reduction happens in the generator before input/reply credit retires.
                self.advance(values)
                for handle in handles:
                    if not handle.retire():
                        self.retiring.append(handle)
                return True
        except Exception as failure:
            handles = tuple(self.handles.values())
            for handle in handles:
                handle.cancel()
            self.advance(error=failure)
            for handle in handles:
                if not handle.retire():
                    self.retiring.append(handle)
            return True
        return progress

    def futures(self):
        return [
            h.future for h in (*self.handles.values(), *self.retiring) if not h.future.done()
        ] + [future for child in self.children.values() for future in child.futures()]

    def flush(self):
        for handle in self.handles.values():
            flush = getattr(handle, "flush", None)
            if flush is not None:
                flush()
        for child in self.children.values():
            child.flush()

    def close(self):
        failures = []
        try:
            self.abandon_requests()
        except BaseException as error:
            failures.append(error)
        for child in self.children.values():
            try:
                child.close()
            except BaseException as error:
                failures.append(error)
        for handle in (*self.handles.values(), *self.retiring):
            try:
                handle.cancel()
                handle.retire()
            except BaseException as error:
                failures.append(error)
        try:
            self.plan.close()
        except BaseException as error:
            failures.append(error)
        if failures:
            for extra in failures[1:]:
                failures[0].add_note("additional plan cleanup failure: " + str(extra))
            raise failures[0]


def drive_prepared_work(plan: Generator[Any, Any, Any], check_active: Callable[[], None]):
    """One parent loop drives standalone and bounded nested invocation plans."""
    root = _Node(plan)
    try:
        while not root.done:
            check_active()
            if not root.tick():
                root.flush()
                running = root.futures()
                if running:
                    wait(running, timeout=0.1, return_when=FIRST_COMPLETED)
                else:
                    # Flush may have completed a small exchange synchronously.
                    # Revisit collection before classifying a fixed admission stall.
                    if root.tick():
                        continue
                    running = root.futures()
                    if running:
                        wait(running, timeout=0.1, return_when=FIRST_COMPLETED)
                    else:
                        raise RuntimeError(
                            "ready work cannot acquire capacity and has no in-flight work "
                            "that can release admission"
                        )
        if root.error is not None:
            raise root.error
        return root.value
    finally:
        import sys

        primary = sys.exception()
        try:
            root.close()
        except BaseException as cleanup:
            if primary is None:
                raise
            primary.add_note("ready-plan cleanup failure: " + str(cleanup))
