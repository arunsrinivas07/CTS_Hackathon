import pymupdf
from PIL import Image


def has_text(pdf_path, minimum_chars=30):

    with pymupdf.open(pdf_path) as doc:

        for page in doc:

            text = page.get_text(
                "text"
            ).strip()

            if len(text) >= minimum_chars:

                return True

    return False


def extract_pdf_text(pdf_path):

    text_pages = []

    with pymupdf.open(pdf_path) as doc:

        for page in doc:

            page_text = page.get_text(
                "text"
            )

            if page_text:

                text_pages.append(
                    page_text
                )

    return "\n".join(text_pages)


def render_pdf(
    pdf_path,
    dpi=250
):

    images = []

    with pymupdf.open(pdf_path) as doc:

        for page in doc:

            matrix = pymupdf.Matrix(
                dpi / 72,
                dpi / 72
            )

            pix = page.get_pixmap(
                matrix=matrix,
                alpha=False
            )

            image = Image.frombytes(
                "RGB",
                [
                    pix.width,
                    pix.height
                ],
                pix.samples
            )

            images.append(image)

    return images