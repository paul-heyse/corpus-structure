"""Independent semantic matching expectations; no published expected results are reused."""
import copy
from decimal import Decimal
from dataclasses import dataclass
from typing import Any
from corpus_structure.semantic.types import ClassDefinition,PropertyDefinition,PreparedArtifact,RegistryRow
from corpus_structure.evaluate.semantic_alignment import SemanticSide,align_semantic,equivalent

@dataclass
class AlignmentFixture:
    definitions:tuple[ClassDefinition,...]
    registry_rows:tuple[RegistryRow,...]=()
    artifacts:tuple[PreparedArtifact,...]=()

P='https://example.org/Person';NAME='https://example.org/name'
def prepared():
    entity=ClassDefinition('Entity','https://example.org/Entity',(),(),('id',),(('id',),))
    person=ClassDefinition('Person',P,('Entity',),(),('id',),(('id',),))
    return AlignmentFixture((entity,person))

def batch(label='Alice',polarity=True,evidence=True)->dict[str,Any]:
    return {'entities':[{'id':'p','class_iri':P,'label':label}], 'claims':[{'id':'c','subject':'p','predicate':NAME,'object':{'kind':'text','text':'Alice'},'qualification':{'modality':'asserted','polarity':polarity},'establishment':'stated','evidence':[{'role':'primary','outcome':'located','start':0,'end':5}] if evidence else []}]}

def side(value,**kwargs):return SemanticSide('source#unit',value,**kwargs)

def test_canonical_qualifications_and_evidence_have_separate_scoring_tiers():
    a,b=batch(),batch(polarity=False)
    alignment=align_semantic(side(a),side(b),prepared())
    assert alignment.counts['core'].matched==1
    assert alignment.counts['full'].matched==0
    assert alignment.counts['evidence'].matched==0
    b=batch(evidence=False)
    alignment=align_semantic(side(a),side(b),prepared())
    assert alignment.counts['full'].matched==1
    assert alignment.counts['evidence'].matched==0

def test_duplicate_supports_cannot_inflate_a_fact_and_context_is_uncounted():
    a=batch();b=batch();duplicate=copy.deepcopy(b['claims'][0]);duplicate['id']='duplicate';duplicate['evidence']=[{'role':'primary','outcome':'located','start':1,'end':5}];b['claims'].append(duplicate)
    got=align_semantic(side(a),side(b),prepared())
    assert got.counts['full'].as_dict()=={'reference':1,'prediction':1,'matched':1,'precision':1.,'recall':1.,'f1':1.}
    got=align_semantic(side(a,context=frozenset({'c'})),side(b),prepared())
    assert got.counts['core'].reference==0 and got.counts['core'].matched==0

def test_ambiguous_labels_refuse_alignment_and_known_identity_disambiguates():
    a,b=batch(),batch();b['entities'].append({'id':'other','class_iri':P,'label':'Alice'})
    ambiguous=align_semantic(side(a),side(b),prepared())
    assert ambiguous.counts['core'].matched==0
    assert ambiguous.undecided[0]['reason']=='ambiguous label/anchor assignment'
    matched=align_semantic(side(a,known_ids={'p':'known:first'}),side(b,known_ids={'p':'known:first','other':'known:other'}),prepared())
    assert matched.counts['core'].matched==1

def test_alias_normalization_requires_class_compatibility():
    from corpus_structure.semantic.domain_operations import RULE_INPUT
    p=prepared();p.artifacts=(PreparedArtifact(RULE_INPUT,b'identity:\n  aliases:\n    articles: [the]\nrules: []\n'),)
    a,b=batch('The Alice'),batch('Alice')
    got=align_semantic(side(a),side(b),p)
    assert got.entity_pairs==[('p','p','alias_normalization')]
    b['entities'][0]['class_iri']='https://example.org/Incompatible'
    assert align_semantic(side(a),side(b),p).entity_pairs==[]

