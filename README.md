# 🎓 ApplyMate — Career Automation & Multi-Role Lead Workflow

A Flask-based global career application platform with specialized role-based workflows for **Students**, **Assigners**, **S1 Employees (Job Finders)**, **S2 Employees (ATS Resume Specialists)**, **S3 Employees (Job Appliers)**, and **Admins**.

---

## 🔄 The 3-Employee Pipeline Workflow

1. **Student Registration**: Student registers and completes their comprehensive onboarding profile.
2. **Assigner Assignment**: The Assigner reviews registered student leads and assigns a dedicated **3-member employee team**:
   - **S1 Employee**: Job Searcher / Finder
   - **S2 Employee**: ATS Resume Specialist
   - **S3 Employee**: Job Applier
3. **S1 Employee (Job Finder)**:
   - Evaluates the candidate's skills, visa status, preferences, and experience.
   - Slices and matches 10 to 30 suitable job opportunities.
   - Posts job entries with direct links, Job IDs, locations, and full Job Descriptions (JDs).
   - Submits jobs to S2.
4. **S2 Employee (ATS Resume Maker)**:
   - Reviews the specific Job Description (JD) and the candidate's original resume/materials.
   - Tailors an ATS-compliant, keyword-optimized resume for that specific job and candidate.
   - Uploads the custom ATS resume into the respective job column with ATS match notes.
   - Submits to S3.
5. **S3 Employee (Job Applier)**:
   - Uses the quick-reference cheat sheet for the candidate's personal, visa, and background details.
   - Downloads the custom ATS resume prepared by S2 and opens the external job portal link.
   - Submits the official application and records confirmation codes, date, and optional proof screenshot.
6. **Student Reflection**:
   - The student dashboard updates in real-time, showing all jobs sourced, tailored ATS resumes available for download, and submitted applications with confirmation numbers.

---

## 🚀 Quick Setup

```bash
git clone https://github.com/suryachandrasoma/applymate.git
cd applymate
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python init_db.py
python app.py
```

Open `http://127.0.0.1:5000`

---

## 🔑 Default Accounts & Logins

| Role | Email | Password | Responsibilities |
|---|---|---|---|
| **System Admin** | `admin@applymate.com` | `Admin@123` | Full system oversight, employee management, assignment control |
| **Assigner** | `assigner@applymate.com` | `Assigner@123` | Assigns registered leads to S1, S2, and S3 employee teams |
| **S1 Employee** | `s1@applymate.com` | `S1@123` | Searches 10–30 jobs, posts links, Job IDs, and JDs |
| **S1 Alternate** | `s1_lisa@applymate.com` | `S1@123` | Additional S1 team member |
| **S2 Employee** | `s2@applymate.com` | `S2@123` | Reviews JDs, creates & uploads custom ATS resumes |
| **S2 Alternate** | `s2_david@applymate.com` | `S2@123` | Additional S2 team member |
| **S3 Employee** | `s3@applymate.com` | `S3@123` | Applies to jobs using ATS resumes, enters confirmation proof |
| **S3 Alternate** | `s3_elena@applymate.com` | `S3@123` | Additional S3 team member |
| **Student** | Sign up via `/signup` or use existing student | Completes onboarding, tracks real-time applications |