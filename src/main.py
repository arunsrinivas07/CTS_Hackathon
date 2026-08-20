import sys
import json
from pathlib import Path

from src.document_loader import (
    has_text,
    extract_pdf_text,
    render_pdf
)

from src.ocr import extract_ocr_text

from src.text_processor import clean_text

from src.json_extractor import (
    extract_structured_data
)


# ============================================================
# DOCUMENT PROCESSING
# ============================================================

def process_document(file_path):

    path = Path(file_path)

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    if path.suffix.lower() == ".pdf":

        # -----------------------------------------------
        # Text-based PDF
        # -----------------------------------------------

        if has_text(str(path)):

            print(
                "Text-based PDF detected."
            )

            raw_text = extract_pdf_text(
                str(path)
            )

        # -----------------------------------------------
        # Scanned PDF
        # -----------------------------------------------

        else:

            print(
                "Scanned PDF detected."
            )

            print(
                "Running OCR..."
            )

            raw_text = ""

            pages = render_pdf(
                str(path)
            )

            for image in pages:

                page_text = (
                    extract_ocr_text(
                        image
                    )
                )

                raw_text += (
                    page_text
                    + "\n"
                )

    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    elif path.suffix.lower() in [
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".tif",
        ".bmp"
    ]:

        print(
            "Image detected."
        )

        print(
            "Running OCR..."
        )

        from PIL import Image

        image = Image.open(
            path
        )

        raw_text = extract_ocr_text(
            image
        )

    # --------------------------------------------------------
    # INVALID FILE
    # --------------------------------------------------------

    else:

        raise ValueError(
            "Unsupported file type. "
            "Use PDF, PNG, JPG, JPEG, TIFF, "
            "or BMP."
        )

    # --------------------------------------------------------
    # CLEAN TEXT
    # --------------------------------------------------------

    processed_text = clean_text(
        raw_text
    )

    return processed_text


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # CHECK ARGUMENT
    # --------------------------------------------------------

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python -m src.main "
            "<document_path>"
        )

        return

    input_file = Path(
        sys.argv[1]
    )

    # --------------------------------------------------------
    # CHECK FILE
    # --------------------------------------------------------

    if not input_file.exists():

        print(
            f"File not found: "
            f"{input_file}"
        )

        return

    # --------------------------------------------------------
    # PROCESS DOCUMENT
    # --------------------------------------------------------

    processed_text = process_document(
        str(input_file)
    )

    # ========================================================
    # SAVE PROCESSED TEXT
    # ========================================================

    text_output_dir = Path(
        "data/processed_text"
    )

    text_output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    text_output_file = (
        text_output_dir
        / f"{input_file.stem}.txt"
    )

    with open(
        text_output_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            processed_text
        )

    # ========================================================
    # CONVERT TEXT → STRUCTURED JSON
    # ========================================================

    json_data = extract_structured_data(

        text=processed_text,

        file_name=input_file.name,

        file_type=input_file.suffix.lower()
    )

    # ========================================================
    # SAVE JSON
    # ========================================================

    json_output_dir = Path(
        "data/processed_json"
    )

    json_output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    json_output_file = (
        json_output_dir
        / f"{input_file.stem}.json"
    )

    with open(
        json_output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            json_data,
            file,
            indent=4,
            ensure_ascii=False
        )

    # ========================================================
    # DISPLAY RESULT
    # ========================================================

    print()
    print(
        "======================================"
    )

    print(
        "Document processing completed."
    )

    print(
        "======================================"
    )

    print()

    print(
        f"Processed text:"
    )

    print(
        f"  {text_output_file}"
    )

    print()

    print(
        f"Structured JSON:"
    )

    print(
        f"  {json_output_file}"
    )

    print()

    print(
        "======================================"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()