"""Bounded production-layout and segmentation comparison; run from repository root."""
import json
import statistics
import time
from pathlib import Path

import spacy
from pydantic import TypeAdapter

from corpus_structure.core.vocab import SegmentKind
from corpus_structure.ingest.html import build_rendition
from corpus_structure.ingest.profile import load_profile
from corpus_structure.ingest.sentences import (
    SentenceConfig, TextLayout, boundaries, make_doc, pipeline, prepare_layout,
)
from corpus_structure.methods.math.scope import segment_block


def timed(fn, repeats=3):
    samples = []
    result = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = fn()
        samples.append(time.perf_counter() - start)
    return result, statistics.median(samples)


def main():
    cfg = SentenceConfig()
    nlp = pipeline(cfg)
    pages = []
    for name in ('LocationScale', 'Normal', 'LogNormal', 'Gamma'):
        uri = f'siegrist_random/random/special/{name}.html'
        pages.append(build_rendition((Path('fixtures/trace/corpus') / uri).read_bytes(),
                                    load_profile('siegrist'), cfg, source_uri=uri))
    layouts = []
    blocks = []
    stored = []
    for page in pages:
        for segment in page.content.document.walk():
            sentences = [c for c in segment.children if c.kind is SegmentKind.SENTENCE]
            if sentences:
                block = segment_block(page.content, segment)
                blocks.append(block)
                layouts.append(prepare_layout(nlp, block, start=segment.start))
                stored.append([(s.start-segment.start, s.end-segment.start) for s in sentences])
    assert len(blocks) == len(layouts)
    def cold_docs():
        return [make_doc(nlp, block) for block in blocks]
    def reused_docs():
        return [make_doc(nlp, block, layout, start=layout.block_start)
                for block, layout in zip(blocks, layouts, strict=True)]
    adapter = TypeAdapter(tuple[TextLayout, ...])
    payload, serialize_s = timed(lambda: adapter.dump_json(tuple(layouts)))
    _, deserialize_s = timed(lambda: adapter.validate_json(payload))
    _, cold_s = timed(cold_docs)
    _, rebuild_s = timed(reused_docs)
    variants = {'current': nlp,
                'parser-reduced': spacy.load(cfg.model, exclude=['ner', 'lemmatizer', 'tagger', 'attribute_ruler', 'senter']),
                'senter': spacy.load(cfg.model, exclude=['ner', 'lemmatizer', 'tagger', 'attribute_ruler', 'parser', 'tok2vec'])}
    variants['senter'].enable_pipe('senter')
    rule = spacy.blank('en')
    rule.add_pipe('sentencizer', config={'overwrite': False})
    variants['rule'] = rule
    comparisons = {}
    for name, candidate in variants.items():
        def run():
            docs = (make_doc(candidate, block, layout, start=layout.block_start)
                    for block, layout in zip(blocks, layouts, strict=True))
            return [boundaries(block, doc) for block, doc in zip(blocks, candidate.pipe(docs), strict=True)]
        actual, seconds = timed(run)
        comparisons[name] = {'pipeline': candidate.pipe_names,
                             'component_problems': candidate.analyze_pipes(pretty=False)['problems'],
                             'seconds_median': seconds,
                             'blocks_differing_from_stored': sum(a != b for a, b in zip(actual, stored, strict=True))}
    print(json.dumps({'pages': 4, 'blocks': len(blocks), 'tokens': sum(len(x.tokens) for x in layouts),
                      'layout_json_bytes': len(payload), 'tokenize_and_rebuild_seconds': cold_s,
                      'serialize_seconds': serialize_s, 'deserialize_seconds': deserialize_s,
                      'prepared_rebuild_seconds': rebuild_s, 'segmentation': comparisons}, indent=2))


if __name__ == '__main__':
    main()
