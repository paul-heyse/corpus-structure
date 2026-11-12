"""Unselected shared-host checkpoint (CPython 3.14, primary/isolated environments, no database imports).

The protocol/lifecycle implementation accepts an injected adapter for controlled
checks. Real provider adapters are deliberately refused until their shared-host
profile/loading cutover is complete. No production execution selects this module.
"""

from __future__ import annotations

import json
import math
import os
import runpy
import sys
from concurrent.futures import CancelledError, ThreadPoolExecutor
from contextlib import nullcontext
from hashlib import sha256
from pathlib import Path
from threading import BoundedSemaphore, Event, Lock

_DIPO_GATE = Lock()


def _canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate native host field")
        value[key] = item
    return value


def _float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("nonfinite native host number")
    return value


def _read(stream, limit):
    line = stream.readline(limit + 1)
    if not line:
        return None
    if len(line) > limit or not line.endswith(b"\n"):
        raise ValueError("native host request exceeds frame byte bound")
    return json.loads(line, object_pairs_hook=_object, parse_float=_float)


def _configure(profiles):
    import torch

    first = profiles[0]
    globals_ = (
        first["threads"],
        first["interop_threads"],
        first["matmul_precision"],
        first["cudnn_allow_tf32"],
    )
    for profile in profiles:
        if profile.get("version") != "nlp-gpu-profile-1" or profile.get("device") != "cuda":
            raise ValueError("host accepts explicit frozen CUDA profiles only")
        if (
            profile["threads"],
            profile["interop_threads"],
            profile["matmul_precision"],
            profile["cudnn_allow_tf32"],
        ) != globals_:
            raise ValueError("declared residents disagree on process-global execution settings")
    if globals_[2:] != ("highest", False):
        raise ValueError("unsupported FP32 numerical host policy")
    torch.set_num_threads(first["threads"])
    torch.set_num_interop_threads(first["interop_threads"])
    torch.set_float32_matmul_precision(first["matmul_precision"])
    torch.backends.cudnn.allow_tf32 = first["cudnn_allow_tf32"]
    if not torch.cuda.is_available():
        raise RuntimeError("selected CUDA host has no GPU; CPU fallback is not permitted")
    return torch


def _load(declaration, torch):
    adapter = runpy.run_path(str(Path(__file__).with_name("native_host_adapters.py")))
    return adapter["load"](declaration, torch)


class _Resident:
    def __init__(self, declaration, torch, loader):
        self.declaration, self.torch = declaration, torch
        self.profile = declaration["profile"]
        self.provider = self.profile["provider"]
        self.identity = declaration["fingerprint"]
        if self.identity != sha256(_canonical(self.profile)).hexdigest():
            raise ValueError("declared profile fingerprint differs from frozen content")
        self.stream = torch.cuda.Stream(device=0)
        self.cupy = None
        self.cupy_stream = None
        if self.provider == "spacy":
            import cupy

            self.cupy = cupy
            self.cupy_stream = cupy.cuda.Stream(non_blocking=True)
        with self._context():
            self.metadata, self.infer = loader(declaration, torch)
        self.stream.synchronize()
        if self.cupy_stream is not None:
            self.cupy_stream.synchronize()
        self.metadata.update(
            provider=self.provider,
            profile=self.identity,
            matmul_precision=torch.get_float32_matmul_precision(),
            cudnn_allow_tf32=torch.backends.cudnn.allow_tf32,
            native_threads=dict(
                intra_op=torch.get_num_threads(), inter_op=torch.get_num_interop_threads()
            ),
            host_stream=int(self.stream.cuda_stream),
        )
        self.executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="native-" + self.provider,
            initializer=torch.init_num_threads,
        )

    def _context(self):
        from contextlib import ExitStack

        stack = ExitStack()
        stack.enter_context(self.torch.cuda.device(0))
        stack.enter_context(self.torch.cuda.stream(self.stream))
        if self.cupy is not None:
            from thinc.api import use_ops

            assert self.cupy_stream is not None
            stack.enter_context(self.cupy.cuda.Device(0))
            stack.enter_context(self.cupy_stream)
            stack.enter_context(use_ops("cupy"))
        return stack

    def execute(self, payload, cancelled):
        if cancelled.is_set():
            raise CancelledError("native member cancelled before inference")
        gate = _DIPO_GATE if self.provider == "dipo" else nullcontext()
        with gate, self._context():
            if (
                self.torch.get_num_threads() != self.profile["threads"]
                or self.torch.get_num_interop_threads() != self.profile["interop_threads"]
            ):
                raise RuntimeError("native worker thread differs from frozen host policy")
            # Native adapters retain their own gradient contexts. In particular,
            # HanLP enables gradients for constituency CRF marginal decoding.
            result = self.infer(payload)
            self.stream.synchronize()
            if self.cupy_stream is not None:
                self.cupy_stream.synchronize()
        if cancelled.is_set():
            raise CancelledError("native member cancelled after inference")
        if not isinstance(result, dict):
            raise RuntimeError("native adapter did not return detached object values")
        return result


