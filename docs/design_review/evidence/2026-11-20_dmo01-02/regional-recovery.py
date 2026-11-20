"""Bounded native missing-region control using actual prepared stage providers."""
from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from time import monotonic
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from corpus_structure.core.evidence import document_key
from corpus_structure.orchestrate.data_operations import NativeRequestClaim
from corpus_structure.orchestrate.native_demand_io import NativeDemandIO
from corpus_structure.orchestrate.source_operation import prepare_source_demand
from corpus_structure.orchestrate.source_request import SourceRunRequest
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_demands import DemandPlanner
from corpus_structure.semantic.data_operation_service import acquire_data_execution_basis, create_native_demand, execute_data_demand
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.original_documents import register_original_document
from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from pydantic import TypeAdapter

ROOT = Path(__file__).resolve().parents[4]
FOLDER = ROOT / "build/dmo01-02"
RAW = FOLDER / 'regional'
RAW.mkdir(exist_ok=True)
OLD = ROOT / 'docs/design_review/evidence/2026-11-19_udm20-regional-confirmation'
RECORD = json.loads((FOLDER / 'n43-host-runtime-refresh.json').read_text())
SOURCE = ROOT / 'python/corpus-structure/src'
PROJECT = 'dmo02-n43-withheld-region'
TARGET = 'text.compose_view/organized-captured-full-native'
POLICY = TypeAdapter(CharacterizationExecutionPolicy).validate_python(json.loads((OLD / 'regional-execution-policy.json').read_text()))


def engine(role):
    return create_engine(URL.create('postgresql+psycopg', username=role, database='corpus_structure_ddo_stage', query={'host': '/var/run/postgresql', 'port': '5434'}))


def write(name, value):
    (RAW / name).write_text(json.dumps(value, indent=2, default=str) + '\n')
    print(name, flush=True)


def original_pdf():
    stream = b'BT /F1 20 Tf 72 720 Td (1 FIRST SAMPLE) Tj 0 -50 Td /F1 12 Tf (The sample contains five observations.) Tj 0 -200 Td /F1 20 Tf (2 SECOND SAMPLE) Tj 0 -50 Td /F1 12 Tf (The mean describes the sample.) Tj ET'
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
        b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    content = b'%PDF-1.4\n'
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(content))
        content += f'{index} 0 obj\n'.encode() + obj + b'\nendobj\n'
    start = len(content)
    content += f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
    content += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
    content += f'trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()
    path = RAW / 'two-regions.pdf'
    path.write_bytes(content)
    return path, content


def snapshot(writer, model, demand):
    with writer.begin() as conn:
        return DemandPlanner(model, DataOperationStorage(conn)).resume(demand)


