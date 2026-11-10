from types import SimpleNamespace

import pytest

from corpus_structure.semantic.types import VocabularyMember, VocabularySnapshot
from corpus_structure.semantic.vocabulary_impact import append_vocabulary_impact, vocabulary_facets


def release(*, label="normal", meaning="STATO:0000227", source="a", status="available"):
    return SimpleNamespace(
        release_id="release:example",
        vocabularies=(
            VocabularySnapshot(
                "Family",
                (VocabularyMember("normal", meaning, label),),
                "captured",
                dependency_digest=source,
            ),
        ),
        vocabulary_metadata=dict(
            status=status,
            reason="missing metadata",
            sources={"stato": {"digest": source}},
            enums={
                "Family": dict(
                    fields=[dict(class_name="Fields", property="family")],
                    unchecked=[],
                    members=[
                        dict(
                            value="normal",
                            meaning=meaning,
                            label=label,
                            definitions=["Distribution definition"],
                            status="checked",
                        )
                    ],
                )
            },
        ),
    )


def changes(before, after):
    rows, unknowns = [], set()
    append_vocabulary_impact(
        before, after, rows, unknowns, lambda a, b, p: [dict(path=p, before=a, after=b)], object()
    )
    return rows, unknowns


def test_label_change_does_not_change_admitted_member_meaning():
    rows, unknowns = changes(release(), release(label="Normal distribution"))
    assert "vocabulary_membership" not in {r["aspect"] for r in rows}
    assert "vocabulary_metadata" in {r["aspect"] for r in rows}
    assert next(r for r in rows if r["aspect"] == "vocabulary_metadata")["consumers"] == [
        "Fields.family"
    ]
    assert any("not surveyed" in u for u in unknowns)


def test_meaning_change_and_source_only_change_are_separate():
    rows, _ = changes(release(), release(meaning="STATO:other"))
    assert "vocabulary_membership" in {r["aspect"] for r in rows}
    rows, _ = changes(release(), release(source="b"))
    assert {r["aspect"] for r in rows} == {"vocabulary_sources", "vocabulary_source_profiles"}


def test_missing_historical_detail_does_not_invent_metadata_removal():
    rows, unknowns = changes(release(), release(status="unavailable"))
    assert not rows
    assert any("unavailable" in u for u in unknowns)


def test_corrupt_metadata_refuses_and_unchanged_needs_no_use_survey():
    from corpus_structure.semantic.releases import ReleaseConflict

    with pytest.raises(ReleaseConflict, match="missing metadata"):
        vocabulary_facets(release(status="corrupt"))
    assert changes(release(), release()) == ([], set())
