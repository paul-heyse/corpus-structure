"""Capture the score kernel's selected libraries and actual numerical contract."""

from __future__ import annotations

import inspect
import sys
from importlib.metadata import version
from pathlib import Path

from .data_operation_model import MODEL_VERSION
from .identity import canonical_bytes
from .nominal_schema_kinds import nominal_schema_kinds
from .operation_policy import (
    OperationEventAlgorithm,
    OperationEventParameters,
    OperationScoreNumericalPolicy,
    operation_score_numerical_policy,
)
from .python_operation_sources import PythonSource, PythonSourceCollection
from .types import SourceArtifact


def operation_score_inputs() -> tuple[SourceArtifact, ...]:
    """The actual Pydantic parameter schema is the closed nominal body authority."""
    return (
        SourceArtifact(
            "operation-score/parameter-kinds",
            canonical_bytes(
                {
                    "version": MODEL_VERSION,
                    "kinds": nominal_schema_kinds(
                        OperationEventParameters.model_json_schema(),
                        namespace="urn:corpus:kind:operation-event:",
                        root_name="parameters",
                    ),
                    "operations": [],
                }
            ),
        ),
    )


def operation_score_sources() -> PythonSourceCollection:
    policy = operation_score_numerical_policy()
    path = Path(__file__).with_name("operation_policy.py")
    return PythonSourceCollection(
        (PythonSource("corpus_structure.semantic.operation_policy", path.read_bytes(), str(path)),),
        boundary_contracts=(
            SourceArtifact(
                "operation-score/numerical-policy",
                canonical_bytes(
                    {
                        "policy": policy.model_dump(mode="json"),
                        "factory": inspect.getsource(operation_score_numerical_policy),
                        "type": inspect.getsource(OperationScoreNumericalPolicy),
                    }
                ),
            ),
            SourceArtifact(
                "numpy-float64-array-arithmetic-v1",
                canonical_bytes(
                    {
                        "policy": policy.model_dump(mode="json"),
                        "operations": ["asarray", "dot", "isfinite", "errstate"],
                    }
                ),
            ),
            SourceArtifact(
                "scipy-expit-v1",
                canonical_bytes(
                    {"scipy": policy.scipy_version, "operation": "scipy.special.expit"}
                ),
            ),
            SourceArtifact(
                "pydantic2-operation-event-ingress-v1",
                canonical_bytes(
                    {
                        "pydantic": version("pydantic"),
                        "classes": {
                            cls.__name__: inspect.getsource(cls)
                            for cls in (
                                OperationEventAlgorithm,
                                OperationEventParameters,
                                OperationScoreNumericalPolicy,
                            )
                        },
                    }
                ),
            ),
            SourceArtifact(
                "python-3.14-typing-v1",
                canonical_bytes(
                    {"python": sys.version.split()[0], "interpretation": "python-typing"}
                ),
            ),
        ),
    )
