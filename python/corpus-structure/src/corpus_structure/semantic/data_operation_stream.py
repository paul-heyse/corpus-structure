"""Owned pull transport for one iterator in the existing CPU process pool."""

from concurrent.futures import Future
from contextlib import suppress
from hashlib import sha256
from threading import Thread

from corpus_structure.core.work import PreparedWork

from .identity import canonical_bytes


class _Pull:
    def __init__(self, stream):
        self.stream = stream
        self.future = Future()
        self.thread = Thread(target=self._read, name='data-stream-pull', daemon=True)
        self.stream.pulls.append(self)
        self.thread.start()

    def _read(self):
        try:
            stream = self.stream
            stream.check_active()
            stream.parent.send_bytes(stream.credit())
            while not stream.parent.poll(0.1):
                stream.check_active()
                if stream.handle.future.done():
                    stream.handle.collect()  # exposes a failed native job, never invents terminal
                    raise RuntimeError('CPU stream ended without its terminal frame')
            import json
            try:
                content = stream.parent.recv_bytes(stream.max_bytes)
            except EOFError:
                from concurrent.futures import TimeoutError
                while not stream.handle.future.done():
                    stream.check_active()
                    with suppress(TimeoutError):
                        stream.handle.future.result(timeout=.1)
                stream.handle.collect()
                raise RuntimeError('CPU stream closed without terminal evidence') from None
            frame = json.loads(content)
            stream.validate_frame(frame)
            stream.child.close()  # child received its duplicate before its first response
            self.future.set_result(frame)
        except BaseException as error:
            self.future.set_exception(error)

    def collect(self):
        try:
            return self.future.result()
        finally:
            self.thread.join()
            if self in self.stream.pulls:
                self.stream.pulls.remove(self)

    def cancel(self):
        self.stream.handle.cancel()

    def retire(self):
        return self.future.done() and not self.thread.is_alive()


class OwnedCPUStream:
    def __init__(self, cpu, admission, packet, check_active):
        self.cpu = cpu
        self.pulls = []
        self.handle = None
        self.closed = False
        self.parent, self.child = cpu._context.Pipe(duplex=True)
        cpu._stream_transports.add(self)
        self.check_active = check_active
        self.digest, self.ordinal = sha256(packet).hexdigest(), 0
        self.max_bytes = cpu.policy.max_reply_bytes
        self.fence = {"slot": admission.slot, "generation": admission.generation}
        try:
            self.handle = cpu.submit_closed_python_stream(admission, packet, self.child, check_active)
        except BaseException:
            self.parent.close()
            self.child.close()
            cpu._stream_transports.discard(self)
            raise

    def credit(self):
        return canonical_bytes({"pull": self.ordinal})

    def validate_frame(self, frame):
        if (set(frame) != {"request", "fence", "ordinal", "state", *(["value"] if frame.get("state") == "item" else [])}
            or frame["request"] != self.digest or frame["fence"] != self.fence
            or type(frame["ordinal"]) is not int or frame["ordinal"] != self.ordinal
            or frame["state"] not in {"item", "complete"}):
            raise ValueError("stream frame differs from admitted request or ordinal")

    def pull(self):
        return _Pull(self)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.handle.cancel()
        with suppress(OSError):
            self.parent.close()
        with suppress(OSError):
            self.child.close()
        self.handle.retire()
        if all(not pull.thread.is_alive() for pull in self.pulls):
            self.cpu._stream_transports.discard(self)

    def drain_transport(self, deadline):
        from time import monotonic
        self.parent.close()
        self.child.close()
        for pull in tuple(self.pulls):
            pull.thread.join(max(0, deadline - monotonic()))
        return all(not pull.thread.is_alive() for pull in self.pulls)


