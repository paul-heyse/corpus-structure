"""Controlled native-stage failure characterization; not model-quality evidence."""
import json
from pathlib import Path
from PIL import Image
from docling_core.types.doc import DoclingDocument,DocItemLabel
from docling.datamodel.base_models import ItemAndImageEnrichmentElement
from docling.models.stages.code_formula.code_formula_vlm_model import CodeFormulaVlmModel
class FailingEngine:
 def predict_batch(self,inputs):raise RuntimeError('controlled inference failure')
 def cleanup(self):pass
stage=object.__new__(CodeFormulaVlmModel)
stage.enabled=True;stage.engine=FailingEngine();stage._repetition_stopper=None
D=DoclingDocument(name='failure-probe');item=D.add_text(label=DocItemLabel.FORMULA,text='backend fallback',orig='backend fallback')
result=list(stage(D,[ItemAndImageEnrichmentElement(item=item,image=Image.new('RGB',(20,20)))]))
assert result[0].text=='backend fallback'
out={'controlled_failure':True,'native_stage_returned_unchanged_item':result[0] is item,'text':result[0].text,'meaning':'failure-control only; no successful recognition or provider-quality claim'}
Path(__file__).with_name('raw').joinpath('health.json').write_text(json.dumps(out,indent=2));print(out)
