"""Recompute the exact retained CPU-native selection; never publish or recognize PDF."""
from __future__ import annotations

import json
import logging
from collections import Counter
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import text

from corpus_structure.core.method import MethodContext, UnitRef, UnitView
from corpus_structure.cli.characterization_options import method_settings
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.native_evidence import NativeEvidenceConfig, NativeEvidenceMethod
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization import characterization_inputs
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parent


def main():
    settings = Settings()
    with open_runtime_engine(settings, 'bep-e01-read-only-reproduction', purpose='read') as engine:
        with engine.connect() as conn:
            row = conn.execute(text('SELECT t.*,cfg.params,cfg.config_hash,m.name,m.version,r.runtime_id FROM ops.task t JOIN ops.method_config cfg ON cfg.id=t.method_config_id JOIN ops.method m ON m.id=cfg.method_id JOIN ops.run r ON r.id=t.run_id WHERE t.id=2528')).mappings().one()
            task = dict(row)
            (ROOT / 'raw/task-selection.json').write_bytes(canonical_bytes(json.loads(json.dumps(task, default=str))))
            archived = open_release(conn, task['release_id'])
            core = Path('python/corpus-structure/src/corpus_structure/model/semantic/core.yaml')
            prepared = prepare_release(characterization_inputs(SourceBundle('core', (SourceArtifact('core', core.read_bytes()),))))
            from corpus_structure.methods.pm2_worker import preflight_pm2_runtime
            import corpus_structure.methods.pm2_native as native_module
            script = Path(native_module.__file__)
            project = Path('services/pm2-hanlp').resolve()
            active_settings = method_settings(settings)
            custody = preflight_pm2_runtime(python=project/'.venv/bin/python', script=script, project=project, provider='hanlp', assets=active_settings.model_cache/'pm2')
            (ROOT/'raw/current-hanlp-custody.json').write_bytes(canonical_bytes(custody))
            cfg = NativeEvidenceConfig.model_validate({**task['params'], 'hanlp_runtime':custody['runtime_identity'], 'hanlp_artifacts':custody['assets']})
            (ROOT/'raw/recomputation-config.json').write_bytes(canonical_bytes(cfg.model_dump(mode='json')))
            reader = BoundReader(conn, 610, prepared, 614, analysis=False)
            ref = reader.source_view_ref(480)
            assert ref.section_pointer == '#/groups/375'
            assert ref.native_product.task_id == 1627
            assert ref.native_product.content_digest == '35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb'
            view = reader.source_view(480)
            source = canonical_bytes(dict(text=view.text, pieces=view.pieces, items=view.items, ancestors=view.ancestors, scope=cfg.characterization_source_scope))
            (ROOT / 'raw/retained-source.json').write_bytes(source)
            run = SimpleNamespace(reader=reader)
            unit = UnitView(UnitRef(TaskUnitType.DOCUMENT, task['unit_id']), run)
            identity = dict(key=task['name'], version=NativeEvidenceMethod.version, runtime=task['runtime_id'], configuration=sha256(canonical_bytes(cfg.model_dump(mode='json'))).hexdigest(), input=sha256(NativeEvidenceMethod().input_digest(unit,cfg).bytes).hexdigest(), **{k:task['params'][k] for k in ('model','grammar','context')})
            ctx = MethodContext(run, reader, method_settings(settings), logging.getLogger(__name__), characterization_operation=lambda ref: identity)
            print('retained source read; starting actual CPU-native producer', flush=True)
            (result,) = NativeEvidenceMethod().run([unit], cfg, ctx)
            report = result.characterization_layer
            assert report is not None
            (ROOT / 'raw/layer.json').write_bytes(report.content)
            body = report.payload
            counts = {key:len(body.get(key, ())) for key in ('occurrences','annotations','memberships','roles','terms','choices','native_runs','coverage')}
            summary = dict(date='2026-11-11', source_run=610, failed_task=2528, source_capture=496, source_cut=614, source_view=480, section_pointer=ref.section_pointer, base=ref.native_product.values(), original_release=archived.release_id, recomputation_release=prepared.release_id, canonical_bytes=len(report.content), canonical_sha256=sha256(report.content).hexdigest(), source_bytes=len(source), source_sha256=sha256(source).hexdigest(), counts=counts, families=dict(Counter(a['family'] for a in body['annotations'])), outcome=body['outcome'], coverage=body['coverage'], note='Actual CPU providers on exact captured source; current method v2 and locally compiled characterization release with current frozen HanLP custody/config/input. Not the original failed v1 body or a publication.')
            (ROOT / 'summary.json').write_bytes(canonical_bytes(summary))
            print(json.dumps({k:v for k,v in summary.items() if k!='coverage'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
