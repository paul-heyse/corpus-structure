"""Read one native parser page without inference to diagnose missing inline candidates."""
import json
from pathlib import Path
from collections import Counter
from docling_parse.pdf_parser import DoclingPdfParser,ContentConfig,ContentLevel
from docling.datamodel.backend_options import ThreadedDoclingParseBackendOptions
parser=DoclingPdfParser()
doc=parser.load('/home/paul/corpus-structure/docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf',content_config=ContentConfig(char_cells_content_level=ContentLevel.SKIP,bitmaps_content_level=ContentLevel.SKIP))
page=doc.get_page(85)
result={'word_cells':len(page.word_cells),'shapes':len(page.shapes),'fonts':dict(Counter(getattr(c,'font_name',None) for c in page.word_cells)),
        'first_words':[{'text':c.text,'font':getattr(c,'font_name',None),'bbox':c.rect.to_bounding_box().model_dump(mode='json')} for c in page.word_cells[:30]],
        'backend_options':ThreadedDoclingParseBackendOptions().model_dump(mode='json')}
(Path(__file__).resolve().parent/'raw/native-cell-inspection.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='first_words'},indent=2))
