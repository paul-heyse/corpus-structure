"""Captured code and material inputs for native preparation."""

from __future__ import annotations

import ast
from contextlib import contextmanager
from dataclasses import asdict
from functools import cache
from hashlib import sha256
from pathlib import Path

from .identity import canonical_bytes


@cache
def _analyze_generator_code():
    from .code_identity import capture_code_identity
    from .external_runtime import acquire_codec_runtime

    root = Path(__file__).resolve().parents[1]
    return capture_code_identity(
        root,
        ("corpus_structure.semantic.target_installation",),
        callables=(
            "corpus_structure.semantic.native_rendering.render_captured",
            "corpus_structure.model.compiled.CompiledModel.__init__",
            "corpus_structure.model.compiled.CompiledModel.exact_physical",
            "corpus_structure.model.compiled.model_request_scope",
            "corpus_structure.semantic.pdf_domain.prepare_native_pdf_sources",
            "corpus_structure.semantic.pdf_domain.pdf_domain_sources",
            "corpus_structure.semantic.target_installation.render_target_installation",
            "corpus_structure.semantic.target_installation._build_target_installation",
            "corpus_structure.semantic.target_installation.foundation_programs",
            "corpus_structure.semantic.native_products._capture_native_authoring_inputs",
            "corpus_structure.semantic.native_protocol_authoring._native_protocol_sources",
        ),
        external_runtime=acquire_codec_runtime(),
    )


def capture_generator_code():
    from corpus_structure._query_custody import capture_workload_sources

    root = Path(__file__).resolve().parents[1]
    identity = _analyze_generator_code()
    for capability in identity.external_runtime:
        capability.check()
    capture_workload_sources(root, identity)
    return identity


def capture_generator_sources(identity) -> tuple[tuple[str, bytes], ...]:
    """Capture the renderer-declared source files copied into its exact artifact."""
    from .file_custody import observed_file

    root = Path(__file__).resolve().parents[1]
    available = {item.filename: item.content for item in identity.modules}
    captured = []
    for filename in sorted(_copied_source_paths(available)):
        path = root / filename
        record = observed_file(path)
        content = available.get(filename)
        if content is None:
            content = path.read_bytes()
        record.check()
        if sha256(content).hexdigest() != record.digest:
            raise ValueError(f"copied native provenance changed during capture: {filename}")
        captured.append((filename, content))
    return tuple(captured)


def _copied_source_paths(available: dict[str, bytes]) -> set[str]:
    """Read copied-file references from the same renderer definitions that use them."""
    owners = {
        "semantic/target_installation.py": "_build_target_installation",
        "semantic/native_products.py": "_capture_native_authoring_inputs",
        "semantic/native_protocol_authoring.py": "_native_protocol_sources",
        "semantic/data_operation_projections.py": "capture_projection_sources",
    }
    paths: set[str] = set()

    def constants(node):
        return {
            item.value
            for item in ast.walk(node)
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        }

    for module_path, function_name in owners.items():
        content = available.get(module_path)
        if content is None:
            raise ValueError(f"generator identity omitted source owner: {module_path}")
        tree = ast.parse(content)
        function = next(
            (
                node
                for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == function_name
            ),
            None,
        )
        if function is None:
            raise ValueError(f"generator source owner is missing: {module_path}:{function_name}")
        assigned = {}
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                assigned[node.targets[0].id] = node.value
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == "captured_module_sources"
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                paths.add(node.slice.value)
            if (
                not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Name)
                or node.func.id
                not in {
                    "captured_source",
                    "_captured_source",
                    "_captured_module",
                    "_captured_native_module",
                }
                or len(node.args) < 2
            ):
                continue
            argument = node.args[1]
            names = constants(argument)
            if not names and isinstance(argument, ast.Name):
                # Comprehension variables are sourced by the native artifact
                # declarations in this same renderer function.
                for comp in ast.walk(function):
                    if not isinstance(comp, ast.comprehension):
                        continue
                    if isinstance(comp.target, ast.Name) and comp.target.id == argument.id:
                        names.update(constants(comp.iter))
                if not names and argument.id == "module":
                    programs = assigned.get("programs")
                    if isinstance(programs, ast.Tuple):
                        names.update(
                            item.value
                            for record in programs.elts
                            if isinstance(record, ast.Tuple) and len(record.elts) > 1
                            for item in (record.elts[1],)
                            if isinstance(item, ast.Constant) and isinstance(item.value, str)
                        )
            if node.func.id in {"captured_source", "_captured_source"}:
                paths.update(names)
            else:
                paths.update("semantic/" + name for name in names)
    # Model resources and the vocabularies YAML are captured by their typed
    # source owners, not as Python provenance files.
    paths.discard("semantic/operation-vocabularies.yaml")
    return paths


@contextmanager
def capture_generator_custody(identity, *, closed=False):
    from .code_identity import authenticate_workload

    root = Path(__file__).resolve().parents[1]
    with authenticate_workload(root, identity, closed=closed):
        yield


def input_key(inputs) -> bytes | None:
    if not inputs.complete:
        return None
    return _input_document(inputs, generator=inputs.code_identity.digest)


def observed_input_digest(inputs, *, generated_outputs: frozenset[str]) -> str:
    """Fingerprint an input observation without granting program reuse."""
    code = inputs.code_identity
    generator = {
        "sources": [
            (item.filename, sha256(item.content).hexdigest())
            for item in code.modules
            if item.filename not in generated_outputs
        ],
        "distributions": code.distributions,
        "external_runtime": [
            (item.reference, item.contract, item.digest) for item in code.external_runtime
        ],
    }
    return sha256(
        _input_document(inputs, generator=generator, generated_outputs=generated_outputs)
    ).hexdigest()


def _input_document(inputs, *, generator, generated_outputs: frozenset[str] = frozenset()) -> bytes:
    copied = tuple(
        sorted(
            (name, sha256(content).hexdigest())
            for name, content in inputs.module_sources
            if name not in generated_outputs
        )
    )
    resources = tuple(sorted((item.name, item.digest) for item in inputs.resource_sources))

    def source(value):
        return None if value is None else (value.name, value.digest)

    return canonical_bytes(
        dict(
            model_sources=tuple(
                (name, sha256(content).hexdigest()) for name, content in inputs.model_sources
            ),
            generator=generator,
            trigger_inputs=asdict(inputs.trigger_inputs),
            copied_source_bytes=copied,
            physical=tuple(
                (name, sha256(content).hexdigest()) for name, content in inputs.physical_sources
            ),
            linkml_types=sha256(inputs.linkml_types).hexdigest(),
            logical=sorted(
                (name, sha256(content).hexdigest()) for name, content in inputs.logical_sources
            ),
            pdf_actions=source(inputs.pdf_actions),
            pdf_sources=None
            if inputs.pdf_sources is None
            else tuple(map(source, inputs.pdf_sources)),
            extra=tuple(map(source, inputs.extra_sources)),
            resources=resources,
            analysis_runtime=inputs.analysis_runtime,
            native_library_runtime=inputs.native_library_runtime,
        )
    )
