"""Finite native codec capabilities acquired before workload identity is derived."""

from __future__ import annotations

import ast
import builtins
import codecs
import dis
import importlib
import inspect
import json
import math
import re
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from types import CodeType, MemberDescriptorType, ModuleType, WrapperDescriptorType

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
        elif self.reference == "json":
            _verify_standard_json(dict(self.modules), self.files)


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


def acquire_codec_runtime(*, standard_json_io: bool = False) -> tuple[ExternalRuntime, ...]:
    """Acquire the finite codec profiles, selecting stdlib JSON I/O explicitly."""
    standard_json = acquire_standard_json_runtime(public_io=standard_json_io)
    return (
        *(_acquire_native_api(*profile) for profile in _PROFILES),
        _base64_runtime(),
        standard_json,
    )


def acquire_numeric_runtime() -> ExternalRuntime:
    """Own the native finite-number predicate used by source decoding."""
    return _acquire_native_api("math", "math", ("isfinite",), ())


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


def acquire_standard_json_runtime(*, public_io: bool = True) -> ExternalRuntime:
    """Acquire stdlib JSON initialization and, when selected, its two I/O wrappers."""
    from sysconfig import get_path

    modules = tuple(
        (name, importlib.import_module(name))
        for name in ("json", "json.encoder", "json.decoder", "json.scanner", "_json")
    )
    root = Path(get_path("stdlib")).resolve()
    paths = {Path(sys.executable).resolve()}
    for name, module in modules:
        spec = module.__spec__
        if spec is None or spec.name != name or spec.origin is None:
            raise ValueError("standard JSON module has no original import specification")
        if name == "_json" and spec.origin == "built-in":
            continue
        path = Path(spec.origin).resolve()
        module_file = vars(module).get("__file__")
        if (
            not path.is_relative_to(root)
            or module_file is None
            or Path(module_file).resolve() != path
        ):
            raise ValueError("standard JSON module origin differs: " + name)
        paths.add(path)
    loaded = dict(modules)
    files = tuple(observed_file(path) for path in sorted(paths))
    _verify_standard_json(loaded, files)
    public = loaded["json"]
    symbols = (("json.loads", public.loads), ("json.dumps", public.dumps)) if public_io else ()
    payload = dict(
        profile="standard-json-v1",
        python=sys.version,
        files=[(str(file.path), file.digest) for file in files],
        symbols=[name for name, _ in symbols],
    )
    return ExternalRuntime(
        "json",
        "standard-json-v1",
        sha256(public.dumps(payload, sort_keys=True).encode()).hexdigest(),
        symbols,
        modules,
        files,
    )


@lru_cache(maxsize=12)
def _standard_json_definitions(path: Path, digest: str, filename: str):
    data = path.read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError("standard JSON source changed during acquisition")
    return ast.parse(data), compile(data, filename, "exec", dont_inherit=True)


def _verify_json_wrappers(module, files, functions, *, owner=None):
    source = Path(module.__file__).resolve()
    record = next(file for file in files if file.path == source)
    for name in functions:
        function = vars(module if owner is None else owner).get(name)
        if not inspect.isfunction(function) or function.__globals__ is not vars(module):
            raise ValueError("standard JSON wrapper differs: " + name)
        syntax, emitted = _standard_json_definitions(
            source, record.digest, function.__code__.co_filename
        )
        if owner is not None:
            syntax = next(
                node
                for node in syntax.body
                if isinstance(node, ast.ClassDef) and node.name == owner.__name__
            )
            emitted = next(
                code
                for code in emitted.co_consts
                if isinstance(code, CodeType) and code.co_name == owner.__name__
            )
        declaration = next(
            node for node in syntax.body if isinstance(node, ast.FunctionDef) and node.name == name
        )
        code = next(
            code
            for code in emitted.co_consts
            if isinstance(code, CodeType) and code.co_name == name
        )
        defaults = {
            arg.arg: ast.literal_eval(value)
            for arg, value in zip(
                declaration.args.kwonlyargs, declaration.args.kw_defaults, strict=True
            )
            if value is not None
        }
        keyword_defaults = function.__kwdefaults__ or {}
        if (
            function.__code__ != code
            or function.__closure__ is not None
            or keyword_defaults.keys() != defaults.keys()
            or any(keyword_defaults[key] is not value for key, value in defaults.items())
        ):
            raise ValueError("standard JSON wrapper differs: " + name)
        if name == "decode":
            whitespace = module.WHITESPACE
            if (
                type(whitespace) is not re.Pattern
                or whitespace.pattern != r"[ \t\n\r]*"
                or whitespace.flags != re.UNICODE | re.MULTILINE | re.DOTALL | re.VERBOSE
                or function.__defaults__ != (whitespace.match,)
            ):
                raise ValueError("standard JSON whitespace parser differs")
        elif function.__defaults__ != (
            tuple(ast.literal_eval(value) for value in declaration.args.defaults) or None
        ):
            raise ValueError("standard JSON wrapper defaults differ: " + name)
        for instruction in dis.get_instructions(function):
            field = instruction.argval
            if (
                instruction.opname == "LOAD_GLOBAL"
                and field in vars(builtins)
                and vars(module).get(field, function.__builtins__.get(field))
                is not vars(builtins)[field]
            ):
                raise ValueError("standard JSON builtin differs: " + field)


def _verify_json_native_type(value, name, fields):
    if type(value) is not type or value.__name__ != name or value.__module__ != "_json":
        raise ValueError("standard JSON native type differs: " + name)
    bindings = vars(value)
    constructor = bindings.get("__new__")
    call = bindings.get("__call__")
    if (
        bindings.keys() != {"__module__", "__doc__", "__new__", "__call__", *fields}
        or not inspect.isbuiltin(constructor)
        or constructor.__self__ is not value
        or type(call) is not WrapperDescriptorType
        or call.__objclass__ is not value
        or any(
            type(bindings[field]) is not MemberDescriptorType
            or bindings[field].__objclass__ is not value
            or bindings[field].__name__ != field
            for field in fields
        )
    ):
        raise ValueError("standard JSON native type differs: " + name)


