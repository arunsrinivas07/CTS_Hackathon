import os
import datetime
import shutil
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR_V2 = os.path.join(r"F:\CTS_main\sample_test_files", "v2_provider_samples")
SAMPLE_DIR_BACKEND2 = os.path.join(BASE_DIR, "sample_files")

os.makedirs(SAMPLE_DIR_V2, exist_ok=True)
os.makedirs(SAMPLE_DIR_BACKEND2, exist_ok=True)

def generate_provider_txt(filename: str, provider_id: str, provider_name: str, state: str,
                          tier: str, claim_count: int, avg_reimb: float, ghost_count: int,
                          phys_count: int, output_dirs: list):
    lines = []
    lines.append("================================================================================")
    lines.append(f"  CAREGUARD AI -- MEDICARE PROVIDER BATCH CLAIM REPORT ({tier.upper()} RISK)")
    lines.append("================================================================================")
    lines.append(f"Provider ID      : {provider_id}")
    lines.append(f"Provider Name    : {provider_name}")
    lines.append(f"CMS State        : {state}")
    lines.append(f"County           : 120")
    lines.append(f"Target Risk Tier : {tier.upper()}")
    lines.append(f"Total Claims     : {claim_count}")
    lines.append(f"Report Generated : {datetime.date.today().strftime('%Y-%m-%d')}")
    lines.append("================================================================================")
    lines.append("")
    lines.append("ITEMIZED PROVIDER CLAIMS:")
    lines.append("--------------------------------------------------------------------------------")

    for i in range(1, claim_count + 1):
        clm_id = f"CLM-{provider_id}-{i:04d}"
        bene_id = f"BENE-{1000 + i}"
        is_ghost = (i <= ghost_count)
        start_dt = "2023-05-10"
        end_dt = "2023-05-12"
        dob = "1948-03-15"
        dod = "2022-11-04" if is_ghost else ""
        reimb = avg_reimb * (1.0 + (i % 5) * 0.15)
        ded = 150.0 if "CRIT" in provider_id or "HIGH" in provider_id else 50.0
        clm_type = "Inpatient" if reimb > 1000 else "Outpatient"

        att_phy = f"PHY-ATT-{i}"
        oper_phy = f"PHY-OP-{i}" if phys_count >= 2 else "None"
        oth_phy = f"PHY-OTH-{i}" if phys_count >= 3 else "None"

        lines.append(f"Claim ID: {clm_id} | Bene ID: {bene_id} | Type: {clm_type}")
        lines.append(f"  Date of Service : {start_dt} to {end_dt}")
        lines.append(f"  Beneficiary DOB : {dob} | DOD: {dod if dod else 'N/A'}")
        lines.append(f"  Attending Phys  : {att_phy} | Operating: {oper_phy} | Other: {oth_phy}")
        lines.append(f"  Reimbursed Amt  : ${reimb:,.2f} | Deductible: ${ded:.2f}")
        lines.append(f"  Primary Diagnosis: 401.9 | State: {state} | County: 120")
        lines.append("--------------------------------------------------------------------------------")

    content = "\n".join(lines)
    for d in output_dirs:
        out_path = os.path.join(d, filename)
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