def test_alternative_readings_are_one_scoring_item():
    a,b=batch(),batch();other=copy.deepcopy(a['claims'][0]);other['id']='c2';other['object']={'kind':'text','text':'Alison'};a['claims'].append(other);a['alternatives']=[{'id':'alternative','members':['c','c2']}]
    result=align_semantic(side(a),side(b),prepared())
    assert result.counts['core'].as_dict()=={'reference':1,'prediction':1,'matched':1,'precision':1.,'recall':1.,'f1':1.}

def test_decimal_quantity_and_condition_semantics_remain_typed():
    assert equivalent({'kind':'number','number':'1.00'},{'kind':'number','number':Decimal('1')},{}).equal
    assert not equivalent({'kind':'quantity','number':'1','unit':'m'},{'kind':'quantity','number':'1','unit':'s'},{}).equal
    a={'kind':'all','terms':[{'kind':'claim','ref':'a'},{'kind':'claim','ref':'b'}]}
    b={'kind':'all','terms':[{'kind':'claim','ref':'y'},{'kind':'claim','ref':'x'}]}
    assert equivalent(a,b,{}, {'a':'x','b':'y'}).equal

def test_symbolic_math_and_explicit_undecided():
    a={'kind':'expression','language':'latex','expression':'x+x','bindings':[{'kind':'free','symbol':'x'}]}
    b={**a,'expression':'2 x'}
    result=equivalent(a,b,{})
    assert result.equal and result.outcome=='symbolic'
    unknown=equivalent({**a,'language':'unimplemented'},{**b,'language':'unimplemented'}, {})
    assert unknown.outcome=='undecided' and not unknown.equal


def test_external_known_endpoints_need_no_redeclared_entity_or_label():
    a,b=batch(),batch();a['entities']=[];b['entities']=[]
    a['claims'][0]['subject']='known:alice';b['claims'][0]['subject']='known:alice'
    known={'known:alice':'known:alice'}
    result=align_semantic(side(a,known_ids=known),side(b,known_ids=known),prepared())
    assert result.counts['full'].matched==1
    assert align_semantic(side(a),side(b),prepared()).counts['core'].matched==0


def test_scalar_declared_identity_attributes_align_without_a_label():
    p=prepared()
    prop=PropertyDefinition('name',NAME,'string',False,False,None,None,None,None,None,False)
    p.definitions=(p.definitions[0],ClassDefinition('Person',P,('Entity',),(prop,),('id',),(('id',),('name',))))
    a,b=batch(),batch()
    for value in (a,b):
        value['entities'][0].pop('label')
        value['entities'][0]['attributes']=[{'predicate':NAME,'value':{'kind':'text','text':'Alice'}}]
    result=align_semantic(side(a),side(b),p)
    assert result.entity_pairs==[('p','p','declared_identity_keys')]
    assert result.counts['full'].matched==1


def test_release_qualification_provenance_does_not_change_meaning_and_statement_is_required():
    p=prepared()
    field=PropertyDefinition('confidence','https://example.org/confidence','string',False,False,None,None,None,None,None,False,key_role='provenance')
    p.definitions=(*p.definitions,ClassDefinition('Qualification','https://example.org/Qualification',(),(field,),()))
    a,b=batch(),batch()
    a['claims'][0]['qualification']['confidence']='source-A'
    b['claims'][0]['qualification']['confidence']='source-B'
    assert align_semantic(side(a),side(b),p).counts['full'].matched==1
    a['claims'][0]['statement']='unmatched-reference-statement'
    assert align_semantic(side(a),side(b),p).counts['full'].matched==0


def test_located_evidence_in_the_same_source_sentence_matches_without_quote_overlap():
    a,b=batch(),batch()
    a['claims'][0]['evidence'][0]['locator']='source#sentence'
    b['claims'][0]['evidence'][0].update(locator='source#sentence',start=8,end=10)
    assert align_semantic(side(a),side(b),prepared()).counts['evidence'].matched==1
