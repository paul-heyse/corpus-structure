"""Source-authored asymmetric pixels, independent of region conversion code."""

from io import BytesIO

import pypdfium2 as pdfium
from PIL import Image, ImageDraw


def asymmetric_pdf(width: int = 200, height: int = 300) -> bytes:
    with Image.new("RGB", (width, height), "white") as pixels:
        draw = ImageDraw.Draw(pixels)
        draw.rectangle((30, 40, 50, 60), fill="red")
        draw.rectangle((90, 40, 110, 60), fill="blue")
        draw.rectangle((65, 35, 75, 45), fill="green")
        with pdfium.PdfDocument.new() as document:
            page = document.new_page(width, height)
            try:
                bitmap = pdfium.PdfBitmap.from_pil(pixels)
                image = pdfium.PdfImage.new(document)
                try:
                    image.set_bitmap(bitmap)
                    image.set_matrix(pdfium.PdfMatrix(width, 0, 0, height, 0, 0))
                    page.insert_obj(image)  # Page now owns the image's native lifetime.
                    page.gen_content()
                finally:
                    if image.page is None:
                        image.close()
                    bitmap.close()
                output = BytesIO()
                document.save(output)
                return output.getvalue()
            finally:
                page.close()
