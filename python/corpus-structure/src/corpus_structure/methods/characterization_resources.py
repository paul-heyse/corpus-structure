"""Explicit invocation-owned native lanes and detached parent-side work intents."""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Callable
from concurrent.futures import CancelledError, Future
from contextlib import ExitStack, contextmanager, suppress
from dataclasses import asdict, dataclass, field, replace
from hashlib import sha256
from threading import BoundedSemaphore, Event, Lock, Thread
from typing import Any, Literal

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.method import PreparedWork
from corpus_structure.semantic.identity import canonical_bytes

from .gliner import GlinerInput, GlinerPack, GlinerProfile, GlinerRefused
from .gliner_worker import validate_request
from .model_observation import ordered_native_bytes, pm2_cohort_digest, pm2_member_digest
from .native_host import (
    NativeExecutionReceipt,
    NativeHostGroup,
    host_request_frame_size,
    payload_digest,
)
from .native_profiles import NativeSelection, pm2_selection
from .pm2_worker import Pm2WorkerError, Pm2WorkerRefused


@dataclass(frozen=True)
class LogicalProviderMember:
    """Exact producing attempt and contiguous ordered native-input membership."""

    request_id: str
    generation: int
    task_id: int
    attempt: int
    member: str
    start: int
    count: int
    input_digest: str


@dataclass(frozen=True)
class ProviderExecutionReceipt:
    """Immutable original-work/cohort scatter and physical exchange correspondence."""

    correlation: str
    cohort_digest: str
    member_offset: int
    member_count: int
    native_member_digests: tuple[str, ...]
    logical_members: tuple[LogicalProviderMember, ...]
    physical: tuple[NativeExecutionReceipt, ...]
    cohort_members: tuple[str, ...]
    work_members: tuple[tuple[str, int, int], ...]


def _native_members(request):
    if isinstance(request, GLiNERWork):
        return [asdict(item) for item in request.inputs]
    if request.payload is None:
        return []
    value = json.loads(request.payload)
    key = {"d1": "batch", "hanlp": "sentences", "spacy": "documents"}.get(
        request.selection.provider
    )
    return value[key] if key is not None else [value]


def _validate_logical_members(request):
    if not request.logical_members:
        return
    values = _native_members(request)
    cursor = 0
    keys = set()
    for member in request.logical_members:
        key = (member.request_id, member.generation, member.task_id, member.attempt, member.member)
        if (
            not member.request_id
            or not member.member
            or key in keys
            or any(
                type(value) is not int or value < 1
                for value in (member.generation, member.task_id, member.attempt, member.count)
            )
            or type(member.start) is not int
            or member.start != cursor
            or member.input_digest
            != payload_digest(values[member.start : member.start + member.count])
        ):
            raise ValueError("logical provider member differs from its ordered native input")
        keys.add(key)
        cursor += member.count
    if cursor != len(values):
        raise ValueError("logical provider members do not cover native input population")


def _execution_receipt(
    request, physical, *, cohort=None, offset=0, cohort_members=None, work_members=None
):
    _validate_logical_members(request)
    values = _native_members(request)
    local = tuple(payload_digest(item) for item in values)
    population = local if cohort_members is None else tuple(cohort_members)
    works = (
        ((request.correlation, 0, len(values)),) if work_members is None else tuple(work_members)
    )
    if (
        type(offset) is not int
        or offset < 0
        or population[offset : offset + len(local)] != local
        or (request.correlation, offset, len(local)) not in works
    ):
        raise ValueError("provider scatter receipt differs from original native member range")
    digest = payload_digest({"works": works, "members": population})
    if cohort is not None and cohort != digest:
        raise ValueError("provider cohort identity differs from original ordered membership")
    return ProviderExecutionReceipt(
        request.correlation,
        digest,
        offset,
        len(values),
        local,
        request.logical_members,
        tuple(physical),
        population,
        works,
    )


@dataclass(frozen=True)
class PM2Work:
    selection: NativeSelection
    payload: bytes | None
    correlation: str
    borrowers: tuple[Callable[[], None], ...]
    logical_members: tuple[LogicalProviderMember, ...] = ()


@dataclass(frozen=True)
class GLiNERWork:
    profile: GlinerProfile
    pack: GlinerPack
    inputs: tuple[GlinerInput, ...]
    threshold: float
    overlap_policy: str
    correlation: str
    borrowers: tuple[Callable[[], None], ...]
    evaluation: bool = False
    logical_sizes: tuple[int, ...] = ()
    logical_members: tuple[LogicalProviderMember, ...] = ()


def validate_gliner_policy(profile: GlinerProfile, policy: CharacterizationExecutionPolicy):
    """Reject a selected policy that cannot execute the immutable GLiNER profile."""
    if profile.threads != policy.provider_threads or policy.provider_interop_threads != 1:
        raise GlinerRefused("frozen GLiNER threads/inter-op differ from execution policy")
    if profile.device != "cuda":
        raise GlinerRefused("current native execution requires an explicit CUDA GLiNER profile")


@dataclass(frozen=True)
class ProviderReply:
    correlation: str
    startup_content: bytes = b"{}"
    payload_content: bytes = b"{}"
    reports: tuple = ()
    admissions: tuple = ()
    error_type: str | None = None
    error_message: str | None = None
    execution_receipt: ProviderExecutionReceipt | None = None

    @property
    def startup(self):
        return json.loads(self.startup_content)

    @property
    def payload(self):
        if self.error_type is not None:
            if self.error_type == "CapacityExceeded":
                from corpus_structure.semantic.cpu_execution import CapacityExceeded

                raise CapacityExceeded(self.error_message)
            kind = Pm2WorkerRefused if self.error_type == "Pm2WorkerRefused" else Pm2WorkerError
            raise kind(self.error_message)
        return json.loads(self.payload_content)


