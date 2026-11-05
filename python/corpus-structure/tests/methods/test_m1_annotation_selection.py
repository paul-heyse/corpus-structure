"""Annotation selection authenticates one declared view before source hydration."""

from types import SimpleNamespace

import pytest

from corpus_structure.methods.m1_annotations import M1AnnotationConfig, M1Annotations


def view(identity, digest, *, eligible=True):
    return SimpleNamespace(
        id=identity,
        key=f"source:{identity}",
        projection_digest=digest,
        analysis_eligible=eligible,
    )


def run(*views):
    def hydrate(_):
        raise AssertionError("selection must use source metadata without hydration")

    return SimpleNamespace(
        reader=SimpleNamespace(
            source_views=lambda: views,
            source_view=hydrate,
        )
    )


def test_annotation_projection_selects_one_eligible_view():
    selected = M1Annotations().select(
        run(view(1, "b" * 64), view(2, "a" * 64), view(3, "a" * 64, eligible=False)),
        M1AnnotationConfig(source_projection_digest="a" * 64),
    )
    assert [(unit.unit_id, unit.unit_key) for unit in selected] == [(2, "source:2")]


@pytest.mark.parametrize(
    "views",
    [
        (),
        (view(1, "b" * 64),),
        (view(1, "a" * 64), view(2, "a" * 64)),
        (view(1, "a" * 64, eligible=False),),
    ],
)
def test_annotation_projection_refuses_missing_or_ambiguous_view(views):
    with pytest.raises(ValueError, match="exactly one eligible source view"):
        M1Annotations().select(run(*views), M1AnnotationConfig(source_projection_digest="a" * 64))


def test_default_annotation_selection_preserves_eligible_population():
    selected = M1Annotations().select(
        run(view(1, "a" * 64), view(2, "b" * 64, eligible=False), view(3, "c" * 64)),
        M1AnnotationConfig(),
    )
    assert [unit.unit_id for unit in selected] == [1, 3]