def plan_cpu_stream(descriptor, bound, signature, *, verify, execution_owner, check_active):
    """Bounded private staging; only terminal+CPU receipt can return a logical result."""
    from .data_operation_cpu import PythonCPUDescriptor

    if not isinstance(descriptor, PythonCPUDescriptor):
        raise ValueError('CPU stream requires its acquired source descriptor')
    packet = descriptor.packet(bound.arguments, signature)
    cpu = execution_owner.cpu
    stream = None

    def start():
        nonlocal stream
        verify()
        check_active()
        admission = cpu.try_admit(check_active, reservation=execution_owner.reservation)
        if admission is None:
            return None
        try:
            stream = OwnedCPUStream(cpu, admission, packet, check_active)
            return stream.pull()
        except BaseException:
            if not admission.submitted:
                cpu.release_admission(admission)
            raise

    staged = bytearray(b'[')
    try:
        (frame,) = yield (PreparedWork(start),)
        while frame['state'] == 'item':
            item = frame['value'].encode('utf-8')
            if len(staged) + len(item) + 2 > cpu.policy.max_reply_bytes:
                raise ValueError('complete stream output exceeds admitted reply capacity')
            if stream.ordinal:
                staged.extend(b',')
            staged.extend(item)
            stream.ordinal += 1
            verify()
            check_active()
            (frame,) = yield (PreparedWork(stream.pull),)
        if frame != {'request': stream.digest, 'fence': stream.fence, 'ordinal': stream.ordinal, 'state': 'complete'}:
            raise ValueError('stream has no valid complete terminal')
        staged.extend(b']')
        # The normal CPU receipt retains admission and verifies native process identity.
        (reply,) = yield (PreparedWork(lambda: stream.handle),)
        import json
        if json.loads(reply.content) != {'items': stream.ordinal, 'state': 'complete'}:
            raise ValueError('CPU stream receipt differs from observed terminal')
        verify()
        check_active()
        return bytes(staged), reply
    finally:
        if stream is not None:
            stream.close()


class OwnedCPUCoroutine(OwnedCPUStream):
    """Typed duplex continuation on the same owned iterator process and pipe."""

    reply_content = None

    def credit(self):
        credit = {"pull": self.ordinal}
        if self.ordinal:
            if self.reply_content is None:
                raise ValueError("CPU coroutine lacks its typed pending reply")
            credit["reply"] = self.reply_content.decode()
        content = canonical_bytes(credit)
        if len(content) > self.max_bytes:
            raise ValueError("CPU coroutine reply exceeds owned transport capacity")
        return content

    def validate_frame(self, frame):
        if (set(frame) != {"request", "fence", "ordinal", "state", "value"}
            or frame["request"] != self.digest or frame["fence"] != self.fence
            or type(frame["ordinal"]) is not int or frame["ordinal"] != self.ordinal
            or frame["state"] not in {"question", "complete"} or not isinstance(frame["value"], str)):
            raise ValueError("CPU coroutine frame differs from pending question/fence")


def plan_cpu_coroutine(descriptor, bound, signature, *, verify, execution_owner, check_active, answer_plan):
    """Keep one original CPU generator alive across typed provider exchanges.

    A waiting provider retains that process/state and admission. Its native host
    plan releases its own GPU claim after each reply; no CPU replay or private pool
    substitutes for the original continuation.
    """
    import json

    from .data_operation_cpu import PythonCPUDescriptor, coroutine_adapters

    if not isinstance(descriptor, PythonCPUDescriptor) or descriptor.invocation_form != "coroutine":
        raise ValueError("CPU coroutine requires its acquired coroutine descriptor")
    question_adapter, reply_adapter, result_adapter = coroutine_adapters(signature)
    packet = descriptor.packet(bound.arguments, signature)
    cpu, stream = execution_owner.cpu, None

    def start():
        nonlocal stream
        verify()
        check_active()
        admission = cpu.try_admit(check_active, reservation=execution_owner.reservation)
        if admission is None:
            return None
        try:
            stream = OwnedCPUCoroutine(cpu, admission, packet, check_active)
            return stream.pull()
        except BaseException:
            if not admission.submitted:
                cpu.release_admission(admission)
            raise

    try:
        (frame,) = yield (PreparedWork(start),)
        while frame["state"] == "question":
            verify()
            check_active()
            question = question_adapter.validate_json(frame["value"], strict=True)
            answer = yield from answer_plan(question)
            verify()
            check_active()
            stream.reply_content = reply_adapter.dump_json(reply_adapter.validate_python(answer, strict=True))
            stream.ordinal += 1
            (frame,) = yield (PreparedWork(stream.pull),)
        encoded = frame["value"].encode()
        result = result_adapter.validate_json(encoded, strict=True)
        (reply,) = yield (PreparedWork(lambda: stream.handle),)
        if json.loads(reply.content) != dict(turns=stream.ordinal, state="complete", result_digest=sha256(encoded).hexdigest()):
            raise ValueError("CPU coroutine terminal differs from native process receipt")
        verify()
        check_active()
        return result, reply
    finally:
        if stream is not None:
            stream.close()