def _verify_standard_json(modules, files):
    public, encoder, decoder, scanner, native = (
        modules[name] for name in ("json", "json.encoder", "json.decoder", "json.scanner", "_json")
    )
    _verify_json_wrappers(public, files, ("loads", "dumps", "detect_encoding"))
    _verify_json_wrappers(
        encoder, files, ("__init__", "encode", "iterencode", "default"), owner=encoder.JSONEncoder
    )
    _verify_json_wrappers(
        decoder, files, ("__init__", "decode", "raw_decode"), owner=decoder.JSONDecoder
    )
    _verify_json_wrappers(decoder, files, ("__init__", "__reduce__"), owner=decoder.JSONDecodeError)
    aliases = (
        (public.JSONEncoder, encoder.JSONEncoder),
        (public.JSONDecoder, decoder.JSONDecoder),
        (public.JSONDecodeError, decoder.JSONDecodeError),
        (public.codecs, codecs),
        (decoder.scanner, scanner),
        (encoder.encode_basestring, native.encode_basestring),
        (encoder.encode_basestring_ascii, native.encode_basestring_ascii),
        (encoder.c_make_encoder, native.make_encoder),
        (decoder.scanstring, native.scanstring),
        (scanner.make_scanner, native.make_scanner),
    )
    if any(actual is not expected for actual, expected in aliases):
        raise ValueError("standard JSON native implementation binding differs")
    if any(
        not inspect.isbuiltin(member) or member.__self__ is not native or member.__name__ != name
        for name in ("encode_basestring", "encode_basestring_ascii", "scanstring")
        for member in (getattr(native, name),)
    ):
        raise ValueError("standard JSON native primitive differs")
    _verify_json_native_type(
        native.make_encoder,
        "Encoder",
        (
            "markers",
            "default",
            "encoder",
            "indent",
            "key_separator",
            "item_separator",
            "sort_keys",
            "skipkeys",
        ),
    )
    _verify_json_native_type(
        native.make_scanner,
        "Scanner",
        (
            "strict",
            "object_hook",
            "object_pairs_hook",
            "parse_float",
            "parse_int",
            "parse_constant",
        ),
    )
    wrappers = (
        (
            encoder.JSONEncoder,
            object,
            {
                "__init__",
                "default",
                "encode",
                "iterencode",
                "item_separator",
                "key_separator",
                "__dict__",
            },
        ),
        (decoder.JSONDecoder, object, {"__init__", "decode", "raw_decode", "__dict__"}),
        (decoder.JSONDecodeError, ValueError, {"__init__", "__reduce__"}),
    )
    metadata = {"__module__", "__firstlineno__", "__doc__", "__static_attributes__", "__weakref__"}
    if any(
        type(owner) is not type
        or owner.__bases__ != (base,)
        or vars(owner).keys() != keys | metadata
        for owner, base, keys in wrappers
    ):
        raise ValueError("standard JSON wrapper class differs")
    if (
        type(encoder.JSONEncoder.item_separator) is not str
        or encoder.JSONEncoder.item_separator != ", "
        or type(encoder.JSONEncoder.key_separator) is not str
        or encoder.JSONEncoder.key_separator != ": "
        or type(encoder.INFINITY) is not float
        or float("inf") != encoder.INFINITY
    ):
        raise ValueError("standard JSON constants differ")
    if any(
        type(getattr(codecs, name, None)) is not bytes or getattr(codecs, name) != value
        for name, value in {
            "BOM_UTF8": b"\xef\xbb\xbf",
            "BOM_UTF16_BE": b"\xfe\xff",
            "BOM_UTF16_LE": b"\xff\xfe",
            "BOM_UTF32_BE": b"\x00\x00\xfe\xff",
            "BOM_UTF32_LE": b"\xff\xfe\x00\x00",
        }.items()
    ):
        raise ValueError("standard JSON byte encoding markers differ")
    standard_encoder = public._default_encoder
    standard_decoder = public._default_decoder
    encoder_settings = {
        "skipkeys": False,
        "ensure_ascii": True,
        "check_circular": True,
        "allow_nan": True,
        "sort_keys": False,
        "indent": None,
    }
    if (
        type(standard_encoder) is not encoder.JSONEncoder
        or vars(standard_encoder).keys() != encoder_settings.keys()
        or any(vars(standard_encoder)[key] is not value for key, value in encoder_settings.items())
        or type(standard_decoder) is not decoder.JSONDecoder
    ):
        raise ValueError("standard JSON default wrapper differs")
    scan = standard_decoder.scan_once
    constants = decoder._CONSTANTS
    if (
        type(scan) is not native.make_scanner
        or scan.strict is not True
        or scan.object_hook is not None
        or scan.object_pairs_hook is not None
        or scan.parse_float is not float
        or scan.parse_int is not int
        or type(constants) is not dict
        or constants.keys() != {"NaN", "Infinity", "-Infinity"}
        or any(type(value) is not float for value in constants.values())
        or constants["Infinity"] != float("inf")
        or constants["-Infinity"] != float("-inf")
        or not math.isnan(constants["NaN"])
        or not inspect.isbuiltin(scan.parse_constant)
        or scan.parse_constant.__name__ != "__getitem__"
        or scan.parse_constant.__self__ is not constants
        or "decode" in vars(standard_decoder)
        or "raw_decode" in vars(standard_decoder)
    ):
        raise ValueError("standard JSON default scanner differs")


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
