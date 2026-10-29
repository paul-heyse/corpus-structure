"""Parallel source readings retain independent reference identity at identical offsets."""

from types import SimpleNamespace
from typing import Any

from corpus_structure.core.evidence import RenditionContent, Segment, segment_key
from corpus_structure.core.payloads import MentionPayload
from corpus_structure.core.vocab import (
    ObservationKind,
    ObservationOutcome,
    ScopeExtent,
    SegmentKind,
)
from corpus_structure.methods.llm.packet import stored_bound_scopes
from corpus_structure.methods.math.methods import _Rendition, scope_drafts, stored_math
from corpus_structure.methods.math.scope import BindingSite, Scope
from corpus_structure.semantic.operations import SourceObservationView


def test_parallel_same_span_readings_remain_separately_addressed():
    math = Segment(kind=SegmentKind.MATH_INLINE, start=0, end=5)
    sentence = Segment(kind=SegmentKind.SENTENCE, start=0, end=5, children=(math,))
    document = Segment(kind=SegmentKind.DOCUMENT, start=0, end=5, children=(sentence,))
    content = RenditionContent(canonical_text=r"\(x\)", document=document)
    key = "ren:" + "0" * 32
    skey = segment_key(key, SegmentKind.MATH_INLINE, 0, 5)
    ren = _Rendition(1, key, "digest", content, {skey: 7})

    def report(task, key, sub):
        p = MentionPayload(
            label="symbol",
            text="x",
            start=2,
            end=3,
            math_ref=skey,
            math={"name": "x", "base": "x", "constant": False, "in_subscript_of": sub},
        )
        return SourceObservationView(
            id=task,
            task_id=task,
            kind=ObservationKind.MENTION,
            rendition_id=1,
            segment_id=7,
            span_id=8,
            payload=p.model_dump(mode="json"),
            payload_hash=key,
            score=None,
            outcome=ObservationOutcome.PRODUCED,
            observation_key=key,
            release_id="r",
        )

    a, b = report(11, "observation:a", None), report(22, "observation:b", "outer")
    reader: Any = SimpleNamespace(
        observations=lambda _, __, kind: [a, b] if kind == ObservationKind.MENTION else []
    )
    stored = stored_math(reader, ren)
    assert len(stored.refs) == 2
    assert set(stored.source_refs.values()) == {"observation:a", "observation:b"}
    site = BindingSite(
        stored.mentions[0],
        "x",
        sentence,
        ScopeExtent.STATEMENT,
        document,
        0,
        5,
        ("initial",),
        False,
    )
    scopes = [Scope(mention, "x", site) for mention in stored.mentions]
    drafts = scope_drafts(ren, scopes, stored.refs, stored.source_refs)
    assert [d.payload.mention_ref.task for d in drafts] == [11, 22]
    assert [[r.observation_key for r in d.input_refs if r.role == "mention"] for d in drafts] == [
        ["observation:a"],
        ["observation:b"],
    ]
    rows = [
        SourceObservationView(
            id=30 + i,
            task_id=30,
            kind=ObservationKind.SCOPE,
            rendition_id=1,
            segment_id=7,
            span_id=8,
            payload=d.payload.model_dump(mode="json"),
            payload_hash="scope",
            score=None,
            outcome=ObservationOutcome.PRODUCED,
            observation_key="scope:" + str(i),
            release_id="r",
            input_refs=d.input_refs,
        )
        for i, d in enumerate(drafts)
    ]
    views = stored_bound_scopes(content, [a, b], rows, {})
    assert [v.mention.in_subscript_of for v in views] == [None, "outer"]
