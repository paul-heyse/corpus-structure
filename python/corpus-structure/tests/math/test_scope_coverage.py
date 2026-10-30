"""Unknown scope prerequisites stay explicit in producer and actual packet boundaries."""

from dataclasses import replace
import json
from types import SimpleNamespace
from typing import Literal

import pytest

from corpus_structure.core.evidence import RenditionContent, Segment
from corpus_structure.core.method import CoverageDraft, SourceCoverageReading
from corpus_structure.core.values import Formula, SymbolBinding
from corpus_structure.core.vocab import BindKind, ParseOutcome, ScopeExtent, SegmentKind
from corpus_structure.methods.llm import packet as packets
from corpus_structure.methods.math.scope import BindingSite, Scope, scope_coverage
from corpus_structure.methods.math.spans import SpanValue, SymbolMention
from corpus_structure.semantic.proposals import ProposalFrame, ProposalPacket


def source(math=True):
    node = Segment(kind=SegmentKind.MATH_INLINE, start=4, end=5)
    sentence = Segment(kind=SegmentKind.SENTENCE, start=0, end=6,
                       children=(node,) if math else ())
    paragraph = Segment(kind=SegmentKind.PARAGRAPH, start=0, end=6, children=(sentence,))
    unit = Segment(kind=SegmentKind.UNIT, start=0, end=6, attrs={"id":"u"}, children=(paragraph,))
    content = RenditionContent(canonical_text="Let x.", document=Segment(
        kind=SegmentKind.DOCUMENT, start=0, end=6, children=(unit,)))
    mention = SymbolMention(node, 4, 5, "x", "x", None, None, False, None)
    value = SpanValue(node, Formula(t="formula", latex="x", parse=ParseOutcome.OK,
        symbols={"x":SymbolBinding(bind=BindKind.UNRESOLVED)}), "formula", None)
    site = BindingSite(mention, "x", sentence, ScopeExtent.STATEMENT, unit, 0, 6, ("initial",), False)
    return content, unit, mention, value, Scope(mention, "x", site)


@pytest.mark.parametrize("parse,outcome", [(ParseOutcome.AMBIGUOUS,"partial"),
    (ParseOutcome.PARTIAL,"partial"), (ParseOutcome.FAILED,"unknown")])
def test_unavailable_or_ambiguous_interpretation_cannot_be_complete_scope(parse, outcome):
    content, _, mention, value, scope = source()
    value = replace(value, value=value.value.model_copy(update={"parse":parse}))
    (coverage,) = scope_coverage(content, [value], [mention], [scope])
    assert coverage.outcome == outcome
    assert coverage.reason


def test_required_unresolved_binding_and_missing_values_are_not_empty_absence():
    content, _, mention, value, scope = source()
    assert scope_coverage(content, [value], [mention], [replace(scope, site=None)])[0].outcome == "partial"
    assert scope_coverage(content, [], [mention], [scope])[0].outcome == "unknown"
    assert scope_coverage(content, [value], [], [])[0].outcome == "unknown"
    assert scope_coverage(content, [value], [mention], [scope])[0].outcome == "complete"
    unsupported = replace(value, parse_error="unknown-command",
                          value=value.value.model_copy(update={"parse":ParseOutcome.FAILED}))
    assert scope_coverage(content, [unsupported], [mention], [])[0].outcome == "unsupported"


def recorded(outcome: Literal["complete", "partial", "unknown", "unsupported"]="partial", task=7):
    return SourceCoverageReading(CoverageDraft(family="resolve.symbol_scope", scope="span-x",
        outcome=outcome, reason=None if outcome == "complete" else "required symbol binding unresolved"),
        task, "release", 0, 4, 5)


