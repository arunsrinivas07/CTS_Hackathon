import pytesseract

from PIL import Image, ImageOps, ImageFilter


pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def preprocess_image(image):

    image = image.convert("L")

    image = ImageOps.autocontrast(image)

    image = image.filter(
        ImageFilter.SHARPEN
    )

    return image


def extract_ocr_text(image):

    image = preprocess_image(image)

    text = pytesseract.image_to_string(
        image,
        config="--psm 6"
    )

    return text