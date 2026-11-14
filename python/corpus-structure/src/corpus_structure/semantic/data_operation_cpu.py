"""Compact acquired Python calls in the invocation's existing CPU process owner.

This is physical custody, not a second semantic operation registry. Only resolved
ports or prepared kernel adapters create descriptors after their own admission.
"""

from __future__ import annotations

import base64
import importlib
import inspect
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter

from .identity import canonical_bytes


class _Source(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    module: str
    path: str
    content: str


class _Call(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sources: tuple[_Source, ...]
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

    def __post_init__(self) -> None:
        if self.control_parameter is not None and (
            self.verification != "prepared-kernel" or not self.control_parameter
        ):
            raise ValueError("only prepared kernels can bind an owned CPU control parameter")

        if (self.prepared_parameter is None) != (self.prepared_release_id is None) or (
            self.prepared_parameter is not None and (self.verification != "prepared-kernel" or not self.prepared_parameter or not self.prepared_release_id or self.prepared_parameter == self.control_parameter)
        ):
            raise ValueError("only prepared kernels can bind the exact admitted release capsule")

    def packet(self, arguments, signature) -> bytes:
        return canonical_bytes(
            {
                "sources": [
                    dict(module=module, path=path, content=base64.b64encode(content).decode())
                    for module, path, content in self.sources
                ],
                "entrypoint": self.entrypoint,
                "expected_nodes": self.expected_nodes,
                "receiver": self.receiver,
                "verification": self.verification,
                "control_parameter": self.control_parameter,
                "prepared_parameter": self.prepared_parameter,
                "prepared_release_id": self.prepared_release_id,
                "invocation_form": self.invocation_form,
                "arguments": {
                    name: TypeAdapter(signature.parameters[name].annotation)
                    .dump_json(value)
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
    from .data_operation_ports import PortRefusal, _runtime_members
    from .python_operation_sources import PythonSource, PythonSourceCollection

    sources = PythonSourceCollection(
        tuple(
            PythonSource(
                source.module, base64.b64decode(source.content, validate=True), source.path
            )
            for source in call.sources
        )
    )
    paths = {source.module: Path(source.filename) for source in sources.sources}
    if len(paths) != len(sources.sources) or not paths:
        raise PortRefusal("CPU source collection must have distinct actual modules")
    roots = set()
    for source in sources.sources:
        path = paths[source.module]
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
            _verify_closed_runtime_sources(sources, modules, paths, set(call.expected_nodes), standard_references=_stream_annotation_references() if call.invocation_form in {"stream", "coroutine"} else None)
        else:
            import ast

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

    verify()
    return function, verify


def _bound_arguments(call, signature, check_active, prepared_releases):
    controls = {name for name in (call.control_parameter, call.prepared_parameter) if name is not None}
    if controls and (call.verification != "prepared-kernel" or not controls <= set(signature.parameters)):
        raise ValueError("CPU controls differ from admitted prepared-kernel parameters")
    if set(call.arguments) != set(signature.parameters) - controls:
        raise ValueError("CPU call arguments differ from acquired original signature")
    arguments = {name: TypeAdapter(signature.parameters[name].annotation).validate_json(value, strict=True) for name, value in call.arguments.items()}
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
    positional = tuple(arguments[p.name] for p in signature.parameters.values() if p.kind == inspect.Parameter.POSITIONAL_ONLY)
    keywords = {name: value for name, value in arguments.items() if signature.parameters[name].kind != inspect.Parameter.POSITIONAL_ONLY}
    return signature.bind(*positional, **keywords)


def execute_python_call(content: bytes, check_active, prepare_runtime=lambda: None, prepared_releases=None) -> bytes:
    """Child-only: typed original ingress and egress; no native/database access."""
    call = _Call.model_validate_json(content, strict=True)
    function, verify = _load(call)
    signature = inspect.signature(function, eval_str=True)
    bound = _bound_arguments(call, signature, check_active, prepared_releases)
    prepare_runtime()
    check_active()
    result = function(*bound.args, **bound.kwargs)
    prepare_runtime()
    check_active()
    verify()
    adapter = TypeAdapter(signature.return_annotation)
    return adapter.dump_json(adapter.validate_python(result, strict=True))



def execute_python_stream(content, connection, check_active, prepare_runtime, max_reply_bytes, fence, prepared_releases=None):
    """Child-owned iterator with one item per authenticated parent pull credit."""
    import json
    from collections.abc import Iterator, Generator
    from hashlib import sha256
    from typing import get_args, get_origin

    call = _Call.model_validate_json(content, strict=True)
    if call.invocation_form == "coroutine":
        return execute_python_coroutine(call, content, connection, check_active, prepare_runtime, max_reply_bytes, fence, prepared_releases)
    if call.invocation_form != "stream":
        raise ValueError("CPU stream requires its admitted stream descriptor")
    function, verify = _load(call)
    signature = inspect.signature(function, eval_str=True)
    annotation = signature.return_annotation
    if get_origin(annotation) not in (Iterator, Generator):
        raise ValueError('stream call requires its typed iterator annotation')
    arguments = {name: TypeAdapter(signature.parameters[name].annotation).validate_json(value, strict=True) for name, value in call.arguments.items()}
    if set(arguments) != set(signature.parameters):
        raise ValueError('stream arguments differ from original callable')
    positional = tuple(arguments[p.name] for p in signature.parameters.values() if p.kind == inspect.Parameter.POSITIONAL_ONLY)
    keywords = {name: value for name, value in arguments.items() if signature.parameters[name].kind != inspect.Parameter.POSITIONAL_ONLY}
    bound = signature.bind(*positional, **keywords)
    iterator = function(*bound.args, **bound.kwargs)
    if not isinstance(iterator, Iterator):
        raise ValueError('stream callable did not return an iterator')
    adapter, ordinal = TypeAdapter(get_args(annotation)[0]), 0
    digest = sha256(content).hexdigest()
    try:
        while True:
            check_active()
            while not connection.poll(0.1):
                check_active()
            if json.loads(connection.recv_bytes(4096)) != {'pull': ordinal}:
                raise ValueError('stream pull credit differs from next ordinal')
            prepare_runtime()
            check_active()
            verify()
            try:
                value = next(iterator)
            except StopIteration:
                verify()
                connection.send_bytes(canonical_bytes({'request': digest, 'fence': fence, 'ordinal': ordinal, 'state': 'complete'}))
                return canonical_bytes({'items': ordinal, 'state': 'complete'})
            check_active()
            verify()
            encoded = adapter.dump_json(adapter.validate_python(value, strict=True)).decode('utf-8')
            frame = canonical_bytes({'request': digest, 'fence': fence, 'ordinal': ordinal, 'state': 'item', 'value': encoded})
            if len(frame) > max_reply_bytes:
                raise ValueError('stream item exceeds owned transport capacity')
            connection.send_bytes(frame)
            ordinal += 1
    finally:
        close = getattr(iterator, 'close', None)
        if close is not None:
            close()
        connection.close()


def coroutine_adapters(signature):
    """The original callable supplies one nominal question/reply/result contract."""
    from collections.abc import Generator
    from typing import Any, get_args, get_origin

    annotation = signature.return_annotation
    types = get_args(annotation)
    if get_origin(annotation) is not Generator or len(types) != 3 or any(value is Any for value in types):
        raise ValueError("CPU coroutine requires Generator[Question, Reply, Result] annotation")
    return tuple(TypeAdapter(value) for value in types)


def execute_python_coroutine(call, content, connection, check_active, prepare_runtime, max_reply_bytes, fence, prepared_releases=None):
    """Child-only original generator; one typed reply advances one pending question.

    Domain failure disposition is part of the declared reply type. Unexpected
    infrastructure errors never become fabricated answers or replayed computation.
    """
    import json
    from collections.abc import Generator
    from hashlib import sha256

    function, verify = _load(call)
    signature = inspect.signature(function, eval_str=True)
    question_adapter, reply_adapter, result_adapter = coroutine_adapters(signature)
    bound = _bound_arguments(call, signature, check_active, prepared_releases)
    generator = function(*bound.args, **bound.kwargs)
    if not isinstance(generator, Generator):
        raise ValueError("CPU coroutine callable did not return its original generator")
    digest, ordinal = sha256(content).hexdigest(), 0

    def send(state, value):
        frame = canonical_bytes(dict(request=digest, fence=fence, ordinal=ordinal, state=state, value=value.decode()))
        if len(frame) > max_reply_bytes:
            raise ValueError("CPU coroutine message exceeds owned transport capacity")
        connection.send_bytes(frame)

    try:
        while True:
            check_active()
            while not connection.poll(.1):
                check_active()
            credit = json.loads(connection.recv_bytes(max_reply_bytes))
            fields = {"pull"} if ordinal == 0 else {"pull", "reply"}
            if set(credit) != fields or type(credit["pull"]) is not int or credit["pull"] != ordinal:
                raise ValueError("CPU coroutine reply differs from pending question ordinal")
            reply = None if ordinal == 0 else reply_adapter.validate_json(credit["reply"], strict=True)
            prepare_runtime()
            check_active()
            verify()
            try:
                question = next(generator) if ordinal == 0 else generator.send(reply)
            except StopIteration as completed:
                result = result_adapter.dump_json(result_adapter.validate_python(completed.value, strict=True))
                check_active()
                verify()
                send("complete", result)
                return canonical_bytes(dict(turns=ordinal, state="complete", result_digest=sha256(result).hexdigest()))
            check_active()
            verify()
            question = question_adapter.dump_json(question_adapter.validate_python(question, strict=True))
            send("question", question)
            ordinal += 1
    finally:
        generator.close()
        connection.close()