def main():
    writer, admin, admitter = engine('corpus_sem_writer'), engine('paul'), engine('corpus_sem_admitter')
    held = None
    try:
        with admin.begin() as conn:
            observed = conn.execute(text('SELECT current_database(),(SELECT oid FROM pg_database WHERE datname=current_database()),(SELECT version_num FROM public.semantic_alembic_version)')).one()
            assert tuple(observed) == ('corpus_structure_ddo_stage', 130661481, 'semantic_ddo_pe_n43')
            basis = acquire_data_execution_basis(conn, RECORD['release'], RECORD['runtime_id'], source_root=SOURCE)
        model = bound_data_operation_model(basis.prepared)
        path, content = original_pdf()
        with writer.begin() as conn:
            storage = DataOperationStorage(conn)
            storage.initialize_source_project({'project_id': PROJECT, 'release_id': RECORD['release']})
            register_original_document(conn, prepared=basis.prepared, project_id=PROJECT, source_uri='two-regions.pdf', original_path=str(path), original=content, mime='application/pdf', title='Two independently authored native regions')
            document = document_key(PROJECT, 'two-regions.pdf', sha256(content).hexdigest())
            request = SourceRunRequest(project_id=PROJECT, release_id=RECORD['release'], runtime_id=RECORD['runtime_id'], selection={'kind': 'whole_document'}, documents=(document,), targets=(TARGET,))
            native = prepare_source_demand(conn, request, prepared=basis.prepared)
            native = native.model_copy(update={'selections': tuple(row.model_copy(update={'parameters': {'sections': ['1 FIRST SAMPLE', '2 SECOND SAMPLE'], 'membership': 'direct'}}) if row.operation == 'source.pdf_organized_views/discovery' else row for row in native.selections)})
            demand = create_native_demand(conn, native, prepared=basis.prepared)['demand_id']
        write('registered.json', {'demand': demand, 'document': document, 'original_sha256': sha256(content).hexdigest(), 'release': RECORD['release'], 'runtime': RECORD['runtime_id']})
        first = execute_data_demand(writer, demand, source_root=SOURCE, project_id=PROJECT, admission_engine=admitter, database_capacity=6, policy=POLICY, max_rounds=3)
        snap = snapshot(writer, model, demand)
        write('after-source.json', snap)
        # Discovery closes on the next bounded sweep; the already prepared families remain unexecuted.
        with writer.begin() as conn:
            planner = DemandPlanner(model, DataOperationStorage(conn))
            obligations = {row['obligation_id']: row for row in snap['obligations']}
            for use in snap['uses']:
                if use['fate'] == 'fulfilled' and obligations[use['obligation_id']]['operation_id'] == 'source.pdf_organized_views/discovery':
                    for product in use['products']:
                        if product['role'] == 'result':
                            planner.expand_discovery(snap, population='selected-source-views', product=product['product_id'], derivation=use['derivation_id'])
        snap = snapshot(writer, model, demand)
        members = [member for population in snap['populations'] if population['name'] == 'selected-source-views' for member in population['members']]
        assert len(members) == 2, f'expected exactly two actual regions, found {len(members)}'
        with writer.begin() as conn:
            ready = DemandPlanner(model, DataOperationStorage(conn)).ready(snap, authorization=b'{}')
            selected = sorted((item for item in ready if item.operation == 'segment.sentences/source-native'), key=lambda item: item.subject)
            assert len(selected) == 2, f'expected two sentence requests, found {len(selected)}'
            pending = json.loads(selected[-1].native)
            holder = 'udm20-deliberately-held:' + uuid4().hex
            claimed = DataOperationStorage(conn).claim_data_requests({'holder': holder, 'lease_seconds': 300, 'items': [{'request_id': pending['request_id'], 'generation': pending['generation']}]})['items'][0]
            assert claimed['state'] == 'claimed', claimed
            claim = claimed['result']
            held = {key: claim[key] for key in ('request_id','generation','task_id','attempt','holder')}
        owned = NativeRequestClaim(claim['request_id'], claim['generation'], claim['task_id'], claim['attempt'], claim['holder'], claim['release_id'], datetime.fromisoformat(claim['lease_until'].replace('Z','+00:00')), runtime_id=claim['runtime_id'])
        with NativeDemandIO(writer, admitter).claims(holder) as owner:
            owner.add_claim(owned)
            completed = execute_data_demand(writer, demand, source_root=SOURCE, project_id=PROJECT, admission_engine=admitter, database_capacity=6, policy=POLICY)
            snap = snapshot(writer, model, demand)
            before = monotonic()
            with writer.begin() as conn:
                tuple(DemandPlanner(model, DataOperationStorage(conn)).bound_requests(snap, authorization=b'{}'))
            seconds = monotonic()-before
            current = snapshot(writer, model, demand)
            write('withheld.json', {'held': held, 'binding_seconds': seconds, 'population_members': len(members), 'snapshot': current})
            obs = {row['obligation_id']: row for row in current['obligations']}
            view = [use for use in current['uses'] if obs[use['obligation_id']]['operation_id'] == TARGET]
            assert len(view) == 1 and view[0]['fate'] == 'not-applicable', view
            assert {reason['code'] for reason in view[0]['selection']['reasons']} == {'binding-covers'}
            assert any(use['fate'] == 'fulfilled' and obs[use['obligation_id']]['operation_id'] == 'segment.sentences/source-native' for use in current['uses'])
            with admin.begin() as conn:
                release = DataOperationStorage(conn).release_data_attempt({**held, 'physical_retirement':'confirmed', 'failure': {'code':'deliberately-withheld-region', 'message':'No provider computation was submitted for this held proof claim.'}})
            owner.owner.active.pop((owned.task_id, owned.attempt, holder))
            held = None
            write('held-release.json', release)
        final = execute_data_demand(writer, demand, source_root=SOURCE, project_id=PROJECT, admission_engine=admitter, database_capacity=6, policy=POLICY)
        write('final.json', {'receipt_count': final.receipt_count, 'snapshot': json.loads(final.snapshot)})
        assert final.receipt_count > 0
        repeated = execute_data_demand(writer, demand, source_root=SOURCE, project_id=PROJECT, admission_engine=admitter, database_capacity=6, policy=POLICY)
        assert repeated.receipt_count == 0
        after = snapshot(writer, model, demand)
        write('unchanged-repeat.json', {'receipt_count': repeated.receipt_count, 'snapshot': after})
    finally:
        if held is not None:
            with admin.begin() as conn:
                write('failed-held-release.json', DataOperationStorage(conn).release_data_attempt({**held, 'physical_retirement':'confirmed', 'failure': {'code':'proof-driver-retired', 'message':'Held native proof claim had no submitted physical computation.'}}))
        writer.dispose()
        admin.dispose()
        admitter.dispose()


if __name__ == '__main__':
    main()
