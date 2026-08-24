import os
import re
import sys
import json
from pathlib import Path
from datetime import datetime

try:
    import pymupdf
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

try:
    import pytesseract
    from pytesseract import TesseractNotFoundError
    HAS_PYTESSERACT = True
except ImportError:
    pytesseract = None
    TesseractNotFoundError = Exception
    HAS_PYTESSERACT = False

from PIL import (
    Image,
    ImageOps,
    ImageFilter,
    UnidentifiedImageError
)


# ============================================================
# CONFIGURATION
# ============================================================

SUPPORTED_PDF = {".pdf"}
SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg"}
SUPPORTED_TXT = {".txt"}

OUTPUT_DIR = Path("outputs")
OUTPUT_FILE = OUTPUT_DIR / "extracted_claim.json"

DEFAULT_WINDOWS_TESSERACT_PATH = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

TESSERACT_CMD = os.environ.get("TESSERACT_CMD")

if HAS_PYTESSERACT:
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

    if suffix in SUPPORTED_TXT:
        return "txt"

    raise ValueError(
        f"Unsupported file type: {suffix}. "
        "Supported formats: PDF, PNG, JPG, JPEG, TXT."
    )


# ============================================================
# PDF TEXT DETECTION
# ============================================================

def pdf_has_text(pdf_path, minimum_chars=30):
    if pymupdf is None:
        raise RuntimeError("PyMuPDF / fitz library is not installed in environment.")
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
    if pymupdf is None:
        raise RuntimeError("PyMuPDF / fitz library is not installed in environment.")
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
    if pymupdf is None:
        raise RuntimeError("PyMuPDF / fitz library is not installed in environment.")
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
    # TXT
    # --------------------------------------------------------
    if file_type == "txt":
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as exc:
            raise RuntimeError(f"Could not read text file: {exc}")

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


def extract_key_value(text, labels):
    if not text:
        return None
    for label in labels:
        # Pattern matching 'Label: Value', 'Label (alias): Value', or 'Label\nValue'
        pattern = rf"(?:{re.escape(label)}|\b{re.escape(label)}\b)\s*(?:\([^\)]+\))?\s*\*?\s*:?\s*([^\n\r]+)"
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw_val = match.group(1).strip().strip(":").strip()
            # Clean JSON syntax characters (quotes, colons, trailing commas)
            val = re.sub(r'^[":,\s]+|[":,\s]+$', '', raw_val).strip()
            if val and not val.startswith("*") and not val.startswith("(") and val.lower() not in ["select...", "full name", "dd-mm-yyyy", "information", "required field", "e.g. appendectomy"]:
                return val
    return None


def extract_integer(text, labels):
    if not text:
        return None
    for label in labels:
        pattern = rf"(?:{re.escape(label)}|\b{re.escape(label)}\b)\s*(?:\([^\)]+\))?\s*\*?\s*:?\s*[\"\':\s]*(-?\d+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                pass
    return None


def extract_text_field(text, labels):
    return extract_key_value(text, labels)


