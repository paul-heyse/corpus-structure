from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.consolidation import SourceItem, assemble
from corpus_structure.semantic.publication import EvidenceRow


def prepared():
    core = Path(__file__).parents[2] / 'src/corpus_structure/model/semantic/core.yaml'
    domain = {'id':'https://example.org/domain', 'name':'domain', 'imports':['semantic_core'],
              'prefixes':{'ex':'https://example.org/'},'default_prefix':'ex',
              'classes':{'Thing':{'is_a':'Entity','attributes':{'label':{'range':'string'}}}}}
    return prepare_release(SourceBundle('domain', (SourceArtifact('domain',yaml.safe_dump(domain).encode()),SourceArtifact('semantic_core',core.read_bytes()))))


def test_repeated_items_keep_occurrences_and_shared_fact_without_selecting_truth():
    release = prepared()
    item = SourceItem('subject','Thing','label','same',{'modality':'asserted','polarity':True},'source','item:0','stated',(EvidenceRow('evidence','source','page#p','parser','1'),))
    batch = assemble(release,'realization','batch',(item,replace(item,item='item:1')))
    assert len(batch.fact)==1
    assert len(batch.occurrence)==2
    assert len(batch.support)==2
    assert batch.selection==()
    assert len(batch.occurrence_establishment)==2
    assert len(batch.evidence)==1
    assert batch.content==assemble(release,'realization','batch',(replace(item,item='item:1'),item)).content
    with pytest.raises(ValueError,match='different content'):
        assemble(release,'realization','batch',(item,replace(item,object='changed')))
    with pytest.raises(ValueError,match='inference publishes proofs'):
        assemble(release,'realization','batch',(replace(item,establishment='derived'),))


def test_different_semantic_scope_does_not_fuse_facts():
    release=prepared()
    item=SourceItem('subject','Thing','label','same',{'modality':'asserted','polarity':True,'scope':{'extent':'section','locator':'page#one'}},'source','item:0','stated',(EvidenceRow('evidence','source','page#p','parser','1'),))
    other=replace(item,item='item:1',qualification={**item.qualification,'scope':{'extent':'section','locator':'page#two'}})
    assert len(assemble(release,'realization','batch',(item,other)).fact)==2
