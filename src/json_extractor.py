import re
from datetime import datetime


# ============================================================
# OCR NORMALIZATION
# ============================================================

def normalize_ocr_text(text):
    """
    Fix a few common OCR mistakes.
    """

    replacements = {
        "RECQRD": "RECORD",
        "NOTA REAL": "NOT A REAL",
        "RO7.9": "R07.9",
        "RO7": "R07",
        "—": "-",
        "–": "-"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


# ============================================================
# GENERIC LABEL-VALUE EXTRACTION
# ============================================================

def get_value(text, label, all_labels):
    """
    Extract a value after a label.

    Handles:

        Provider: Riverside General Hospital

    and:

        Provider
        Riverside General Hospital

    and multiple labels on the same line:

        Provider: Riverside General Hospital,
        Claim Number: SYN-CLM-2026-001247
    """

    if not text:
        return None

    # --------------------------------------------------------
    # CASE 1
    # Label: Value
    # --------------------------------------------------------

    pattern = (
        rf"{re.escape(label)}\s*:\s*"
        rf"(.+?)"
        rf"(?=\s+[A-Za-z][A-Za-z /&\-]+?\s*:|$)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if match:

        value = match.group(1).strip()

        value = value.rstrip(
            " ,:;-_"
        )

        return value.strip()

    # --------------------------------------------------------
    # CASE 2
    # Label on one line
    # Value on next line
    # --------------------------------------------------------

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for index, line in enumerate(lines):

        if line.lower() == label.lower():

            if index + 1 < len(lines):

                value = lines[index + 1].strip()

                return value

    return None


# ============================================================
# PROVIDER NAME
# ============================================================

def extract_provider_name(text):

    match = re.search(
        r"Provider\s*:\s*"
        r"(.+?)"
        r"(?=\s*,?\s*Claim Number\s*:)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1).strip()

    return get_value(
        text,
        "Provider",
        []
    )


# ============================================================
# PROVIDER ID
# ============================================================

def extract_provider_id(text):

    match = re.search(
        r"Provider ID\s*:\s*"
        r"(SYN-[A-Z]+-\d+)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1)

    return None


# ============================================================
# BENEFICIARY ID
# ============================================================

def extract_beneficiary_id(text):

    match = re.search(
        r"Beneficiary ID\s*:\s*"
        r"(SYN-[A-Z]+-\d+)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1)

    return None


# ============================================================
# PATIENT NAME
# ============================================================

def extract_patient_name(text):

    match = re.search(
        r"Patient Name\s*:\s*"
        r"(.+?)"
        r"(?=\s+Admission Type\s*:)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1).strip()

    return get_value(
        text,
        "Patient Name",
        []
    )


# ============================================================
# DATE OF BIRTH
# ============================================================

def extract_date_of_birth(text):

    match = re.search(
        r"Date of Birth\s*:\s*"
        r"([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1)

    return None


# ============================================================
# AGE
# ============================================================

def extract_age(
    date_of_birth,
    date_of_service
):
    """
    Calculate age at time of service.
    """

    if not date_of_birth:
        return None

    try:

        dob = datetime.strptime(
            date_of_birth,
            "%B %d, %Y"
        )

        # Get first date from service period
        match = re.search(
            r"([A-Za-z]+\s+\d{1,2},\s+\d{4})",
            date_of_service or ""
        )

        if match:

            service_date = datetime.strptime(
                match.group(1),
                "%B %d, %Y"
            )

        else:

            service_date = datetime.today()

        age = (
            service_date.year
            - dob.year
            - (
                (service_date.month, service_date.day)
                <
                (dob.month, dob.day)
            )
        )

        return age

    except ValueError:

        return None


# ============================================================
# DIAGNOSIS
# ============================================================

def extract_diagnosis(text):

    match = re.search(
        r"Primary Diagnosis\s*:\s*"
        r"([A-Z]\d{2}(?:\.\d+)?)"
        r"\s*[-]\s*"
        r"(.+?)"
        r"(?=\s+Admission Type\s*:)",
        text,
        re.IGNORECASE
    )

    if match:

        return (
            match.group(1).upper(),
            match.group(2).strip()
        )

    return None, None


# ============================================================
# MONEY
# ============================================================

def extract_money_from_label(
    text,
    label
):
    """
    Extract money values such as:

        Total Provider Billed Charges: $5,740.00
    """

    pattern = (
        rf"{re.escape(label)}\s*:\s*"
        rf"\$([\d,]+\.\d{{2}})"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if match:

        return float(
            match.group(1)
            .replace(",", "")
        )

    return None


# ============================================================
# DATE OF SERVICE
# ============================================================

def extract_date_of_service(text):

    match = re.search(
        r"Date of Service\s*:\s*"
        r"(.+?)"
        r"(?=\s+Primary Diagnosis\s*:)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1).strip()

    return None


# ============================================================
# CLAIM INFORMATION
# ============================================================

def extract_claim_number(text):

    match = re.search(
        r"Claim Number\s*:\s*"
        r"(SYN-[A-Z]+-\d+)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1)

    return None


def extract_claim_type(text):

    match = re.search(
        r"Claim Type\s*:\s*"
        r"(.+?)"
        r"(?=\s+Date of Service\s*:)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1).strip()

    return None


# ============================================================
# ADDRESS
# ============================================================

def extract_address(text):

    match = re.search(
        r"Address\s*:\s*"
        r"(.+?)"
        r"(?=\s+Date of Service\s*:)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1).strip()

    return None


# ============================================================
# MEDICARE COVERAGE
# ============================================================

def extract_coverage(text):

    match = re.search(
        r"Medicare Coverage\s*:\s*"
        r"(.+?)"
        r"(?=\s+Attending Specialty\s*:)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1).strip()

    return None


# ============================================================
# MEMBER REFERENCE
# ============================================================

def extract_member_reference(text):

    match = re.search(
        r"Member/Policy Reference\s*:\s*"
        r".*?(SYN-MCR-\d+)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1)

    return None


# ============================================================
# ADMISSION TYPE
# ============================================================

def extract_admission_type(text):

    match = re.search(
        r"Admission Type\s*:\s*"
        r"(.+?)"
        r"(?=\s+Place of Service\s*:)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1).strip()

    return None


# ============================================================
# PLACE OF SERVICE
# ============================================================

def extract_place_of_service(text):

    match = re.search(
        r"Place of Service\s*:\s*"
        r"(.+?)"
        r"(?=\s+Attending Specialty\s*:)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1).strip()

    return None


# ============================================================
# ATTENDING SPECIALTY
# ============================================================

def extract_specialty(text):

    match = re.search(
        r"Attending Specialty\s*:\s*"
        r"(.+?)(?=\n|$)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1).strip()

    return None


# ============================================================
# ITEMIZED SERVICES
# ============================================================

def extract_services(text):

    services = []

    # --------------------------------------------------------
    # Current scanned document does not preserve the table.
    #
    # Therefore we only extract services if OCR actually
    # provides recognizable rows.
    # --------------------------------------------------------

    pattern = re.compile(
        r"(?P<date>\d{2}/\d{2}/\d{2})\s+"
        r"(?P<procedure>.*?)\s+"
        r"(?P<code>\d{4,5})\s+"
        r"(?P<quantity>\d+)\s+"
        r"\$(?P<amount>[\d,]+\.\d{2})",
        re.IGNORECASE
    )

    matches = pattern.finditer(text)

    for match in matches:

        services.append({

            "date":
                match.group("date"),

            "procedure":
                match.group("procedure").strip(),

            "procedure_code":
                match.group("code"),

            "quantity":
                int(
                    match.group("quantity")
                ),

            "billed_amount":
                float(
                    match.group("amount")
                    .replace(",", "")
                )
        })

    return services


# ============================================================
# SUPPORTING DOCUMENTS
# ============================================================

def extract_supporting_documents(text):

    documents = []

    known_documents = [

        "Physician order / clinical note",

        "Laboratory result",

        "CT procedure report",

        "Itemized provider bill"
    ]

    for document in known_documents:

        if document.lower() in text.lower():

            documents.append(document)

    return documents


# ============================================================
# MAIN STRUCTURED EXTRACTION
# ============================================================

def extract_structured_data(
    text,
    file_name,
    file_type
):

    # --------------------------------------------------------
    # Normalize OCR
    # --------------------------------------------------------

    text = normalize_ocr_text(text)

    # --------------------------------------------------------
    # DATE OF SERVICE
    # --------------------------------------------------------

    date_of_service = (
        extract_date_of_service(text)
    )

    # --------------------------------------------------------
    # DATE OF BIRTH
    # --------------------------------------------------------

    date_of_birth = (
        extract_date_of_birth(text)
    )

    # --------------------------------------------------------
    # DIAGNOSIS
    # --------------------------------------------------------

    diagnosis_code, diagnosis_description = (
        extract_diagnosis(text)
    )

    # --------------------------------------------------------
    # BUILD STRUCTURED JSON
    # --------------------------------------------------------

    structured_data = {

        "document": {

            "file_name":
                file_name,

            "file_type":
                file_type,

            "extraction_method":
                "OCR"
        },

        "provider": {

            "name":
                extract_provider_name(text),

            "provider_id":
                extract_provider_id(text),

            "address":
                extract_address(text)
        },

        "patient": {

            "beneficiary_id":
                extract_beneficiary_id(text),

            "name":
                extract_patient_name(text),

            "date_of_birth":
                date_of_birth,

            "age_at_service":
                extract_age(
                    date_of_birth,
                    date_of_service
                ),

            "coverage":
                extract_coverage(text),

            "member_reference":
                extract_member_reference(text)
        },

        "claim": {

            "claim_number":
                extract_claim_number(text),

            "claim_type":
                extract_claim_type(text),

            "date_of_service":
                date_of_service,

            "admission_type":
                extract_admission_type(text),

            "place_of_service":
                extract_place_of_service(text)
        },

        "clinical": {

            "primary_diagnosis_code":
                diagnosis_code,

            "primary_diagnosis":
                diagnosis_description,

            "attending_specialty":
                extract_specialty(text)
        },

        "services":
            extract_services(text),

        "financial": {

            "total_billed":
                extract_money_from_label(
                    text,
                    "Total Provider Billed Charges"
                ),

            "medicare_approved_amount":
                extract_money_from_label(
                    text,
                    "Synthetic Medicare-Approved Amount"
                ),

            "medicare_payment":
                extract_money_from_label(
                    text,
                    "Synthetic Medicare Payment"
                ),

            "beneficiary_responsibility":
                extract_money_from_label(
                    text,
                    "Synthetic Beneficiary Responsibility"
                )
        },

        "supporting_documents":
            extract_supporting_documents(text)
    }

    return structured_data