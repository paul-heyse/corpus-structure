"""Freeze exact original Grinstead–Snell physical191–310, split into ten-page native inputs."""
from __future__ import annotations
import json
from hashlib import file_digest, sha256
from pathlib import Path
import pypdfium2 as pdfium
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PARENT=ROOT/'docs/statistics_corpus/corpus/grinstead_snell/Introduction_to_probability_grinstead_and_snell.pdf'
EXPECTED='763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e'
def digest(path):
    with path.open('rb') as stream:return file_digest(stream,'sha256').hexdigest()
def main():
    if digest(PARENT)!=EXPECTED:raise ValueError('parent source differs from authenticated inventory')
    out=HERE/'corpus';out.mkdir(exist_ok=False)
    cuts=[]
    with pdfium.PdfDocument(PARENT) as parent:
        for start in range(191,311,10):
            name=f'grinstead-snell-physical{start}-{start+9}.pdf';path=out/name
            with pdfium.PdfDocument.new() as cut:
                cut.import_pages(parent,pages=list(range(start-1,start+9)));cut.save(path)
            pages=[]
            with pdfium.PdfDocument(path) as cut:
                assert len(cut)==10
                for i in range(10):
                    a,b=parent[start-1+i],cut[i]
                    try:
                        ai,bi=a.render(scale=1).to_pil(),b.render(scale=1).to_pil()
                        try:
                            hashes=tuple(sha256(image.tobytes()).hexdigest() for image in (ai,bi))
                            if hashes[0]!=hashes[1] or a.get_size()!=b.get_size():raise ValueError('cut changes original page')
                            pages.append(dict(parent_physical_page=start+i,excerpt_physical_page=i+1,pixels_sha256=hashes[0],size_points=list(a.get_size())))
                        finally:ai.close();bi.close()
                    finally:a.close();b.close()
            cuts.append(dict(file=name,sha256=digest(path),pages=pages))
    manifest=dict(protocol='wce-gs120-source-cut-1',parent=str(PARENT.relative_to(ROOT)),parent_sha256=EXPECTED,parent_physical_pages=518,physical_pages=list(range(191,311)),page_count=120,cuts=cuts,origin_group='grinstead-snell',use='shared development, fitting, debugging, regression and assessment',exposure='known exposed source family; no fresh-origin claim',partition='feature_fit',predictions_included=False,script_sha256=digest(Path(__file__)))
    (HERE/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(outcome='passed',pages=120,cuts=12,parent_sha256=EXPECTED)))
if __name__=='__main__':main()
