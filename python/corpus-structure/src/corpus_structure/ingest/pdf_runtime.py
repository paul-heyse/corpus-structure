"""Acquired initialized PDF objects and the mutable premises used before conversion."""

from __future__ import annotations

import inspect
import json
import marshal
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from types import CodeType, FunctionType
from typing import Any

from corpus_structure.semantic.file_custody import FileCustody, observed_file

from .pdf_assets import PreparedPdfAssets


def _relocatable_code(code: CodeType) -> CodeType:
    """Observe loaded bytecode without making a source-correspondence claim."""
    return code.replace(
        co_filename="",
        co_consts=tuple(
            _relocatable_code(value) if isinstance(value, CodeType) else value
            for value in code.co_consts
        ),
    )


@dataclass(frozen=True)
class InitializedPdfRuntime:
    """An initialized binding observation with process-local invalidation checks.

    These facts describe the concrete converter. Reuse eligibility additionally needs
    its admitted source, initialization and input/resource contract at the capture owner.
    """

    content: bytes
    files: tuple[FileCustody, ...] = field(repr=False, compare=False)
    bindings: tuple[tuple[str, Callable[[], Any], Any], ...] = field(repr=False, compare=False)
    code: tuple[tuple[FunctionType, Any], ...] = field(repr=False, compare=False)
    options: tuple[tuple[Callable[[], bytes], bytes], ...] = field(repr=False, compare=False)
    assets: PreparedPdfAssets | None = field(repr=False, compare=False)

    def check(self) -> None:
        for record in self.files:
            record.check()
        if self.assets is not None:
            self.assets.verify()
        for name, getter, expected in self.bindings:
            try:
                current = getter()
            except (AttributeError, KeyError, IndexError) as error:
                raise ValueError("initialized PDF runtime binding disappeared: " + name) from error
            if current is not expected:
                raise ValueError("initialized PDF runtime binding changed: " + name)
        for function, expected in self.code:
            if function.__code__ is not expected:
                raise ValueError("initialized PDF runtime code changed: " + function.__qualname__)
        for getter, expected in self.options:
            if getter() != expected:
                raise ValueError("initialized PDF runtime options changed")

    @property
    def digest(self) -> str:
        return sha256(self.content).hexdigest()


def capture_initialized_pdf_runtime(
    owner, *, assets: PreparedPdfAssets | None
) -> InitializedPdfRuntime:
    """Capture actual pipeline and stage objects after repository wrappers are installed."""
    bindings = []
    functions = {}
    files: dict[Path, FileCustody] = {}
    facts = []
    options = []

    def observe(name, getter):
        value = getter()
        bindings.append((name, getter, value))
        if value is None:
            return
        value_type = type(value)
        cls = value if inspect.isclass(value) else value_type
        bindings.append((name + ".__class__", lambda value=value: type(value), value_type))
        methods = []
        for base in cls.__mro__:
            for member, descriptor in vars(base).items():
                function = (
                    descriptor.__func__
                    if isinstance(descriptor, (staticmethod, classmethod))
                    else descriptor
                )
                if not inspect.isfunction(function):
                    continue
                key = function.__module__ + "." + function.__qualname__
                functions[id(function)] = function
                bindings.append(
                    (
                        key,
                        lambda base=base, member=member: inspect.getattr_static(base, member),
                        descriptor,
                    )
                )
                module = sys.modules.get(function.__module__)
                if module is not None:
                    bindings.append(
                        (
                            function.__module__,
                            lambda name=function.__module__: sys.modules.get(name),
                            module,
                        )
                    )
                source = inspect.getsourcefile(function)
                source_digest = None
                if source is not None and Path(source).is_file():
                    path = Path(source).resolve()
                    if path not in files:
                        files[path] = observed_file(path)
                    source_digest = files[path].digest
                methods.append(
                    (
                        key,
                        source_digest,
                        sha256(marshal.dumps(_relocatable_code(function.__code__))).hexdigest(),
                    )
                )
        facts.append(
            {
                "role": name,
                "class": cls.__module__ + "." + cls.__qualname__,
                "methods": sorted(set(methods)),
            }
        )

    for name in ("_converter", "_pipeline", "_formula"):
        observe(name, lambda name=name: getattr(owner, name))
    converter = owner._converter
    if converter is not None and hasattr(converter, "backend"):
        for name in ("pipeline_cls", "backend"):
            observe("converter.pdf_" + name, lambda name=name: getattr(converter, name))
        bindings.append(("converter.pipeline", lambda: converter.pipeline, converter.pipeline))
        for name in ("pipeline_options", "backend_options"):
            configured = getattr(converter, name)
            bindings.append(
                ("converter.pdf_" + name, lambda name=name: getattr(converter, name), configured)
            )
            if configured is not None:

                def getter(configured=configured):
                    return configured.model_dump_json(serialize_as_any=True).encode()

                options.append((getter, getter()))
    pipeline = owner._pipeline
    if pipeline is not None:
        if hasattr(pipeline, "pipeline_options"):
            bindings.append(
                (
                    "pipeline.pipeline_options",
                    lambda: pipeline.pipeline_options,
                    pipeline.pipeline_options,
                )
            )
        for name in sorted(vars(pipeline)):
            value = vars(pipeline)[name]
            if name.endswith("_model"):
                observe("pipeline." + name, lambda name=name: getattr(pipeline, name))
            elif name.endswith("_pipe") and isinstance(value, (list, tuple)):
                bindings.append(
                    ("pipeline." + name, lambda name=name: getattr(pipeline, name), value)
                )
                count = len(value)
                # Storing the immutable count catches list extension/removal as well as substitution.
                bindings.append(
                    (
                        "pipeline." + name + ".length",
                        lambda value=value, count=count: count if len(value) == count else None,
                        count,
                    )
                )
                for index in range(count):
                    observe(
                        f"pipeline.{name}[{index}]",
                        lambda value=value, index=index: value[index],
                    )
    formula = owner._formula
    if formula is not None:
        observe("formula.native", lambda: formula.native)
        observe("formula.engine", lambda: getattr(formula.native, "engine", None))
    content = json.dumps(
        {
            "profile": "pdf-initialized-bindings-v1",
            "bindings": facts,
            "assets": assets.digest if assets is not None else None,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    runtime = InitializedPdfRuntime(
        content,
        tuple(files.values()),
        tuple(bindings),
        tuple((function, function.__code__) for function in functions.values()),
        tuple(options),
        assets,
    )
    runtime.check()
    return runtime
