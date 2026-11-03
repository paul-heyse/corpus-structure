"""Inspect native projection of the actual core declaration without editing it."""
from pathlib import Path
from hashlib import sha256
import json
import subprocess
from linkml.generators.protogen import ProtoGenerator
root = Path(__file__).resolve().parent
source = Path('python/corpus-structure/src/corpus_structure/model/core.yaml')
result = {'input': str(source), 'sha256': sha256(source.read_bytes()).hexdigest()}
try:
    generated = ProtoGenerator(str(source)).serialize()
    target = root/'raw/core.proto'
    target.write_text(generated)
    proc = subprocess.run(['protoc',f'-I{target.parent}',f'--descriptor_set_out={target.parent / "core.pb"}',str(target)],capture_output=True,text=True,check=False)
    result.update(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
except Exception as error:
    result.update(error_type=type(error).__name__,error=str(error))
(root/'raw/product-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
