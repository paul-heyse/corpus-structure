"""Bounded candidate comparison using vendored source and real mathematical kernels."""
from __future__ import annotations
import json
import subprocess
import sys
import time
import types
from collections import Counter
from pathlib import Path

import lark
import yaml
from lark.parsers.earley_forest import ForestToParseTree, ForestVisitor
from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef
from corpus_structure.ingest.html import build_rendition
from corpus_structure.ingest.profile import compile_profile, load_profile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.math import grammar as g
from corpus_structure.methods.math.spans import math_spans

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parents[1] / 'raw'
BASELINE = '38f79f5'
source = subprocess.check_output(['git', 'show', BASELINE + ':python/corpus-structure/src/corpus_structure/methods/math/grammar.py'], text=True)
base = types.ModuleType('corpus_structure.methods.math._probe_baseline')
sys.modules[base.__name__] = base
base.__file__ = str(Path(g.__file__))
exec(compile(source, '<frozen grammar baseline>', 'exec'), base.__dict__)
page = 'siegrist_random/random/special/LocationScale.html'
content = build_rendition((ROOT/'fixtures/trace/corpus'/page).read_bytes(), compile_profile(load_profile('siegrist')), SentenceConfig(), source_uri=page).content
config = yaml.safe_load((ROOT/'domains/statistics/methods.yaml').read_text())['math']
macros = tex.effective_macros(content.macros, {k: MacroDef(body=v) for k,v in config['macros'].items()})
context = g.MathContext(constants=frozenset(config['constants']), definition_rule='function-definition-1')
inputs = [(s.latex, 'any_value', context) for s in math_spans(content)]
for value, declared in [(r'f(x)', 'function'), (r'f(x)', 'variable'), (r'a b / c', None), (r'(0,1)', None), (r'x_{n+1} = x_n + 1', None)]:
    ctx = g.MathContext(functions=frozenset({'f'}) if declared=='function' else frozenset(), variables=frozenset({'f'}) if declared=='variable' else frozenset(), definition_rule='function-definition-1')
    inputs.append((value, 'any_value', ctx))

if '--subset-only' in sys.argv:
    import re
    admission = re.compile(r"[0-9]+(?:\s*[+-]\s*[0-9]+)*")
    eligible = [text for text, kind, ctx in inputs if admission.fullmatch(text.strip())]
    subset = lark.Lark('start: INT (("+" | "-") INT)*\n%import common.INT\n%import common.WS\n%ignore WS', parser='lalr',lexer='contextual',strict=False)
    start=time.perf_counter()
    for text in eligible:
        subset.parse(text)
    subset_result={'strict_mode':'unavailable without optional interegular; not an adopted or qualified backend',
                   'scope':'unsigned integer literals and explicit integer addition/subtraction only',
                   'eligible_inputs':len(eligible),'total_inputs':len(inputs),
                   'examples':eligible[:10], 'recognition_seconds':time.perf_counter()-start,
                   'decision':'not adopted: very narrow local population; typed tree/offset and outcome projection still required; broader subset uniqueness remains open'}
    (OUT/'parser-subset.json').write_text(json.dumps(subset_result,indent=2)+'\n')
    print(json.dumps(subset_result,indent=2))
    raise SystemExit(0)

if '--phases-only' in sys.argv:
    parser = g.parser_for(g.classify(macros))
    original_parse = parser.lark.parse
    clock = [0.0]
    def timed_parse(*args, **kwargs):
        start = time.perf_counter()
        try:
            return original_parse(*args, **kwargs)
        finally:
            clock[0] += time.perf_counter()-start
    parser.lark.parse = timed_parse
    start = time.perf_counter()
    reads = [g._read(text, kind, macros, ctx, 2.0) for text, kind, ctx in inputs]
    total = time.perf_counter()-start
    phases = {'inputs':len(inputs), 'recognition_seconds':clock[0],
              'post_recognition_seconds':total-clock[0], 'total_seconds':total,
              'statuses':dict(Counter(str(r.status) for r in reads)),
              'conditions':'Diagnostic phase clocks; not an unprofiled speedup comparison.'}
    (OUT/'parser-phases.json').write_text(json.dumps(phases,indent=2)+'\n')
    print(json.dumps(phases,indent=2))
    raise SystemExit(0)

class CountForest(ForestVisitor):
    def __init__(self):
        super().__init__(single_visit=True)
        self.nodes = 0
        self.cycles = 0
    def visit_symbol_node_in(self, node):
        self.nodes += 1
        return node.children
    def visit_packed_node_in(self, node):
        self.nodes += 1
        return node.children
    def on_cycle(self, node, path):
        self.cycles += 1

original = g._Resolver
start = time.perf_counter()
g.parser_for(g.classify(macros))
parser_build_seconds = time.perf_counter()-start
results = {'parser_build_seconds':parser_build_seconds}
for name, resolver in [('baseline', base._Resolver), ('summarized', original)]:
    g._Resolver = resolver
    reads = []
    start = time.perf_counter()
    for text, kind, ctx in inputs:
        reads.append(g._read(text, kind, macros, ctx, 2.0))
    elapsed = time.perf_counter()-start
    results[name] = {'seconds':elapsed, 'statuses':dict(Counter(str(r.status) for r in reads)), 'outcomes':[(str(r.status),r.kind,None if r.failure is None else r.failure.category,[(o.name,o.start,o.end) for o in r.occurrences]) for r in reads]}
g._Resolver = original
classes = g.classify(macros)
explicit = g.parser_for(classes)
start = time.perf_counter()
forest = lark.Lark(g.grammar_text(classes), source_path=str(g.SHIPPED), parser='earley', lexer='dynamic', ambiguity='forest', propagate_positions=True, maybe_placeholders=False, keep_all_tokens=True, ordered_sets=True, start=list(g.STARTS), edit_terminals=g.whole_name)
build_seconds = time.perf_counter()-start
recognition = projection = 0.0
counts=[]
for text, kind, _ in inputs:
    try:
        with g.deadline(2):
            start=time.perf_counter(); root=forest.parse(text,start=kind); recognition+=time.perf_counter()-start
            visitor=CountForest(); visitor.visit(root); counts.append((visitor.nodes,visitor.cycles))
            start=time.perf_counter(); ForestToParseTree(callbacks=explicit.lark._callbacks, resolve_ambiguity=False).transform(root); projection+=time.perf_counter()-start
    except (Exception, g.Expired):
        continue
results['forest']={'build_seconds':build_seconds,'recognition_seconds':recognition,'tree_projection_seconds':projection,'successful_inputs':len(counts),'maximum_nodes':max((n for n,c in counts),default=0),'cycles':sum(c for n,c in counts),'qualification':'recognition and projection attribution only; no production adoption'}
try:
    lark.Lark(g.grammar_text(classes),source_path=str(g.SHIPPED),parser='lalr',lexer='contextual',strict=True,start=list(g.STARTS),edit_terminals=g.whole_name)
    results['lalr']={'outcome':'built; unique semantic subset still requires admission'}
except Exception as error:
    results['lalr']={'outcome':'refused','error':str(error)[:1200]}
results['baseline_ref']=BASELINE
results['source']=page
results['inputs']=len(inputs)
results['differences']=[i for i,(a,b) in enumerate(zip(results['baseline']['outcomes'],results['summarized']['outcomes'],strict=True)) if a!=b]
for result in (results['baseline'],results['summarized']):
    result.pop('outcomes')
(OUT/'parser-candidates.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
