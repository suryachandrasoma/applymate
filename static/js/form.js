let currentStep = 1;
const totalSteps = 7;

function updateWizardUI() {
  // Toggle steps
  for (let i = 1; i <= totalSteps; i++) {
    const el = document.getElementById(`step-${i}`);
    if (el) el.classList.toggle('d-none', i !== currentStep);

    const dot = document.getElementById(`nav-dot-${i}`);
    if (dot) {
      if (i < currentStep) {
        dot.classList.remove('bg-light','text-muted','bg-success','text-white');
        dot.classList.add('bg-success','text-white');
        dot.innerHTML = '<i class="fa-solid fa-check"></i>';
      } else if (i === currentStep) {
        dot.classList.remove('bg-light','text-muted');
        dot.classList.add('bg-success','text-white');
        dot.innerText = i;
      } else {
        dot.classList.remove('bg-success','text-white');
        dot.classList.add('bg-light','text-muted');
        dot.innerText = i;
      }
    }
  }

  document.getElementById('prev-btn').disabled = currentStep === 1;
  const nextBtn   = document.getElementById('next-btn');
  const submitBtn = document.getElementById('submit-btn');
  if (currentStep === totalSteps) {
    nextBtn.classList.add('d-none');
    submitBtn.classList.remove('d-none');
  } else {
    nextBtn.classList.remove('d-none');
    submitBtn.classList.add('d-none');
  }

  const pct = (currentStep / totalSteps) * 100;
  document.getElementById('progress-bar-fill').style.width = `${pct}%`;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function changeStep(dir) {
  if (dir === 1 && currentStep < totalSteps) {
    // Simple validation before moving forward
    const active = document.getElementById(`step-${currentStep}`);
    const requiredFields = active.querySelectorAll('[required]');
    let ok = true;
    requiredFields.forEach(f => {
      if (!f.checkValidity()) { ok = false; f.classList.add('is-invalid'); }
      else f.classList.remove('is-invalid');
    });
    if (!ok) { alert('Please fill in all required fields before continuing.'); return; }
    currentStep++;
  } else if (dir === -1 && currentStep > 1) {
    currentStep--;
  }
  updateWizardUI();
}

function goToStep(step) {
  if (step >= 1 && step <= totalSteps) { currentStep = step; updateWizardUI(); }
}

/* --- Repeaters --- */

function addProjectLinkField() {
  const container = document.getElementById('project-links-container');
  const div = document.createElement('div');
  div.className = 'input-group mb-2 project-link-row';
  div.innerHTML = `
    <input type="url" name="project_links" class="form-control" placeholder="https://...">
    <button type="button" class="btn btn-outline-danger" onclick="removeProjectLinkField(this)">
      <i class="fa-solid fa-trash"></i>
    </button>`;
  container.appendChild(div);
  updateRemoveButtons('project-link-row');
}

function removeProjectLinkField(btn) {
  btn.closest('.project-link-row').remove();
  updateRemoveButtons('project-link-row');
}

function addExperienceBlock() {
  const container = document.getElementById('experience-container');
  const div = document.createElement('div');
  div.className = 'border rounded-3 p-3 mb-3 experience-card bg-light';
  div.innerHTML = `
    <div class="row g-3">
      <div class="col-md-4"><label class="small fw-semibold">Company *</label><input name="exp_company[]" class="form-control" required></div>
      <div class="col-md-4"><label class="small fw-semibold">Title *</label><input name="exp_title[]" class="form-control" required></div>
      <div class="col-md-4"><label class="small fw-semibold">Location *</label><input name="exp_location[]" class="form-control" required></div>
      <div class="col-md-4"><label class="small fw-semibold">From *</label><input type="date" name="exp_from[]" class="form-control" required></div>
      <div class="col-md-4"><label class="small fw-semibold">To</label><input type="date" name="exp_to[]" class="form-control"></div>
      <div class="col-md-4 d-flex align-items-end">
        <div class="form-check">
          <input type="checkbox" name="exp_current[]" value="yes" class="form-check-input" onchange="toggleCurrent(this)">
          <label class="form-check-label small">Currently Working Here</label>
        </div>
      </div>
      <div class="col-12"><label class="small fw-semibold">Description</label><textarea name="exp_description[]" rows="2" class="form-control"></textarea></div>
    </div>
    <button type="button" class="btn btn-sm btn-outline-danger mt-2" onclick="removeBlock(this)">
      <i class="fa-solid fa-trash"></i> Remove
    </button>`;
  container.appendChild(div);
  updateRemoveButtons('experience-card');
}

function addEducationBlock() {
  const container = document.getElementById('education-container');
  const div = document.createElement('div');
  div.className = 'border rounded-3 p-3 mb-3 education-card bg-light';
  div.innerHTML = `
    <div class="row g-3">
      <div class="col-md-6">
        <label class="small fw-semibold">Level *</label>
        <select name="edu_level[]" class="form-select" required>
          <option value="">Select</option>
          <option>Master of Science (MS)</option>
          <option>Bachelor's Degree</option>
          <option>Associate Degree</option>
          <option>High School</option>
          <option>Doctorate / Ph.D.</option>
          <option>Other</option>
        </select>
      </div>
      <div class="col-md-6"><label class="small fw-semibold">Major *</label><input name="edu_major[]" class="form-control" required></div>
      <div class="col-md-4"><label class="small fw-semibold">University *</label><input name="edu_university[]" class="form-control" required></div>
      <div class="col-md-2"><label class="small fw-semibold">From *</label><input type="number" name="edu_year_from[]" class="form-control" required></div>
      <div class="col-md-2"><label class="small fw-semibold">To *</label><input type="number" name="edu_year_to[]" class="form-control" required></div>
      <div class="col-md-4"><label class="small fw-semibold">GPA / CGPA</label><input name="edu_gpa[]" class="form-control"></div>
    </div>
    <button type="button" class="btn btn-sm btn-outline-danger mt-2" onclick="removeBlock(this)">
      <i class="fa-solid fa-trash"></i> Remove
    </button>`;
  container.appendChild(div);
  updateRemoveButtons('education-card');
}

function removeBlock(btn) {
  const card = btn.closest('.experience-card, .education-card');
  const cls = card.classList.contains('experience-card') ? 'experience-card' : 'education-card';
  card.remove();
  updateRemoveButtons(cls);
}

function updateRemoveButtons(cls) {
  const cards = document.querySelectorAll('.' + cls);
  cards.forEach(c => {
    const btn = c.querySelector('button.btn-outline-danger, button[onclick*="remove"]');
    if (!btn) return;
    if (cards.length === 1) { btn.disabled = true; btn.title = 'Cannot remove last item'; }
    else { btn.disabled = false; btn.title = ''; }
  });
}

function toggleCurrent(checkbox) {
  const card = checkbox.closest('.experience-card');
  const toInput = card.querySelector('input[name="exp_to[]"]');
  if (checkbox.checked) {
    toInput.value = '';
    toInput.disabled = true;
    toInput.classList.add('bg-light');
  } else {
    toInput.disabled = false;
    toInput.classList.remove('bg-light');
  }
}

/* ---------- AJAX Submit ---------- */
document.addEventListener('DOMContentLoaded', () => {
  updateWizardUI();

  const form = document.getElementById('applymate-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Final validation
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    const submitBtn = document.getElementById('submit-btn');
    const originalHtml = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting…';

    try {
      const res = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form)
      });
      const data = await res.json();
      if (data.success) {
        form.classList.add('d-none');
        const success = document.createElement('div');
        success.className = 'card border-0 shadow-sm text-center p-5';
        success.innerHTML = `
          <div class="mb-3">
            <i class="fa-solid fa-circle-check text-success display-4"></i>
          </div>
          <h3 class="fw-bold">Profile Successfully Registered!</h3>
          <p class="text-muted">Registration ID: <strong>${data.registration_id}</strong></p>
          <a href="/student/dashboard" class="btn btn-success mt-2">Go to Dashboard</a>`;
        form.parentNode.appendChild(success);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        alert(data.message || 'Submission failed.');
      }
    } catch (err) {
      alert('Unexpected error: ' + err.message);
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalHtml;
    }
  });
});