"""Run an isolated native trained artifact through the ordinary owned M1 graph."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from pathlib import Path
from hashlib import file_digest, sha256

from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.orchestrate.m1 import (
    bind_record_policy, bind_retained_document, registry, retained_document, source_graph,
)
from corpus_structure.orchestrate.registry import MethodRegistry
from corpus_structure.methods.m1_source import M1Config
from corpus_structure.orchestrate.phase0 import bind_pdf_source
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.orchestrate.slices import records
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.authored_sql import (
    admit_archived_sql, analyze_archived_sql, has_authored_sql,
)
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, seal_cut
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
PACK = Path('domains/statistics')


def artifact_configuration(training_attempt, base, output):
    import json

    training_attempt = training_attempt.resolve(strict=True)
    owner = (HERE.parent / '2026-11-04_m1-contextual-adaptation').resolve()
    if training_attempt.parent != owner or not training_attempt.name.startswith('attempt-'):
        raise ValueError('select one isolated contextual-adaptation attempt')
    result = json.loads((training_attempt / 'result.json').read_bytes())
    settlement = json.loads((training_attempt / 'external-settlement.json').read_bytes())
    if settlement.get('outcome') != 'passed' or settlement.get('observed_processes_still_live'):
        raise ValueError('the native learning process tree must settle before prediction')
    if result.get('outcome') != 'passed' or not result.get('no_adoption') or not result.get('no_heldout'):
        raise ValueError('native learning result must pass with held-out isolation and no adoption')
    if result['native_result']['total_epochs'] != 1 or result['rows'] != result['counts']['optimizer_post']:
        raise ValueError('the declared complete bounded epoch did not settle')
    # Bind this inference recipe to the actual completed training inputs before
    # replacing only artifact provenance. Serialized numeric equality is not the
    # live profile fingerprint; both are checked.
    import shutil
    profile = json.loads((training_attempt / 'effective-profile.json').read_bytes())
    manifest = json.loads((training_attempt / 'input-manifest.json').read_bytes())
    configuration, = [entry for entry in manifest if entry['relative'] == 'contextual-configuration.json']
    config_path = Path(configuration['path'])
    if sha256(config_path.read_bytes()).hexdigest() != configuration['sha256']:
        raise ValueError('training input configuration changed')
    frozen = json.loads(config_path.read_bytes())
    if (canonical_bytes(base.model_dump(mode='json')) != canonical_bytes(frozen['params'])
            or base.profile().fingerprint != frozen['profile_fingerprint']
            or profile['profile'] != base.profile().fingerprint):
        raise ValueError('current inference recipe differs from the frozen training recipe')
    for entry in json.loads((training_attempt / 'loader-source-receipts.json').read_bytes()):
        if sha256(Path(entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('trained loader source changed: ' + entry['path'])
    base.profile().verify_artifacts()
    native = training_attempt / 'native/final'
    declared = {entry['relative']: entry for entry in result['checkpoint_files']}
    actual_files = {path.relative_to(native).as_posix() for path in native.rglob('*') if path.is_file()}
    if actual_files != set(declared):
        raise ValueError('native final artifact inventory changed')
    for name, entry in declared.items():
        with (native / name).open('rb') as stream:
            if file_digest(stream, 'sha256').hexdigest() != entry['sha256']:
                raise ValueError('native final artifact changed: ' + name)
    # Native saving may include auxiliary files. Keep the immutable full output,
    # but give the production loader its exact qualified five-file snapshot.
    snapshot = output / 'artifact-snapshot'
    snapshot.mkdir(exist_ok=False)
    hashes = []
    origins = []
    for name, _ in base.artifact_hashes:
        entry = declared[name]
        source = native / name
        target = snapshot / name
        target.parent.mkdir(exist_ok=True, parents=True)
        shutil.copyfile(source, target)
        with target.open('rb') as stream:
            actual = file_digest(stream, 'sha256').hexdigest()
        if actual != entry['sha256']:
            raise ValueError('isolated native artifact differs: ' + name)
        hashes.append((name, actual))
        origins.append(dict(relative=name, source=str(source), sha256=actual, bytes=target.stat().st_size))
    identity = sha256(canonical_bytes(hashes)).hexdigest()
    values = base.model_dump(mode='json')
    values.update(snapshot=str(snapshot), checkpoint='local/m1-contextual-epoch1',
        revision=identity, artifact_hashes=hashes)
    config = M1Config.model_validate(values)
    config.profile().verify_artifacts()
    return config, dict(training_attempt=str(training_attempt), training_result_sha256=sha256(
        (training_attempt / 'result.json').read_bytes()).hexdigest(), artifact_identity=identity,
        artifact_hashes=hashes, artifact_origins=origins,
        native_final_inventory=result['checkpoint_files'],
        training_profile=profile['profile'], profile=config.profile().fingerprint, no_adoption=True)


def main():
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origin', choices=('grinstead-snell',))
    parser.add_argument('output_name')
    parser.add_argument('--training-attempt', type=Path, required=True)
    parser.add_argument('--record-policy', type=Path)
    args = parser.parse_args()
    output = HERE / args.output_name
    output.mkdir(exist_ok=False)
    (output / 'executed-runner.py.txt').write_bytes(Path(__file__).read_bytes())
    settings = Settings()
    base = registry(PACK).config('extract.m1_candidates', 'contextual').config
    config, artifact = artifact_configuration(args.training_attempt, base, output)
    policy = json.loads(args.record_policy.read_bytes()) if args.record_policy else None
    (output / 'experimental-artifact.json').write_bytes(canonical_bytes(artifact))
    bundle, deps, profile, prepared = prepare_pack(PACK)
    with open_runtime_engine(settings, 'm1-preparation-release', purpose='admit') as engine:
        with engine.begin() as conn:
            persist_release(conn, bundle, deps, profile, prepared)
        if has_authored_sql(prepared):
            with open_runtime_engine(settings, 'm1-preparation-sql', purpose='read') as reader_engine, reader_engine.connect() as reader:
                analyzed = analyze_archived_sql(reader, prepared.release_id)
            with engine.begin() as conn:
                admit_archived_sql(conn, prepared.release_id, analyzed=analyzed)
        with engine.begin() as conn:
            admit_release(prepared, connection=conn)
    original = json.loads((HERE.parent / '2026-11-04_m1-source-populations/intake001' / args.origin / 'result.json').read_bytes())
    product = original['source_freeze']['pins'][0]['native_product']
    reference = ProductReference(product['task_id'], product['product_key'], product['content_digest'])
    project_id = 'm1-source-' + args.origin
    realization_id = 'm1-experimental:' + args.output_name + ':' + prepared.release_id
    with open_runtime_engine(settings, 'm1-preparation-owned-run', purpose='write') as engine:
        with engine.begin() as conn:
            initialize_source_project(conn, project_id=ProjectId(project_id),
                release_id=ReleaseId(prepared.release_id), realization_id=RealizationId(realization_id),
                projection_context=prepared)
            realization, document = table('data.realization'), table('kb.document')
            input_revision = conn.execute(select(realization.c.data_revision).where(realization.c.realization_id == realization_id)).scalar_one()
            documents = [dict(row) for row in conn.execute(select(document).where(document.c.project_id == project_id)).mappings()]
            selected = retained_document(conn, reference, prepared=prepared, project_id=project_id, documents=documents)
            corpus_record, scope_record = records([row for row in documents if row['id'] == selected.id], {},
                slice=None, scope=None, corpus=None)
        selected_registry = bind_retained_document(bind_pdf_source(registry(PACK), reference,
            method_name='ingest.pdf_integrated', input_role='integrated'), selected)
        configs = {name: dict(named) for name, named in selected_registry.file.configs.items()}
        configs['extract.m1_candidates']['contextual'] = config.model_dump(mode='json')
        selected_registry = MethodRegistry(selected_registry.methods(),
            replace(selected_registry.file, configs=configs), selected_registry.sources,
            prepared=selected_registry.prepared)
        if policy is not None:
            selected_registry = bind_record_policy(selected_registry, prepared, policy)
        # Capture the effective registry, including the explicitly isolated artifact;
        # never rewrite the domain default or claim this is the base checkpoint.
        snapshot = dict(version=selected_registry.file.version,
            configs=selected_registry.file.configs, **selected_registry.file.sections)
        (output / 'effective-methods.json').write_bytes(canonical_bytes(snapshot))
        report = run_source_methods(engine, project_id=project_id, prepared=prepared,
            binding=OperationBinding(prepared.release_id, realization_id, input_revision,
                canonical_bytes(dict(domain='statistics', release=prepared.release_id))),
            registry=selected_registry, graph=source_graph('contextual'),
            method_settings=MethodSettings(data_dir=settings.paths.data_dir, model_cache=settings.paths.model_cache),
            domain='statistics', corpus_record=corpus_record, scope_record=scope_record,
            guideline=(PACK / 'm1-guideline.md').read_text(), extraction_policy='m1-candidate',
            extraction_policy_config=canonical_bytes(snapshot).decode(),
            configurations={'extract.m1_candidates': 'contextual'},
            record_acceptance=tuple(policy.get('record_acceptance', ())) if policy else ())
        (output / 'source-run.json').write_bytes(canonical_bytes(report.model_dump(mode='json')))
        with engine.begin() as conn:
            cut = seal_cut(conn, report.run_id, 'm1-isolated-native-artifact-final', final=True)
        published = consolidate_cut(engine, cut, 'm1-experimental-result:' + str(report.run_id) + ':' + prepared.release_id)
    config.profile().verify_artifacts()
    result = dict(outcome='passed', scope='actual_isolated_trained_artifact_nondefault',
        report=report.model_dump(mode='json'), publication=asdict(published),
        source_run_id=int(report.run_id), source_cut_id=int(cut), release_id=prepared.release_id,
        native_product=product, model_execution='actual_native_CPU', pdf_conversion='not_run',
        experimental_artifact=artifact, origin_group=args.origin,
        quality_claim='not_established', operational_default_changed=False)
    (output / 'completed-result.json').write_bytes(canonical_bytes(result))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