@dataclass(eq=False)
class ProviderHandle:
    owner: ProviderExecution
    lane: _Lane
    request: PM2Work | GLiNERWork
    reservation: int
    future: Future = field(default_factory=Future)
    stopped: Event = field(default_factory=Event)
    collected: bool = False
    retired: bool = False

    def flush(self):
        self.lane.flush()

    def active(self):
        if self.owner._stop.is_set() or self.stopped.is_set():
            raise CancelledError("native physical request cancelled")
        failures = []
        for borrower in self.request.borrowers:
            try:
                borrower()
                return
            except Exception as error:
                failures.append(error)
        if failures:
            raise CancelledError("native request has no live logical borrowers") from failures[0]

    def check_active(self):
        self.active()

    def collect(self):
        if not self.future.done():
            return None
        if not self.collected:
            self.collected = True
            self.lane.slots.release()
        reply = self.future.result()
        if reply.correlation != self.request.correlation:
            raise ValueError("native response correlation differs from admitted request")
        receipt = reply.execution_receipt
        if receipt is not None:
            expected = _execution_receipt(
                self.request,
                receipt.physical,
                cohort=receipt.cohort_digest,
                offset=receipt.member_offset,
                cohort_members=receipt.cohort_members,
                work_members=receipt.work_members,
            )
            if receipt != expected:
                raise ValueError(
                    "native execution receipt differs from admitted logical membership"
                )
        if (
            reply.error_type is None
            and self.request.logical_members
            and (receipt is None or not receipt.physical)
        ):
            raise ValueError("logical request lacks authenticated physical execution receipt")
        return reply

    def cancel(self):
        self.stopped.set()
        if self.future.cancel():
            with self.lane.lock, suppress(ValueError):
                self.lane.pending.remove(self)

    def retire(self):
        if not self.future.done():
            return False
        if not self.collected:
            self.collected = True
            self.lane.slots.release()
        if not self.retired:
            self.retired = True
            self.owner.budget.release(self.reservation)
            self.owner._handles.discard(self)
        return True


class _Lane:
    def __init__(self, owner, name):
        self.owner, self.name = owner, name
        self.pending = deque()
        self.lock = Lock()
        self.thread = None
        self.closed = False
        self.wake = Event()
        self.close_error = None
        self.slots = BoundedSemaphore(owner.policy.max_provider_jobs)
        self.stack = ExitStack()
        self.worker = None
        self.key = None
        self.current = None
        self.broken = None

    def active(self):
        if self.current is None:
            raise CancelledError("native lane has no active physical request")
        self.current.active()

    def discard(self):
        stack, self.stack = self.stack, ExitStack()
        self.worker, self.key = None, None
        try:
            stack.close()
        except BaseException as error:
            self.broken = error
            raise

    def execute(self, handle):
        self.current = handle
        request = handle.request
        startup = {}
        physical = []
        try:
            handle.active()
            _validate_logical_members(request)
            if self.broken is not None:
                raise Pm2WorkerError("native lane has unresolved teardown failure") from self.broken
            if isinstance(request, PM2Work):
                selection = request.selection
                group = self.owner.native_group
                group.declare((selection,))
                startup = group.startup(selection, self.active)
                payload = {}
                if request.payload is not None:
                    response = group.infer_result(
                        selection, json.loads(request.payload), self.active
                    )
                    payload = response.payload
                    if (
                        response.receipt.provider != selection.provider
                        or response.receipt.profile != selection.native.fingerprint
                        or response.receipt.runtime != sha256(selection.runtime).hexdigest()
                        or response.receipt.input_digest
                        != payload_digest(json.loads(request.payload))
                        or response.receipt.output_digest != payload_digest(payload)
                    ):
                        raise ValueError(
                            "native host execution receipt differs from admitted exchange"
                        )
                    physical.append(response.receipt)
                reply = ProviderReply(
                    request.correlation,
                    canonical_bytes(startup),
                    ordered_native_bytes(payload),
                    execution_receipt=_execution_receipt(request, physical),
                )
            else:
                key = request.profile
                if self.worker is None or self.worker.closed or self.key != key:
                    self.discard()
                    from .native_host_clients import HostedGliner

                    self.worker = HostedGliner(request.profile, group=self.owner.native_group)
                    self.stack.callback(self.worker.close)
                    self.key = key
                admissions = self.worker.prepare_members(
                    request.pack,
                    request.inputs,
                    threshold=request.threshold,
                    overlap_policy=request.overlap_policy,
                    evaluation=request.evaluation,
                    check_active=self.active,
                    receipt_sink=physical.append,
                )
                sizes = request.logical_sizes or (len(request.inputs),)
                admitted = []
                offset = 0
                for length in sizes:
                    selected = admissions[offset : offset + length]
                    if all(member.admitted for member in selected):
                        admitted.extend(request.inputs[offset : offset + length])
                    offset += length
                if offset != len(request.inputs):
                    raise Pm2WorkerError(
                        "logical native population differs from physical admission"
                    )
                reports = (
                    self.worker.extract(
                        request.pack,
                        tuple(admitted),
                        threshold=request.threshold,
                        overlap_policy=request.overlap_policy,
                        evaluation=request.evaluation,
                        check_active=self.active,
                        receipt_sink=physical.append,
                    )
                    if admitted
                    else ()
                )
                reply = ProviderReply(
                    request.correlation,
                    reports=reports,
                    admissions=admissions,
                    execution_receipt=_execution_receipt(request, physical),
                )
            handle.active()
            size = (
                len(reply.startup_content)
                + len(reply.payload_content)
                + len(canonical_bytes([asdict(report) for report in reply.reports]))
                + len(canonical_bytes([asdict(member) for member in reply.admissions]))
                + (
                    0
                    if reply.execution_receipt is None
                    else len(canonical_bytes(asdict(reply.execution_receipt)))
                )
            )
            if size > self.owner.policy.max_native_reply_bytes:
                from corpus_structure.semantic.cpu_execution import CapacityExceeded

                raise CapacityExceeded("native reply exceeds admitted byte capacity")
            return reply
        except Exception as error:
            try:
                if (
                    not isinstance(error, (Pm2WorkerRefused, GlinerRefused))
                    or self.worker is None
                    or self.worker.closed
                ):
                    self.discard()
            except BaseException as cleanup:
                error.add_note("native teardown failed: " + str(cleanup))
            detail = "; ".join((str(error), *getattr(error, "__notes__", ())))[:1800]
            return ProviderReply(
                request.correlation,
                canonical_bytes(startup),
                error_type=type(error).__name__,
                error_message=detail,
            )
        finally:
            self.current = None

    def enqueue(self, handle):
        with self.lock:
            self.pending.append(handle)

    def flush(self):
        with self.lock:
            if self.closed:
                return
            self.wake.set()
            if self.thread is None:
                self.thread = Thread(target=self.drain, name="native-" + self.name, daemon=True)
                self.thread.start()

    def drain(self):
        try:
            while True:
                with self.lock:
                    if self.closed:
                        return
                    if not self.pending:
                        self.wake.clear()
                        group = None
                    else:
                        first = self.pending.popleft()
                        if not first.future.set_running_or_notify_cancel():
                            continue
                        group = [first]
                        provider = (
                            first.request.selection.provider
                            if isinstance(first.request, PM2Work)
                            else "gliner"
                        )
                        if provider in self.owner.coalescing_providers:
                            while self.pending and self.owner.compatible(group, self.pending[0]):
                                following = self.pending.popleft()
                                if following.future.set_running_or_notify_cancel():
                                    group.append(following)
                if group is None:
                    self.wake.wait()
                    continue
                try:
                    replies = self.owner.exchange(self, group)
                except BaseException as error:
                    for handle in group:
                        handle.future.set_exception(error)
                else:
                    for handle, reply in zip(group, replies, strict=True):
                        handle.future.set_result(reply)
        finally:
            try:
                # Native context/device tokens are created and closed by this same
                # persistent owner thread, including explicit CUDA handoff contexts.
                self.discard()
            except BaseException as error:
                self.close_error = error

    def close(self):
        with self.lock:
            self.closed = True
            for handle in self.pending:
                handle.future.cancel()
            self.pending.clear()
            self.wake.set()
            thread = self.thread
        if thread is not None:
            thread.join(timeout=130)
            if thread.is_alive():
                raise Pm2WorkerError("native lane did not drain within startup bounds")
        else:
            self.discard()
        if self.close_error is not None or self.broken is not None:
            raise Pm2WorkerError("native lane teardown failed") from self.close_error or self.broken


