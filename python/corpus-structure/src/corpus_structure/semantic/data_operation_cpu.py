"""Compact acquired Python calls in the invocation's existing CPU process owner.

This is physical custody, not a second semantic operation registry. Only resolved
ports or prepared kernel adapters create descriptors after their own admission.
"""

from __future__ import annotations

import importlib
import inspect
import sys
from dataclasses import dataclass
from functools import cached_property, lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict

from .identity import canonical_bytes


class _Source(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    module: str
    path: str
    digest: str


class _AssetCustody(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    digest: str
    identity: tuple[int, int, int, int, int]
    racily_clean: bool


class _Call(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sources: tuple[_Source, ...]
    asset_custody: tuple[_AssetCustody, ...] = ()
    entrypoint: str
    expected_nodes: tuple[str, ...]
    receiver: bool
    verification: Literal["closed-slice", "prepared-kernel"]
    arguments: dict[str, str]
    control_parameter: str | None
    prepared_parameter: str | None = None
    prepared_release_id: str | None = None
    invocation_form: Literal["scalar", "batch", "stream", "coroutine"] = "scalar"


@dataclass(frozen=True)
class PythonCPUDescriptor:
    """Owned source custody and entrypoint; no model/schema or execution authority."""

    sources: tuple[tuple[str, str, bytes], ...]
    entrypoint: str
    expected_nodes: tuple[str, ...]
    receiver: bool = False
    verification: Literal["closed-slice", "prepared-kernel"] = "closed-slice"
    control_parameter: str | None = None
    prepared_parameter: str | None = None
    prepared_release_id: str | None = None
    invocation_form: Literal["scalar", "batch", "stream", "coroutine"] = "scalar"
    asset_custody: tuple = ()

    def __post_init__(self) -> None:
        if self.control_parameter is not None and (
            self.verification != "prepared-kernel" or not self.control_parameter
        ):
            raise ValueError("only prepared kernels can bind an owned CPU control parameter")

        if (self.prepared_parameter is None) != (self.prepared_release_id is None) or (
            self.prepared_parameter is not None
            and (
                self.verification != "prepared-kernel"
                or not self.prepared_parameter
                or not self.prepared_release_id
                or self.prepared_parameter == self.control_parameter
            )
        ):
            raise ValueError("only prepared kernels can bind the exact admitted release capsule")

    @cached_property
    def source_records(self):
        return tuple(dict(module=module, path=path, digest=sha256(content).hexdigest()) for module, path, content in self.sources)

    @cached_property
    def adapter_sets(self):
        return {}

    def adapters(self, signature):
        from .data_operation_ports import PortAdapters

        key = tuple(id(parameter.annotation) for parameter in signature.parameters.values()) + (id(signature.return_annotation),)
        if key not in self.adapter_sets:
            selected = signature.replace(parameters=[parameter for name, parameter in signature.parameters.items() if name not in {self.control_parameter, self.prepared_parameter}])
            self.adapter_sets[key] = (signature, PortAdapters(selected))
        return self.adapter_sets[key][1]

    def packet(self, arguments, signature) -> bytes:
        adapters = self.adapters(signature)
        return canonical_bytes(
            {
                "sources": self.source_records,
                "asset_custody": [dict(zip(("path", "digest", "identity", "racily_clean"), receipt, strict=True)) for receipt in self.asset_custody],
                "entrypoint": self.entrypoint,
                "expected_nodes": self.expected_nodes,
                "receiver": self.receiver,
                "verification": self.verification,
                "control_parameter": self.control_parameter,
                "prepared_parameter": self.prepared_parameter,
                "prepared_release_id": self.prepared_release_id,
                "invocation_form": self.invocation_form,
                "arguments": {
                    name: adapters.get(signature.parameters[name].annotation).dump_json(value)
                    .decode()
                    for name, value in arguments.items()
                    if name not in {self.control_parameter, self.prepared_parameter}
                },
            }
        )


def plan_cpu_call(descriptor, bound, signature, *, verify, execution_owner, check_active):
    """One validated original call, one shared admission, one physically owned reply."""
    from corpus_structure.core.method import PreparedWork

    if not isinstance(descriptor, PythonCPUDescriptor):
        raise ValueError("CPU call requires its acquired source descriptor")
    check_active()
    verify()
    packet = descriptor.packet(bound.arguments, signature)
    cpu = execution_owner.cpu

    def submit():
        verify()
        check_active()
        admission = cpu.try_admit(check_active, reservation=execution_owner.reservation)
        if admission is None:
            return None
        try:
            return cpu.submit_closed_python(admission, packet, check_active)
        except BaseException:
            if not admission.submitted:
                cpu.release_admission(admission)
            raise

    (reply,) = yield (PreparedWork(submit),)
    check_active()
    verify()
    return reply


def _load(call):
    prepared = _load_descriptor(call.model_dump_json(exclude={"arguments"}))
    prepared.verify()
    return prepared.function, prepared.verify


@dataclass(frozen=True)
class _LoadedCall:
    function: Callable[..., Any]
    verify: Callable[[], None]
    signature: inspect.Signature
    adapters: Any


@lru_cache(maxsize=64)
def _load_descriptor(content):
    call = _Call.model_validate_json(content[:-1] + ',"arguments":{}}', strict=True)
    from .file_custody import accept_file_receipt
    assets = tuple(accept_file_receipt((receipt.path, receipt.digest, receipt.identity, receipt.racily_clean), path=Path(receipt.path), expected=receipt.digest) for receipt in call.asset_custody)
    function, verify, signature, adapters = _load_original(call)
    def check():
        verify()
        for asset in assets:
            asset.check()
    return _LoadedCall(function, check, signature, adapters)


def _prepared_call(call):
    return _load_descriptor(call.model_dump_json(exclude={"arguments"}))


def _load_original(call):
    import ast
    from .data_operation_ports import PortRefusal, _runtime_members
    from .python_operation_sources import PythonSource, PythonSourceCollection

    sources = PythonSourceCollection(
        tuple(
            PythonSource(source.module, Path(source.path).read_bytes(), source.path)
            for source in call.sources
        )
    )
    paths = {source.module: Path(source.filename) for source in sources.sources}
    if len(paths) != len(sources.sources) or not paths:
        raise PortRefusal("CPU source collection must have distinct actual modules")
    roots = set()
    digests = {source.module: source.digest for source in call.sources}
    for source in sources.sources:
        path = paths[source.module]
        if sha256(source.content).hexdigest() != digests[source.module]:
            raise PortRefusal("CPU runtime source digest differs from acquired parent")
        if not path.is_absolute() or path.resolve() != path or path.read_bytes() != source.content:
            raise PortRefusal("CPU runtime source differs from acquired bytes")
        parts = source.module.split(".")
        expected = (
            Path(*parts, "__init__.py")
            if path.name == "__init__.py"
            else Path(*parts).with_suffix(".py")
        )
        if tuple(path.parts[-len(expected.parts) :]) != expected.parts:
            raise PortRefusal("CPU module path differs from its captured import name")
        root = path
        for _ in expected.parts:
            root = root.parent
        roots.add(str(root))
    for root in sorted(roots, reverse=True):
        if root not in sys.path:
            sys.path.insert(0, root)
    importlib.invalidate_caches()
    modules = {source.module: importlib.import_module(source.module) for source in sources.sources}
    for name, module in modules.items():
        if Path(inspect.getfile(module)).resolve() != paths[name]:
            raise PortRefusal("CPU module resolved outside acquired source")
    names = [name for name in modules if call.entrypoint.startswith(name + ".")]
    if not names:
        raise PortRefusal("CPU entrypoint is outside acquired source")
    module_name = max(names, key=len)
    member = call.entrypoint.removeprefix(module_name + ".").split(".")
    owner = modules[module_name]
    for name in member[:-1]:
        owner = inspect.getattr_static(owner, name)
    if call.receiver:
        if not isinstance(owner, type) or type(owner) is not type:
            raise PortRefusal("CPU receiver lacks its admitted plain class")
        function = getattr(object.__new__(owner), member[-1])
    else:
        function = inspect.getattr_static(owner, member[-1])
    if call.receiver and not inspect.ismethod(function):
        raise PortRefusal("CPU receiver entrypoint is not its original bound method")
    if not (inspect.isfunction(function) or inspect.ismethod(function)):
        raise PortRefusal("CPU entrypoint is not its original Python function")
    if hasattr(function, "__signature__") or hasattr(function, "__wrapped__"):
        raise PortRefusal("CPU callable transformation is outside acquired profile")

    def verify():
        if call.verification == "closed-slice":
            from .data_operation_ports import _verify_closed_runtime_sources

            if not call.expected_nodes:
                raise PortRefusal("closed CPU call lacks its owning implementation slice")
            from .data_operation_ports import _stream_annotation_references

            _verify_closed_runtime_sources(
                sources,
                modules,
                paths,
                set(call.expected_nodes),
                standard_references=_stream_annotation_references()
                if call.invocation_form in {"stream", "coroutine"}
                else None,
            )
        else:
            # Prepared kernels admit their explicit library/asset boundary in the
            # parent. Here authenticate every physical source and loaded entrypoint.
            for source in sources.sources:
                if paths[source.module].read_bytes() != source.content:
                    raise PortRefusal("prepared CPU kernel source changed")
            source = next(source for source in sources.sources if source.module == module_name)
            code = compile(source.content, source.filename, "exec", dont_inherit=True)
            members = _runtime_members(
                ast.parse(source.content).body, modules[module_name], code, module_name
            )
            selected = next((entry for entry in members if entry[0] == call.entrypoint), None)
            actual = function.__func__ if inspect.ismethod(function) else function
            if (
                selected is None
                or actual is not selected[2]
                or actual.__code__ != selected[3]
                or actual.__globals__ is not modules[module_name].__dict__
            ):
                raise PortRefusal("prepared CPU kernel implementation differs")
        if call.receiver and inspect.ismethod(function) and vars(function.__self__):
            raise PortRefusal("CPU receiver acquired unbound mutable state")

    from .data_operation_ports import PortAdapters
    signature = inspect.signature(function, eval_str=True)
    controls = {call.control_parameter, call.prepared_parameter}
    adapters = PortAdapters(signature.replace(parameters=[p for p in signature.parameters.values() if p.name not in controls]))
    verify()
    from .file_custody import verified_file
    from .runtime_slice import AuthenticatedSlice
    from .data_operation_ports import _authenticated_closed_slice, _stream_annotation_references, _code_globals

    if call.verification == "closed-slice":
        runtime = _authenticated_closed_slice(
            sources, modules, paths, set(call.expected_nodes),
            standard_references=_stream_annotation_references() if call.invocation_form in {"stream", "coroutine"} else None,
        )
    else:
        files = tuple(verified_file(paths[source.module], digests[source.module]) for source in sources.sources)
        getters = []
        for source in sources.sources:
            module = modules[source.module]
            for path, node, value, _ in _runtime_members(ast.parse(source.content).body, module, compile(source.content, source.filename, "exec", dont_inherit=True), source.module):
                if inspect.isfunction(value):
                    components = path.removeprefix(source.module + ".").split(".")
                    def getter(module=module, components=components):
                        value = module
                        for component in components:
                            value = inspect.getattr_static(value, component)
                        return value
                    getters.append(getter)
        actual = function.__func__ if inspect.ismethod(function) else function
        globals = tuple((modules[module_name], name, actual.__builtins__.get(name)) for name in _code_globals(actual.__code__))
        runtime = AuthenticatedSlice(files, modules, getters, globals)

    def check():
        try:
            runtime.check()
            if call.receiver and inspect.ismethod(function) and vars(function.__self__):
                raise ValueError("CPU receiver acquired mutable state")
        except ValueError as error:
            raise PortRefusal(str(error)) from error
    return function, check, signature, adapters


def _bound_arguments(call, signature, check_active, prepared_releases, *, adapters=None):
    controls = {
        name for name in (call.control_parameter, call.prepared_parameter) if name is not None
    }
    if controls and (
        call.verification != "prepared-kernel" or not controls <= set(signature.parameters)
    ):
        raise ValueError("CPU controls differ from admitted prepared-kernel parameters")
    if set(call.arguments) != set(signature.parameters) - controls:
        raise ValueError("CPU call arguments differ from acquired original signature")
    if adapters is None:
        from .data_operation_ports import PortAdapters
        adapters = PortAdapters()
    arguments = {
        name: adapters.get(signature.parameters[name].annotation).validate_json(value, strict=True)
        for name, value in call.arguments.items()
    }
    if call.control_parameter is not None:
        arguments[call.control_parameter] = check_active
    if call.prepared_parameter is not None:
        if call.prepared_parameter == call.control_parameter or not call.prepared_release_id:
            raise ValueError("CPU prepared capsule binding is invalid")
        prepared = (prepared_releases or {}).get(call.prepared_release_id)
        if prepared is None or prepared.release_id != call.prepared_release_id:
            raise ValueError("CPU kernel lacks its exact admitted prepared release capsule")
        arguments[call.prepared_parameter] = prepared
    elif call.prepared_release_id is not None:
        raise ValueError("CPU release capsule lacks its admitted parameter")
    positional = tuple(
        arguments[p.name]
        for p in signature.parameters.values()
        if p.kind == inspect.Parameter.POSITIONAL_ONLY
    )
    keywords = {
        name: value
        for name, value in arguments.items()
        if signature.parameters[name].kind != inspect.Parameter.POSITIONAL_ONLY
    }
    return signature.bind(*positional, **keywords)


def execute_python_call(
    content: bytes, check_active, prepare_runtime=lambda: None, prepared_releases=None
) -> bytes:
    """Child-only: typed original ingress and egress; no native/database access."""
    call = _Call.model_validate_json(content, strict=True)
    function, verify = _load(call)
    signature = _prepared_call(call).signature
    bound = _bound_arguments(call, signature, check_active, prepared_releases, adapters=_prepared_call(call).adapters)
    prepare_runtime()
    check_active()
    result = function(*bound.args, **bound.kwargs)
    prepare_runtime()
    check_active()
    verify()
    adapter = _prepared_call(call).adapters.get(signature.return_annotation)
    return adapter.dump_json(adapter.validate_python(result, strict=True))


def execute_python_stream(
    content,
    connection,
    check_active,
    prepare_runtime,
    max_reply_bytes,
    fence,
    prepared_releases=None,
    request_digest=None,
):
    """Child-owned iterator with one item per authenticated parent pull credit."""
    import json
    from collections.abc import Generator, Iterator
    from hashlib import sha256
    from typing import get_args, get_origin

    call = _Call.model_validate_json(content, strict=True)
    if call.invocation_form == "coroutine":
        return execute_python_coroutine(
            call,
            content,
            connection,
            check_active,
            prepare_runtime,
            max_reply_bytes,
            fence,
            prepared_releases,
            request_digest=request_digest,
        )
    if call.invocation_form != "stream":
        raise ValueError("CPU stream requires its admitted stream descriptor")
    function, verify = _load(call)
    signature = _prepared_call(call).signature
    annotation = signature.return_annotation
    if get_origin(annotation) not in (Iterator, Generator):
        raise ValueError("stream call requires its typed iterator annotation")
    adapters = _prepared_call(call).adapters
    arguments = {
        name: adapters.get(signature.parameters[name].annotation).validate_json(value, strict=True)
        for name, value in call.arguments.items()
    }
    if set(arguments) != set(signature.parameters):
        raise ValueError("stream arguments differ from original callable")
    positional = tuple(
        arguments[p.name]
        for p in signature.parameters.values()
        if p.kind == inspect.Parameter.POSITIONAL_ONLY
    )
    keywords = {
        name: value
        for name, value in arguments.items()
        if signature.parameters[name].kind != inspect.Parameter.POSITIONAL_ONLY
    }
    bound = signature.bind(*positional, **keywords)
    iterator = function(*bound.args, **bound.kwargs)
    if not isinstance(iterator, Iterator):
        raise ValueError("stream callable did not return an iterator")
    adapter, ordinal = _prepared_call(call).adapters.get(get_args(annotation)[0]), 0
    digest = request_digest if request_digest is not None else sha256(content).hexdigest()
    try:
        while True:
            check_active()
            while not connection.poll(0.1):
                check_active()
            if json.loads(connection.recv_bytes(4096)) != {"pull": ordinal}:
                raise ValueError("stream pull credit differs from next ordinal")
            prepare_runtime()
            check_active()
            verify()
            try:
                value = next(iterator)
            except StopIteration:
                verify()
                connection.send_bytes(
                    canonical_bytes(
                        {"request": digest, "fence": fence, "ordinal": ordinal, "state": "complete"}
                    )
                )
                return canonical_bytes({"items": ordinal, "state": "complete"})
            check_active()
            verify()
            encoded = adapter.dump_json(adapter.validate_python(value, strict=True)).decode("utf-8")
            frame = canonical_bytes(
                {
                    "request": digest,
                    "fence": fence,
                    "ordinal": ordinal,
                    "state": "item",
                    "value": encoded,
                }
            )
            if len(frame) > max_reply_bytes:
                raise ValueError("stream item exceeds owned transport capacity")
            connection.send_bytes(frame)
            ordinal += 1
    finally:
        close = getattr(iterator, "close", None)
        if close is not None:
            close()
        connection.close()


def coroutine_adapters(signature, descriptor):
    """The original callable supplies one nominal question/reply/result contract."""
    from collections.abc import Generator
    from typing import Any, get_args, get_origin

    annotation = signature.return_annotation
    types = get_args(annotation)
    if (
        get_origin(annotation) is not Generator
        or len(types) != 3
        or any(value is Any for value in types)
    ):
        raise ValueError("CPU coroutine requires Generator[Question, Reply, Result] annotation")
    adapters = descriptor.adapters(signature)
    return tuple(adapters.get(value) for value in types)


def execute_python_coroutine(
    call,
    content,
    connection,
    check_active,
    prepare_runtime,
    max_reply_bytes,
    fence,
    prepared_releases=None,
    request_digest=None,
):
    """Child-only original generator; one typed reply advances one pending question.

    Domain failure disposition is part of the declared reply type. Unexpected
    infrastructure errors never become fabricated answers or replayed computation.
    """
    import json
    from collections.abc import Generator
    from hashlib import sha256

    function, verify = _load(call)
    signature = _prepared_call(call).signature
    from typing import get_args
    question_adapter, reply_adapter, result_adapter = tuple(_prepared_call(call).adapters.get(item) for item in get_args(signature.return_annotation))
    bound = _bound_arguments(call, signature, check_active, prepared_releases, adapters=_prepared_call(call).adapters)
    generator = function(*bound.args, **bound.kwargs)
    if not isinstance(generator, Generator):
        raise ValueError("CPU coroutine callable did not return its original generator")
    digest, ordinal = request_digest if request_digest is not None else sha256(content).hexdigest(), 0

    def send(state, value):
        frame = canonical_bytes(
            dict(request=digest, fence=fence, ordinal=ordinal, state=state, value=value.decode())
        )
        if len(frame) > max_reply_bytes:
            raise ValueError("CPU coroutine message exceeds owned transport capacity")
        connection.send_bytes(frame)

    try:
        while True:
            check_active()
            while not connection.poll(0.1):
                check_active()
            credit = json.loads(connection.recv_bytes(max_reply_bytes))
            fields = {"pull"} if ordinal == 0 else {"pull", "reply"}
            if (
                set(credit) != fields
                or type(credit["pull"]) is not int
                or credit["pull"] != ordinal
            ):
                raise ValueError("CPU coroutine reply differs from pending question ordinal")
            reply = (
                None if ordinal == 0 else reply_adapter.validate_json(credit["reply"], strict=True)
            )
            prepare_runtime()
            check_active()
            verify()
            try:
                question = next(generator) if ordinal == 0 else generator.send(reply)
            except StopIteration as completed:
                result = result_adapter.dump_json(
                    result_adapter.validate_python(completed.value, strict=True)
                )
                check_active()
                verify()
                send("complete", result)
                return canonical_bytes(
                    dict(turns=ordinal, state="complete", result_digest=sha256(result).hexdigest())
                )
            check_active()
            verify()
            question = question_adapter.dump_json(
                question_adapter.validate_python(question, strict=True)
            )
            send("question", question)
            ordinal += 1
    finally:
        generator.close()
        connection.close()
