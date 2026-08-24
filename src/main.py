import os
import re
import sys
import json
from pathlib import Path
from datetime import datetime

import pymupdf
import pytesseract

from PIL import (
    Image,
    ImageOps,
    ImageFilter,
    UnidentifiedImageError
)

from pytesseract import TesseractNotFoundError


# ============================================================
# CONFIGURATION
# ============================================================

SUPPORTED_PDF = {".pdf"}
SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg"}

OUTPUT_DIR = Path("outputs")
OUTPUT_FILE = OUTPUT_DIR / "extracted_claim.json"

DEFAULT_WINDOWS_TESSERACT_PATH = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

TESSERACT_CMD = os.environ.get("TESSERACT_CMD")

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

elif (
    os.name == "nt"
    and os.path.exists(DEFAULT_WINDOWS_TESSERACT_PATH)
):
    pytesseract.pytesseract.tesseract_cmd = (
        DEFAULT_WINDOWS_TESSERACT_PATH
    )


# ============================================================
# REQUIRED ML FEATURES
# ============================================================

REQUIRED_FIELDS = [
    "transaction_type",
    "claim_id",
    "bene_id",
    "provider_id",
    "at_physn_npi",
    "claim_type",
    "claim_start_date",
    "claim_end_date",
    "clm_pmt_amt",
    "clm_tot_chrg_amt",
    "line_count",
    "diag_count",
    "proc_count",
    "state"
]


# ============================================================
# DOCUMENT TYPE
# ============================================================

def detect_file_type(file_path):

    suffix = Path(file_path).suffix.lower()

    if suffix in SUPPORTED_PDF:
        return "pdf"

    if suffix in SUPPORTED_IMAGES:
        return "image"

    raise ValueError(
        f"Unsupported file type: {suffix}. "
        "Supported formats: PDF, PNG, JPG, JPEG."
    )


# ============================================================
# PDF TEXT DETECTION
# ============================================================

def pdf_has_text(pdf_path, minimum_chars=30):

    with pymupdf.open(str(pdf_path)) as doc:

        for page in doc:

            text = page.get_text("text").strip()

            if len(text) >= minimum_chars:
                return True

    return False


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_pdf_text(pdf_path):

    pages = []

    with pymupdf.open(str(pdf_path)) as doc:

        for page in doc:

            text = page.get_text("text")

            if text:
                pages.append(text)

    return "\n".join(pages)


# ============================================================
# PDF → IMAGE
# ============================================================

def render_pdf_to_images(pdf_path, dpi=250):

    images = []

    with pymupdf.open(str(pdf_path)) as doc:

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
                [pix.width, pix.height],
                pix.samples
            )

            images.append(image)

    return images


# ============================================================
# OCR IMAGE PREPROCESSING
# ============================================================

def preprocess_image(image):

    image = image.convert("L")

    image = ImageOps.autocontrast(
        image
    )

    image = image.filter(
        ImageFilter.SHARPEN
    )

    return image


# ============================================================
# OCR
# ============================================================

def extract_ocr_text(image):

    try:

        processed_image = preprocess_image(
            image
        )

        text = pytesseract.image_to_string(
            processed_image,
            config="--psm 6"
        )

        return text or ""

    except TesseractNotFoundError as exc:

        raise RuntimeError(
            "Tesseract OCR was not found.\n"
            "Expected location:\n"
            f"{DEFAULT_WINDOWS_TESSERACT_PATH}\n\n"
            "Install Tesseract or set the "
            "TESSERACT_CMD environment variable."
        ) from exc

    except Exception as exc:

        raise RuntimeError(
            f"OCR failed: {exc}"
        ) from exc


# ============================================================
# DOCUMENT LOADER
# ============================================================

def load_document(file_path):

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Path is not a file: {file_path}"
        )

    file_type = detect_file_type(path)

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    if file_type == "pdf":

        try:

            with pymupdf.open(str(path)) as doc:
                page_count = doc.page_count

        except Exception as exc:

            raise RuntimeError(
                f"Could not open PDF: {exc}"
            )

        if page_count == 0:
            raise RuntimeError(
                "PDF contains no pages."
            )

        # Normal PDF
        if pdf_has_text(path):

            print(
                "Text-based PDF detected."
            )

            text = extract_pdf_text(path)

            if text.strip():
                return text

        # Scanned PDF
        print(
            "Scanned PDF detected."
        )

        print(
            "Converting PDF pages to images..."
        )

        images = render_pdf_to_images(
            path
        )

        all_text = []

        for index, image in enumerate(
            images,
            start=1
        ):

            print(
                f"Running OCR on page {index}..."
            )

            page_text = extract_ocr_text(
                image
            )

            all_text.append(
                page_text
            )

        result = "\n".join(
            all_text
        )

        if not result.strip():

            raise RuntimeError(
                "OCR produced no text."
            )

        return result

    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    print(
        "Image detected."
    )

    try:

        image = Image.open(path)

        image.load()

    except UnidentifiedImageError as exc:

        raise RuntimeError(
            "The image is invalid or corrupted."
        ) from exc

    except Exception as exc:

        raise RuntimeError(
            f"Could not open image: {exc}"
        ) from exc

    print(
        "Running OCR..."
    )

    text = extract_ocr_text(
        image
    )

    if not text.strip():

        raise RuntimeError(
            "OCR produced no text."
        )

    return text


