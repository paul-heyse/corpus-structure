"""Runtime preparation contracts; these controls do not impersonate model/provider execution."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import prepare_pdf_assets
from corpus_structure.ingest.pdf_candidates import capture_candidates
from corpus_structure.ingest.pdf_methods import PdfIngestConfig


def test_active_registry_selects_pdf_not_html():
    from corpus_structure.orchestrate.phase0 import PHASE0, registry
    configured = registry(Path(__file__).resolve().parents[1]/'domains/statistics')
    assert 'ingest.pdf' in {m.name for m in configured.methods()}
    assert 'ingest.html' not in {m.name for m in configured.methods()}
    assert configured.resolve('ingest.pdf','default').config.originals == ('siegrist_random/Full_PDF/Full.pdf',)
    assert PHASE0.stages[0][1][0].config == 'ingest.pdf/default'
    assert PdfIngestConfig().recipe().timeout_seconds is None


def test_owned_assets_pin_actual_table_revision_and_detect_changed_bytes(tmp_path, monkeypatch):
    import huggingface_hub
    revisions = {'docling-project/docling-layout-heron':'a'*40,
                 'docling-project/CodeFormulaV2':'b'*40,
                 'docling-project/docling-models':'c'*40}
    for repository, revision in revisions.items():
        directory=tmp_path/'snapshots'/repository.replace('/','--')/revision
        directory.mkdir(parents=True)
        (directory/'config.json').write_text('{"model":"independent asset fixture"}')
    def resolve(repo_id,revision,local_files_only):
        assert local_files_only is True
        return str(tmp_path/'snapshots'/repo_id.replace('/','--')/revisions[repo_id])
    monkeypatch.setattr(huggingface_hub,'snapshot_download',resolve)
    cache=tmp_path/'models'
    (cache/'RapidOcr').mkdir(parents=True)
    for name in ('PP-OCRv6_det_small.onnx','ch_ppocr_mobile_v2.0_cls_mobile.onnx','PP-OCRv6_rec_small.onnx'):
        (cache/'RapidOcr'/name).write_bytes(b'independent artifact bytes')
    assets=prepare_pdf_assets(PdfRecipe('a'*40,'b'*40),cache=cache)
    assert dict(assets.repositories)['docling-project/docling-models']=='c'*40
    assert len(assets.files)==6
    changed=assets.root/assets.files[0][0]
    changed.chmod(0o644)
    changed.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='integrity'):
        assets.verify()


def test_native_inline_capture_distinguishes_missing_cells_from_empty_and_retains_math_font():
    from docling_core.types.doc import BoundingBox
    box=BoundingBox(l=1,t=2,r=9,b=12)
    cell=SimpleNamespace(text='x',font_name='ABCDEF+CMMI10',
                         rect=SimpleNamespace(to_bounding_box=lambda:box))
    captured=capture_candidates(SimpleNamespace(page_no=1,
        parsed_page=SimpleNamespace(word_cells=[cell],has_words=True,has_chars=False)))
    assert captured.has_words is True
    assert captured.candidates[0].text=='x'
    assert captured.candidates[0].basis=='native-math-font-v1'
    missing=capture_candidates(SimpleNamespace(page_no=2,parsed_page=None))
    assert missing.has_words is False
    assert missing.candidates==()


def test_unnumbered_organizational_subheads_preserve_native_levels():
    from docling_core.types.doc import DoclingDocument,DocItemLabel
    from corpus_structure.ingest.pdf_hierarchy import organize,snapshot,load_snapshot
    document=DoclingDocument(name='independent unnumbered hierarchy fixture')
    for label,level in [('1.1: Sets',1),('Sets and subsets',2),('Definition',3),
                        ('Proof of Theorem 1',3),('Examples and Applications',2),
                        ('Answer',3),('Distribution Functions',2)]:
        document.add_heading(text=label,level=level)
        document.add_text(label=DocItemLabel.TEXT,text='Content under '+label)
    organization=organize(snapshot(document),PdfIngestConfig().section_policy())
    derived=load_snapshot(organization.document)
    names=[derived.groups[int(s.group_ref.rsplit('/',1)[1])].name for s in organization.sections]
    assert names==['1.1: Sets','Sets and subsets','Examples and Applications','Distribution Functions']
    assert [s.level for s in organization.sections]==[1,2,2,2]


def test_inline_decomposition_keeps_prose_and_qualified_formula_in_same_native_hierarchy():
    from PIL import Image
    from docling_core.types.doc import BoundingBox,DoclingDocument,DocItemLabel,PageItem,ProvenanceItem,Size
    from corpus_structure.ingest.pdf_candidates import InlineCandidate
    from corpus_structure.ingest.pdf_enrichment import PositionedCandidate,enrich_inline
    from corpus_structure.ingest.pdf_health import ObservedFormulaStage
    from corpus_structure.ingest.pdf_hierarchy import snapshot,load_snapshot,organize,project_section
    from test_pdf_conversion import CatchingStage,Engine
    document=DoclingDocument(name='independent inline geometry fixture')
    document.pages[1]=PageItem(page_no=1,size=Size(width=100,height=100))
    document.add_heading(text='1.1: Sets',level=1)
    paragraph=document.add_text(label=DocItemLabel.TEXT,text='Let x be real.',orig='Let x be real.',
        prov=ProvenanceItem(page_no=1,bbox=BoundingBox(l=10,t=10,r=95,b=30),charspan=(0,14)))
    organized=organize(snapshot(document),PdfIngestConfig().section_policy())
    inline=InlineCandidate(1,'x',25,10,35,30,'TOPLEFT','CMMI10','native-math-font-v1')
    source=organized.document
    result=enrich_inline(source,(PositionedCandidate(paragraph.self_ref,4,5,inline),),
        stage=ObservedFormulaStage(CatchingStage(Engine())),
        render_region=lambda page,box:Image.new('RGB',(20,40)))
    native=load_snapshot(result.native)
    section=organized.sections[0].group_ref
    projected=project_section(native,result.native.digest,section,'direct',section_refs=frozenset([section]))
    assert projected.text=='1.1: Sets\nLet x be real.'
    formulas=[n for n in native.texts if str(n.label)=='formula']
    assert len(formulas)==1
    assert formulas[0].text=='x'
    assert formulas[0].prov[0].charspan==(0,1)
    assert result.mappings[0]['origin_pointer']==paragraph.self_ref
    assert (result.mappings[0]['start'],result.mappings[0]['end'])==(4,5)
    assert native.texts[int(paragraph.self_ref.rsplit('/',1)[1])].orig=='Let x be real.'
    assert result.outcomes[0].outcome=='succeeded'