@dataclass(eq=False)
class _PendingIntent:
    owner: Any
    request: Any
    size: int
    held: bool = True

    def abandon(self):
        with self.owner._lock:
            if self.held:
                self.held = False
                self.owner.budget.release(self.size)
                self.owner._intents.discard(self)


class ProviderExecution:
    """One owner, bounded admission and serialized exchange for each native provider."""

    def __init__(self, budget, policy: CharacterizationExecutionPolicy):
        self.budget, self.policy = budget, policy
        self._lanes = {}
        self._handles = set()
        self._intents = set()
        self._stop = Event()
        self._lock = Lock()
        self.coalescing_providers = frozenset({"hanlp", "d1", "gliner", "spacy"})
        self.native_group = NativeHostGroup(policy)

    def declare_native(self, selections, endpoint=None):
        if endpoint is not None:
            if self.native_group._serving and self.native_group.endpoint != endpoint:
                raise Pm2WorkerRefused("native custody endpoint changed after serving")
            self.native_group.endpoint = endpoint
        self.native_group.declare(tuple(selections))

    def _request_size(self, request):
        _validate_logical_members(request)
        if isinstance(request, GLiNERWork):
            validate_gliner_policy(request.profile, self.policy)
            if request.logical_sizes and (
                any(type(size) is not int or size < 1 for size in request.logical_sizes)
                or sum(request.logical_sizes) != len(request.inputs)
            ):
                raise GlinerRefused("logical GLiNER sizes differ from admitted inputs")
            validate_request(
                request.profile,
                request.pack,
                request.inputs,
                threshold=request.threshold,
                overlap_policy=request.overlap_policy,
                evaluation=request.evaluation,
            )
        size = (
            len(request.payload or b"")
            + len(request.selection.profile)
            + len(request.selection.runtime)
            + len(request.selection.artifacts)
            if isinstance(request, PM2Work)
            else len(
                canonical_bytes(
                    dict(
                        pack=asdict(request.pack), inputs=[asdict(item) for item in request.inputs]
                    )
                )
            )
        )
        if isinstance(request, GLiNERWork) and request.profile.device == "cuda":
            from .native_host_clients import HostedGliner, gliner_host_payload

            selected = HostedGliner(request.profile, group=self.native_group).selection
            size = max(
                size,
                host_request_frame_size(
                    selected,
                    gliner_host_payload(
                        request.pack,
                        request.inputs,
                        request.threshold,
                        request.overlap_policy,
                        request.evaluation,
                    ),
                    min(
                        self.policy.max_native_request_bytes,
                        request.profile.max_request_frame_bytes,
                    ),
                ),
            )
        if size > self.policy.max_native_request_bytes:
            from corpus_structure.semantic.cpu_execution import CapacityExceeded

            raise CapacityExceeded("complete native request exceeds admitted byte capacity")
        if isinstance(request, PM2Work) and request.payload is not None:
            # Keep the serialized frame owned as well as the frozen selection.
            try:
                size = max(
                    size,
                    host_request_frame_size(
                        request.selection,
                        json.loads(request.payload),
                        self.policy.max_native_request_bytes,
                    ),
                )
            except Pm2WorkerRefused as error:
                from corpus_structure.semantic.cpu_execution import CapacityExceeded

                raise CapacityExceeded(str(error)) from error
        return size + (
            len(canonical_bytes([asdict(member) for member in request.logical_members]))
            if request.logical_members
            else 0
        )

    @staticmethod
    def _pm2_payload(payloads, provider):
        key = "batch" if provider == "d1" else "documents" if provider == "spacy" else "sentences"
        combined = {**payloads[0], key: [value for payload in payloads for value in payload[key]]}
        if provider == "hanlp" and "admitted_row_tokens" in payloads[0]:
            combined["admitted_row_tokens"] = [
                value for payload in payloads for value in payload["admitted_row_tokens"]
            ]
        return combined

    def try_submit(self, request, pending=None):
        from corpus_structure.semantic.cpu_execution import CapacityExceeded

        if self._stop.is_set():
            raise CancelledError("native invocation is closed")
        provider = request.selection.provider if isinstance(request, PM2Work) else "gliner"
        if provider not in {"hanlp", "maverick", "dipo", "d1", "gliner", "spacy"}:
            raise ValueError("unsupported native provider")
        size = self._request_size(request) if pending is None else pending.size
        with self._lock:
            if self._stop.is_set():
                raise CancelledError("native invocation is closed")
            lane_key = provider
            lane = (
                self._lanes.setdefault(lane_key, _Lane(self, lane_key))
                if lane_key not in self._lanes
                else self._lanes[lane_key]
            )
            if not lane.slots.acquire(blocking=False):
                return None
            reservation = size + self.policy.max_native_reply_bytes
            if pending is not None and not pending.held:
                lane.slots.release()
                raise ValueError("native pending intent is no longer owned")
            try:
                self.budget.reserve(
                    reservation if pending is None else self.policy.max_native_reply_bytes
                )
            except CapacityExceeded:
                lane.slots.release()
                return None
            if pending is not None:
                pending.held = False
                self._intents.discard(pending)
            handle = ProviderHandle(self, lane, request, reservation)
            self._handles.add(handle)
            try:
                lane.enqueue(handle)
            except BaseException:
                handle.future.cancel()
                handle.retire()
                raise
            return handle

    def compatible(self, group, following):
        from corpus_structure.semantic.cpu_execution import CapacityExceeded

        first = group[0].request
        other = following.request
        payloads: list[Any] = []
        if isinstance(first, GLiNERWork):
            if not isinstance(other, GLiNERWork) or (
                first.profile,
                first.pack,
                first.threshold,
                first.overlap_policy,
                first.evaluation,
            ) != (
                other.profile,
                other.pack,
                other.threshold,
                other.overlap_policy,
                other.evaluation,
            ):
                return False
            inputs = tuple(item for handle in (*group, following) for item in handle.request.inputs)
            try:
                self._request_size(replace(first, inputs=inputs, logical_sizes=()))
            except GlinerRefused, CapacityExceeded:
                return False
            return True
        if not isinstance(other, PM2Work) or first.selection.identity != other.selection.identity:
            return False
        requests = [handle.request for handle in (*group, following)]
        if any(request.payload is None for request in requests):
            return all(request.payload is None for request in requests)
        payloads = [json.loads(request.payload) for request in requests]
        if first.selection.provider == "d1":
            admitted = (
                all(isinstance(payload.get("batch"), list) for payload in payloads)
                and sum(len(payload["batch"]) for payload in payloads) <= 16
            )
        elif first.selection.provider == "spacy":
            options = [
                {key: value for key, value in payload.items() if key != "documents"}
                for payload in payloads
            ]
            admitted = (
                all(option == options[0] for option in options)
                and sum(len(payload["documents"]) for payload in payloads)
                <= first.selection.native.parameters["batch_size"]
            )
        elif first.selection.provider == "hanlp":
            options = [
                {
                    key: value
                    for key, value in payload.items()
                    if key not in {"sentences", "admitted_row_tokens"}
                }
                for payload in payloads
            ]
            sentences = [
                sentence for payload in payloads for sentence in payload.get("sentences", ())
            ]
            if not payloads[0].get("prepare_bulk"):
                lengths = [
                    length
                    for payload in payloads
                    for length in payload.get("admitted_row_tokens", ())
                ]
                if (
                    len(lengths) != len(sentences)
                    or any(type(length) is not int or length < 1 for length in lengths)
                    or len(lengths) * max(lengths, default=0) > 2048
                ):
                    return False
            admitted = (
                all(option == options[0] for option in options)
                and len(sentences) <= 8
                and sum(len(word) for sentence in sentences for word in sentence) <= 32768
            )
        else:
            return False
        if not admitted:
            return False
        try:
            host_request_frame_size(
                first.selection,
                self._pm2_payload(payloads, first.selection.provider),
                self.policy.max_native_request_bytes,
            )
        except Pm2WorkerRefused:
            return False
        return True

    def exchange(self, lane, group):
        if (
            len(group) == 1
            and isinstance(group[0].request, PM2Work)
            and group[0].request.selection.provider not in {"d1", "hanlp"}
        ):
            return [lane.execute(group[0])]
        first = group[0].request
        borrowers = tuple(handle.active for handle in group)
        digest = sha256(
            canonical_bytes([handle.request.correlation for handle in group])
        ).hexdigest()
        if isinstance(first, PM2Work) and first.payload is None:
            if any(handle.request.payload is not None for handle in group):
                raise ValueError("native startup cannot share an inference envelope")
            combined = PM2Work(first.selection, None, digest, borrowers)
            reply = lane.execute(ProviderHandle(self, lane, combined, 0))
            return [
                ProviderReply(
                    handle.request.correlation,
                    reply.startup_content,
                    reply.payload_content,
                    error_type=reply.error_type,
                    error_message=reply.error_message,
                )
                for handle in group
            ]
        payloads: list[Any] = []
        key = "batch"
        if isinstance(first, GLiNERWork):
            inputs = tuple(item for handle in group for item in handle.request.inputs)
            lengths = [len(handle.request.inputs) for handle in group]
            combined = GLiNERWork(
                first.profile,
                first.pack,
                inputs,
                first.threshold,
                first.overlap_policy,
                digest,
                borrowers,
                first.evaluation,
                tuple(
                    length
                    for handle in group
                    for length in (handle.request.logical_sizes or (len(handle.request.inputs),))
                ),
            )
        else:
            for handle in group:
                raw = handle.request.payload
                if raw is None:
                    raise ValueError("native inference requires its complete envelope")
                payloads.append(json.loads(raw))
            key = (
                "batch"
                if first.selection.provider == "d1"
                else "documents"
                if first.selection.provider == "spacy"
                else "sentences"
            )
            lengths = [len(payload[key]) for payload in payloads]
            combined_payload = self._pm2_payload(payloads, first.selection.provider)
            content = ordered_native_bytes(combined_payload)
            combined = PM2Work(first.selection, content, digest, borrowers)
        synthetic = ProviderHandle(self, lane, combined, 0)
        reply = lane.execute(synthetic)
        if reply.error_type is not None:
            return [
                ProviderReply(
                    handle.request.correlation,
                    reply.startup_content,
                    error_type=reply.error_type,
                    error_message=reply.error_message,
                )
                for handle in group
            ]
        replies, offset = [], 0
        physical = () if reply.execution_receipt is None else reply.execution_receipt.physical
        cohort_members = tuple(payload_digest(item) for item in _native_members(combined))
        work_members = []
        position = 0
        for handle, count in zip(group, lengths, strict=True):
            work_members.append((handle.request.correlation, position, count))
            position += count

        def scattered(replies):
            cursor = 0
            result = []
            for handle, count, part in zip(group, lengths, replies, strict=True):
                result.append(
                    replace(
                        part,
                        execution_receipt=_execution_receipt(
                            handle.request,
                            physical,
                            offset=cursor,
                            cohort_members=cohort_members,
                            work_members=work_members,
                        ),
                    )
                )
                cursor += count
            return result

        if isinstance(first, GLiNERWork):
            if len(reply.admissions) != sum(lengths):
                raise Pm2WorkerError("native admission changed original logical population")
            report_offset = 0
            for handle, length in zip(group, lengths, strict=True):
                members = reply.admissions[offset : offset + length]
                refused = [member.reason for member in members if not member.admitted]
                if handle.request.logical_sizes:
                    count = 0
                    local_offset = 0
                    for logical_size in handle.request.logical_sizes:
                        selected = members[local_offset : local_offset + logical_size]
                        if all(member.admitted for member in selected):
                            count += logical_size
                        local_offset += logical_size
                    reports = reply.reports[report_offset : report_offset + count]
                    if len(reports) != count:
                        raise Pm2WorkerError("native inference omitted admitted logical member")
                    replies.append(
                        ProviderReply(
                            handle.request.correlation, reports=reports, admissions=members
                        )
                    )
                    report_offset += count
                elif refused:
                    replies.append(
                        ProviderReply(
                            handle.request.correlation,
                            error_type="GlinerRefused",
                            error_message="; ".join(refused),
                        )
                    )
                else:
                    reports = reply.reports[report_offset : report_offset + length]
                    if len(reports) != length:
                        raise Pm2WorkerError("native inference omitted admitted logical member")
                    replies.append(ProviderReply(handle.request.correlation, reports=reports))
                    report_offset += length
                offset += length
            if report_offset != len(reply.reports):
                raise Pm2WorkerError("native inference added an unadmitted logical member")
            return scattered(replies)
        body = reply.payload
        flattened = [value for payload in payloads for value in payload[key]]
        if first.selection.provider == "spacy":
            documents = body.get("documents")
            if not isinstance(documents, list) or len(documents) != len(flattened):
                raise Pm2WorkerError("combined spaCy response changed admitted document population")
            for handle, length in zip(group, lengths, strict=True):
                replies.append(
                    ProviderReply(
                        handle.request.correlation,
                        reply.startup_content,
                        ordered_native_bytes({"documents": documents[offset : offset + length]}),
                    )
                )
                offset += length
            return scattered(replies)
        header = dict(
            provider=first.selection.provider,
            profile=sha256(first.selection.profile).hexdigest(),
            runtime=sha256(first.selection.runtime).hexdigest(),
        )
        members = [pm2_member_digest(value) for value in flattened]
        receipt = dict(
            version=2,
            header=header,
            members=members,
            digest=pm2_cohort_digest(header, members),
        )
        if first.selection.provider == "d1" and (
            not isinstance(body.get("batch"), list) or len(body["batch"]) != len(flattened)
        ):
            raise Pm2WorkerError("combined d1 response changed admitted batch population")
        for handle, length in zip(group, lengths, strict=True):
            part = dict(body)
            if first.selection.provider == "d1":
                part["batch"] = [
                    {**value, "batch_receipt": {**receipt, "member_ordinal": ordinal}}
                    for ordinal, value in enumerate(body["batch"][offset : offset + length], offset)
                ]
            elif body.get("outcome") == "prepared_batch":
                if len(body.get("members", ())) != len(flattened):
                    raise Pm2WorkerError("combined HanLP preparation changed admitted population")
                part["members"] = [
                    {**value, "ordinal": local, "batch_member_ordinal": offset + local}
                    for local, value in enumerate(body["members"][offset : offset + length])
                ]
            elif body.get("outcome") == "succeeded":
                native, prepared = body.get("native"), body.get("preparation")
                if (
                    not isinstance(native, dict)
                    or native.get("tok") != flattened
                    or not isinstance(prepared, list)
                    or len(prepared) != len(flattened)
                ):
                    raise Pm2WorkerError(
                        "combined HanLP output changed admitted sentence population"
                    )
                part["native"] = {
                    key: value[offset : offset + length]
                    if isinstance(value, list) and len(value) == len(flattened)
                    else value
                    for key, value in native.items()
                }
                part["preparation"] = [
                    {**value, "batch_receipt": {**receipt, "member_ordinal": ordinal}}
                    for ordinal, value in enumerate(prepared[offset : offset + length], offset)
                ]
            part["batch_receipt"] = {
                **receipt,
                "member_ordinals": list(range(offset, offset + length)),
            }
            replies.append(
                ProviderReply(
                    handle.request.correlation, reply.startup_content, ordered_native_bytes(part)
                )
            )
            offset += length
        return scattered(replies)

    def _try_lazy(self, factory, lane_key):
        from corpus_structure.semantic.cpu_execution import CapacityExceeded

        if lane_key not in {"hanlp", "maverick", "dipo", "d1", "gliner", "spacy"}:
            raise ValueError("unsupported native provider lane")
        with self._lock:
            if self._stop.is_set():
                raise CancelledError("native invocation is closed")
            lane = (
                self._lanes.setdefault(lane_key, _Lane(self, lane_key))
                if lane_key not in self._lanes
                else self._lanes[lane_key]
            )
            if not lane.slots.acquire(blocking=False):
                return None
            reservation = self.policy.max_native_request_bytes + self.policy.max_native_reply_bytes
            try:
                self.budget.reserve(reservation)
            except CapacityExceeded:
                lane.slots.release()
                return None
            try:
                # Serialized bodies do not exist while admission is waiting. The
                # factory reads its already-owned immutable semantic/source values.
                request = factory()
                actual_lane = (
                    request.selection.provider if isinstance(request, PM2Work) else "gliner"
                )
                if actual_lane != lane_key:
                    raise ValueError("native request changed its admitted lane")
                size = self._request_size(request)
                unused = self.policy.max_native_request_bytes - size
                self.budget.release(unused)
                reservation -= unused
                handle = ProviderHandle(self, lane, request, reservation)
                self._handles.add(handle)
                lane.enqueue(handle)
                return handle
            except BaseException:
                self.budget.release(reservation)
                lane.slots.release()
                raise

    def lazy_work(self, factory, *, lane_key):
        """Wait for lane and byte capacity before materializing a native envelope."""
        pending: list[Callable[[], PM2Work | GLiNERWork] | None] = [factory]

        def submit():
            create = pending[0]
            if create is None:
                raise ValueError("native work intent was abandoned or submitted")
            handle = self._try_lazy(create, lane_key)
            if handle is not None:
                pending[0] = None
            return handle

        def abandon():
            pending[0] = None

        return PreparedWork(submit, abandon=abandon)

    def work(self, request):
        size = self._request_size(request)
        with self._lock:
            if self._stop.is_set():
                raise CancelledError("native invocation is closed")
            self.budget.reserve(size)
            intent = _PendingIntent(self, request, size)
            self._intents.add(intent)
        return PreparedWork(lambda: self.try_submit(request, intent), abandon=intent.abandon)

    def close(self):
        with self._lock:
            self._stop.set()
            intents = tuple(self._intents)
            handles = tuple(self._handles)
            lanes = tuple(self._lanes.values())
        for intent in intents:
            intent.abandon()
        for handle in handles:
            handle.cancel()
        errors = []
        for lane in lanes:
            try:
                lane.close()
            except BaseException as error:
                errors.append(error)
        for handle in tuple(self._handles):
            handle.retire()
        try:
            self.native_group.close()
        except BaseException as error:
            errors.append(error)
        if errors:
            failure = RuntimeError("native invocation teardown failed")
            for error in errors:
                failure.add_note(str(error))
            raise failure