def serve(input_stream, output_stream, *, configure=_configure, loader=_load):
    write_lock, state_lock = Lock(), Lock()
    requests, residents, permits = {}, {}, {}
    failed = Event()
    generation = None
    reply_limit = 8 * 1024**2

    def send(message, *, limit=None):
        content = (
            json.dumps(message, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
            + b"\n"
        )
        if len(content) > (reply_limit if limit is None else min(reply_limit, limit)):
            raise RuntimeError("native host reply exceeds frame byte bound")
        with write_lock:
            output_stream.write(content)
            output_stream.flush()

    def fatal(error):
        with state_lock:
            if failed.is_set():
                return
            failed.set()
        send(
            dict(
                kind="fatal",
                generation=generation,
                message=f"{type(error).__name__}: {error}"[:1800],
            )
        )

    def done(request, resident, cancelled, future):
        try:
            try:
                result = future.result()
            except CancelledError as error:
                message = dict(kind="cancelled", message=str(error))
            except ValueError as error:
                message = dict(kind="refused", message=str(error)[:1800])
            else:
                message = dict(kind="result", payload=result)
            if not failed.is_set():
                send(
                    dict(
                        generation=generation,
                        request_id=request["request_id"],
                        provider=resident.provider,
                        profile=resident.identity,
                        **message,
                    ),
                    limit=resident.profile.get("parameters", {}).get("gliner_profile", {}).get("max_reply_frame_bytes"),
                )
        except BaseException as error:
            fatal(error)
        finally:
            with state_lock:
                requests.pop(request["request_id"], None)
            permits[resident.provider].release()

    try:
        initialize = _read(input_stream, 1024 * 1024)
        if not isinstance(initialize, dict) or initialize.get("kind") != "initialize":
            raise ValueError("native host requires one initialization envelope")
        generation = initialize["generation"]
        declarations = initialize["residents"]
        request_limit, reply_limit, jobs = (
            initialize[key] for key in ("max_request_bytes", "max_reply_bytes", "max_jobs")
        )
        if not isinstance(generation, str) or len(generation) != 32 or not declarations:
            raise ValueError("native host requires a generation and declared residents")
        if any(type(value) is not int or value < 1 for value in (request_limit, reply_limit, jobs)):
            raise ValueError("native host requires bounded positive frame/job limits")
        torch = configure([entry["profile"] for entry in declarations])
        # This entire loading/import/patch phase is serial, before any inference.
        for declaration in declarations:
            resident = _Resident(declaration, torch, loader)
            if resident.identity in residents:
                raise ValueError("native host declaration repeats one resident")
            residents[resident.identity] = resident
            permits.setdefault(resident.provider, BoundedSemaphore(jobs))
        from threadpoolctl import threadpool_info, threadpool_limits

        limiter = threadpool_limits(limits=declarations[0]["profile"]["threads"])
        try:
            for resident in residents.values():
                resident.metadata["native_threads"]["supported_pools"] = threadpool_info()
            send(
                dict(
                    kind="ready",
                    generation=generation,
                    residents={
                        identity: resident.metadata for identity, resident in residents.items()
                    },
                )
            )
            while not failed.is_set():
                request = _read(input_stream, request_limit)
                if request is None:
                    break
                if not isinstance(request, dict) or request.get("generation") != generation:
                    raise ValueError("native request belongs to another host generation")
                kind = request.get("kind")
                if kind == "shutdown":
                    break
                if kind == "cancel":
                    with state_lock:
                        pending = requests.get(request.get("request_id"))
                    if pending is not None:
                        pending[0].set()
                        pending[1].cancel()
                    continue
                identity, request_id = request.get("profile"), request.get("request_id")
                resident = residents.get(identity)
                if (
                    kind != "infer"
                    or resident is None
                    or request.get("provider") != resident.provider
                    or not isinstance(request.get("payload"), dict)
                ):
                    raise ValueError("native request differs from its declared resident/payload")
                if not isinstance(request_id, str) or len(request_id) != 32:
                    raise ValueError(
                        "native request requires a fixed-width physical request identity"
                    )
                with state_lock:
                    if request_id in requests:
                        raise ValueError("native host received a duplicate request identity")
                permit = permits[resident.provider]
                if not permit.acquire(blocking=False):
                    raise ValueError("native host provider queue exceeds pre-submission admission")
                cancelled = Event()
                try:
                    future = resident.executor.submit(
                        resident.execute, request["payload"], cancelled
                    )
                except BaseException:
                    permit.release()
                    raise
                with state_lock:
                    requests[request_id] = (cancelled, future)
                future.add_done_callback(
                    lambda future, request=request, resident=resident, cancelled=cancelled: done(
                        request, resident, cancelled, future
                    )
                )
        finally:
            for resident in residents.values():
                resident.executor.shutdown(wait=True, cancel_futures=True)
            limiter.restore_original_limits()
    except BaseException as error:
        fatal(error)


if __name__ == "__main__":
    with os.fdopen(os.dup(sys.stdout.fileno()), "wb") as protocol:
        os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
        if len(sys.argv) > 1 and sys.argv[1] == "--preflight":
            adapter = runpy.run_path(str(Path(__file__).with_name("pm2_native.py")))
            try:
                provider, assets = sys.argv[2], Path(sys.argv[3])
                root = Path(__file__).resolve().parents[5]
                project = root if provider in {"d1", "hanlp", "gliner", "spacy"} else root / "services/nlp-host-isolated"
                result = dict(runtime_identity=adapter["_runtime_identity"](provider, project=project), assets=adapter["_verify_assets"](assets.resolve(strict=True), provider) if provider in {"d1", "hanlp", "maverick", "dipo"} else {})
                message = dict(kind="ready", payload=result)
            except Exception as error:
                message = dict(kind="error", message=f"{type(error).__name__}: {error}"[:1800])
            protocol.write(
                json.dumps(message, ensure_ascii=False, allow_nan=False).encode() + b"\n"
            )
            protocol.flush()
        else:
            serve(sys.stdin.buffer, protocol)
