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

from config import Config
from models import db, User, StudentProfile

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
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], name))
    return name


# ---------- PUBLIC ROUTES ----------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('student_dashboard'))

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
    if current_user.role == 'assigner':
        return redirect(url_for('assigner_dashboard'))
    return redirect(url_for('student_dashboard'))


# ---------- STUDENT ROUTES ----------
@app.route('/student/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    return render_template('student_dashboard.html', profile=profile)


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
    is_new = profile is None
    if is_new:
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


# ---------- ADMIN / ASSIGNER ROUTES ----------
@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    leads = StudentProfile.query.order_by(StudentProfile.created_at.desc()).all()
    assigners = User.query.filter_by(role='assigner').all()
    stats = {
        'total': len(leads),
        'new': sum(1 for l in leads if l.status == 'new'),
        'in_progress': sum(1 for l in leads if l.status == 'in_progress'),
        'closed': sum(1 for l in leads if l.status == 'closed')
    }
    return render_template('admin_dashboard.html',
                           leads=leads, assigners=assigners, stats=stats)


@app.route('/assigner/dashboard')
@login_required
@role_required('assigner')
def assigner_dashboard():
    # Assigners see leads assigned to them plus unassigned ones
    leads = StudentProfile.query.filter(
        (StudentProfile.assigned_to == current_user.id) |
        (StudentProfile.assigned_to.is_(None))
    ).order_by(StudentProfile.created_at.desc()).all()
    stats = {
        'mine': sum(1 for l in leads if l.assigned_to == current_user.id),
        'unassigned': sum(1 for l in leads if l.assigned_to is None),
        'in_progress': sum(1 for l in leads if l.status == 'in_progress'),
    }
    return render_template('assigner_dashboard.html', leads=leads, stats=stats)


@app.route('/lead/<int:lead_id>')
@login_required
@role_required('admin', 'assigner')
def lead_detail(lead_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    assigners = User.query.filter_by(role='assigner').all() if current_user.role == 'admin' else []
    return render_template('lead_detail.html', lead=lead, assigners=assigners)


@app.route('/lead/<int:lead_id>/assign', methods=['POST'])
@login_required
@role_required('admin')
def assign_lead(lead_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    assigner_id = request.form.get('assigner_id')
    lead.assigned_to = int(assigner_id) if assigner_id else None
    lead.status = 'in_progress' if assigner_id else 'new'
    db.session.commit()
    flash('Lead assigned successfully.', 'success')
    return redirect(url_for('lead_detail', lead_id=lead.id))


@app.route('/lead/<int:lead_id>/status', methods=['POST'])
@login_required
@role_required('admin', 'assigner')
def update_lead_status(lead_id):
    lead = StudentProfile.query.get_or_404(lead_id)
    lead.status = request.form.get('status', lead.status)
    db.session.commit()
    flash('Status updated.', 'success')
    return redirect(url_for('lead_detail', lead_id=lead.id))


@app.route('/uploads/<filename>')
@login_required
@role_required('admin', 'assigner', 'student')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


# ---------- ERROR HANDLERS ----------
@app.errorhandler(403)
def forbidden(e):
    return render_template('base.html', error_code=403,
                           error_msg='Access Denied'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', error_code=404,
                           error_msg='Page Not Found'), 404


# ---------- CLI ----------
@app.cli.command('init-db')
def init_db():
    db.create_all()
    create_default_users()
    print("Database initialised with default users.")


def create_default_users():
    if not User.query.filter_by(email='admin@applymate.com').first():
        db.session.add(User(
            email='admin@applymate.com',
            password_hash=generate_password_hash('Admin@123'),
            role='admin', full_name='System Admin'))

    if not User.query.filter_by(email='assigner@applymate.com').first():
        db.session.add(User(
            email='assigner@applymate.com',
            password_hash=generate_password_hash('Assigner@123'),
            role='assigner', full_name='Default Assigner'))

    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_default_users()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)