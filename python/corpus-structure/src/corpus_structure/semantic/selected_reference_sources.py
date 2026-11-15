"""Acquire the closed protected reference schema and its original snapshot callable."""

from pathlib import Path

import yaml

from .python_operation_sources import PythonSource, PythonSourceCollection
from .types import SourceArtifact, SourceBundle

_ROOT = Path(__file__).parents[1]
_MODEL = _ROOT / "model/semantic/data-operation-assessment.yaml"


def selected_reference_inputs(bundle: SourceBundle) -> SourceBundle:
    from .data_product_reference import reference_inputs

    bundle = reference_inputs(bundle)
    name, root = "data_operation_assessment", "data_operation_assessment_root"
    existing = {source.name: source.content for source in bundle.sources}
    if name in existing:
        if existing[name] != _MODEL.read_bytes():
            raise ValueError("selected reference schema differs from its acquired owner")
        return bundle
    if root in existing:
        raise ValueError("selected reference schema uses its reserved root")
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact(name, _MODEL.read_bytes()),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    dict(
                        id="urn:corpus:selected-reference-root",
                        name=root,
                        imports=[bundle.root, name],
                    )
                ).encode(),
            ),
        ),
    )


def selected_reference_operation_sources():
    name = "methods/selected_reference.py"
    path = _ROOT / name
    return PythonSourceCollection(
        (
            PythonSource(
                "corpus_structure.methods.selected_reference",
                path.read_bytes(),
                str(path.resolve()),
            ),
        )
    )
