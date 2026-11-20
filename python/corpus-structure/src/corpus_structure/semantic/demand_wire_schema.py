"""Captured, data-only validation schemas for generated native demand records."""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import sys
import typing
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from typing import Any

from .file_custody import FileCustody, observed_file


class UnsupportedWireSchema(ValueError):
    """The generated adapter needs an unmodeled validation capability."""


_NODE_KEYS = {
    "definitions": {"schema", "definitions"},
    "typed-dict": {"fields", "cls", "computed_fields", "extra_behavior", "config"},
    "typed-dict-field": {"schema", "required", "metadata"},
    "list": {"items_schema"},
    "dict": {"keys_schema", "values_schema"},
    "union": {"choices"},
    "nullable": {"schema"},
    "definition-ref": {"schema_ref"},
    "literal": {"expected"},
    "str": set(),
    "int": set(),
    "float": set(),
    "decimal": set(),
    "bool": set(),
    "none": set(),
}


def _schema_bytes(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode()


def _typed_dict_class(cls: Any, fields: dict, module: ModuleType, declarations: dict) -> None:
    if not typing.is_typeddict(cls) or cls.__module__ != module.__name__:
        raise UnsupportedWireSchema("wire schema requires a generated TypedDict class")
    if vars(module).get(cls.__name__) is not cls:
        raise ValueError("generated TypedDict binding changed")
    allowed = {
        "__module__",
        "__firstlineno__",
        "__static_attributes__",
        "__orig_bases__",
        "__dict__",
        "__weakref__",
        "__doc__",
        "__annotate_func__",
        "__annotations_cache__",
        "__annotations__",
        "__required_keys__",
        "__optional_keys__",
        "__readonly_keys__",
        "__mutable_keys__",
        "__total__",
    }
    if set(vars(cls)) - allowed:
        raise ValueError("generated TypedDict has additional behavior")
    declaration = declarations.get(cls.__name__)
    if (
        declaration is None
        or declaration.decorator_list
        or declaration.keywords
        or len(declaration.bases) != 1
    ):
        raise UnsupportedWireSchema("generated TypedDict declaration differs")
    if (
        not isinstance(declaration.bases[0], ast.Name)
        or vars(module).get(declaration.bases[0].id) is not typing.TypedDict
    ):
        raise UnsupportedWireSchema("generated TypedDict base differs")
    for name in ("TypedDict", "Required", "NotRequired"):
        if vars(module).get(name) is not getattr(typing, name):
            raise ValueError("generated wire typing binding changed: " + name)
    annotations = {}
    required = set()
    for item in declaration.body:
        if (
            isinstance(item, ast.Expr)
            and isinstance(item.value, ast.Constant)
            and type(item.value.value) is str
        ):
            continue
        if (
            not isinstance(item, ast.AnnAssign)
            or not isinstance(item.target, ast.Name)
            or item.value is not None
        ):
            raise UnsupportedWireSchema("generated TypedDict has executable fields")
        allowed_syntax = (
            ast.Name,
            ast.Load,
            ast.Constant,
            ast.Subscript,
            ast.Tuple,
            ast.BinOp,
            ast.BitOr,
        )
        if any(not isinstance(node, allowed_syntax) for node in ast.walk(item.annotation)):
            raise UnsupportedWireSchema("generated TypedDict annotation has unsupported syntax")
        annotations[item.target.id] = item.annotation
        is_optional = (
            isinstance(item.annotation, ast.Subscript)
            and isinstance(item.annotation.value, ast.Name)
            and item.annotation.value.id == "NotRequired"
        )
        if not is_optional:
            required.add(item.target.id)
    actual_annotations = cls.__annotations__
    source_fields = annotations
    for name, value in actual_annotations.items():
        if isinstance(value, typing.ForwardRef):
            if name not in source_fields or ast.dump(
                ast.parse(value.__forward_arg__, mode="eval").body
            ) != ast.dump(source_fields[name]):
                raise ValueError("generated TypedDict annotation changed")
        else:
            raise UnsupportedWireSchema(
                "generated TypedDict requires captured postponed annotations"
            )
    if (
        set(actual_annotations) != set(annotations)
        or cls.__required_keys__ != set(annotations)
        or cls.__optional_keys__
        or not cls.__total__
    ):
        raise ValueError("generated TypedDict fields changed")
    if set(fields) != set(annotations) or any(
        type(fields[name]) is not dict or fields[name].get("required") is not (name in required)
        for name in fields
    ):
        raise ValueError("compiled wire schema requiredness differs")


def capture_core_schema(schema: object, module: ModuleType) -> bytes:
    """Lower the reached finite schema, refusing hooks and unknown node options."""
    references: dict[str, str] = {}
    if module.__file__ is None:
        raise ValueError("generated wire module has no source file")
    source = ast.parse(Path(module.__file__).read_bytes())
    declarations = {item.name: item for item in source.body if isinstance(item, ast.ClassDef)}
    if not any(
        isinstance(item, ast.ImportFrom)
        and item.module == "__future__"
        and any(alias.name == "annotations" for alias in item.names)
        for item in source.body
    ):
        raise UnsupportedWireSchema("wire schema requires captured postponed annotations")

    def reference(value):
        if type(value) is not str:
            raise UnsupportedWireSchema("wire schema references require strings")
        return references.setdefault(value, "wire-definition-" + str(len(references)))

    def lower(value, *, fields=False):
        if type(value) is list or type(value) is tuple:
            return [lower(item) for item in value]
        if type(value) is not dict:
            if value is None or type(value) in (str, int, bool):
                return value
            raise UnsupportedWireSchema("wire schema requires primitive data")
        if fields:
            if any(type(name) is not str for name in value):
                raise UnsupportedWireSchema("wire fields require string names")
            return {name: lower(value[name]) for name in sorted(value)}
        kind = value.get("type")
        if type(kind) is not str or kind not in _NODE_KEYS:
            raise UnsupportedWireSchema("unsupported wire schema node: " + str(kind))
        if set(value) - (_NODE_KEYS[kind] | {"type", "ref"}):
            raise UnsupportedWireSchema("unsupported wire schema options for " + kind)
        if kind == "typed-dict":
            computed = value.get("computed_fields", [])
            if type(value.get("fields")) is not dict or type(computed) is not list or computed:
                raise UnsupportedWireSchema("wire schema requires plain generated fields")
            _typed_dict_class(value.get("cls"), value["fields"], module, declarations)
        result: dict[str, Any] = {"type": kind}
        for name in sorted(value.keys() - {"type"}):
            item = value[name]
            if name == "cls":
                continue
            if name in {"metadata", "computed_fields"}:
                expected_type = dict if name == "metadata" else list
                if type(item) is not expected_type or item:
                    raise UnsupportedWireSchema("wire schema metadata must be empty")
                continue
            if name == "config":
                if (
                    type(item) is not dict
                    or set(item) - {"title"}
                    or any(type(v) is not str for v in item.values())
                ):
                    raise UnsupportedWireSchema("wire schema config must contain only a title")
                result[name] = dict(item)
            elif name in {"ref", "schema_ref"}:
                result[name] = reference(item)
            elif name == "fields":
                result[name] = lower(item, fields=True)
            else:
                result[name] = lower(item)
        return result

    return _schema_bytes(lower(schema))


@dataclass(frozen=True, slots=True)
class WireValidatorRuntime:
    """The selected native constructor, descriptor and extension binding."""

    digest: str
    constructor: Any = field(compare=False, repr=False)
    descriptor: Any = field(compare=False, repr=False)
    native: ModuleType = field(compare=False, repr=False)
    public: ModuleType = field(compare=False, repr=False)
    members: tuple[tuple[str, object], ...] = field(compare=False, repr=False)
    files: tuple[FileCustody, ...] = field(compare=False, repr=False)

    def check(self):
        for record in self.files:
            record.check()
        if (
            sys.modules.get(self.native.__name__) is not self.native
            or sys.modules.get(self.public.__name__) is not self.public
        ):
            raise ValueError("wire validator module binding changed")
        if (
            self.native.SchemaValidator is not self.constructor
            or self.public.SchemaValidator is not self.constructor
        ):
            raise ValueError("wire validator constructor binding changed")
        if set(vars(self.constructor)) != {name for name, _ in self.members} or any(
            vars(self.constructor).get(name) is not value for name, value in self.members
        ):
            raise ValueError("wire validator native class changed")


def acquire_wire_validator_runtime() -> WireValidatorRuntime:
    native = importlib.import_module("pydantic_core._pydantic_core")
    public = importlib.import_module("pydantic_core")
    constructor = native.SchemaValidator
    descriptor = inspect.getattr_static(constructor, "validate_python")
    create = inspect.getattr_static(constructor, "__new__")
    if (
        public.SchemaValidator is not constructor
        or not isinstance(constructor, type)
        or constructor.__module__ != native.__name__
        or constructor.__name__ != "SchemaValidator"
    ):
        raise ValueError("wire validator constructor has no native correspondence")
    if (
        not inspect.ismethoddescriptor(descriptor)
        or descriptor.__objclass__ is not constructor
        or descriptor.__name__ != "validate_python"
        or not inspect.isbuiltin(create)
        or create.__self__ is not constructor
    ):
        raise ValueError("wire validator native method differs")
    reduction = inspect.getattr_static(constructor, "__reduce__")
    if (
        not inspect.ismethoddescriptor(reduction)
        or reduction.__objclass__ is not constructor
        or reduction.__name__ != "__reduce__"
    ):
        raise ValueError("wire validator native schema witness differs")
    files = []
    for module in (native, public):
        if (
            module.__spec__ is None
            or module.__spec__.origin is None
            or module.__spec__.name != module.__name__
            or module.__file__ is None
            or Path(module.__spec__.origin).resolve() != Path(module.__file__).resolve()
        ):
            raise ValueError("wire validator native origin differs")
        files.append(observed_file(Path(module.__file__).resolve()))
    digest = sha256(
        _schema_bytes(
            {
                "contract": "generated-wire-validator-v1",
                "files": [
                    (module.__name__, record.digest)
                    for module, record in zip((native, public), files, strict=True)
                ],
                "python": sys.version,
            }
        )
    ).hexdigest()
    runtime = WireValidatorRuntime(
        digest,
        constructor,
        descriptor,
        native,
        public,
        tuple(vars(constructor).items()),
        tuple(files),
    )
    runtime.check()
    return runtime


@dataclass(frozen=True, slots=True)
class CapturedWireValidator:
    schema: bytes
    runtime: WireValidatorRuntime = field(compare=False, repr=False)
    _validator: Any = field(compare=False, repr=False)
    generated: ModuleType = field(compare=False, repr=False)
    source_file: FileCustody = field(compare=False, repr=False)
    digest: str = field(init=False)

    def __post_init__(self):
        self.runtime.check()
        if type(self._validator) is not self.runtime.constructor:
            raise ValueError("wire validator instance differs")
        constructor, arguments = self._validator.__reduce__()
        if (
            constructor is not self.runtime.constructor
            or _schema_bytes(arguments[0]) != self.schema
        ):
            raise ValueError("wire validator schema differs from captured material")
        options = _schema_bytes({"strict": True, "extra": "forbid"})
        object.__setattr__(
            self, "digest", sha256(self.schema + self.runtime.digest.encode() + options).hexdigest()
        )

    def check(self):
        self.runtime.check()
        self.source_file.check()
        if sys.modules.get(self.generated.__name__) is not self.generated:
            raise ValueError("generated wire module binding changed")

    def validate_python(self, value):
        self.check()
        result = self.runtime.descriptor(self._validator, value, strict=True, extra="forbid")
        self.check()
        return result


def capture_wire_validator(adapter, generated_module: ModuleType) -> CapturedWireValidator:
    """Capture an acquired schema, then execute only its closed native validator."""
    from corpus_structure._query_custody import capture_sources

    if generated_module.__file__ is None:
        raise ValueError("generated wire module has no source file")
    path = Path(generated_module.__file__).resolve()
    capture_sources((path,))
    runtime = acquire_wire_validator_runtime()
    schema = capture_core_schema(adapter.core_schema, generated_module)
    validator = runtime.constructor(json.loads(schema))
    captured = CapturedWireValidator(
        schema, runtime, validator, generated_module, observed_file(path)
    )
    captured.check()
    return captured
