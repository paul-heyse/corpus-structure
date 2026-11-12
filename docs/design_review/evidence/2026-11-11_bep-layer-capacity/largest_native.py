"""Actual CPU-native upper-tail capacity probe on retained SourceView561; no publication."""
from __future__ import annotations

import json
import logging
from collections import Counter
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import text

from corpus_structure.cli.characterization_options import method_settings
from corpus_structure.core.method import MethodContext, UnitRef, UnitView
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods import pm2_native
from corpus_structure.methods.native_evidence import NativeEvidenceConfig, NativeEvidenceMethod
from corpus_structure.methods.pm2_worker import preflight_pm2_runtime
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization import characterization_inputs
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parent
SOURCE_DIGEST = '35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb'


def main():
    settings = Settings()
    selected_settings = method_settings(settings)
    with open_runtime_engine(settings, 'bep-e01-largest-source-read', purpose='read') as engine:
        with read_snapshot(engine) as conn:
            original = dict(conn.execute(text('SELECT t.*,cfg.params,m.name,r.runtime_id FROM ops.task t JOIN ops.method_config cfg ON cfg.id=t.method_config_id JOIN ops.method m ON m.id=cfg.method_id JOIN ops.run r ON r.id=t.run_id WHERE t.id=2528')).mappings().one())
            core = Path('python/corpus-structure/src/corpus_structure/model/semantic/core.yaml')
            prepared = prepare_release(characterization_inputs(SourceBundle('core', (SourceArtifact('core', core.read_bytes()),))))
            reader = BoundReader(conn, 496, prepared, 614, analysis=False)
            view = reader.source_view(561)
            ref = view.ref
            assert ref.section_pointer == '#/groups/456'
            assert ref.native_product.task_id == 1627
            assert ref.native_product.product_key == 'integrated'
            assert ref.native_product.content_digest == SOURCE_DIGEST
            scope = dict(profile='full_document', source_view_ids=[561], source_views=[dict(source_view_id=561, key=ref.key, base_document=ref.native_product.values(), section_pointer=ref.section_pointer, membership=ref.membership, projection_digest=ref.projection_digest, recipe_digest=ref.recipe_digest)], selectors=[dict(projection=ref.projection_digest, start=0, end=len(view.text))])
            script = Path(pm2_native.__file__)
            project = Path('services/pm2-hanlp').resolve()
            custody = preflight_pm2_runtime(python=project/'.venv/bin/python', script=script, project=project, provider='hanlp', assets=selected_settings.model_cache/'pm2')
            cfg = NativeEvidenceConfig.model_validate({**original['params'], 'characterization_source_scope':scope, 'hanlp_runtime':custody['runtime_identity'], 'hanlp_artifacts':custody['assets']})
            source = canonical_bytes(dict(text=view.text, pieces=view.pieces, items=view.items, ancestors=view.ancestors, health=view.health, integrated_context=view.integrated_context, scope=scope))
            (ROOT/'raw/largest-source.json').write_bytes(source)
            (ROOT/'raw/largest-current-hanlp-custody.json').write_bytes(canonical_bytes(custody))
            (ROOT/'raw/largest-config.json').write_bytes(canonical_bytes(cfg.model_dump(mode='json')))
            run = SimpleNamespace(reader=reader)
            unit = UnitView(UnitRef(TaskUnitType.DOCUMENT, ref.document_id), run)
            method = NativeEvidenceMethod()
            operation = dict(key=method.name, version=method.version, runtime=original['runtime_id'], configuration=sha256(canonical_bytes(cfg.model_dump(mode='json'))).hexdigest(), input=sha256(method.input_digest(unit,cfg).bytes).hexdigest(), model=cfg.model, grammar=cfg.grammar, context=cfg.context)
            context = MethodContext(run, reader, selected_settings, logging.getLogger(__name__), characterization_operation=lambda ref: operation)
            print('Largest retained source authenticated; starting actual CPU-native producer', flush=True)
            (result,) = method.run([unit], cfg, context)
            report = result.characterization_layer
            assert report is not None
            (ROOT/'raw/largest-layer.json').write_bytes(report.content)
            body = report.payload
            summary = dict(date='2026-11-11', source_capture=496, source_cut=614, source_view=561, section_pointer=ref.section_pointer, base=ref.native_product.values(), source_text_chars=len(view.text), source_bytes=len(source), source_sha256=sha256(source).hexdigest(), recomputation_release=prepared.release_id, canonical_bytes=len(report.content), canonical_sha256=sha256(report.content).hexdigest(), counts={key:len(body.get(key,())) for key in ('occurrences','annotations','memberships','roles','terms','choices','native_runs','coverage')}, inventory_bytes={key:len(canonical_bytes(body[key])) for key in ('occurrences','annotations','memberships','roles','native_runs','coverage')}, families=dict(Counter(row['family'] for row in body['annotations'])), outcome=body['outcome'], coverage=body['coverage'], within_64_mib=len(report.content)<=67108864, note='Actual current method v2 with locally compiled release and frozen current HanLP custody, complete natural unit561; private production, not publication or whole-book acceptance.')
            (ROOT/'largest-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
            print(json.dumps({key:value for key,value in summary.items() if key!='coverage'},indent=2),flush=True)


if __name__ == '__main__':
    main()
