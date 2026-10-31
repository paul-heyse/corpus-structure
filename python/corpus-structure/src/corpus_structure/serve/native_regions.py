"""On-demand region rendering under an explicit retained-original binding."""
from __future__ import annotations

from collections.abc import Mapping
from io import BytesIO
from math import isfinite
from typing import Any


def render_pdf_region(original: bytes, region: Mapping[str, Any], *, scale: float = 2.0) -> bytes:
    """Render a typed PDF-point region; never use recognized-text offsets as geometry."""
    if not original.startswith(b'%PDF-') or not isfinite(scale) or not 0 < scale <= 8:
        raise ValueError('PDF region requires retained PDF bytes and scale in (0,8]')
    import pypdfium2 as pdfium

    document=pdfium.PdfDocument(original)
    try:
        page_no=int(region['page_no'])
        if not 1 <= page_no <= len(document):
            raise ValueError('physical page outside retained original')
        page=document[page_no-1]
        try:
            width,height=page.get_size()
            if abs(width-float(region['page_width']))>1e-5 or abs(height-float(region['page_height']))>1e-5:
                raise ValueError('retained page dimensions differ from native geometry')
            left,top,right,bottom=(float(region[n]) for n in ('left','top','right','bottom'))
            if not all(isfinite(x) for x in (left,top,right,bottom)) or not 0 <= left < right <= width:
                raise ValueError('invalid region coordinates')
            if region['origin']=='top_left':
                if not 0 <= top < bottom <= height:
                    raise ValueError('invalid top-left region')
                crop=(left,height-bottom,width-right,top)
            elif region['origin']=='bottom_left':
                if not 0 <= bottom < top <= height:
                    raise ValueError('invalid bottom-left region')
                crop=(left,bottom,width-right,height-top)
            else:
                raise ValueError('unsupported region origin')
            bitmap=page.render(scale=scale,crop=crop)
            try:
                image=bitmap.to_pil()
                try:
                    output=BytesIO()
                    image.save(output,format='PNG')
                    return output.getvalue()
                finally:
                    image.close()
            finally:
                bitmap.close()
        finally:
            page.close()
    finally:
        document.close()
