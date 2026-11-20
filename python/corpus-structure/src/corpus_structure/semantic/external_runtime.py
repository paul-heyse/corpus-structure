"""Finite native codec capabilities acquired before workload identity is derived."""

from __future__ import annotations

import importlib
import inspect
import json
import sys
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from types import ModuleType

from .file_custody import FileCustody, verified_file


@dataclass(frozen=True)
class ExternalRuntime:
    """Original native symbols and the files and bindings which implement them.

    The supported profile is closed here. A captured arbitrary Python object cannot
    turn an unknown external call into an admitted capability.
    """

    reference: str
    contract: str
    digest: str
    symbols: tuple[tuple[str, object], ...] = field(compare=False, hash=False, repr=False)
    modules: tuple[tuple[str, ModuleType], ...] = field(compare=False, hash=False, repr=False)
    files: tuple[FileCustody, ...] = field(compare=False, hash=False, repr=False)

    def check(self):
        for file in self.files:
            file.check()
        for name, module in self.modules:
            if sys.modules.get(name) is not module:
                raise ValueError("external codec module was replaced: " + name)
        for name, expected in self.symbols:
            module, _, member = name.rpartition(".")
            if vars(sys.modules[module]).get(member) is not expected:
                raise ValueError("external codec symbol was replaced: " + name)


# Native classes are immutable CPython types. Their Python wrappers are captured
# separately and must export those same original types. Python implementations of
# json/base64 and abstract collection types need their own closed source proof.
_PROFILES = (
    ("math", "math", ("isfinite",), ()),
    (
        "rapidjson",
        "rapidjson",
        ("loads", "dumps"),
        (("NM_DECIMAL", 2), ("BM_NONE", 0)),
    ),
    ("decimal", "_decimal", ("Decimal",), ()),
    ("datetime", "_datetime", ("date", "datetime", "UTC"), ()),
)


def acquire_codec_runtime() -> tuple[ExternalRuntime, ...]:
    """Acquire the selected finite CPython and RapidJSON native API profiles."""
    result = []
    for public_name, native_name, names, constants in _PROFILES:
        public = importlib.import_module(public_name)
        native = importlib.import_module(native_name)
        captured = []
        modules = tuple(dict(((public_name, public), (native_name, native))).items())
        paths = {Path(sys.executable).resolve()}
        for name, module in modules:
            spec = module.__spec__
            if spec is None or spec.name != name:
                raise ValueError("external codec module has no original import specification")
            if spec.origin not in {"built-in", "frozen"}:
                if spec.origin is None or module.__file__ is None:
                    raise ValueError("external codec module has no original file")
                origin = Path(spec.origin).resolve()
                if Path(module.__file__).resolve() != origin:
                    raise ValueError("external codec module origin differs: " + name)
                paths.add(origin)
        for name in names:
            value = getattr(native, name)
            if getattr(public, name) is not value:
                raise ValueError("external codec wrapper binding differs: " + public_name + "." + name)
            if inspect.isbuiltin(value):
                if value.__self__ is not native or value.__name__ != name:
                    raise ValueError("external codec native callable differs: " + name)
            elif isinstance(value, type):
                if not value.__flags__ & (1 << 8) or value.__name__ != name:
                    raise ValueError("external codec type is not an immutable native type")
            elif public_name != "datetime" or name != "UTC" or value is not native.timezone.utc:
                raise ValueError("unsupported external codec symbol: " + name)
            captured.extend((owner + "." + name, value) for owner, _ in modules)
        for name, expected in constants:
            value = getattr(public, name)
            if type(value) is not int or value != expected:
                raise ValueError("external codec constant differs: " + name)
            captured.append((public_name + "." + name, value))
        files = tuple(
            verified_file(path, sha256(path.read_bytes()).hexdigest()) for path in sorted(paths)
        )
        payload = dict(
            profile="native-codec-api-v1",
            module=public_name,
            symbols=[name for name, _ in captured],
            constants=constants,
            python=sys.version,
            files=[(str(path), file.digest) for path, file in zip(sorted(paths), files, strict=True)],
        )
        digest = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        capability = ExternalRuntime(
            public_name, "native-codec-api-v1", digest, tuple(captured), modules, files
        )
        capability.check()
        result.append(capability)
    return tuple(result)