def generate_provider_pdf(filename: str, provider_id: str, provider_name: str, state: str,
                          tier: str, claim_count: int, avg_reimb: float, ghost_count: int,
                          phys_count: int, output_dirs: list):
    from reportlab.lib.pagesizes import landscape
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=15, leading=19, textColor=colors.HexColor('#1E293B'))
    meta_style = ParagraphStyle('DocMeta', parent=styles['Normal'], fontSize=8, leading=12, textColor=colors.HexColor('#475569'))
    header_cell = ParagraphStyle('HCell', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.white, fontName='Helvetica-Bold')
    cell_style = ParagraphStyle('BCell', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#1E293B'))
    ghost_style = ParagraphStyle('GCell', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#DC2626'), fontName='Helvetica-Bold')

    first_dir = output_dirs[0]
    first_path = os.path.join(first_dir, filename)

    # Use landscape mode (792 x 612 pt) so column widths have plenty of space
    doc = SimpleDocTemplate(first_path, pagesize=landscape(letter), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elements = []

    elements.append(Paragraph(f"<b>CareGuard AI — Provider Intelligence Batch Report</b>", title_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        f"<b>Provider ID:</b> {provider_id} &nbsp;|&nbsp; <b>Provider Name:</b> {provider_name} &nbsp;|&nbsp; <b>CMS State:</b> {state} &nbsp;|&nbsp; <b>County:</b> 120<br/>"
        f"<b>Total Claims:</b> {claim_count} &nbsp;|&nbsp; <b>Target Tier:</b> {tier.upper()} &nbsp;|&nbsp; <b>Report Date:</b> {datetime.date.today().strftime('%Y-%m-%d')}",
        meta_style
    ))
    elements.append(Spacer(1, 10))

    # All 12 raw fields represented across columns
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

    for i in range(1, claim_count + 1):
        clm_id = f"CLM-{provider_id}-{i:03d}"
        bene_id = f"B100{i}"
        is_ghost = (i <= ghost_count)
        start_dt = "2023-05-10"
        end_dt = "2023-05-12"
        dob = "1948-03-15"
        dod = "2022-11-04" if is_ghost else "N/A"
        reimb = avg_reimb * (1.0 + (i % 5) * 0.15)
        ded = 150.0 if "CRIT" in provider_id or "HIGH" in provider_id else 50.0
        clm_type = "Inpatient" if reimb > 1000 else "Outpatient"

        att_phy = f"PHY-ATT-{i}"
        oper_phy = f"PHY-OP-{i}" if phys_count >= 2 else "None"
        oth_phy = f"PHY-OTH-{i}" if phys_count >= 3 else "None"
        phy_str = f"{att_phy} | {oper_phy} | {oth_phy}"

        dates_str = f"{start_dt} to {end_dt}"
        dob_dod_str = f"DOB: {dob} | DOD: {dod}"

        c_style = ghost_style if is_ghost else cell_style

        table_data.append([
            Paragraph(clm_id, cell_style),
            Paragraph(bene_id, cell_style),
            Paragraph(dates_str, cell_style),
            Paragraph(dob_dod_str, c_style),
            Paragraph(phy_str, cell_style),
            Paragraph(clm_type, cell_style),
            Paragraph(f"${reimb:,.2f}", cell_style),
            Paragraph(f"${ded:.2f}", cell_style),
            Paragraph("401.9", cell_style),
        ])

    t = Table(table_data, colWidths=[140, 60, 110, 110, 150, 55, 65, 45, 35])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8FAFC'), colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    elements.append(t)

    try:
        doc.build(elements)
    except Exception as e:
        print(f"    Notice: Could not build {first_path} ({e})")

    # Copy generated PDF to remaining output directories
    for d in output_dirs[1:]:
        target_path = os.path.join(d, filename)
        try:
            shutil.copy2(first_path, target_path)
        except Exception as e:
            print(f"    Notice: Could not copy to {target_path} ({e})")

def main():
    dirs = [SAMPLE_DIR_V2, SAMPLE_DIR_BACKEND2]
    print("======================================================================")
    print("  GENERATING FULL 12-FIELD v2 PROVIDER-LEVEL SAMPLE TEST FILES")
    print("======================================================================")

    samples = [
        ("low_risk_provider.pdf", "low_risk_provider.txt", "PRV_LOW_101", "Acme Health Clinic", "NY", "Low Risk", 30, 380.0, 0, 1),
        ("medium_risk_provider.pdf", "medium_risk_provider.txt", "PRV_MED_202", "Metro Medical Care", "TX", "Medium Risk", 120, 5200.0, 30, 2),
        ("high_risk_provider.pdf", "high_risk_provider.txt", "PRV_HIGH_303", "Apex Specialty Hospital", "FL", "High Risk", 280, 8500.0, 100, 3),
        ("critical_risk_provider.pdf", "critical_risk_provider.txt", "PRV_CRIT_404", "Omni Care Billing Network", "FL", "Critical Risk", 520, 35000.0, 320, 3),
    ]

    for pdf_name, txt_name, prv_id, prv_name, state, tier, claims, avg_r, ghost, phys in samples:
        generate_provider_txt(txt_name, prv_id, prv_name, state, tier, claims, avg_r, ghost, phys, dirs)
        generate_provider_pdf(pdf_name, prv_id, prv_name, state, tier, claims, avg_r, ghost, phys, dirs)
        print(f"  Generated: {pdf_name:<28} & {txt_name:<28} ({claims} claims)")

    print("======================================================================")
    print("  All full 12-field v2 Provider Sample files successfully created!")

if __name__ == "__main__":
    main()