class PM2Client:
    """Parent-only intent builder; lanes admit work and the shared host owns residents."""

    def __init__(self, execution, selection_factory, check_active, correlation, lane_key):
        self.execution, self.selection_factory = execution, selection_factory
        self.lane_key = lane_key
        self.check_active, self.correlation = check_active, correlation
        self.startup = {}
        self.serial = 0

    def request(self, payload):
        self.serial += 1
        correlation = self.correlation + ":" + str(self.serial)
        return self.execution.lazy_work(
            lambda: PM2Work(
                self.selection_factory(),
                None if payload is None else ordered_native_bytes(payload),
                correlation,
                (self.check_active,),
            ),
            lane_key=self.lane_key,
        )

    def start(self):
        (reply,) = yield (self.request(None),)
        self.startup = reply.startup
        _ = reply.payload  # Raises a structured startup failure inside the parent plan.
        return self

    def infer(self, payload, *, check_active=None):
        (reply,) = yield (self.request(payload),)
        self.startup = reply.startup
        return reply.payload


def pm2_client(
    execution,
    ctx,
    *,
    provider,
    assets,
    runtime,
    artifacts,
    device: Literal["cpu", "cuda"] | None = None,
):
    device = "cuda" if device is None else device
    if provider == "d1" and device != "cuda":
        raise Pm2WorkerRefused("d1 execution requires CUDA; CPU execution is not selected")

    if device != "cuda":
        raise Pm2WorkerRefused("learned PM2 execution requires explicit CUDA selection")

    def selection_factory():
        return pm2_selection(
            provider,
            assets,
            runtime,
            artifacts,
            threads=execution.policy.provider_threads,
            interop_threads=execution.policy.provider_interop_threads,
        )

    # Declaration itself is side-effect-free; enclosing characterization declares
    # its complete population before any stage flushes these work intents.
    execution.declare_native((selection_factory(),), ctx.settings.nemotron_endpoint)

    claims = tuple(getattr(ctx.check_active, "active", ()))
    correlation = sha256(
        canonical_bytes(dict(provider=provider, claims=claims, client=id(selection_factory)))
    ).hexdigest()
    return PM2Client(
        execution,
        selection_factory,
        ctx.check_active,
        correlation,
        provider,
    )


