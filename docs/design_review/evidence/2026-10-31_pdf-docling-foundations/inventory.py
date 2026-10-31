"""Record installed capabilities and immutable cache/source identities."""
import json,shutil,importlib,importlib.metadata as m
from pathlib import Path
from hashlib import sha256
B=Path(__file__).resolve().parent
mods={'asr':'whisper','easyocr':'easyocr','htmlrender':'playwright','onnxruntime':'onnxruntime','rapidocr':'rapidocr','remote-serving':'tritonclient.grpc','tesserocr':'tesserocr','vlm':'transformers','xbrl':'arelle'}
r={'extras':{},'executables':{p:shutil.which(p) for p in ['ffmpeg','tesseract']},'packages':{d.metadata['Name']:d.version for d in m.distributions()}}
for extra,mod in mods.items():
 try:importlib.import_module(mod);r['extras'][extra]={'import':'available','module':mod}
 except Exception as e:r['extras'][extra]={'import':'unavailable','module':mod,'error':repr(e)}
r['extras']['ocrmac']={'outcome':'not_applicable','reason':'macOS-only; host Linux'}
from huggingface_hub.constants import HF_HUB_CACHE
r['model_snapshots']={p.parent.parent.name:p.name for p in Path(HF_HUB_CACHE).glob('models--docling-project--*/snapshots/*')}
source=B.parents[3]/'docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf'
r['source']={'path':str(source.relative_to(B.parents[3])),'sha256':sha256(source.read_bytes()).hexdigest()}
(B/'raw/inventory.json').write_text(json.dumps(r,indent=2));print(json.dumps(r['extras'],indent=2))
