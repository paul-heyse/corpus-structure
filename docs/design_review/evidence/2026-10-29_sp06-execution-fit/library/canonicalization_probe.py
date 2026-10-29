"""Cheap correctness probe of the installed LinkML native RDF canonicalization helper."""
import json
import warnings
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

from linkml_runtime.utils.rdf_canonicalize import RDFCanonicalizationWarning, canonicalize_rdf_graph
import rdflib
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import XSD

EX = 'https://example.org/'
graph = Graph()
for index in range(3):
    blank = BNode('local' + str(index))
    graph.add((URIRef(EX + 'root'), URIRef(EX + 'member'), blank))
    graph.add((blank, URIRef(EX + 'label'), Literal('label', datatype=XSD.string)))
graph.add((URIRef(EX + 'root'), URIRef(EX + 'decimal'), Literal('1.2300', datatype=XSD.decimal, normalize=False)))
graph.add((URIRef(EX + 'root'), URIRef(EX + 'integer'), Literal('01', datatype=XSD.integer, normalize=False)))
started = perf_counter()
first = canonicalize_rdf_graph(graph, output_format='nt')
elapsed = perf_counter() - started
second = canonicalize_rdf_graph(graph, output_format='nt')
original_normalization = rdflib.NORMALIZE_LITERALS
rdflib.NORMALIZE_LITERALS = False
try:
    roundtrip = Graph().parse(data=first, format='nt')
finally:
    rdflib.NORMALIZE_LITERALS = original_normalization
normalized = Graph()
for subject, predicate, obj in graph:
    if isinstance(obj, Literal) and obj.datatype == XSD.string:
        obj = Literal(str(obj))
    normalized.add((subject, predicate, obj))
nonstandard = Graph()
nonstandard.add((URIRef('relative'), URIRef(EX + 'p'), Literal('x')))
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always', RDFCanonicalizationWarning)
    fallback = canonicalize_rdf_graph(nonstandard, output_format='nt')
report = {
    'versions': {name: version(name) for name in ('linkml-runtime', 'linkml', 'pyoxigraph', 'rdflib')},
    'native_seconds_tiny_graph': elapsed,
    'deterministic_repeat': first == second,
    'raw_rdflib_isomorphic': isomorphic(graph, roundtrip),
    'rdf11_normalized_isomorphic': isomorphic(normalized, roundtrip),
    'input_triples': len(graph), 'output_triples': len(roundtrip),
    'decimal_literals': sorted(str(o) for o in roundtrip.objects(URIRef(EX + 'root'), URIRef(EX + 'decimal'))),
    'integer_literal_lexical_from_output': [line for line in first.splitlines() if EX + 'integer' in line],
    'relative_iri_warning': [str(w.message) for w in caught],
    'fallback_preserves_relative': '<relative>' in fallback,
}
(Path(__file__).resolve().parents[1] / 'raw' / 'canonicalization_probe.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