def fork_builder(builder):
    """Own mutable reduction collections while retaining read-only source/contracts."""
    from copy import copy

    fork = copy(builder)
    baseline: dict[str, Any] = {}
    for name, value in vars(builder).items():
        if isinstance(value, list):
            baseline[name] = len(value)
            setattr(fork, name, list(value))
        elif isinstance(value, dict):
            if name == "covered":
                baseline[name] = {key: len(rows) for key, rows in value.items()}
                setattr(fork, name, {key: list(rows) for key, rows in value.items()})
            else:
                baseline[name] = dict(value)
                setattr(fork, name, dict(value))
    return fork, baseline


def merge_builder(builder, branch):
    fork, baseline = branch
    for name, prior in baseline.items():
        value, target = getattr(fork, name), getattr(builder, name)
        if isinstance(prior, int):
            target.extend(value[prior:])
        elif name == "covered":
            for family, rows in value.items():
                target[family].extend(rows[prior[family] :])
        else:
            for key, item in value.items():
                if key not in prior:
                    if key in target and target[key] != item:
                        raise ValueError("independent native branches disagree on shared identity")
                    target[key] = item


@contextmanager
def provider_scope(units, *, policy: CharacterizationExecutionPolicy | None = None):
    """Direct method callers own the same runtime used by enclosing source execution."""
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope

    if not units:
        yield None, None
        return
    reader = units[0].run.reader
    with ExitStack() as stack:
        cpu = getattr(reader, "cpu_execution", None)
        if cpu is None:
            cpu = CPUExecutionScope(reader.prepared, policy)
            stack.callback(cpu.close)
        providers = getattr(reader, "provider_execution", None)
        if providers is None:
            providers = ProviderExecution(cpu.budget, cpu.policy)
            stack.callback(providers.close)
        yield cpu, providers


