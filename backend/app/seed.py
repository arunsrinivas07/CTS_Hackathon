from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.database import engine, SessionLocal, Base
from app.models.role import Role
from app.models.user import User
from app.models.provider import Provider
from app.models.patient import Patient
from app.models.claim import Claim
from app.models.claim_line_item import ClaimLineItem
from app.models.claim_status import ClaimStatusHistory
from app.models.investigation import Investigation
from app.models.finding import Finding
from app.models.evidence import Evidence
from app.models.decision import Decision
from app.models.notification import Notification
from app.models.risk import RiskScore
from app.models.anomaly import Anomaly
from app.models.report import Report
from app.models.documentation_request import DocumentationRequest
from app.crud.user import hash_password


def seed_database(db: Session = None):
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        # 1. Seed Roles
        role_map = {}
        roles_data = [
            ('Admin', 'Full administrative access to all system modules and analytics'),
            ('Investigator', 'Specialist access for fraud detection and case resolution'),
            ('Provider', 'Healthcare provider portal access for claim submission and tracking'),
        ]
        for name, desc in roles_data:
            existing = db.query(Role).filter(Role.name.ilike(name)).first()
            if not existing:
                role = Role(name=name, description=desc, is_active=True)
                db.add(role)
                db.commit()
                db.refresh(role)
                role_map[name.lower()] = role.id
            else:
                role_map[name.lower()] = existing.id

        admin_role_id = role_map.get('admin', 1)
        inv_role_id = role_map.get('investigator', 2)
        prv_role_id = role_map.get('provider', 3)

        # 2. Seed Users
        users_data = [
            ('logesh@gmail.com', 'Logesh', '123456', inv_role_id, '(987) 654-3210'),
            ('hema@gmail.com', 'Hemajothi', '123456', prv_role_id, '(987) 654-3211'),
            ('ganesh@gmail.com', 'Ganesh', '123456', admin_role_id, '(987) 654-3212'),
            ('arun@gmail.com', 'Arun', '123456', inv_role_id, '(987) 654-3213'),
            ('shivaani@gmail.com', 'Shivaani', '123456', prv_role_id, '(987) 654-3214'),
        ]
        user_map = {}
        for email, full_name, pwd, role_id, phone in users_data:
            existing = db.query(User).filter(User.email.ilike(email)).first()
            if not existing:
                user = User(
                    email=email,
                    full_name=full_name,
                    password_hash=hash_password(pwd),
                    role_id=role_id,
                    phone=phone,
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                user_map[email] = user.id
            else:
                existing.full_name = full_name
                existing.password_hash = hash_password(pwd)
                existing.role_id = role_id
                db.commit()
                user_map[email] = existing.id

        # 3. Seed Providers
        providers_data = [
            ('1234567890', 'Metro Health Hospital', 'Hospital', 'General Surgery', '36-1234567', '742 Evergreen Terrace, Chicago, IL 60601'),
            ('0987654321', 'Sunrise Health Clinic', 'Clinic', 'Primary Care', '74-9876543', '100 Sunrise Blvd, Austin, TX 78701'),
            ('1122334455', 'Valley Orthopedics', 'Specialty Clinic', 'Orthopedics', '84-1122334', '450 Mountain Ave, Denver, CO 80202'),
            ('5566778899', 'Northside Neurological', 'Specialty Hospital', 'Neurology', '04-5566778', '88 Beacon St, Boston, MA 02108'),
        ]
        provider_map = {}
        for npi, name, ptype, spec, tax_id, addr in providers_data:
            existing = db.query(Provider).filter(Provider.npi == npi).first()
            if not existing:
                p = Provider(
                    npi=npi,
                    name=name,
                    provider_type=ptype,
                    specialty=spec,
                    tax_id=tax_id,
                    address=addr,
                    is_active=True,
                )
                db.add(p)
                db.commit()
                db.refresh(p)
                provider_map[npi] = p.id
            else:
                provider_map[npi] = existing.id

        # 4. Seed Patients
        patients_data = [
            ('PAT-4421', 'James', 'Thornton', date(1982, 4, 12), 'male', 'MEM-1001'),
            ('PAT-3318', 'Maria', 'Gonzalez', date(1975, 9, 23), 'female', 'MEM-1002'),
            ('PAT-2209', 'Alan', 'Brooks', date(1968, 11, 5), 'male', 'MEM-1003'),
            ('PAT-5502', 'Linda', 'Carter', date(1990, 1, 30), 'female', 'MEM-1004'),
            ('PAT-1107', 'Robert', 'Nguyen', date(1985, 7, 19), 'male', 'MEM-1005'),
            ('PAT-6634', 'Patricia', 'Wells', date(1959, 12, 2), 'female', 'MEM-1006'),
            ('PAT-7721', 'David', 'Kim', date(1993, 3, 14), 'male', 'MEM-1007'),
            ('PAT-3390', 'Susan', 'Taylor', date(1971, 8, 25), 'female', 'MEM-1008'),
        ]

        patient_map = {}
        for ext_id, fn, ln, dob, gen, mem in patients_data:
            existing = db.query(Patient).filter(Patient.patient_external_id == ext_id).first()
            if not existing:
                pat = Patient(
                    patient_external_id=ext_id,
                    first_name=fn,
                    last_name=ln,
                    date_of_birth=dob,
                    gender=gen,
                    member_id=mem,
                )
                db.add(pat)
                db.commit()
                db.refresh(pat)
                patient_map[ext_id] = pat.id
            else:
                patient_map[ext_id] = existing.id

        # 5. Seed Claims
        claims_data = [
            ('CLM-2024-0081', 'PAT-4421', '1234567890', 'Inpatient Surgery', date(2024, 7, 12), date(2024, 7, 14), Decimal('48200.00'), None, 'flagged'),
            ('CLM-2024-0079', 'PAT-3318', '0987654321', 'Outpatient', date(2024, 7, 8), date(2024, 7, 10), Decimal('12450.00'), Decimal('12450.00'), 'paid'),
            ('CLM-2024-0075', 'PAT-2209', '1234567890', 'Inpatient', date(2024, 6, 30), date(2024, 7, 2), Decimal('91750.00'), None, 'flagged'),
            ('CLM-2024-0071', 'PAT-5502', '1122334455', 'Outpatient Surgery', date(2024, 6, 22), date(2024, 6, 24), Decimal('33600.00'), Decimal('33600.00'), 'paid'),
            ('CLM-2024-0068', 'PAT-1107', '0987654321', 'Emergency', date(2024, 6, 18), date(2024, 6, 19), Decimal('7890.00'), None, 'denied'),
            ('CLM-2024-0064', 'PAT-6634', '5566778899', 'Inpatient', date(2024, 6, 10), date(2024, 6, 12), Decimal('62100.00'), None, 'flagged'),
            ('CLM-2024-0058', 'PAT-7721', '1122334455', 'Outpatient', date(2024, 5, 28), date(2024, 5, 29), Decimal('5200.00'), Decimal('5200.00'), 'paid'),
            ('CLM-2024-0052', 'PAT-3390', '1234567890', 'Inpatient', date(2024, 5, 15), date(2024, 5, 17), Decimal('18900.00'), Decimal('18900.00'), 'paid'),
        ]
        claim_map = {}
        for cnum, pat_key, prv_key, ctype, sdate, subdate, billed, paid, status in claims_data:
            existing = db.query(Claim).filter(Claim.claim_number == cnum).first()
            if not existing:
                c = Claim(
                    claim_number=cnum,
                    patient_id=patient_map[pat_key],
                    provider_id=provider_map[prv_key],
                    claim_type=ctype,
                    service_date=sdate,
                    submission_date=subdate,
                    total_billed_amount=billed,
                    total_paid_amount=paid,
                    status=status,
                )
                db.add(c)
                db.commit()
                db.refresh(c)
                claim_map[cnum] = c.id
            else:
                claim_map[cnum] = existing.id

        # 6. Seed Line Items
        line_items_data = [
            ('CLM-2024-0081', 1, '44950', Decimal('32000.00'), Decimal('32000.00'), '1'),
            ('CLM-2024-0081', 2, '00840', Decimal('6200.00'), Decimal('6200.00'), '1'),
            ('CLM-2024-0081', 3, '99223', Decimal('10000.00'), Decimal('10000.00'), '1'),
            ('CLM-2024-0075', 1, '33533', Decimal('55000.00'), Decimal('55000.00'), '1'),
            ('CLM-2024-0075', 2, '33518', Decimal('22000.00'), Decimal('22000.00'), '1'),
            ('CLM-2024-0075', 3, '33530', Decimal('14750.00'), Decimal('14750.00'), '1'),
        ]
        for cnum, lnum, code, billed, paid, modifier in line_items_data:
            cid = claim_map.get(cnum)
            if cid:
                existing = db.query(ClaimLineItem).filter(
                    ClaimLineItem.claim_id == cid,
                    ClaimLineItem.line_number == lnum,
                ).first()
                if not existing:
                    li = ClaimLineItem(
                        claim_id=cid,
                        line_number=lnum,
                        procedure_code=code,
                        units=Decimal('1'),
                        billed_amount=billed,
                        paid_amount=paid,
                        modifier=modifier,
                    )
                    db.add(li)
        db.commit()


        # 7. Seed Status History
        for cnum, cid in claim_map.items():
            existing = db.query(ClaimStatusHistory).filter(ClaimStatusHistory.claim_id == cid).first()
            if not existing:
                h1 = ClaimStatusHistory(
                    claim_id=cid,
                    old_status=None,
                    new_status='submitted',
                    reason='Claim received by payer intake gateway',
                )
                h2 = ClaimStatusHistory(
                    claim_id=cid,
                    old_status='submitted',
                    new_status='processing',
                    reason='Automated rule engine validation and scoring',
                )
                db.add_all([h1, h2])
        db.commit()

        # 8. Seed Investigations
        logesh_id = user_map.get('logesh@gmail.com')
        arun_id = user_map.get('arun@gmail.com')
        inv_data = [
            ('CLM-2024-0081', logesh_id, 'high', 'Suspected duplicate billing for same patient on overlapping dates', 'in_review', 'Patient admission records conflict with billing date.'),
            ('CLM-2024-0075', arun_id, 'critical', 'Unbundling / Upcoding detected. Multiple procedure codes billed separately that should be bundled per CCI edits', 'in_review', 'CPT 33533 and 33518 billed with 33530 add-on code.'),
            ('CLM-2024-0064', None, 'medium', 'High-Cost Outlier: Claim amount significantly exceeds peer average', 'open', 'Initial triage anomaly flag.'),
            ('CLM-2024-0068', None, 'low', 'Missing Documentation: Required surgical documentation not submitted', 'resolved', 'Operative report request fulfilled and verified.'),
        ]
        inv_map = {}
        for cnum, assignee, prio, rsn, st, nts in inv_data:
            cid = claim_map.get(cnum)
            if cid:
                existing = db.query(Investigation).filter(Investigation.claim_id == cid).first()
                if not existing:
                    inv = Investigation(
                        claim_id=cid,
                        assigned_to=assignee,
                        priority=prio,
                        reason=rsn,
                        status=st,
                        notes=nts,
                    )
                    db.add(inv)
                    db.commit()
                    db.refresh(inv)
                    inv_map[cnum] = inv.id
                else:
                    inv_map[cnum] = existing.id

        # 9. Seed Findings and Evidence
        inv_81_id = inv_map.get('CLM-2024-0081')
        if inv_81_id:
            if not db.query(Finding).filter(Finding.investigation_id == inv_81_id).first():
                f1 = Finding(
                    investigation_id=inv_81_id,
                    finding_type='date_discrepancy',
                    severity='high',
                    title='Admission Date Mismatch',
                    description='Hospital EHR indicates admission July 10, whereas claim form states July 12.',
                )
                db.add(f1)
            if not db.query(Evidence).filter(Evidence.investigation_id == inv_81_id).first():
                e1 = Evidence(
                    investigation_id=inv_81_id,
                    evidence_type='document',
                    title='EHR Intake Records - Thornton',
                    source_reference='EHR System / Patient ID PAT-4421',
                    file_path='/documents/DOC-002-EHR-Thornton.pdf',
                    collected_by=logesh_id,
                )
                db.add(e1)

        inv_75_id = inv_map.get('CLM-2024-0075')
        if inv_75_id:
            if not db.query(Finding).filter(Finding.investigation_id == inv_75_id).first():
                f2 = Finding(
                    investigation_id=inv_75_id,
                    finding_type='unbundling',
                    severity='critical',
                    title='CCI Edit Violation on CABG',
                    description='CPT codes 33533 and 33518 should be bundled. Separate billing inflated charge by ~$34,000.',
                )
                db.add(f2)

        # 10. Seed Risk Scores (Live ML Hybrid Scoring)
        from app.routers.ml import score_db_claim
        for cnum, cid in claim_map.items():
            # Check if risk score already exists for this claim
            existing_risk = db.query(RiskScore).filter(RiskScore.claim_id == cid).first()
            if existing_risk:
                continue  # Skip if already scored
                
            try:
                score_db_claim(claim_id=cid, db=db, _=None)
            except Exception as ex:
                print(f"[SEED ML] Warning: Live scoring failed for claim {cnum}: {ex}")
                # Fallback if ML fails - only if no risk score exists
                if not db.query(RiskScore).filter(RiskScore.claim_id == cid).first():
                    rs = RiskScore(
                        claim_id=cid,
                        claim_number=cnum,
                        overall_score=75.0,
                        fraud_score=70.0,
                        risk_level='high',
                        explanation='Fallback risk classification',
                        model_version='v2.5-hybrid-adaptive',
                    )
                    db.add(rs)
        db.commit()

        # 11. Seed Notifications / Alerts
        ganesh_id = user_map.get('ganesh@gmail.com', 1)
        alerts_data = [
            (ganesh_id, 'Critical Alert: INV-2024-0039', 'INV-2024-0039 is past due date — Cardiac Bypass claim still unresolved.', 'critical', False),
            (ganesh_id, 'Provider Risk Threshold', 'Metro Health Hospital risk score exceeded 70 threshold.', 'warning', False),
            (ganesh_id, 'New Claim Intake', 'New claim CLM-2024-0082 submitted by Valley Orthopedics for review.', 'info', True),
            (ganesh_id, 'Workload Imbalance', 'Investigator workload imbalance: Logesh has 6 open cases.', 'warning', True),
            (ganesh_id, 'Monthly Report Ready', 'Monthly fraud detection report generated for June 2024.', 'info', True),
        ]
        for uid, title, msg, ntype, read in alerts_data:
            existing = db.query(Notification).filter(Notification.title == title).first()
            if not existing:
                n = Notification(
                    user_id=uid,
                    title=title,
                    message=msg,
                    notification_type=ntype,
                    is_read=read,
                )
                db.add(n)

        # 12. Seed Reports (requires investigation_id — link to first investigation)
        first_inv_id = list(inv_map.values())[0] if inv_map else None
        if first_inv_id:
            reports_data = [
                ('Monthly FWA Summary - June 2024', 'summary', first_inv_id, ganesh_id),
                ('Provider Risk Assessment Q2', 'risk', first_inv_id, ganesh_id),
                ('High-Cost Outlier Audit Report', 'audit', first_inv_id, ganesh_id),
            ]
            for title, rtype, inv_id, gen_by in reports_data:
                existing = db.query(Report).filter(Report.title == title).first()
                if not existing:
                    r = Report(
                        investigation_id=inv_id,
                        report_type=rtype,
                        title=title,
                        content=f'Auto-generated {rtype} report for ClaimGuard AI investigation.',
                        generated_by=gen_by,
                    )
                    db.add(r)

        # 13. Seed Documentation Requests
        doc_requests_data = [
            (inv_map.get('CLM-2024-0081'), 'Metro Health Hospital', 'Operative Report', 'Complete operative report for appendectomy procedure dated 2024-07-12', datetime.now() + timedelta(days=7), False),
            (inv_map.get('CLM-2024-0081'), 'Metro Health Hospital', 'Anesthesia Records', 'Detailed anesthesia administration records and dosage logs', datetime.now() + timedelta(days=5), False),
            (inv_map.get('CLM-2024-0075'), 'Metro Health Hospital', 'CABG Surgical Notes', 'Complete cardiac surgery notes including vessel graft details', datetime.now() + timedelta(days=10), False),
            (inv_map.get('CLM-2024-0075'), 'Metro Health Hospital', 'Post-Op Care Records', 'ICU admission records and post-operative monitoring logs', datetime.now() + timedelta(days=7), True),
            (inv_map.get('CLM-2024-0064'), 'Northside Neurological', 'Neurology Consultation', 'Specialist consultation notes and diagnostic impressions', datetime.now() + timedelta(days=3), False),
        ]
        for inv_id, req_from, doc_type, desc, due, fulfilled in doc_requests_data:
            if inv_id:
                existing = db.query(DocumentationRequest).filter(
                    DocumentationRequest.investigation_id == inv_id,
                    DocumentationRequest.document_type == doc_type
                ).first()
                if not existing:
                    doc_req = DocumentationRequest(
                        investigation_id=inv_id,
                        requested_from=req_from,
                        document_type=doc_type,
                        description=desc,
                        due_date=due,
                        is_fulfilled=fulfilled,
                    )
                    db.add(doc_req)

        db.commit()
        print('Database seeded successfully with all initial records!')
    except Exception as e:
        db.rollback()
        print(f'Error seeding: {e}')
        raise
    finally:
        if own_session:
            db.close()

if __name__ == '__main__':
    seed_database()