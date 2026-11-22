"""Finite native codec capabilities acquired before workload identity is derived."""

from __future__ import annotations

import ast
import builtins
import dis
import importlib
import inspect
import json
import sys
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from types import ModuleType

from .file_custody import FileCustody, observed_file


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
        if self.reference == "base64":
            _verify_base64(dict(self.modules)["base64"], dict(self.modules)["binascii"])


# Native classes are immutable CPython types. Their Python wrappers are captured
# separately and must export those same original types. The Python Base64
# profile verifies its complete finite helper group separately.
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
    ("hashlib", "_hashlib", ("sha256",), ()),
)


def acquire_codec_runtime() -> tuple[ExternalRuntime, ...]:
    """Acquire the selected finite CPython and RapidJSON native API profiles."""
    return (*(_acquire_native_api(*profile) for profile in _PROFILES), _base64_runtime())


def acquire_bisect_runtime() -> ExternalRuntime:
    """Own the native ordered search used by positioned source checking."""
    return _acquire_native_api("bisect", "_bisect", ("bisect_left",), ())


def _acquire_native_api(public_name, native_name, names, constants):
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
        native_symbol = "openssl_sha256" if public_name == "hashlib" else name
        value = getattr(native, native_symbol)
        if getattr(public, name) is not value:
            raise ValueError("external codec wrapper binding differs: " + public_name + "." + name)
        if inspect.isbuiltin(value):
            if value.__self__ is not native or value.__name__ != native_symbol:
                raise ValueError("external codec native callable differs: " + name)
        elif isinstance(value, type):
            if not value.__flags__ & (1 << 8) or value.__name__ != name:
                raise ValueError("external codec type is not an immutable native type")
        elif public_name != "datetime" or name != "UTC" or value is not native.timezone.utc:
            raise ValueError("unsupported external codec symbol: " + name)
        captured.extend(
            dict(
                ((public_name + "." + name, value), (native_name + "." + native_symbol, value))
            ).items()
        )
    for name, expected in constants:
        value = getattr(public, name)
        if type(value) is not int or value != expected:
            raise ValueError("external codec constant differs: " + name)
        captured.append((public_name + "." + name, value))
    files = tuple(observed_file(path) for path in sorted(paths))
    payload = dict(
        profile="native-codec-api-v1",
        module=public_name,
        symbols=[name for name, _ in captured],
        constants=constants,
        python=sys.version,
        files=[(str(file.path), file.digest) for file in files],
    )
    digest = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    capability = ExternalRuntime(
        public_name, "native-codec-api-v1", digest, tuple(captured), modules, files
    )
    capability.check()
    return capability


def _verify_base64(module, native):
    """Verify the small standard Base64 implementation and every consumed global."""
    path = Path(module.__file__)
    tree = ast.parse(path.read_bytes())
    code = compile(
        path.read_bytes(), module.urlsafe_b64encode.__code__.co_filename, "exec", dont_inherit=True
    )
    codes = {item.co_name: item for item in code.co_consts if isinstance(item, type(code))}
    references = {
        "b64encode": module.b64encode,
        "_bytes_from_decode_data": module._bytes_from_decode_data,
        "binascii": native,
        "_urlsafe_encode_translation": bytes.maketrans(b"+/", b"-_"),
        "bytes_types": (bytes, bytearray),
    }
    names = ("b64encode", "b64decode", "urlsafe_b64encode", "_bytes_from_decode_data")
    for name in names:
        value = getattr(module, name)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
        defaults = tuple(ast.literal_eval(n) for n in node.args.defaults) or None
        if (
            not inspect.isfunction(value)
            or value.__code__ != codes[name]
            or value.__globals__ is not module.__dict__
            or value.__defaults__ != defaults
            or value.__kwdefaults__ is not None
            or value.__closure__ is not None
        ):
            raise ValueError("standard Base64 callable differs from its original source: " + name)
        # These four leaf functions have no nested functions or comprehensions.
        for instruction in dis.get_instructions(value):
            if instruction.opname != "LOAD_GLOBAL":
                continue
            global_name = instruction.argval
            if global_name in references:
                expected = references[global_name]
                actual = vars(module).get(global_name)
                if global_name == "bytes_types":
                    same = (
                        type(actual) is tuple
                        and len(actual) == 2
                        and actual[0] is bytes
                        and actual[1] is bytearray
                    )
                elif global_name == "_urlsafe_encode_translation":
                    same = type(actual) is bytes and actual == expected
                else:
                    same = actual is expected
                if not same:
                    raise ValueError("standard Base64 global differs: " + global_name)
            elif global_name in vars(builtins):
                if (
                    vars(module).get(global_name, value.__builtins__.get(global_name))
                    is not vars(builtins)[global_name]
                ):
                    raise ValueError("standard Base64 builtin differs: " + global_name)
            else:
                raise ValueError("standard Base64 global lacks a contract: " + global_name)
    for name in ("b2a_base64", "a2b_base64"):
        value = getattr(native, name)
        if not inspect.isbuiltin(value) or value.__self__ is not native or value.__name__ != name:
            raise ValueError("standard Base64 native primitive differs: " + name)


def _base64_runtime():
    module = importlib.import_module("base64")
    native = importlib.import_module("binascii")
    if (
        module.__file__ is None
        or module.__spec__ is None
        or module.__spec__.origin is None
        or native.__spec__ is None
    ):
        raise ValueError("standard Base64 runtime has no original module origin")
    if Path(module.__spec__.origin).resolve() != Path(module.__file__).resolve():
        raise ValueError("standard Base64 runtime source origin differs")
    _verify_base64(module, native)
    symbols = tuple(
        ("base64." + name, getattr(module, name))
        for name in ("urlsafe_b64encode", "b64encode", "b64decode", "_bytes_from_decode_data")
    ) + tuple(("binascii." + name, getattr(native, name)) for name in ("b2a_base64", "a2b_base64"))
    paths = {
        Path(sys.executable).resolve(),
        Path(module.__file__).resolve(),
        Path(__file__).resolve(),
    }
    if native.__spec__.origin != "built-in":
        if native.__file__ is None:
            raise ValueError("standard Base64 primitive has no original file")
        paths.add(Path(native.__file__).resolve())
    files = tuple(observed_file(path) for path in sorted(paths))
    digest = sha256(
        json.dumps([(file.path.name, file.digest) for file in files]).encode()
    ).hexdigest()
    return ExternalRuntime(
        "base64",
        "standard-base64-v1",
        digest,
        symbols,
        (("base64", module), ("binascii", native)),
        files,
    )