def gliner_extract(
    providers,
    profile,
    pack,
    inputs,
    *,
    threshold,
    overlap_policy="flat",
    check_active,
    evaluation=False,
    independent=False,
):
    from .gliner_worker import GlinerWorkerError

    correlation = sha256(
        canonical_bytes(
            dict(
                pack=pack.fingerprint,
                contexts=[(item.context_id, item.context_digest) for item in inputs],
                threshold=threshold,
                overlap=overlap_policy,
            )
        )
    ).hexdigest()
    work = providers.lazy_work(
        lambda: GLiNERWork(
            profile,
            pack,
            inputs,
            threshold,
            overlap_policy,
            correlation,
            (check_active,),
            evaluation,
            (1,) * len(inputs) if independent else (),
        ),
        lane_key="gliner",
    )
    (reply,) = yield (work,)
    if reply.error_type is not None:
        if reply.error_type == "CapacityExceeded":
            from corpus_structure.semantic.cpu_execution import CapacityExceeded

            raise CapacityExceeded(reply.error_message)
        raise GlinerWorkerError(reply.error_message)
    if independent:
        if len(reply.admissions) != len(inputs):
            raise GlinerWorkerError("native admission changed local scope population")
        reports = iter(reply.reports)
        outcomes = tuple(
            next(reports) if member.admitted else GlinerWorkerError(member.reason)
            for member in reply.admissions
        )
        if next(reports, None) is not None:
            raise GlinerWorkerError("native inference added an unadmitted local scope")
        return outcomes
    return reply.reports


