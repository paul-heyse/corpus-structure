"""PE-S28 actual CPU encoders on book text; no DDO publication/ranking claim."""

import json
import math
from dataclasses import asdict, dataclass

import pytest

from corpus_structure.methods.contextual_embeddings import QWEN, encode_contexts, validate_vector
from corpus_structure.semantic.contextual_encoder import ContextualEncoderSelection
from semantic.actual_e5_support import acquire_e5
from semantic.provider_book_panel_support import QWEN_SNAPSHOT, book_panel, encoder_items, panel_release

pytestmark = [pytest.mark.provider_evidence, pytest.mark.prerequisite("provider_book_panel")]


@dataclass(frozen=True)
class EncoderObservation:
    grouping: str
    object_id: str
    role: str
    vector_id: str
    norm: float
    singleton_cosine: float
    nearest_singleton: str
    max_absolute_deviation: float


def _cosine(left, right):
    return math.fsum(a * b for a, b in zip(left, right, strict=True)) / math.sqrt(
        math.fsum(a * a for a in left) * math.fsum(b * b for b in right)
    )


@pytest.mark.parametrize("name", [
    pytest.param("e5", marks=pytest.mark.prerequisite("contextual_e5_snapshot")),
    pytest.param("qwen", marks=pytest.mark.prerequisite("contextual_qwen_snapshot")),
])
def test_actual_book_encoder_cohorts_preserve_identity_attribution_and_normalization(name, request):
    panel = book_panel(panel_release())
    items = encoder_items(panel)
    selected = acquire_e5() if name == "e5" else ContextualEncoderSelection.acquire(QWEN, QWEN_SNAPSHOT)
    profile = selected.profile

    def encode(population):
        result = encode_contexts(
            population, profile, model_path=str(selected.model_path),
            artifact_hashes=selected.artifacts, check_active=lambda: None,
        )
        assert not result.limited_query_ids
        assert len(result.vectors) == len(population)
        return result.vectors

    singleton = {item.object_id: encode((item,))[0] for item in items}
    roles = {item.object_id: item.role for item in items}
    queries = tuple(item for item in items if item.role == "query")
    targets = tuple(item for item in items if item.role == "document")
    groupings = {
        "mixed": (items,),
        "reversed": (tuple(reversed(items)),),
        "regrouped-2+1-per-role": (queries[:2] + targets[:2], queries[2:] + targets[2:]),
    }
    observations = []
    for baseline in singleton.values():
        actual = validate_vector(baseline.values, profile.dimension)
        observations.append(EncoderObservation(
            "singleton", baseline.object_id, roles[baseline.object_id], baseline.vector_id,
            math.sqrt(math.fsum(value * value for value in actual)),
            _cosine(actual, actual), baseline.object_id, 0.0,
        ))
    request.node.user_properties.append(("provider_panel_scope", "actual CPU encoder mechanism; no DDO publication or ranking qualification"))
    request.node.user_properties.append(("provider_panel_sources", json.dumps([
        dict(path=entry.path, original_sha256=entry.original_digest, selector=entry.selector)
        for entry in panel[:3]
    ], sort_keys=True)))
    try:
        for grouping, batches in groupings.items():
            values = [vector for batch in batches for vector in encode(batch)]
            assert {vector.object_id for vector in values} == set(singleton)
            assert len(values) == len(singleton)
            for vector in values:
                baseline = singleton[vector.object_id]
                assert {key: value for key, value in asdict(vector).items() if key != "values"} == {
                    key: value for key, value in asdict(baseline).items() if key != "values"
                }
                actual = validate_vector(vector.values, profile.dimension)
                same_role = {key: candidate for key, candidate in singleton.items() if roles[key] == roles[vector.object_id]}
                similarities = {key: _cosine(actual, candidate.values) for key, candidate in same_role.items()}
                nearest = max(similarities, key=similarities.__getitem__)
                norm = math.sqrt(math.fsum(value * value for value in actual))
                observations.append(EncoderObservation(
                    grouping, vector.object_id, roles[vector.object_id], vector.vector_id, norm,
                    similarities[vector.object_id], nearest,
                    max(abs(a - b) for a, b in zip(actual, baseline.values, strict=True)),
                ))
                # Attribution is relative to these distinct panel members, not a
                # promise about downstream ranking or byte equality across cohorts.
                assert nearest == vector.object_id, observations[-1]
    finally:
        request.node.user_properties.append(("encoder_cohort_observations", json.dumps(dict(
            version="pe-s28-book-panel-v1", profile=asdict(profile), profile_id=profile.profile_id,
            observations=[asdict(value) for value in observations],
        ), sort_keys=True)))