def extract_icd_code(text):
    match = re.search(r"(?:ICD-10\s*Code|ICD-10\s*Dx|ICD-10|ICD\s*Code)\s*(?:\d+)?\s*\*?\s*:?\s*[\"\':\s]*([A-Z]\d{2}(?:\.\d{1,4})?)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def extract_cpt_code(text):
    match = re.search(r"(?:Primary\s*CPT\s*Code|Primary\s*CPT|CPT\s*Code|CPT)\s*(?:\d+)?\s*\*?\s*:?\s*[\"\':\s]*([A-Z]?\d{4,5})", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


# ============================================================
# EXTRACT THE REQUIRED FEATURES
# ============================================================

def extract_claim_features(text):
    clean_txt = clean_text(text)

    # 0. Direct JSON parser check
    json_data = {}
    if clean_txt:
        json_match = re.search(r"\{.*\}", clean_txt, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                if isinstance(parsed, dict):
                    json_data = parsed
            except Exception:
                pass

    def get_json_or_regex(json_keys, regex_labels, extractor_fn=extract_key_value):
        for k in json_keys:
            if k in json_data and json_data[k] is not None:
                val = json_data[k]
                if isinstance(val, (int, float)):
                    return val
                val_str = str(val).strip()
                val_clean = re.sub(r'^[":,\s]+|[":,\s]+$', '', val_str)
                if val_clean:
                    return val_clean
        return extractor_fn(clean_txt, regex_labels)

    # 1. Dates
    start_date = get_json_or_regex(["claim_start_date", "service_date", "claim_date"], ["Claim Start Date", "claim_start_date", "Date of Service", "Service Start Date"])
    end_date = get_json_or_regex(["claim_end_date", "service_end_date"], ["Claim End Date", "claim_end_date", "Service End Date"])
    if not start_date or not end_date:
        parsed_start, parsed_end = extract_service_dates(clean_txt)
        start_date = start_date or parsed_start
        end_date = end_date or parsed_end

    start_date = parse_date(str(start_date)) or (str(start_date) if start_date else None)
    end_date = parse_date(str(end_date)) or (str(end_date) if end_date else None)

    # 2. Claim Type
    claim_type_raw = str(get_json_or_regex(["claim_type", "type"], ["Claim Type", "claim_type"]) or "")
    claim_type = None
    if claim_type_raw:
        for ct in ["outpatient", "inpatient", "carrier", "dme", "hha", "hospice", "snf"]:
            if ct in claim_type_raw.lower():
                claim_type = ct
                break

    # 3. State
    state_val = str(get_json_or_regex(["state"], ["State", "state"]) or "")
    if state_val:
        m = re.search(r"\b([A-Za-z]{2})\b", state_val)
        state_val = m.group(1).upper() if m else state_val.upper()
    else:
        state_val = extract_state(clean_txt)

    # Money helper
    def get_money(json_keys, regex_labels):
        for k in json_keys:
            if k in json_data and json_data[k] is not None:
                try:
                    return float(json_data[k])
                except (ValueError, TypeError):
                    pass
        return extract_money(clean_txt, regex_labels)

    # Integer helper
    def get_int(json_keys, regex_labels, fallback_fn=None):
        for k in json_keys:
            if k in json_data and json_data[k] is not None:
                try:
                    return int(json_data[k])
                except (ValueError, TypeError):
                    pass
        res = extract_integer(clean_txt, regex_labels)
        if res is not None:
            return res
        return fallback_fn(clean_txt) if fallback_fn else None

    result = {
        "transaction_type": "MEDICAL_CLAIM",
        "claim_id": str(get_json_or_regex(["claim_id", "claim_number", "claimId"], ["Claim ID", "claim_id", "Claim Number", "Claim #"]) or extract_id(clean_txt, ["Claim ID", "Claim Number"]) or ""),
        "bene_id": str(get_json_or_regex(["bene_id", "beneficiary_id", "patient_id"], ["Beneficiary ID", "bene_id", "Bene ID"]) or extract_id(clean_txt, ["Beneficiary ID", "Bene ID"]) or ""),
        "patient_name": get_json_or_regex(["patient_name", "patient"], ["Patient Name", "patient_name"]),
        "dob": get_json_or_regex(["dob", "date_of_birth"], ["Date of Birth", "dob", "Birth Date"]),
        "provider_id": str(get_json_or_regex(["provider_id", "provider_npi", "npi"], ["Provider NPI", "provider_id", "Provider ID"]) or extract_id(clean_txt, ["Provider NPI", "Provider ID"]) or ""),
        "at_physn_npi": str(get_json_or_regex(["at_physn_npi", "physician_npi"], ["Attending Physician NPI", "at_physn_npi", "Attending NPI"]) or extract_npi(clean_txt) or ""),
        "claim_type": claim_type or "outpatient",
        "claim_start_date": start_date,
        "claim_end_date": end_date,
        "clm_pmt_amt": get_money(["clm_pmt_amt", "payment_amount"], ["Claim Payment Amount", "Payment Amount ($)", "Payment Amount", "clm_pmt_amt", "Medicare Payment"]),
        "clm_tot_chrg_amt": get_money(["clm_tot_chrg_amt", "total_billed_amount", "billed_amount"], ["Total Billed Charge Amount", "Total Billed Amount", "Total Amount ($)", "Total Charges", "clm_tot_chrg_amt"]),
        "line_count": get_int(["line_count"], ["Line Item Count", "Line Count", "line_count"], extract_line_count),
        "diag_count": get_int(["diag_count"], ["Diagnosis Code Count", "Diagnosis Count", "diag_count"], extract_diagnosis_count),
        "proc_count": get_int(["proc_count"], ["Procedure Code Count", "Procedure Count", "proc_count"], extract_procedure_count),
        "primary_diagnosis": get_json_or_regex(["primary_diagnosis", "diagnosis"], ["Primary Diagnosis", "primary_diagnosis"]),
        "icd_code": get_json_or_regex(["icd_code", "icd10"], ["ICD-10 Code"]) or extract_icd_code(clean_txt),
        "primary_cpt": get_json_or_regex(["primary_cpt", "cpt_code"], ["Primary CPT Code"]) or extract_cpt_code(clean_txt),
        "state": state_val if state_val else None,
    }

    # Clean up empty string IDs to None if needed
    for key in ["claim_id", "bene_id", "provider_id", "at_physn_npi"]:
        if result[key] == "":
            result[key] = None

    try:
        print("\n============================================================")
        print("=== EXTRACTED RAW DOCUMENT TEXT ===")
        print("============================================================")
        print(text if text else "[No text extracted]")
        print("============================================================")
        print("=== EXTRACTED CLAIM FEATURES (DICT) ===")
        print(json.dumps(result, indent=2, default=str))
        print("============================================================\n")
    except Exception as e:
        print(f"[EXTRACTOR LOG ERROR] {e}")

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