def gliner_extract_members(
    providers, profile, pack, inputs, *, threshold, overlap_policy="flat", check_active
):
    """Pack known local scopes, preserving an independent outcome for each input."""
    from corpus_structure.semantic.cpu_execution import CapacityExceeded

    from .gliner_worker import GlinerWorkerError

    validate_gliner_policy(profile, providers.policy)

    def admit(items):
        return providers._request_size(
            GLiNERWork(
                profile,
                pack,
                items,
                threshold,
                overlap_policy,
                "",
                (check_active,),
                logical_sizes=(1,) * len(items),
            )
        )

    def extract(items):
        try:
            return (
                yield from gliner_extract(
                    providers,
                    profile,
                    pack,
                    items,
                    threshold=threshold,
                    overlap_policy=overlap_policy,
                    check_active=check_active,
                    independent=True,
                )
            )
        except (GlinerWorkerError, OSError, ValueError) as error:
            check_active()
            return (error,) * len(items)

    outcomes, cohort = [], ()
    for item in inputs:
        check_active()
        try:
            admit((item,))
        except GlinerRefused as error:
            if cohort:
                outcomes.extend((yield from extract(cohort)))
                cohort = ()
            outcomes.append(error)
            continue
        try:
            admit((*cohort, item))
        except GlinerRefused, CapacityExceeded:
            outcomes.extend((yield from extract(cohort)))
            cohort = ()
        cohort = (*cohort, item)
    if cohort:
        outcomes.extend((yield from extract(cohort)))
    return tuple(outcomes)


