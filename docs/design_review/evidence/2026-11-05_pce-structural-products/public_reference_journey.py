"""Install independently authored exact public frames without authoring new judgments.

Input files retain independent A/B/C provenance. This script validates their common
frozen frames and serializes the existing judgments through the native store.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from corpus_structure.evaluate.structural_assessment import (
    StructuralAuthoredReference, StructuralEvaluationFrame, create_structural_reference_set,
    record_structural_reference_pass,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_admission import POLICIES, structural_statement
from corpus_structure.semantic.structural_products import StructuralProductReport
from corpus_structure.settings import Settings

RAW = Path(__file__).with_name('raw')


def packets(attempt):
    authored = {kind: json.loads((RAW/f'independent-public-{kind}-{attempt}.json').read_bytes()) for kind in 'ABC'}
    indexed = {kind: {item['product_id']:item for item in items} for kind,items in authored.items()}
    if any(len(indexed[k]) != len(authored[k]) for k in 'ABC') or not indexed['A'].keys()==indexed['B'].keys()==indexed['C'].keys():
        raise ValueError('independent authors selected different/repeated products')
    products = {report.product_id:report for name in ('normal','mean','comparison','dossier') for report in (StructuralProductReport.model_validate_json((RAW/f'production-{name}-{attempt}.json').read_bytes()),)}
    if products.keys() != indexed['A'].keys():
        raise ValueError('independent public frames differ from frozen report population')
    selected=[]
    for product_id,report in products.items():
        items={kind:indexed[kind][product_id] for kind in 'ABC'}
        frame=StructuralEvaluationFrame.model_validate(items['A']['frame'])
        if any(StructuralEvaluationFrame.model_validate(item['frame']) != frame for item in items.values()):
            raise ValueError('independent authors differ over frozen source frame')
        if frame.inputs != report.inputs or frame.operation != report.kind or frame.product_ids != (product_id,) or frame.rubric_version != POLICIES[report.kind]:
            raise ValueError('independent source frame differs from actual selected structural product')
        payloads={kind:StructuralAuthoredReference.model_validate(item['authored']) for kind,item in items.items()}
        for payload in payloads.values():
            if payload.frame_digest != frame.identity:
                raise ValueError('authored payload frame digest differs')
            case, = [c for c in payload.cases if c.facet == 'public_statement']
            if case.path != ('public_statement',) or case.judgment != 'supported' or canonical_bytes(case.expected) != canonical_bytes(structural_statement(report)):
                raise ValueError('independent whole-statement judgment does not support exact selected statement')
        selected.append((product_id,frame,{kind:canonical_bytes(item['authored']) for kind,item in items.items()}))
    return selected


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--release',required=True);parser.add_argument('--attempt',default='005');parser.add_argument('--out',required=True);args=parser.parse_args()
    selected=packets(args.attempt)
    bindings=[]
    with open_runtime_engine(Settings(),'pce-public-references',purpose='evaluate') as engine:
        with engine.begin() as conn:
            for product_id,frame,authored in selected:
                set_id=create_structural_reference_set(conn,project_id='pce-statistics-structural',release_id=args.release,frame=frame)
                a=record_structural_reference_pass(conn,set_id=set_id,pass_kind='A',actor='pce-independent-public-A-'+args.attempt,authored=authored['A'])
                b=record_structural_reference_pass(conn,set_id=set_id,pass_kind='B',actor='pce-independent-public-B-'+args.attempt,authored=authored['B'])
                c=record_structural_reference_pass(conn,set_id=set_id,pass_kind='C',actor='pce-independent-public-C-'+args.attempt,authored=authored['C'],parents=(a,b))
                from hashlib import sha256
                bindings.append(dict(product_id=product_id,set_id=set_id,c_pass_id=c,c_content_digest=sha256(authored['C']).hexdigest(),frame_digest=frame.identity,policy_id=frame.rubric_version))
    result=dict(outcome='passed',release_id=args.release,structural_admission=bindings,assessment_scope='selected exposed development source judgments; no unseen population estimate')
    with (RAW/args.out).open('xb') as out:out.write(canonical_bytes(result)+b'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
