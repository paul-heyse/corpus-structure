"""The actual D1 provider numerical recipe refuses CPU and float32 fallbacks."""

from typing import Any

import pytest


def test_current_d1_configuration_requires_cuda_without_cpu_fallback():
    from corpus_structure.methods.native_profiles import NativeProfile

    profile = NativeProfile(
        provider="d1",
        runtime_identity={},
        artifacts={},
        parameters={},
        dtype="bfloat16",
        backend="d1",
        device="cuda",
    )
    assert profile.device == "cuda" and profile.dtype == "bfloat16"
    with pytest.raises(ValueError, match="numerical recipe"):
        NativeProfile(
            provider="d1",
            runtime_identity={},
            artifacts={},
            parameters={},
            dtype="float32",
            backend="d1",
            device="cuda",
        )


def test_native_d1_cpu_refusal_precedes_model_or_asset_loading(tmp_path):
    from corpus_structure.methods.native_profiles import NativeProfile
    from corpus_structure.methods.pm2_native import _load_d1

    with pytest.raises(ValueError, match="requires CUDA"):
        _load_d1(tmp_path / "no-assets", "cpu")
    with pytest.raises(ValueError, match="CUDA"):
        NativeProfile(
            **dict[str, Any](
                provider="d1",
                runtime_identity={},
                artifacts={},
                parameters={},
                dtype="bfloat16",
                backend="d1",
                device="cpu",
            )
        )
