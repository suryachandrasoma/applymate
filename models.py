from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # student, admin, assigner
    full_name = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ Explicitly tell SQLAlchemy which FK to use
    student_profile = db.relationship(
        'StudentProfile',
        foreign_keys='StudentProfile.user_id',
        backref='user',
        uselist=False,
        cascade='all, delete-orphan'
    )


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
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    registration_id = db.Column(db.String(40), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ✅ Assigner relationship (already explicit)
    assignee = db.relationship('User', foreign_keys=[assigned_to])

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