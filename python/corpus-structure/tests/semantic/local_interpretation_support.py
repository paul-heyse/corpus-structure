"""Shared controlled inputs and builders for local interpretation support."""

from math import log

from corpus_structure.semantic import record_interpretation as ri


def local_request():
    return ri.LocalInterpretationRequest(
        decisions=(
            ri.Decision("role", (ri.Candidate("actor"), ri.Candidate("object"))),
            ri.Decision("target", (ri.Candidate("first"), ri.Candidate("second"))),
        ),
        potentials=(
            ri.LogPotential(
                "joint", ("role", "target"), tuple(map(log, (1, 2, 3, 4))), ("source",)
            ),
        ),
        constraints=(),
        dependencies=tuple(
            ri.Dependency(key, kind, "v1")
            for key, kind in (
                ("model", ri.DependencyKind.MODEL),
                ("ontology", ri.DependencyKind.ONTOLOGY),
                ("policy", ri.DependencyKind.POLICY),
                ("source", ri.DependencyKind.OBSERVATION),
            )
        ),
        selection=ri.CandidateSelection("clause", ("source",)),
        model_dependency_id="model",
        ontology_dependency_id="ontology",
        policy_dependency_id="policy",
    )
