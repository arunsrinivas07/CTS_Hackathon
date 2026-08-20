import os
import shutil
import datetime
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

SAMPLE_DIR_ROOT = r"f:\CTS_main\sample_test_files"
SAMPLE_DIR_BACKEND2 = r"f:\CTS_main\backend2\sample_files"

for d in [SAMPLE_DIR_ROOT, SAMPLE_DIR_BACKEND2]:
    os.makedirs(d, exist_ok=True)

def generate_single_claim_txt(filename: str, provider_id: str, provider_name: str, state: str,
                              tier: str, claim_id: str, bene_id: str, reimb: float, ded: float,
                              dob: str, dod: str, claim_type: str, att_phy: str, oper_phy: str,
                              oth_phy: str, diag_code: str, output_dirs: list):
    
    dod_str = f"DOD: {dod}" if dod else "DOD: N/A"
    phy_str = f"{att_phy} | {oper_phy} | {oth_phy}"
    
    content = f"""================================================================================
CareGuard AI — Single Claim Intelligence Report (v2 Schema Test File)
Target Risk Tier: {tier.upper()}
================================================================================
Provider ID: {provider_id} | Provider Name: {provider_name} | State: {state}
Report Date: {datetime.date.today().strftime('%Y-%m-%d')}
--------------------------------------------------------------------------------
Itemized Claim Details (1 Claim)
--------------------------------------------------------------------------------
Claim Number: {claim_id}
Bene ID: {bene_id}
Dates of Service: 2023-05-10 to 2023-05-12
DOB / DOD: DOB: {dob} | {dod_str}
Attending / Operating / Other Physicians: {phy_str}
Claim Type: {claim_type}
Reimbursed Amount: ${reimb:,.2f}
Deductible Paid: ${ded:.2f}
Primary Diagnosis: {diag_code}
================================================================================
"""
    first_dir = output_dirs[0]
    first_path = os.path.join(first_dir, filename)
    with open(first_path, "w", encoding="utf-8") as f:
        f.write(content)

    for d in output_dirs[1:]:
        target_path = os.path.join(d, filename)
        shutil.copy2(first_path, target_path)


