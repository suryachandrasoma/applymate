from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    ROLE_ADMIN = 'admin'
    ROLE_ASSIGNER = 'assigner'
    ROLE_STUDENT = 'student'
    ROLE_EMPLOYEE_S1 = 'employee_s1'
    ROLE_EMPLOYEE_S2 = 'employee_s2'
    ROLE_EMPLOYEE_S3 = 'employee_s3'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False)  # student, admin, assigner, employee_s1, employee_s2, employee_s3
    full_name = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Student Profile Relationship
    student_profile = db.relationship(
        'StudentProfile',
        foreign_keys='StudentProfile.user_id',
        backref='user',
        uselist=False,
        cascade='all, delete-orphan'
    )

    @property
    def role_display(self):
        mapping = {
            'admin': 'Admin',
            'assigner': 'Assigner',
            'student': 'Student',
            'employee_s1': 'S1 - Job Finder',
            'employee_s2': 'S2 - ATS Resume Specialist',
            'employee_s3': 'S3 - Job Applier'
        }
        return mapping.get(self.role, self.role.title())

    @property
    def is_employee(self):
        return self.role in ['employee_s1', 'employee_s2', 'employee_s3']


class StudentProfile(db.Model):
    __tablename__ = 'student_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)

    # Step 1 - Personal
    first_name = db.Column(db.String(80))
    middle_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    email = db.Column(db.String(150))
    phone_country_code = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    dob = db.Column(db.String(20))
    street = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    linkedin_url = db.Column(db.String(255))
    github_url = db.Column(db.String(255))

    # Step 2 - Resume
    resume_filename = db.Column(db.String(255))
    cover_letter_filename = db.Column(db.String(255))
    project_links = db.Column(db.Text)

    # Step 3 - Visa
    work_authorized = db.Column(db.String(10))
    visa_status = db.Column(db.String(120))
    sponsorship_required = db.Column(db.String(10))
    security_clearance = db.Column(db.String(80))

    # Step 4 - Experience & Education (JSON arrays)
    experiences = db.Column(db.Text)
    educations = db.Column(db.Text)

    # Step 5 - Compensation
    salary_currency = db.Column(db.String(10))
    expected_salary = db.Column(db.String(50))
    start_date = db.Column(db.String(30))
    notice_period = db.Column(db.String(80))
    work_schedule = db.Column(db.String(120))

    # Step 6 - Travel
    relocation = db.Column(db.String(80))
    work_arrangement = db.Column(db.String(80))
    travel_willingness = db.Column(db.String(40))

    # Step 7 - Demographics
    gender = db.Column(db.String(60))
    ethnicity = db.Column(db.String(80))
    veteran_status = db.Column(db.String(80))
    disability_status = db.Column(db.String(120))
    terms_accepted = db.Column(db.Boolean, default=False)
    email_updates = db.Column(db.Boolean, default=True)

    # Lead metadata
    status = db.Column(db.String(40), default='new')
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Assigner
    registration_id = db.Column(db.String(40), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Three-employee assignments
    assigned_s1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # S1: Job Finder
    assigned_s2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # S2: Resume Maker
    assigned_s3_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # S3: Job Applier

    # Relationships
    assignee = db.relationship('User', foreign_keys=[assigned_to])
    s1_employee = db.relationship('User', foreign_keys=[assigned_s1_id])
    s2_employee = db.relationship('User', foreign_keys=[assigned_s2_id])
    s3_employee = db.relationship('User', foreign_keys=[assigned_s3_id])

    jobs = db.relationship(
        'LeadJob',
        backref='lead',
        cascade='all, delete-orphan',
        order_by='LeadJob.created_at.desc()'
    )

    # ------- helpers -------
    def project_links_list(self):
        try:
            return json.loads(self.project_links) if self.project_links else []
        except Exception:
            return []

    def experiences_list(self):
        try:
            return json.loads(self.experiences) if self.experiences else []
        except Exception:
            return []

    def educations_list(self):
        try:
            return json.loads(self.educations) if self.educations else []
        except Exception:
            return []

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join([p for p in parts if p]).strip() or "Student"

    @property
    def total_jobs(self):
        return len(self.jobs)

    @property
    def draft_jobs_count(self):
        return sum(1 for j in self.jobs if j.stage == 's1_sourcing')

    @property
    def s2_pending_jobs_count(self):
        return sum(1 for j in self.jobs if j.stage == 's2_resume')

    @property
    def s3_pending_jobs_count(self):
        return sum(1 for j in self.jobs if j.stage == 's3_apply')

    @property
    def applied_jobs_count(self):
        return sum(1 for j in self.jobs if j.stage == 'applied')

    @property
    def is_fully_assigned(self):
        return bool(self.assigned_s1_id and self.assigned_s2_id and self.assigned_s3_id)


class LeadJob(db.Model):
    __tablename__ = 'lead_jobs'

    # Pipeline stages:
    # 1. 's1_sourcing': S1 job finder creates/edits the job entry (draft)
    # 2. 's2_resume': S1 submitted to S2; S2 ATS resume specialist prepares & uploads ATS resume
    # 3. 's3_apply': S2 uploaded ATS resume and submitted to S3; S3 job applier applies to job
    # 4. 'applied': S3 marked job as applied, recorded confirmation & date
    STAGE_S1_SOURCING = 's1_sourcing'
    STAGE_S2_RESUME = 's2_resume'
    STAGE_S3_APPLY = 's3_apply'
    STAGE_APPLIED = 'applied'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)

    # Stage 1: S1 Job Details
    job_title = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    job_id_code = db.Column(db.String(100))  # e.g. "REQ-1049" or Job ID
    job_url = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(200))
    job_description = db.Column(db.Text)  # JD details for S2 to prepare ATS resume
    s1_notes = db.Column(db.Text)  # Why it suits student
    s1_status = db.Column(db.String(50), default='draft')  # 'draft', 'submitted'
    s1_submitted_at = db.Column(db.DateTime)
    added_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Stage 2: S2 ATS Resume Details
    ats_resume_filename = db.Column(db.String(255))
    s2_notes = db.Column(db.Text)  # Notes on ATS keywords, score, adjustments
    s2_status = db.Column(db.String(50), default='pending')  # 'pending', 'submitted'
    s2_submitted_at = db.Column(db.DateTime)
    s2_updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Stage 3: S3 Application Details
    s3_status = db.Column(db.String(50), default='pending')  # 'pending', 'applied', 'skipped'
    application_date = db.Column(db.DateTime)
    portal_submission_id = db.Column(db.String(150))  # Application Confirmation Code
    s3_notes = db.Column(db.Text)  # Application remarks
    proof_filename = db.Column(db.String(255))  # Screenshot / proof file
    s3_updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Overall Pipeline Stage
    stage = db.Column(db.String(50), default='s1_sourcing')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    added_by = db.relationship('User', foreign_keys=[added_by_id])
    s2_user = db.relationship('User', foreign_keys=[s2_updated_by_id])
    s3_user = db.relationship('User', foreign_keys=[s3_updated_by_id])

    @property
    def stage_badge_class(self):
        mapping = {
            's1_sourcing': 'bg-secondary',
            's2_resume': 'bg-warning text-dark',
            's3_apply': 'bg-info text-dark',
            'applied': 'bg-success'
        }
        return mapping.get(self.stage, 'bg-dark')

    @property
    def stage_display(self):
        mapping = {
            's1_sourcing': 'S1: Sourcing (Draft)',
            's2_resume': 'S2: ATS Resume Needed',
            's3_apply': 'S3: Ready to Apply',
            'applied': 'Applied'
        }
        return mapping.get(self.stage, self.stage.title())