import os
import io
import time
import unittest
from app import app, db
from models import User, StudentProfile, LeadJob

def run_tests():
    with app.app_context():
        client = app.test_client()

        print("--- 1. Testing Assigner Login & Team Assignment ---")
        r = client.post('/login', data={'email': 'assigner@applymate.com', 'password': 'Assigner@123'}, follow_redirects=True)
        assert b'Assigner Dashboard' in r.data, 'Assigner login failed'

        lead = StudentProfile.query.first()
        assert lead is not None, 'No lead found'
        s1_emp = User.query.filter_by(role='employee_s1').first()
        s2_emp = User.query.filter_by(role='employee_s2').first()
        s3_emp = User.query.filter_by(role='employee_s3').first()

        r = client.post(f'/lead/{lead.id}/assign_team', data={
            's1_id': s1_emp.id,
            's2_id': s2_emp.id,
            's3_id': s3_emp.id
        }, follow_redirects=True)
        assert r.status_code == 200

        # Check DB
        db.session.refresh(lead)
        assert lead.assigned_s1_id == s1_emp.id
        assert lead.assigned_s2_id == s2_emp.id
        assert lead.assigned_s3_id == s3_emp.id
        print(f"[PASS] Assigner successfully assigned S1 ({s1_emp.full_name}), S2 ({s2_emp.full_name}), S3 ({s3_emp.full_name}) to lead!")

        # Test 2: S1 Employee searches and posts jobs
        print("--- 2. Testing S1 Employee Job Sourcing ---")
        client.get('/logout', follow_redirects=True)
        r = client.post('/login', data={'email': s1_emp.email, 'password': 'S1@123'}, follow_redirects=True)
        assert b'S1 Employee Panel' in r.data, 'S1 login failed'

        test_code = f"GC-{int(time.time())}"
        # Add a job
        r = client.post(f'/s1/lead/{lead.id}/jobs/add', data={
            'job_title': 'Software Engineer - Backend',
            'company_name': 'Google Cloud',
            'job_id_code': test_code,
            'job_url': 'https://careers.google.com/jobs/results/98210',
            'location': 'Sunnyvale, CA',
            'job_description': 'Build scalable distributed systems in Python. Experience with microservices and cloud required.',
            's1_notes': 'Strong match for Python background and visa requirements.'
        }, follow_redirects=True)
        assert b'Software Engineer - Backend' in r.data
        job = LeadJob.query.filter_by(lead_id=lead.id, job_id_code=test_code).first()
        assert job is not None
        assert job.stage == 's1_sourcing'
        print("[PASS] S1 added job in draft!")

        # S1 submits job to S2
        r = client.post(f'/s1/lead/{lead.id}/jobs/{job.id}/submit', follow_redirects=True)
        db.session.refresh(job)
        assert job.stage == 's2_resume'
        assert job.s1_status == 'submitted'
        print("[PASS] S1 submitted job to S2 ATS Resume Specialist!")

        # Test 3: S2 Employee Reviews JD and Uploads ATS Resume
        print("--- 3. Testing S2 Employee ATS Resume Tailoring ---")
        client.get('/logout', follow_redirects=True)
        r = client.post('/login', data={'email': s2_emp.email, 'password': 'S2@123'}, follow_redirects=True)
        assert b'S2 Employee Panel' in r.data, 'S2 login failed'

        # Upload ATS resume and submit to S3
        dummy_pdf = (io.BytesIO(b'%PDF-1.4 dummy resume content'), 'custom_ats_resume.pdf')
        r = client.post(f'/s2/lead/{lead.id}/jobs/{job.id}/upload_resume', data={
            'ats_resume': dummy_pdf,
            's2_notes': 'ATS Match: 96%. Integrated keywords: distributed systems, microservices, gRPC, Python.',
            'action': 'submit'
        }, content_type='multipart/form-data', follow_redirects=True)

        db.session.refresh(job)
        assert job.stage == 's3_apply'
        assert job.s2_status == 'submitted'
        assert job.ats_resume_filename is not None
        print("[PASS] S2 prepared and submitted tailored ATS resume to S3!")

        # Test 4: S3 Employee Applies and Records Proof
        print("--- 4. Testing S3 Employee Job Application ---")
        client.get('/logout', follow_redirects=True)
        r = client.post('/login', data={'email': s3_emp.email, 'password': 'S3@123'}, follow_redirects=True)
        assert b'S3 Employee Panel' in r.data, 'S3 login failed'

        conf_code = f"WD-CONF-{int(time.time())}"
        # S3 marks job as applied
        r = client.post(f'/s3/lead/{lead.id}/jobs/{job.id}/apply', data={
            'portal_submission_id': conf_code,
            's3_notes': 'Submitted application via Google Careers portal with custom ATS resume.'
        }, follow_redirects=True)

        db.session.refresh(job)
        assert job.stage == 'applied'
        assert job.s3_status == 'applied'
        assert job.portal_submission_id == conf_code
        print("[PASS] S3 applied to job with confirmation code!")

        # Test 5: Student Profile Reflection
        print("--- 5. Testing Student Dashboard Reflection ---")
        client.get('/logout', follow_redirects=True)
        student = User.query.filter_by(role='student').first()
        r = client.post('/login', data={'email': student.email, 'password': 'Student@123'}, follow_redirects=True)
        assert b'Student Dashboard' in r.data, 'Student login failed'
        assert b'Your Job Application Pipeline' in r.data, 'Pipeline missing from student dashboard'
        assert b'Google Cloud' in r.data, 'Company name missing'
        assert b'Software Engineer - Backend' in r.data, 'Job title missing'
        assert conf_code.encode() in r.data, 'Confirmation code missing'
        assert b'Download Tailored Resume' in r.data, 'Tailored resume download button missing'
        print("[PASS] Applied job with tailored ATS resume reflects on student dashboard!")

        # Test 6: Admin Dashboard and Employee Creation
        print("--- 6. Testing Admin Dashboard & Employee Creation ---")
        client.get('/logout', follow_redirects=True)
        r = client.post('/login', data={'email': 'admin@applymate.com', 'password': 'Admin@123'}, follow_redirects=True)
        assert b'Admin Dashboard' in r.data

        admin_emp_email = f"emp_{int(time.time())}@applymate.com"
        r = client.post('/admin/employee/create', data={
            'full_name': 'Test New Employee S1',
            'email': admin_emp_email,
            'password': 'Password@123',
            'role': 'employee_s1'
        }, follow_redirects=True)
        assert b'New employee account created' in r.data
        new_emp = User.query.filter_by(email=admin_emp_email).first()
        assert new_emp is not None
        assert new_emp.role == 'employee_s1'
        print("[PASS] Admin created new S1 employee!")

        print("\n===========================================")
        print("  ALL 6 WORKFLOW INTEGRATION TESTS PASSED! ")
        print("===========================================")

if __name__ == '__main__':
    run_tests()
