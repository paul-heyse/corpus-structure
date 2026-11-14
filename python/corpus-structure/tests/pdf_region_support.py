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


def landmark_pdf() -> bytes:
    # Media origin is deliberately nonzero; crop clips all four media edges. Independent
    # red landmark center: absolute PDF(100,450), media-relative TOPLEFT(90,170).
    content = b"1 0 0 rg 95 445 10 10 re f\nBT /F1 12 Tf 0 1 -1 0 200 250 Tm (ROTATED) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R 5 0 R 6 0 R] /Count 4 >>",
    ]
    for rotation in (0, 90, 180, 270):
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [10 20 410 620] "
                f"/CropBox [60 120 360 520] /Rotate {rotation} "
                "/Resources << /Font << /F1 8 0 R >> >> /Contents 7 0 R >>"
            ).encode()
        )
    objects.extend(
        [
            b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n"
            + content
            + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]
    )
    result = b"%PDF-1.4\n"
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(result)
    result += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    result += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return (
        result
        + f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
