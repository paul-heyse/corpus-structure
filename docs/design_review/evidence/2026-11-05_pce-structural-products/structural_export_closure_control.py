"""Actual selected-cut structural closure and offline contract verification."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from corpus_structure.serve.review_bundle import ReviewSelection, export_review_bundle, verify_review_bundle, inspect_review_bundle
from corpus_structure.serve.structural_products import StructuralRequest
from corpus_structure.settings import Settings

parser=argparse.ArgumentParser();parser.add_argument('--run',type=int,required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
checks={}
with TemporaryDirectory(prefix='pce-structural-closure-',dir='build') as temporary:
 root=Path(temporary)
 filtered=ReviewSelection(structural_selections=(StructuralRequest(run_id=args.run,kind='dossier',include_publication=True,include_support=True,max_bytes=8000000),))
 try:export_review_bundle(filtered,root/'filtered',Settings())
 except ValueError as error:
  assert 'dossier predecessor closure missing' in str(error),str(error)
  assert not (root/'filtered').exists()
  checks['filtered_dossier_full_refused_missing_predecessors']=str(error)
 else:raise AssertionError('filtered dossier claimed complete typed predecessor closure')
 full=ReviewSelection(structural_selections=(StructuralRequest(run_id=args.run,include_publication=True,include_support=True,max_bytes=8000000),))
 manifest=export_review_bundle(full,root/'full',Settings());verified=verify_review_bundle(root/'full');summary=inspect_review_bundle(root/'full')
 assert manifest==verified
 assert summary['relations']['structural_products']==4
 def payloads(name):
  return [json.loads(json.loads(line)['payload_json']) for line in (root/'full'/f'{name}.jsonl').read_text().splitlines()]
 captured_releases={row['release_id'] for row in payloads('contracts')}
 required_releases={row['release_id'] for row in payloads('structural_selections')}
 required_releases.update(ref['release_id'] for row in payloads('structural_products') for ref in row['report']['inputs']['sources'])
 assert required_releases<=captured_releases
 checks['required_release_contracts']={'required':sorted(required_releases),'captured':sorted(captured_releases)}
 checks['complete_structural_export_verified']=summary
 result={'outcome':'passed','run_id':args.run,'checks':checks,'scope':'selected structural cases with originals and contracts; not complete corpus coverage'}
 with Path(__file__).with_name('raw').joinpath(args.out).open('x') as out:out.write(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result))
