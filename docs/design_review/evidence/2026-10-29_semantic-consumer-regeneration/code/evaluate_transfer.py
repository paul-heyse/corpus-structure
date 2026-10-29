"""Grade a real completed transfer run against the independently authored source fixture."""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from corpus_structure.core.evidence import RenditionContent, SegmentKind
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.evaluate.semantic import create_reference_set, record_pass, reference_evaluate, split_documents
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.proposals import ProposalFrame, ProposalSentence
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parents[5]
PROJECT = 'semantic-pivot-transfer'
RUN = 2
fixture = ROOT / 'fixtures/toy/semantic-inspection-reference.json'
authored = fixture.read_bytes()
batch = json.loads(authored)
with open_runtime_engine(Settings(), 'ci-regeneration-reference', purpose='evaluate') as engine:
    with engine.begin() as conn:
        split_documents(conn, PROJECT)
        documents = table('kb.document')
        split = table('eval.document_split')
        assigned = conn.execute(select(split.c.split).join(documents, split.c.source_uri == documents.c.source_uri)
                                .where(split.c.project_id == PROJECT, documents.c.project_id == PROJECT,
                                       documents.c.meta['page'].astext == 'inspection.html')).scalar_one()
        reference = create_reference_set(conn, project_id=PROJECT, source_run_id=RUN,
                                         label='inspection-independent-v1', split=assigned,
                                         size=1, forced=(batch['unit_ref'],))
        uid = reference['units'][batch['unit_ref']]
        units, renditions = table('eval.reference_unit'), table('kb.rendition')
        source = conn.execute(select(renditions).join(units, units.c.rendition_id == renditions.c.id)
                              .where(units.c.id == uid)).mappings().one()
        content = RenditionContent.model_validate(source['content'])
        index = LocatorIndex(content, 'inspection.html')
        sentences = []
        for citation in batch['claims'][0]['evidence']:
            matches = [(segment, locator) for segment, locator in index
                       if segment.kind == SegmentKind.SENTENCE
                       and content.canonical_text[segment.start:segment.end] == citation['quote']]
            assert len(matches) == 1, 'expected reference quotation must independently locate exactly one sentence'
            segment, locator = matches[0]
            sentences.append(ProposalSentence(citation['sentence'], str(locator), segment.start, segment.end))
        frame = ProposalFrame(batch['unit_ref'], content.canonical_text, tuple(sentences))
        record_pass(conn, unit_id=uid, pass_kind='C', actor='automated-independent-fixture', authored=authored, frame=frame)
        grade = reference_evaluate(conn, project_id=PROJECT, run_id=RUN, set_id=reference['set_id'])
        print(grade.model_dump_json())