def test_packet_retains_nonblocking_uncertainty_and_hashes_origin_basis():
    content, unit, *_ = source()
    first = packets._CoverageIndex.prepare(content, [recorded()]).for_unit("page#u", [unit], [])
    second = packets._CoverageIndex.prepare(content, [recorded(task=8)]).for_unit("page#u", [unit], [])
    a = packets.render(content, "page", "page#u", [unit], [], source_coverage=first)
    b = packets.render(content, "page", "page#u", [unit], [], source_coverage=second)
    assert "no established context; scope coverage partial" in a.parts[0]
    assert a.parts == b.parts
    assert a.hash != b.hash
    assert first.source_tasks == ((7,"release"),)
    frame = ProposalFrame("page#u", content.canonical_text, ())
    proposal = ProposalPacket("release", frame, b"{}", "guide", b"{}", source_coverage=first)
    other = replace(proposal, source_coverage=second)
    assert proposal.hash != other.hash
    data = json.loads(next(part.text for part in proposal.parts() if part.name == "unit"))
    assert data["source_coverage"]["coverage"]["outcome"] == "partial"
    assert "rows" not in data["source_coverage"]
    assert len(json.dumps(data["source_coverage"])) < 500


def test_missing_source_scope_coverage_is_unknown_only_when_math_is_required():
    content, unit, *_ = source()
    unknown = packets._CoverageIndex.prepare(content, []).for_unit("page#u", [unit], [])
    assert unknown.coverage.outcome == "unknown"
    empty, plain, *_ = source(math=False)
    complete = packets._CoverageIndex.prepare(empty, []).for_unit("page#u", [plain], [])
    assert complete.coverage.outcome == "complete"


def test_packet_preparation_reads_scope_coverage_once_per_rendition():
    content, *_ = source()
    calls = []
    def read_coverage(*args):
        calls.append(args)
        return (recorded(),)
    reader = SimpleNamespace(content=lambda rid:content, observations=lambda *a:(),
                             source_coverage=read_coverage)
    preparation = {}
    first = packets.unit_inputs(reader, rendition_id=1, document_id=None, unit_key="page#u",
        reference_run_id=None, pack_macros={}, golden=True, preparation=preparation)
    second = packets.unit_inputs(reader, rendition_id=1, document_id=None, unit_key="page#u",
        reference_run_id=None, pack_macros={}, golden=True, preparation=preparation)
    assert first.source_coverage == second.source_coverage
    assert first.source_coverage is not None
    assert first.source_coverage.coverage.outcome == "partial"
    assert len(calls) == 1


def test_scope_method_preserves_empty_unresolved_as_partial_coverage(monkeypatch, tmp_path):
    import logging
    from corpus_structure.core.method import MethodContext, MethodSettings, UnitRef, UnitView
    from corpus_structure.core.payloads import MentionRef
    from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.math import methods
    from corpus_structure.methods.math.scope import Binders

    content, _, mention, value, scope = source()
    ren = methods._Rendition(1, "rendition", "digest", content, {})
    stored = methods.StoredMath([mention], [], [value], {id(mention):MentionRef(task=7,ordinal=0)}, {})
    upstream = SourceCoverageReading(CoverageDraft(family=methods.M09,
        scope=ren.key_of(mention.segment), outcome="complete"), 7,"release",0,4,5)
    reader = SimpleNamespace(source_coverage=lambda *a:(upstream,))
    monkeypatch.setattr(methods, "_rendition", lambda *a:ren)
    monkeypatch.setattr(methods, "stored_math", lambda *a:stored)
    monkeypatch.setattr(methods, "resolve_scopes", lambda *a, **kw:[replace(scope, site=None)])
    unit = UnitView(UnitRef(TaskUnitType.RENDITION,1,"page"), SimpleNamespace())
    cfg = methods.SymbolScopeConfig(binders=Binders(sentence_initial=("let",)), sentences=SentenceConfig())
    result, = methods.SymbolScope().run([unit], cfg, MethodContext(unit.run,reader,
        MethodSettings(data_dir=tmp_path,model_cache=tmp_path/"models"),logging.getLogger(__name__)))
    assert result.outcome is ObservationOutcome.EMPTY
    assert result.coverage[0].family == methods.M13
    assert result.coverage[0].outcome == "partial"
    assert result.coverage[0].reason is not None
    assert "unresolved" in result.coverage[0].reason