# ============================================================
# TEXT PROCESSOR
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = text.replace(
        "\r\n",
        "\n"
    )

    text = text.replace(
        "\r",
        "\n"
    )

    lines = [
        line.strip()
        for line in text.split("\n")
    ]

    lines = [
        line
        for line in lines
        if line
    ]

    cleaned_lines = []

    for line in lines:

        line = re.sub(
            r"[ \t]+",
            " ",
            line
        )

        cleaned_lines.append(
            line
        )

    text = "\n".join(
        cleaned_lines
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    # Normalize common OCR typography
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"'
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    return text.strip()


# ============================================================
# GENERIC LABEL EXTRACTION
# ============================================================

def extract_label_value(
    text,
    labels
):
    """
    Extract a value following a known label.

    Handles:

        Provider ID: 12345

    and:

        Provider ID
        12345
    """

    if not text:
        return None

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for label in labels:

        # ----------------------------------------------------
        # Same-line format
        # ----------------------------------------------------

        pattern = (
            rf"(?:Synthetic\s+)?"
            rf"{re.escape(label)}"
            rf"\s*:?\s*"
            rf"(.+?)"
            rf"(?=\n|$)"
        )

        matches = re.finditer(
            pattern,
            text,
            re.IGNORECASE
        )

        for match in matches:

            value = (
                match.group(1)
                .strip()
                .strip(":")
                .strip()
            )

            if value:
                return value

        # ----------------------------------------------------
        # Separate-line format
        # ----------------------------------------------------

        for index, line in enumerate(
            lines
        ):

            if line.lower().strip(":") == label.lower():

                if index + 1 < len(lines):

                    value = (
                        lines[index + 1]
                        .strip()
                    )

                    if value:
                        return value

    return None


# ============================================================
# ID EXTRACTION
# ============================================================

def extract_id(
    text,
    labels
):

    value = extract_label_value(
        text,
        labels
    )

    if not value:
        return None

    # Keep only the first ID-like token.
    match = re.match(
        r"[A-Za-z0-9][A-Za-z0-9\-_/]*",
        value
    )

    if match:

        return match.group(
            0
        ).strip()

    return None


# ============================================================
# MONEY EXTRACTION
# ============================================================

def extract_money(
    text,
    labels
):

    if not text:
        return None

    for label in labels:

        pattern = (
            rf"(?:Synthetic\s+)?"
            rf"{re.escape(label)}"
            rf"\s*:?\s*"
            rf"\$?\s*"
            rf"([\d,]+(?:\.\d{{1,2}})?)"
        )

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:

                return float(
                    match.group(1)
                    .replace(",", "")
                )

            except ValueError:

                pass

    return None


# ============================================================
# NPI EXTRACTION
# ============================================================

def extract_npi(text):

    labels = [
        "Attending Physician NPI",
        "Attending Physician NPI Number",
        "Physician NPI",
        "Attending NPI",
        "NPI"
    ]

    for label in labels:

        pattern = (
            rf"\b{re.escape(label)}"
            rf"\s*:?\s*(\d{{10}})\b"
        )

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(
                1
            )

    # IMPORTANT:
    # Do NOT use Provider ID as NPI.
    return None


# ============================================================
# DATE PARSING
# ============================================================

DATE_FORMATS = [
    "%B %d, %Y",
    "%B %d %Y",
    "%b %d, %Y",
    "%b %d %Y",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%Y-%m-%d"
]


def parse_date(raw):

    if not raw:
        return None

    raw = (
        raw
        .strip()
        .strip(",")
    )

    for date_format in DATE_FORMATS:

        try:

            return datetime.strptime(
                raw,
                date_format
            ).strftime(
                "%Y-%m-%d"
            )

        except ValueError:

            continue

    return None


# ============================================================
# DATE EXTRACTION
# ============================================================

def extract_service_dates(text):

    raw_value = extract_label_value(
        text,
        [
            "Date of Service",
            "Dates of Service",
            "Date(s) of Service",
            "Service Date",
            "Claim Start Date"
        ]
    )

    if not raw_value:

        return None, None

    date_matches = re.findall(
        r"[A-Za-z]+\s+\d{1,2},?\s*\d{4}"
        r"|\d{1,2}/\d{1,2}/\d{2,4}"
        r"|\d{4}-\d{2}-\d{2}",
        raw_value
    )

    parsed_dates = []

    for date in date_matches:

        parsed = parse_date(
            date
        )

        if parsed:

            parsed_dates.append(
                parsed
            )

    if not parsed_dates:

        return None, None

    # One date = start and end
    if len(parsed_dates) == 1:

        return (
            parsed_dates[0],
            parsed_dates[0]
        )

    return (
        parsed_dates[0],
        parsed_dates[1]
    )


# ============================================================
# STATE EXTRACTION
# ============================================================

def extract_state(text):

    # Example:
    # Example City, NY 10001
    address_match = re.search(
        r",\s*([A-Z]{2})\s+"
        r"\d{5}(?:-\d{4})?\b",
        text
    )

    if address_match:

        return address_match.group(
            1
        )

    # Explicit State: OH
    state_value = extract_label_value(
        text,
        ["State"]
    )

    if state_value:

        match = re.match(
            r"([A-Za-z]{2})\b",
            state_value
        )

        if match:

            return match.group(
                1
            ).upper()

    return None


# ============================================================
# CLAIM TYPE
# ============================================================

def extract_claim_type(text):

    value = extract_label_value(
        text,
        ["Claim Type"]
    )

    if not value:
        return None

    # Remove accidental OCR spillover
    value = value.split(
        "\n"
    )[0].strip()

    return value


# ============================================================
# SERVICE LINE COUNT
# ============================================================

def extract_line_count(text):

    """
    Count itemized service lines.

    Looks for lines containing:
        date + service + procedure code + quantity + amount
    """

    lines = text.splitlines()

    count = 0

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # Date at beginning
        date_at_start = re.match(
            r"^\d{1,2}/\d{1,2}/\d{2,4}\b",
            line
        )

        # CPT/HCPCS-like code
        procedure_code = re.search(
            r"\b[A-Z]?\d{4,5}\b",
            line
        )

        # Dollar amount
        amount = re.search(
            r"\$[\d,]+\.\d{2}",
            line
        )

        if (
            date_at_start
            and procedure_code
            and amount
        ):

            count += 1

    return count if count > 0 else None


# ============================================================
# DIAGNOSIS COUNT
# ============================================================

def extract_diagnosis_count(text):

    codes = set()

    # Example:
    # Primary Diagnosis: R07.9
    # Diagnosis Code: E11.9

    pattern = re.compile(
        r"(?:Primary|Secondary|Principal|Admitting)?"
        r"\s*Diagnosis"
        r"(?:\s*Code)?"
        r"\s*:?\s*"
        r"([A-Z]\d{2}(?:\.\d{1,4})?)",
        re.IGNORECASE
    )

    for match in pattern.finditer(
        text
    ):

        codes.add(
            match.group(1).upper()
        )

    return len(codes) if codes else None


# ============================================================
# PROCEDURE COUNT
# ============================================================

def extract_procedure_count(text):

    codes = set()

    # --------------------------------------------------------
    # CPT / HCPCS explicitly labelled
    # --------------------------------------------------------

    explicit_pattern = re.compile(
        r"(?:CPT|HCPCS)"
        r"\s*(?:Code)?"
        r"\s*:?\s*"
        r"([A-Z]?\d{4,5})",
        re.IGNORECASE
    )

    for match in explicit_pattern.finditer(
        text
    ):

        codes.add(
            match.group(1).upper()
        )

    # --------------------------------------------------------
    # Itemized service rows
    # --------------------------------------------------------

    lines = text.splitlines()

    for line in lines:

        date_at_start = re.match(
            r"^\d{1,2}/\d{1,2}/\d{2,4}\b",
            line.strip()
        )

        if not date_at_start:
            continue

        code_match = re.search(
            r"\b[A-Z]?\d{4,5}\b",
            line
        )

        if code_match:

            codes.add(
                code_match.group(
                    0
                ).upper()
            )

    return len(codes) if codes else None


# ============================================================
# EXTRACT THE 14 REQUIRED FEATURES
# ============================================================

def extract_claim_features(text):

    claim_start_date, claim_end_date = (
        extract_service_dates(text)
    )

    result = {

        # ----------------------------------------------------
        # Fixed
        # ----------------------------------------------------

        "transaction_type":
            "MEDICAL_CLAIM",

        # ----------------------------------------------------
        # Claim identifiers
        # ----------------------------------------------------

        "claim_id":
            extract_id(
                text,
                [
                    "Claim Number",
                    "Claim ID",
                    "Claim #",
                    "Claim No"
                ]
            ),

        "bene_id":
            extract_id(
                text,
                [
                    "Beneficiary ID",
                    "Bene ID",
                    "Beneficiary Number"
                ]
            ),

        "provider_id":
            extract_id(
                text,
                [
                    "Provider ID",
                    "Provider Number"
                ]
            ),

        # ----------------------------------------------------
        # NPI
        # ----------------------------------------------------

        "at_physn_npi":
            extract_npi(text),

        # ----------------------------------------------------
        # Claim type
        # ----------------------------------------------------

        "claim_type":
            extract_claim_type(text),

        # ----------------------------------------------------
        # Dates
        # ----------------------------------------------------

        "claim_start_date":
            claim_start_date,

        "claim_end_date":
            claim_end_date,

        # ----------------------------------------------------
        # Financial
        # ----------------------------------------------------

        "clm_pmt_amt":
            extract_money(
                text,
                [
                    "Medicare Payment",
                    "Claim Payment",
                    "Payment Amount",
                    "Medicare Paid Amount"
                ]
            ),

        "clm_tot_chrg_amt":
            extract_money(
                text,
                [
                    "Total Provider Billed Charges",
                    "Total Billed Charges",
                    "Total Claim Charges",
                    "Total Charges"
                ]
            ),

        # ----------------------------------------------------
        # Counts
        # ----------------------------------------------------

        "line_count":
            extract_line_count(text),

        "diag_count":
            extract_diagnosis_count(text),

        "proc_count":
            extract_procedure_count(text),

        # ----------------------------------------------------
        # State
        # ----------------------------------------------------

        "state":
            extract_state(text)
    }

    return result


# ============================================================
# FIND MISSING FEATURES
# ============================================================

def find_missing_features(features):

    missing = []

    for field in REQUIRED_FIELDS:

        # transaction_type is always generated
        if field == "transaction_type":
            continue

        value = features.get(
            field
        )

        # IMPORTANT:
        # 0 is a valid value.
        # Only None means unavailable.
        if value is None:

            missing.append(
                field
            )

    return missing


# ============================================================
# BUILD FINAL OUTPUT
# ============================================================

def build_output(features):

    missing_features = (
        find_missing_features(
            features
        )
    )

    return {

        "extracted_features":
            features,

        "missing_features":
            missing_features,

        "manual_input_required":
            len(missing_features) > 0
    }


# ============================================================
# SAVE JSON
# ============================================================

def save_output(data):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# COMPLETE PIPELINE
# ============================================================

def process_document(
    document_path
):

    print(
        "\n"
        + "=" * 60
    )

    print(
        "MEDICAL CLAIM EXTRACTION"
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # 1. Document → raw text
    # --------------------------------------------------------

    print(
        "\n[1/4] Extracting document text..."
    )

    raw_text = load_document(
        document_path
    )

    # --------------------------------------------------------
    # 2. Clean text
    # --------------------------------------------------------

    print(
        "[2/4] Processing text..."
    )

    processed_text = clean_text(
        raw_text
    )

    if not processed_text.strip():

        raise RuntimeError(
            "No usable text was obtained from the document."
        )

    # --------------------------------------------------------
    # 3. Extract required features
    # --------------------------------------------------------

    print(
        "[3/4] Extracting required claim features..."
    )

    features = extract_claim_features(
        processed_text
    )

    # --------------------------------------------------------
    # 4. Identify missing features
    # --------------------------------------------------------

    print(
        "[4/4] Checking for missing features..."
    )

    output = build_output(
        features
    )

    return output


# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python -m src.main <document_path>"
        )

        print(
            "\nExample:"
        )

        print(
            r"python -m src.main data\input\hospital_bill.pdf"
        )

        print(
            r"python -m src.main data\input\scanned_hospital_bill.png"
        )

        sys.exit(1)

    document_path = sys.argv[1]

    try:

        result = process_document(
            document_path
        )

        # Save
        save_output(
            result
        )

        # Terminal output
        print(
            "\n"
            + "=" * 60
        )

        print(
            "EXTRACTION RESULT"
        )

        print(
            "=" * 60
        )

        print(
            json.dumps(
                result,
                indent=4,
                ensure_ascii=False
            )
        )

        print(
            "\nSaved to:"
        )

        print(
            OUTPUT_FILE
        )

    except FileNotFoundError as exc:

        print(
            f"\nERROR: {exc}"
        )

        sys.exit(1)

    except Exception as exc:

        print(
            f"\nERROR: {exc}"
        )

        sys.exit(1)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()