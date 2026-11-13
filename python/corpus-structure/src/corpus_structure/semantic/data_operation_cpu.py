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


@dataclass(frozen=True)
class PythonCPUDescriptor:
    """Owned source custody and entrypoint; no model/schema or execution authority."""

    sources: tuple[tuple[str, str, bytes], ...]
    entrypoint: str
    expected_nodes: tuple[str, ...]
    receiver: bool = False
    verification: Literal["closed-slice", "prepared-kernel"] = "closed-slice"
    control_parameter: str | None = None

    def __post_init__(self) -> None:
        if self.control_parameter is not None and (
            self.verification != "prepared-kernel" or not self.control_parameter
        ):
            raise ValueError("only prepared kernels can bind an owned CPU control parameter")

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
                "arguments": {
                    name: TypeAdapter(signature.parameters[name].annotation)
                    .dump_json(value)
                    .decode()
                    for name, value in arguments.items()
                    if name != self.control_parameter
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
            _verify_closed_runtime_sources(sources, modules, paths, set(call.expected_nodes))
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


def execute_python_call(content: bytes, check_active, prepare_runtime=lambda: None) -> bytes:
    """Child-only: typed original ingress and egress; no native/database access."""
    call = _Call.model_validate_json(content, strict=True)
    function, verify = _load(call)
    signature = inspect.signature(function, eval_str=True)
    controls = set() if call.control_parameter is None else {call.control_parameter}
    if controls and (
        call.verification != "prepared-kernel" or not controls <= set(signature.parameters)
    ):
        raise ValueError("CPU control requires its admitted prepared-kernel parameter")
    if set(call.arguments) != set(signature.parameters) - controls:
        raise ValueError("CPU call arguments differ from acquired original signature")
    arguments = {
        name: TypeAdapter(signature.parameters[name].annotation).validate_json(value, strict=True)
        for name, value in call.arguments.items()
    }
    if call.control_parameter is not None:
        arguments[call.control_parameter] = check_active
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
    prepare_runtime()
    check_active()
    result = function(*bound.args, **bound.kwargs)
    prepare_runtime()
    check_active()
    verify()
    adapter = TypeAdapter(signature.return_annotation)
    return adapter.dump_json(adapter.validate_python(result, strict=True))