def generate_single_claim_pdf(filename: str, provider_id: str, provider_name: str, state: str,
                              tier: str, claim_id: str, bene_id: str, reimb: float, ded: float,
                              dob: str, dod: str, claim_type: str, att_phy: str, oper_phy: str,
                              oth_phy: str, diag_code: str, output_dirs: list):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#1E293B'))
    meta_style = ParagraphStyle('DocMeta', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#475569'))
    header_cell = ParagraphStyle('HCell', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.white, fontName='Helvetica-Bold')
    cell_style = ParagraphStyle('BCell', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#1E293B'))
    ghost_style = ParagraphStyle('GCell', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#DC2626'), fontName='Helvetica-Bold')

    first_dir = output_dirs[0]
    first_path = os.path.join(first_dir, filename)

    doc = SimpleDocTemplate(first_path, pagesize=landscape(letter), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elements = []

    elements.append(Paragraph(f"<b>CareGuard AI — Single Claim Intelligence Report</b>", title_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        f"<b>Provider ID:</b> {provider_id} &nbsp;|&nbsp; <b>Provider Name:</b> {provider_name} &nbsp;|&nbsp; <b>CMS State:</b> {state}<br/>"
        f"<b>Target Tier:</b> {tier.upper()} &nbsp;|&nbsp; <b>Total Claims:</b> 1 &nbsp;|&nbsp; <b>Report Date:</b> {datetime.date.today().strftime('%Y-%m-%d')}",
        meta_style
    ))
    elements.append(Spacer(1, 10))

    table_data = [[
        Paragraph("Claim Number", header_cell),
        Paragraph("Bene ID", header_cell),
        Paragraph("Dates of Service", header_cell),
        Paragraph("DOB / DOD", header_cell),
        Paragraph("Attending / Operating / Other", header_cell),
        Paragraph("Type", header_cell),
        Paragraph("Reimbursed", header_cell),
        Paragraph("Deductible", header_cell),
        Paragraph("Diag", header_cell),
    ]]

    dates_str = "2023-05-10 to 2023-05-12"
    dob_dod_str = f"DOB: {dob} | DOD: {dod if dod else 'N/A'}"
    phy_str = f"{att_phy} | {oper_phy} | {oth_phy}"
    c_style = ghost_style if dod else cell_style

    table_data.append([
        Paragraph(claim_id, cell_style),
        Paragraph(bene_id, cell_style),
        Paragraph(dates_str, cell_style),
        Paragraph(dob_dod_str, c_style),
        Paragraph(phy_str, cell_style),
        Paragraph(claim_type, cell_style),
        Paragraph(f"${reimb:,.2f}", cell_style),
        Paragraph(f"${ded:.2f}", cell_style),
        Paragraph(diag_code, cell_style),
    ])

    t = Table(table_data, colWidths=[140, 60, 110, 110, 150, 55, 65, 45, 35])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    elements.append(t)

    try:
        doc.build(elements)
    except Exception as e:
        print(f"Notice: Could not build {first_path}: {e}")

    for d in output_dirs[1:]:
        target_path = os.path.join(d, filename)
        shutil.copy2(first_path, target_path)


def main():
    dirs = [SAMPLE_DIR_ROOT, SAMPLE_DIR_BACKEND2]
    print("======================================================================")
    print("  GENERATING SINGLE-CLAIM SYNTHETIC PDF & TXT TEST FILES")
    print("======================================================================")

    samples = [
        ("single_claim_low_risk.pdf", "single_claim_low_risk.txt", "PRV_SINGLE_LOW_1", "Low Risk Clinic", "NY", "Low Risk", "CLM-SINGLE-LOW-001", "BENE-S-101", 350.0, 50.0, "1955-01-01", "", "Outpatient", "PHY1001", "None", "None", "401.9"),
        ("single_claim_medium_risk.pdf", "single_claim_medium_risk.txt", "PRV_SINGLE_MED_2", "Metro Single Health", "TX", "Medium Risk", "CLM-SINGLE-MED-002", "BENE-S-202", 4500.0, 100.0, "1948-03-15", "", "Inpatient", "PHY2001", "PHY2002", "None", "401.9"),
        ("single_claim_high_risk.pdf", "single_claim_high_risk.txt", "PRV_SINGLE_HIGH_3", "Apex Specialty Care", "FL", "High Risk", "CLM-SINGLE-HIGH-003", "BENE-S-303", 28000.0, 250.0, "1940-06-20", "", "Inpatient", "PHY3001", "PHY3002", "PHY3003", "401.9"),
        ("single_claim_critical_risk.pdf", "single_claim_critical_risk.txt", "PRV_SINGLE_CRIT_4", "Omni Billing Network", "FL", "Critical Risk", "CLM-SINGLE-CRIT-004", "BENE-S-404", 185000.0, 500.0, "1935-11-12", "2020-05-10", "Inpatient", "PHY4001", "PHY4002", "PHY4003", "401.9"),
    ]

    for pdf_name, txt_name, prv_id, prv_name, state, tier, clm_id, bene_id, reimb, ded, dob, dod, ctype, att, oper, oth, diag in samples:
        generate_single_claim_txt(txt_name, prv_id, prv_name, state, tier, clm_id, bene_id, reimb, ded, dob, dod, ctype, att, oper, oth, diag, dirs)
        generate_single_claim_pdf(pdf_name, prv_id, prv_name, state, tier, clm_id, bene_id, reimb, ded, dob, dod, ctype, att, oper, oth, diag, dirs)
        print(f"  Generated: {pdf_name:<30} & {txt_name:<30}")

    print("======================================================================")
    print("  Single-claim test files successfully created!")

if __name__ == "__main__":
    main()
