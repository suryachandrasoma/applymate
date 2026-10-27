import os
import json
import uuid
from datetime import datetime
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, session, jsonify, abort, send_from_directory)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import text

from config import Config
from models import db, User, StudentProfile, LeadJob

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'


# ---------- login manager ----------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------- helpers ----------
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def save_upload(file, prefix):
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit('.', 1)[1].lower()
    name = f"{prefix}_{uuid.uuid4().hex[:10]}.{ext}"
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], name))
    return name


# ---------- PUBLIC ROUTES ----------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_router'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not all([full_name, email, password]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('signup'))

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'warning')
            return redirect(url_for('login'))

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            role='student',
            full_name=full_name
        )
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash('Account created! Please complete your onboarding profile.', 'success')
        return redirect(url_for('onboarding_form'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_router'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'Welcome back, {user.full_name or user.email}!', 'success')
            return redirect(url_for('dashboard_router'))

        flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard_router():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'assigner':
        return redirect(url_for('assigner_dashboard'))
    elif current_user.role == 'employee_s1':
        return redirect(url_for('s1_dashboard'))
    elif current_user.role == 'employee_s2':
        return redirect(url_for('s2_dashboard'))
    elif current_user.role == 'employee_s3':
        return redirect(url_for('s3_dashboard'))
    return redirect(url_for('student_dashboard'))


# ---------- STUDENT ROUTES ----------
@app.route('/student/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    jobs = []
    stats = {'total': 0, 's1_sourcing': 0, 's2_resume': 0, 's3_apply': 0, 'applied': 0}
    if profile:
        jobs = LeadJob.query.filter_by(lead_id=profile.id).order_by(LeadJob.created_at.desc()).all()
        stats = {
            'total': len(jobs),
            's1_sourcing': sum(1 for j in jobs if j.stage == 's1_sourcing'),
            's2_resume': sum(1 for j in jobs if j.stage == 's2_resume'),
            's3_apply': sum(1 for j in jobs if j.stage == 's3_apply'),
            'applied': sum(1 for j in jobs if j.stage == 'applied')
        }
    return render_template('student_dashboard.html', profile=profile, jobs=jobs, stats=stats)


@app.route('/onboarding', methods=['GET'])
@login_required
@role_required('student')
def onboarding_form():
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    return render_template('onboarding_form.html', profile=profile)


@app.route('/onboarding/submit', methods=['POST'])
@login_required
@role_required('student')
def onboarding_submit():
    form = request.form

    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if profile is None:
        profile = StudentProfile(user_id=current_user.id)
        profile.registration_id = f"AM-MS-{datetime.utcnow().year}-{uuid.uuid4().hex[:4].upper()}"
        db.session.add(profile)

    # Step 1
    profile.first_name = form.get('first_name')
    profile.middle_name = form.get('middle_name')
    profile.last_name = form.get('last_name')
    profile.email = form.get('email')
    profile.phone_country_code = form.get('phone_country_code')
    profile.phone = form.get('phone')
    profile.dob = form.get('dob')
    profile.street = form.get('street')
    profile.city = form.get('city')
    profile.state = form.get('state')
    profile.postal_code = form.get('postal_code')
    profile.linkedin_url = form.get('linkedin_url')
    profile.github_url = form.get('github_url')

    # Step 2 - files
    if 'resume' in request.files:
        fname = save_upload(request.files['resume'], 'resume')
        if fname:
            profile.resume_filename = fname
    if 'cover_letter' in request.files:
        fname = save_upload(request.files['cover_letter'], 'cover')
        if fname:
            profile.cover_letter_filename = fname

    profile.project_links = json.dumps(form.getlist('project_links'))

    # Step 3
    profile.work_authorized = form.get('work_authorized')
    profile.visa_status = form.get('visa_status')
    profile.sponsorship_required = form.get('sponsorship')
    profile.security_clearance = form.get('security_clearance')

    # Step 4 - experience / education arrays (repeaters)
    experiences = []
    companies = form.getlist('exp_company[]')
    titles = form.getlist('exp_title[]')
    locations = form.getlist('exp_location[]')
    from_dates = form.getlist('exp_from[]')
    to_dates = form.getlist('exp_to[]')
    current_flags = form.getlist('exp_current[]')
    descriptions = form.getlist('exp_description[]')

    for i in range(len(companies)):
        experiences.append({
            'company': companies[i],
            'title': titles[i] if i < len(titles) else '',
            'location': locations[i] if i < len(locations) else '',
            'from': from_dates[i] if i < len(from_dates) else '',
            'to': to_dates[i] if i < len(to_dates) else '',
            'current': current_flags[i] if i < len(current_flags) else 'no',
            'description': descriptions[i] if i < len(descriptions) else ''
        })
    profile.experiences = json.dumps(experiences)

    educations = []
    levels = form.getlist('edu_level[]')
    majors = form.getlist('edu_major[]')
    universities = form.getlist('edu_university[]')
    years_from = form.getlist('edu_year_from[]')
    years_to = form.getlist('edu_year_to[]')
    gpas = form.getlist('edu_gpa[]')

    for i in range(len(levels)):
        educations.append({
            'level': levels[i],
            'major': majors[i] if i < len(majors) else '',
            'university': universities[i] if i < len(universities) else '',
            'year_from': years_from[i] if i < len(years_from) else '',
            'year_to': years_to[i] if i < len(years_to) else '',
            'gpa': gpas[i] if i < len(gpas) else ''
        })
    profile.educations = json.dumps(educations)

    # Step 5
    profile.salary_currency = form.get('salary_currency')
    profile.expected_salary = form.get('expected_salary')
    profile.start_date = form.get('start_date')
    profile.notice_period = form.get('notice_period')
    profile.work_schedule = form.get('work_schedule')

    # Step 6
    profile.relocation = form.get('relocation')
    profile.work_arrangement = form.get('work_arrangement')
    profile.travel_willingness = form.get('travel_willingness')

    # Step 7
    profile.gender = form.get('gender')
    profile.ethnicity = form.get('ethnicity')
    profile.veteran_status = form.get('veteran_status')
    profile.disability_status = form.get('disability_status')
    profile.terms_accepted = bool(form.get('terms_accepted'))
    profile.email_updates = bool(form.get('email_updates'))

    db.session.commit()

    return jsonify({
        'success': True,
        'registration_id': profile.registration_id,
        'message': 'Profile registered successfully.'
    })


# ---------- ASSIGNER & ADMIN ROUTES ----------
@app.route('/assigner/dashboard')
@login_required
@role_required('assigner', 'admin')
def assigner_dashboard():
    leads = StudentProfile.query.order_by(StudentProfile.created_at.desc()).all()
    s1_employees = User.query.filter_by(role='employee_s1').all()
    s2_employees = User.query.filter_by(role='employee_s2').all()
    s3_employees = User.query.filter_by(role='employee_s3').all()

    stats = {
        'total': len(leads),
        'assigned_fully': sum(1 for l in leads if l.is_fully_assigned),
        'unassigned': sum(1 for l in leads if not l.is_fully_assigned),
        'total_jobs_sourced': sum(l.total_jobs for l in leads),
        'total_jobs_applied': sum(l.applied_jobs_count for l in leads),
    }

    return render_template(
        'assigner_dashboard.html',
        leads=leads,
        s1_employees=s1_employees,
        s2_employees=s2_employees,
        s3_employees=s3_employees,
        stats=stats
    )


@app.route('/lead/<int:lead_id>/assign_team', methods=['POST'])
@login_required
@role_required('assigner', 'admin')
def assign_lead_team(lead_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    s1_id = request.form.get('s1_id')
    s2_id = request.form.get('s2_id')
    s3_id = request.form.get('s3_id')

    lead.assigned_s1_id = int(s1_id) if s1_id and s1_id.isdigit() else None
    lead.assigned_s2_id = int(s2_id) if s2_id and s2_id.isdigit() else None
    lead.assigned_s3_id = int(s3_id) if s3_id and s3_id.isdigit() else None
    lead.assigned_to = current_user.id  # Assigner who performed the assignment

    if lead.assigned_s1_id or lead.assigned_s2_id or lead.assigned_s3_id:
        if lead.status == 'new':
            lead.status = 'in_progress'

    db.session.commit()
    flash(f'Team assigned successfully for lead {lead.full_name} ({lead.registration_id}).', 'success')
    return redirect(request.referrer or url_for('assigner_dashboard'))


@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    leads = StudentProfile.query.order_by(StudentProfile.created_at.desc()).all()
    assigners = User.query.filter_by(role='assigner').all()
    s1_employees = User.query.filter_by(role='employee_s1').all()
    s2_employees = User.query.filter_by(role='employee_s2').all()
    s3_employees = User.query.filter_by(role='employee_s3').all()
    all_employees = User.query.filter(User.role.in_(['assigner', 'employee_s1', 'employee_s2', 'employee_s3'])).all()

    total_jobs = sum(l.total_jobs for l in leads)
    total_applied = sum(l.applied_jobs_count for l in leads)

    stats = {
        'total': len(leads),
        'new': sum(1 for l in leads if l.status == 'new'),
        'in_progress': sum(1 for l in leads if l.status == 'in_progress'),
        'closed': sum(1 for l in leads if l.status == 'closed'),
        'total_jobs': total_jobs,
        'total_applied': total_applied,
        'employees_count': len(all_employees)
    }

    return render_template(
        'admin_dashboard.html',
        leads=leads,
        assigners=assigners,
        s1_employees=s1_employees,
        s2_employees=s2_employees,
        s3_employees=s3_employees,
        all_employees=all_employees,
        stats=stats
    )


@app.route('/admin/employee/create', methods=['POST'])
@login_required
@role_required('admin')
def create_employee():
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', '').strip()

    if not all([full_name, email, password, role]):
        flash('All fields are required to create an employee.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if role not in ['employee_s1', 'employee_s2', 'employee_s3', 'assigner', 'admin']:
        flash('Invalid role selected.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if User.query.filter_by(email=email).first():
        flash('An account with this email already exists.', 'warning')
        return redirect(url_for('admin_dashboard'))

    user = User(
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(password),
        role=role
    )
    db.session.add(user)
    db.session.commit()
    flash(f'New employee account created: {full_name} ({user.role_display}).', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/lead/<int:lead_id>')
@login_required
@role_required('admin', 'assigner', 'employee_s1', 'employee_s2', 'employee_s3')
def lead_detail(lead_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    assigners = User.query.filter_by(role='assigner').all() if current_user.role in ['admin', 'assigner'] else []
    s1_employees = User.query.filter_by(role='employee_s1').all()
    s2_employees = User.query.filter_by(role='employee_s2').all()
    s3_employees = User.query.filter_by(role='employee_s3').all()
    jobs = LeadJob.query.filter_by(lead_id=lead.id).order_by(LeadJob.created_at.desc()).all()

    return render_template(
        'lead_detail.html',
        lead=lead,
        jobs=jobs,
        assigners=assigners,
        s1_employees=s1_employees,
        s2_employees=s2_employees,
        s3_employees=s3_employees
    )


@app.route('/lead/<int:lead_id>/assign', methods=['POST'])
@login_required
@role_required('admin')
def assign_lead(lead_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    assigner_id = request.form.get('assigner_id')
    lead.assigned_to = int(assigner_id) if assigner_id and assigner_id.isdigit() else None
    if lead.assigned_to and lead.status == 'new':
        lead.status = 'in_progress'
    db.session.commit()
    flash('Assigner updated successfully.', 'success')
    return redirect(url_for('lead_detail', lead_id=lead.id))


@app.route('/lead/<int:lead_id>/status', methods=['POST'])
@login_required
@role_required('admin', 'assigner')
def update_lead_status(lead_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    lead.status = request.form.get('status', lead.status)
    db.session.commit()
    flash('Status updated successfully.', 'success')
    return redirect(request.referrer or url_for('lead_detail', lead_id=lead.id))


# ---------- S1 EMPLOYEE ROUTES (Job Sourcing / Finder) ----------
@app.route('/s1/dashboard')
@login_required
@role_required('employee_s1', 'admin', 'assigner')
def s1_dashboard():
    # If S1 employee, filter leads assigned to them. If admin/assigner, view all
    if current_user.role == 'employee_s1':
        leads = StudentProfile.query.filter_by(assigned_s1_id=current_user.id).order_by(StudentProfile.created_at.desc()).all()
    else:
        leads = StudentProfile.query.order_by(StudentProfile.created_at.desc()).all()

    all_lead_ids = [l.id for l in leads]
    jobs = LeadJob.query.filter(LeadJob.lead_id.in_(all_lead_ids)).all() if all_lead_ids else []

    stats = {
        'assigned_students': len(leads),
        'total_jobs_sourced': len(jobs),
        'draft_jobs': sum(1 for j in jobs if j.stage == 's1_sourcing'),
        'submitted_to_s2': sum(1 for j in jobs if j.stage != 's1_sourcing')
    }

    return render_template('s1_dashboard.html', leads=leads, stats=stats)


@app.route('/s1/lead/<int:lead_id>/jobs')
@login_required
@role_required('employee_s1', 'admin', 'assigner')
def s1_lead_jobs(lead_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    # Check assignment if employee
    if current_user.role == 'employee_s1' and lead.assigned_s1_id != current_user.id:
        flash('This student lead is not assigned to you.', 'warning')
        return redirect(url_for('s1_dashboard'))

    jobs = LeadJob.query.filter_by(lead_id=lead.id).order_by(LeadJob.created_at.desc()).all()
    return render_template('s1_lead_jobs.html', lead=lead, jobs=jobs)


@app.route('/s1/lead/<int:lead_id>/jobs/add', methods=['POST'])
@login_required
@role_required('employee_s1', 'admin', 'assigner')
def s1_add_job(lead_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    if current_user.role == 'employee_s1' and lead.assigned_s1_id != current_user.id:
        abort(403)

    job_title = request.form.get('job_title', '').strip()
    company_name = request.form.get('company_name', '').strip()
    job_id_code = request.form.get('job_id_code', '').strip()
    job_url = request.form.get('job_url', '').strip()
    location = request.form.get('location', '').strip()
    job_description = request.form.get('job_description', '').strip()
    s1_notes = request.form.get('s1_notes', '').strip()

    if not all([job_title, company_name, job_url]):
        flash('Job Title, Company Name, and Job Link URL are required.', 'danger')
        return redirect(url_for('s1_lead_jobs', lead_id=lead.id))

    new_job = LeadJob(
        lead_id=lead.id,
        job_title=job_title,
        company_name=company_name,
        job_id_code=job_id_code,
        job_url=job_url,
        location=location,
        job_description=job_description,
        s1_notes=s1_notes,
        stage='s1_sourcing',
        s1_status='draft',
        added_by_id=current_user.id
    )
    db.session.add(new_job)
    db.session.commit()

    flash(f'Job "{job_title}" at {company_name} added to draft list.', 'success')
    return redirect(url_for('s1_lead_jobs', lead_id=lead.id))


@app.route('/s1/lead/<int:lead_id>/jobs/<int:job_id>/submit', methods=['POST'])
@login_required
@role_required('employee_s1', 'admin', 'assigner')
def s1_submit_job(lead_id, job_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    job = LeadJob.query.filter_by(id=job_id, lead_id=lead.id).first_or_404()

    job.s1_status = 'submitted'
    job.stage = 's2_resume'
    job.s1_submitted_at = datetime.utcnow()
    lead.status = 'in_progress'

    db.session.commit()
    flash(f'Job "{job.job_title}" submitted to S2 ATS Resume Specialist.', 'success')
    return redirect(url_for('s1_lead_jobs', lead_id=lead.id))


@app.route('/s1/lead/<int:lead_id>/jobs/submit_all', methods=['POST'])
@login_required
@role_required('employee_s1', 'admin', 'assigner')
def s1_submit_all_jobs(lead_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    draft_jobs = LeadJob.query.filter_by(lead_id=lead.id, stage='s1_sourcing').all()

    if not draft_jobs:
        flash('No draft jobs found to submit.', 'info')
        return redirect(url_for('s1_lead_jobs', lead_id=lead.id))

    for job in draft_jobs:
        job.s1_status = 'submitted'
        job.stage = 's2_resume'
        job.s1_submitted_at = datetime.utcnow()

    lead.status = 'in_progress'
    db.session.commit()
    flash(f'{len(draft_jobs)} jobs successfully submitted to S2 ATS Resume Specialist!', 'success')
    return redirect(url_for('s1_lead_jobs', lead_id=lead.id))


@app.route('/s1/lead/<int:lead_id>/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
@role_required('employee_s1', 'admin', 'assigner')
def s1_delete_job(lead_id, job_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    job = LeadJob.query.filter_by(id=job_id, lead_id=lead.id).first_or_404()

    # Can only delete if not yet applied
    if job.stage == 'applied':
        flash('Cannot delete an already applied job.', 'warning')
        return redirect(url_for('s1_lead_jobs', lead_id=lead.id))

    db.session.delete(job)
    db.session.commit()
    flash('Job entry removed.', 'info')
    return redirect(url_for('s1_lead_jobs', lead_id=lead.id))


# ---------- S2 EMPLOYEE ROUTES (ATS Resume Maker) ----------
@app.route('/s2/dashboard')
@login_required
@role_required('employee_s2', 'admin', 'assigner')
def s2_dashboard():
    if current_user.role == 'employee_s2':
        leads = StudentProfile.query.filter_by(assigned_s2_id=current_user.id).order_by(StudentProfile.created_at.desc()).all()
    else:
        leads = StudentProfile.query.order_by(StudentProfile.created_at.desc()).all()

    all_lead_ids = [l.id for l in leads]
    pending_jobs = LeadJob.query.filter(
        LeadJob.lead_id.in_(all_lead_ids),
        LeadJob.stage == 's2_resume'
    ).order_by(LeadJob.created_at.desc()).all() if all_lead_ids else []

    completed_jobs = LeadJob.query.filter(
        LeadJob.lead_id.in_(all_lead_ids),
        LeadJob.stage.in_(['s3_apply', 'applied'])
    ).all() if all_lead_ids else []

    stats = {
        'assigned_students': len(leads),
        'pending_resumes': len(pending_jobs),
        'completed_resumes': len(completed_jobs)
    }

    return render_template(
        's2_dashboard.html',
        leads=leads,
        pending_jobs=pending_jobs,
        stats=stats
    )


@app.route('/s2/lead/<int:lead_id>/jobs')
@login_required
@role_required('employee_s2', 'admin', 'assigner')
def s2_lead_jobs(lead_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    if current_user.role == 'employee_s2' and lead.assigned_s2_id != current_user.id:
        flash('This student lead is not assigned to you.', 'warning')
        return redirect(url_for('s2_dashboard'))

    # S2 sees jobs that are at or past s2_resume stage (plus any draft for visibility)
    jobs = LeadJob.query.filter_by(lead_id=lead.id).order_by(LeadJob.created_at.desc()).all()
    return render_template('s2_lead_jobs.html', lead=lead, jobs=jobs)


@app.route('/s2/lead/<int:lead_id>/jobs/<int:job_id>/upload_resume', methods=['POST'])
@login_required
@role_required('employee_s2', 'admin', 'assigner')
def s2_upload_resume(lead_id, job_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    job = LeadJob.query.filter_by(id=job_id, lead_id=lead.id).first_or_404()

    s2_notes = request.form.get('s2_notes', '').strip()
    action = request.form.get('action', 'submit')  # 'submit' or 'save_draft'

    if 'ats_resume' in request.files and request.files['ats_resume'].filename != '':
        fname = save_upload(request.files['ats_resume'], f"ats_resume_{job.id}")
        if fname:
            job.ats_resume_filename = fname
        else:
            flash('Invalid file format. Please upload PDF, DOC, or DOCX.', 'danger')
            return redirect(url_for('s2_lead_jobs', lead_id=lead.id))

    job.s2_notes = s2_notes
    job.s2_updated_by_id = current_user.id

    if action == 'submit':
        if not job.ats_resume_filename:
            flash('Please upload an ATS Resume before submitting to S3.', 'danger')
            return redirect(url_for('s2_lead_jobs', lead_id=lead.id))
        job.s2_status = 'submitted'
        job.stage = 's3_apply'
        job.s2_submitted_at = datetime.utcnow()
        flash(f'ATS Resume for "{job.job_title}" at {job.company_name} submitted to S3 Job Applier!', 'success')
    else:
        job.s2_status = 'in_progress'
        flash(f'ATS Resume draft saved for "{job.job_title}".', 'info')

    db.session.commit()
    return redirect(url_for('s2_lead_jobs', lead_id=lead.id))


@app.route('/s2/lead/<int:lead_id>/jobs/submit_all', methods=['POST'])
@login_required
@role_required('employee_s2', 'admin', 'assigner')
def s2_submit_all_resumes(lead_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    ready_jobs = LeadJob.query.filter_by(lead_id=lead.id, stage='s2_resume').filter(LeadJob.ats_resume_filename.isnot(None)).all()

    if not ready_jobs:
        flash('No jobs with uploaded ATS resumes found to submit.', 'info')
        return redirect(url_for('s2_lead_jobs', lead_id=lead.id))

    for job in ready_jobs:
        job.s2_status = 'submitted'
        job.stage = 's3_apply'
        job.s2_submitted_at = datetime.utcnow()
        job.s2_updated_by_id = current_user.id

    db.session.commit()
    flash(f'{len(ready_jobs)} jobs with ATS resumes forwarded to S3 Applier!', 'success')
    return redirect(url_for('s2_lead_jobs', lead_id=lead.id))


# ---------- S3 EMPLOYEE ROUTES (Job Applier) ----------
@app.route('/s3/dashboard')
@login_required
@role_required('employee_s3', 'admin', 'assigner')
def s3_dashboard():
    if current_user.role == 'employee_s3':
        leads = StudentProfile.query.filter_by(assigned_s3_id=current_user.id).order_by(StudentProfile.created_at.desc()).all()
    else:
        leads = StudentProfile.query.order_by(StudentProfile.created_at.desc()).all()

    all_lead_ids = [l.id for l in leads]
    ready_to_apply = LeadJob.query.filter(
        LeadJob.lead_id.in_(all_lead_ids),
        LeadJob.stage == 's3_apply'
    ).order_by(LeadJob.created_at.desc()).all() if all_lead_ids else []

    applied_jobs = LeadJob.query.filter(
        LeadJob.lead_id.in_(all_lead_ids),
        LeadJob.stage == 'applied'
    ).order_by(LeadJob.application_date.desc()).all() if all_lead_ids else []

    stats = {
        'assigned_students': len(leads),
        'ready_to_apply': len(ready_to_apply),
        'total_applied': len(applied_jobs)
    }

    return render_template(
        's3_dashboard.html',
        leads=leads,
        ready_to_apply=ready_to_apply,
        stats=stats
    )


@app.route('/s3/lead/<int:lead_id>/jobs')
@login_required
@role_required('employee_s3', 'admin', 'assigner')
def s3_lead_jobs(lead_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    if current_user.role == 'employee_s3' and lead.assigned_s3_id != current_user.id:
        flash('This student lead is not assigned to you.', 'warning')
        return redirect(url_for('s3_dashboard'))

    jobs = LeadJob.query.filter_by(lead_id=lead.id).order_by(LeadJob.created_at.desc()).all()
    return render_template('s3_lead_jobs.html', lead=lead, jobs=jobs)


@app.route('/s3/lead/<int:lead_id>/jobs/<int:job_id>/apply', methods=['POST'])
@login_required
@role_required('employee_s3', 'admin', 'assigner')
def s3_mark_applied(lead_id, job_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    job = LeadJob.query.filter_by(id=job_id, lead_id=lead.id).first_or_404()

    portal_submission_id = request.form.get('portal_submission_id', '').strip()
    s3_notes = request.form.get('s3_notes', '').strip()

    if 'proof_file' in request.files and request.files['proof_file'].filename != '':
        fname = save_upload(request.files['proof_file'], f"proof_{job.id}")
        if fname:
            job.proof_filename = fname

    job.portal_submission_id = portal_submission_id
    job.s3_notes = s3_notes
    job.s3_status = 'applied'
    job.stage = 'applied'
    job.application_date = datetime.utcnow()
    job.s3_updated_by_id = current_user.id

    # If all jobs for this lead are applied, update lead status to 'applied'
    remaining_jobs = LeadJob.query.filter_by(lead_id=lead.id).filter(LeadJob.stage != 'applied').count()
    if remaining_jobs == 0:
        lead.status = 'applied'

    db.session.commit()
    flash(f'Application confirmed for "{job.job_title}" at {job.company_name}! Reflected on student profile.', 'success')
    return redirect(url_for('s3_lead_jobs', lead_id=lead.id))


# ---------- FILE DOWNLOADS ----------
@app.route('/uploads/<filename>')
@login_required
@role_required('admin', 'assigner', 'employee_s1', 'employee_s2', 'employee_s3', 'student')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


# ---------- ERROR HANDLERS ----------
@app.errorhandler(403)
def forbidden(e):
    return render_template('base.html', error_code=403, error_msg='Access Denied'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', error_code=404, error_msg='Page Not Found'), 404


# ---------- DB UPGRADE & SEED ----------
def init_or_upgrade_db():
    db.create_all()
    # Check if student_profiles needs new columns
    with db.engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(student_profiles)"))
        existing_cols = [row[1] for row in result.fetchall()]
        if 'assigned_s1_id' not in existing_cols:
            conn.execute(text("ALTER TABLE student_profiles ADD COLUMN assigned_s1_id INTEGER REFERENCES users(id)"))
        if 'assigned_s2_id' not in existing_cols:
            conn.execute(text("ALTER TABLE student_profiles ADD COLUMN assigned_s2_id INTEGER REFERENCES users(id)"))
        if 'assigned_s3_id' not in existing_cols:
            conn.execute(text("ALTER TABLE student_profiles ADD COLUMN assigned_s3_id INTEGER REFERENCES users(id)"))
        conn.commit()


def create_default_users():
    default_users = [
        ('admin@applymate.com', 'Admin@123', 'admin', 'System Admin'),
        ('assigner@applymate.com', 'Assigner@123', 'assigner', 'Default Assigner'),
        ('s1@applymate.com', 'S1@123', 'employee_s1', 'Alex Rivera (S1 Job Finder)'),
        ('s1_lisa@applymate.com', 'S1@123', 'employee_s1', 'Lisa Ray (S1 Job Finder)'),
        ('s2@applymate.com', 'S2@123', 'employee_s2', 'Sarah Chen (S2 Resume Specialist)'),
        ('s2_david@applymate.com', 'S2@123', 'employee_s2', 'David Kim (S2 Resume Specialist)'),
        ('s3@applymate.com', 'S3@123', 'employee_s3', 'Sam Miller (S3 Job Applier)'),
        ('s3_elena@applymate.com', 'S3@123', 'employee_s3', 'Elena Rostova (S3 Job Applier)')
    ]
    for email, pwd, role, name in default_users:
        user = User.query.filter_by(email=email).first()
        if not user:
            db.session.add(User(
                email=email,
                password_hash=generate_password_hash(pwd),
                role=role,
                full_name=name
            ))
        elif user.role != role:
            user.role = role
    db.session.commit()


@app.cli.command('init-db')
def init_db():
    init_or_upgrade_db()
    create_default_users()
    print("Database initialised and upgraded with all default roles & users.")


if __name__ == '__main__':
    with app.app_context():
        init_or_upgrade_db()
        create_default_users()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)