def selections_for_characterization(options, settings):
    """The complete selected resident population; no GPU custody or model loading."""
    from pydantic import TypeAdapter

    from corpus_structure.ingest.sentences import SentenceConfig

    from .native_profiles import gliner_selection

    policy = settings.execution_policy
    selected = []
    native = options.get("text.native_evidence")
    if native is not None:
        config = SentenceConfig.model_validate(native.get("sentences", {}))
        if native.get("characterization_profile") == "boundary_only":
            config = config.model_copy(
                update={"exclude": ("ner", "tagger", "attribute_ruler", "lemmatizer")}
            )
        frozen = native.get("spacy_native_profile")
        if frozen is not None:
            import spacy

            from .native_profiles import NativeProfile

            selected.append(
                NativeSelection(NativeProfile(**frozen), spacy.util.get_package_path(config.model))
            )
        if (
            native.get("characterization_profile", "full_native") == "full_native"
            and native.get("hanlp_runtime") is not None
        ):
            selected.append(
                pm2_selection(
                    "hanlp",
                    settings.model_cache / "pm2",
                    native["hanlp_runtime"],
                    native["hanlp_artifacts"],
                    threads=policy.provider_threads,
                    interop_threads=policy.provider_interop_threads,
                )
            )
    contextual = options.get("text.contextual_characterization")
    if contextual is not None and contextual.get("native_mode", "infer") == "infer":
        for provider in ("maverick", "dipo"):
            if provider in contextual.get("native_runtime", {}):
                selected.append(
                    pm2_selection(
                        provider,
                        settings.model_cache / "pm2",
                        contextual["native_runtime"][provider],
                        contextual["native_artifacts"][provider],
                        threads=policy.provider_threads,
                        interop_threads=policy.provider_interop_threads,
                    )
                )
    model = options.get("text.model_characterization")
    if model is not None:
        if model.get("d1_runtime") is not None:
            selected.append(
                pm2_selection(
                    "d1",
                    settings.model_cache / "pm2",
                    model["d1_runtime"],
                    model["d1_artifacts"],
                    threads=policy.provider_threads,
                    interop_threads=policy.provider_interop_threads,
                )
            )
        if model.get("gliner_profile") is not None:
            profile = TypeAdapter(GlinerProfile).validate_python(model["gliner_profile"]["profile"])
            runtime = model.get("gliner_runtime")
            if runtime is not None:
                selected.append(gliner_selection(profile, runtime))
    return tuple({value.identity: value for value in selected}.values())


def freeze_characterization_profiles(
    name, parameters, settings, *, cache: dict[tuple[Any, ...], Any] | None = None
):
    """Freeze runtime/device meaning into task configuration before reuse checks."""
    from corpus_structure.ingest.sentences import SentenceConfig

    from .native_profiles import preflight_native_runtime, spacy_selection

    cache = {} if cache is None else cache
    if name == "text.native_evidence" and parameters.get("spacy_native_profile") is None:
        config = SentenceConfig.model_validate(parameters.get("sentences", {}))
        if parameters.get("characterization_profile") == "boundary_only":
            config = config.model_copy(
                update={"exclude": ("ner", "tagger", "attribute_ruler", "lemmatizer")}
            )
        key = (
            "spacy-selection",
            config.model_dump_json(),
            settings.execution_policy.provider_threads,
            settings.execution_policy.provider_interop_threads,
        )
        if key not in cache:
            cache[key] = spacy_selection(
                config,
                threads=settings.execution_policy.provider_threads,
                interop_threads=settings.execution_policy.provider_interop_threads,
            )
        parameters["spacy_native_profile"] = cache[key].native.wire
    if (
        name == "text.model_characterization"
        and parameters.get("gliner_profile") is not None
        and parameters.get("gliner_runtime") is None
    ):
        from pydantic import TypeAdapter

        profile = TypeAdapter(GlinerProfile).validate_python(
            parameters["gliner_profile"]["profile"]
        )
        if profile.device != "cuda":
            raise GlinerRefused(
                "current model characterization requires an explicit CUDA GLiNER profile"
            )
        key = ("gliner-runtime", str(profile.snapshot.absolute()))
        if key not in cache:
            cache[key] = preflight_native_runtime("gliner", profile.snapshot)["runtime_identity"]
        parameters["gliner_runtime"] = cache[key]


def freeze_analytical_profile(
    name, parameters, settings, *, cache: dict[tuple[Any, ...], Any] | None = None
):
    """Freeze a selected domain encoder before its configuration/task is recorded."""
    from .native_profiles import NativeProfile, gliner_selection, preflight_native_runtime

    cache = {} if cache is None else cache
    if name == "extract.m1_candidates":
        from .m1_source import M1Config

        config = M1Config.model_validate(parameters)
        profile = config.profile()
    elif name == "structure.definition_components":
        from .definition_applicability import DefinitionComponentsConfig

        config = DefinitionComponentsConfig.model_validate(parameters)
        if not config.use_model or config.profile is None:
            return None
        profile = config.profile
    else:
        return None
    frozen = parameters.get("native_execution_profile")
    if frozen is not None:
        selection = NativeSelection(NativeProfile(**frozen), profile.snapshot)
        expected = gliner_selection(profile, selection.native.runtime_identity)
        if expected.native != selection.native:
            raise GlinerRefused("analytical GLiNER frozen profile differs from configuration")
        return selection
    if profile.device != "cuda":
        raise GlinerRefused("current analytical GLiNER execution requires an explicit CUDA profile")
    key = ("gliner-runtime", str(profile.snapshot.absolute()))
    if key not in cache:
        cache[key] = preflight_native_runtime("gliner", profile.snapshot)["runtime_identity"]
    selection = gliner_selection(profile, cache[key])
    parameters["native_execution_profile"] = selection.native.wire
    return selection
