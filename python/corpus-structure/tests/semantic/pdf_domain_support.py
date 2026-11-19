"""Current declared PDF helper custody for focused boundary/reader fixtures."""

import json
from hashlib import sha256

import yaml

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_storage import (
    native_operation_declarations,
    native_protocol_sources,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_domain import CONTRACT, HELPER_CONTRACT, PdfDomainContract
from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact


def declarations(domain):
    declaration = json.loads(native_operation_declarations().content)
    operation = next(value for value in declaration["operations"] if value["profile"] == "read")
    operation["capabilities"]["preparation"] = "pdf-native"
    operation["assets"] = [
        *operation["assets"],
        {
            "reference": CONTRACT,
            "contract": HELPER_CONTRACT,
            "role": "native-pdf-helper-bindings",
            "content_digest": sha256(domain.content).hexdigest(),
        },
    ]
    declaration["operations"] = [operation]
    return SourceArtifact("pdf-boundary-operation.json", canonical_bytes(declaration))


def bound_model(domain):
    return compile_data_operations(
        declarations=(declarations(domain),), captured_contracts=native_protocol_sources()
    )


def dependencies(domain):
    return data_operation_dependencies(
        ResolvedDependencies(
            (
                SourceArtifact(CONTRACT, domain.content),
                *domain.sources,
                *native_protocol_sources(),
            )
        ),
        (declarations(domain),),
    )


def altered_domain(domain, *, sources=None, read_version=None):
    content = json.loads(domain.content)
    retained = list(domain.sources if sources is None else sources)
    if read_version is not None:
        content["actions"]["read_pdf_product"]["implementation"]["version"] = read_version
        for index, source in enumerate(retained):
            if source.name == "pdf-domain/native/actions.yaml":
                actions = yaml.safe_load(source.content)
                next(action for action in actions["actions"] if action["id"] == "read_pdf_product")[
                    "implementation"
                ]["version"] = read_version
                retained[index] = SourceArtifact(source.name, yaml.safe_dump(actions).encode())
    content["inputs"] = [{"name": source.name, "sha256": source.digest} for source in retained]
    return PdfDomainContract(canonical_bytes(content), tuple(retained))
