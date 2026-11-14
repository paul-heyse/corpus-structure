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
        self.thread.start()

    def _read(self):
        try:
            stream = self.stream
            stream.check_active()
            stream.parent.send_bytes(canonical_bytes({'pull': stream.ordinal}))
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
            if (set(frame) != {'request', 'fence', 'ordinal', 'state', *(['value'] if frame.get('state') == 'item' else [])} or frame['request'] != stream.digest or frame['fence'] != stream.fence or type(frame['ordinal']) is not int or frame['ordinal'] != stream.ordinal):
                raise ValueError('stream frame differs from admitted request or ordinal')
            stream.child.close()  # child received its duplicate before its first response
            self.future.set_result(frame)
        except BaseException as error:
            self.future.set_exception(error)

    def collect(self):
        return self.future.result()

    def cancel(self):
        self.stream.handle.cancel()

    def retire(self):
        return self.future.done() and not self.thread.is_alive()


class OwnedCPUStream:
    def __init__(self, cpu, admission, packet, check_active):
        self.parent, self.child = cpu._context.Pipe(duplex=True)
        self.check_active = check_active
        self.digest, self.ordinal = sha256(packet).hexdigest(), 0
        self.max_bytes = cpu.policy.max_reply_bytes
        self.fence = {"slot": admission.slot, "generation": admission.generation}
        self.handle = cpu.submit_closed_python_stream(admission, packet, self.child, check_active)
        self.closed = False

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
