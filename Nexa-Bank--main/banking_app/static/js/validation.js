/**
 * NexaBank — Form Validation
 * Client-side validation for all forms.
 */

// ── Email Validation ──────────────────────────────────────────────────
function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// ── Phone Validation ─────────────────────────────────────────────────
function validatePhone(phone) {
  const cleaned = phone.replace(/[\s\-+]/g, '').replace(/^91/, '');
  return /^[6-9]\d{9}$/.test(cleaned);
}

// ── Password Strength ─────────────────────────────────────────────────
function getPasswordStrength(password) {
  let score = 0;
  if (password.length >= 8) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[a-z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++;
  return score;
}

function getStrengthLabel(score) {
  const labels = ['', 'Very Weak', 'Weak', 'Fair', 'Strong', 'Very Strong'];
  const colors = ['', 'var(--danger)', 'var(--danger)', 'var(--warning)', 'var(--success)', 'var(--success)'];
  return { label: labels[score] || '', color: colors[score] || '' };
}

// ── Initialize password strength indicator ────────────────────────────
function initPasswordStrength(inputId, containerId) {
  const input = document.getElementById(inputId);
  const container = document.getElementById(containerId);
  if (!input || !container) return;

  input.addEventListener('input', () => {
    const score = getPasswordStrength(input.value);
    const { label, color } = getStrengthLabel(score);

    // Update bars
    const bars = container.querySelectorAll('.pw-strength-bar');
    bars.forEach((bar, i) => {
      bar.style.background = i < score ? color : 'var(--border)';
    });

    // Update label
    const text = container.querySelector('.pw-strength-text');
    if (text) {
      text.textContent = input.value ? `Password strength: ${label}` : '';
      text.style.color = color;
    }
  });
}

// ── Show/hide password toggle ─────────────────────────────────────────
function initPasswordToggle(inputId, btnId) {
  const input = document.getElementById(inputId);
  const btn = document.getElementById(btnId);
  if (!input || !btn) return;

  btn.addEventListener('click', () => {
    const isPass = input.type === 'password';
    input.type = isPass ? 'text' : 'password';
    btn.innerHTML = isPass ? '<i class="fa-solid fa-eye-slash"></i>' : '<i class="fa-solid fa-eye"></i>';
    btn.setAttribute('aria-label', isPass ? 'Hide password' : 'Show password');
    btn.setAttribute('aria-pressed', String(isPass));
  });
}

// ── Field validation helpers ──────────────────────────────────────────
function setValid(input) {
  input.classList.remove('is-invalid');
  input.classList.add('is-valid');
  const errEl = input.closest('.form-group')?.querySelector('.form-error');
  if (errEl) errEl.textContent = '';
}

function setInvalid(input, message) {
  input.classList.remove('is-valid');
  input.classList.add('is-invalid');
  const errEl = input.closest('.form-group')?.querySelector('.form-error');
  if (errEl) errEl.textContent = message;
}

function clearValidation(input) {
  input.classList.remove('is-valid', 'is-invalid');
  const errEl = input.closest('.form-group')?.querySelector('.form-error');
  if (errEl) errEl.textContent = '';
}

// ── Amount input formatting ───────────────────────────────────────────
function initAmountInput(inputId) {
  const input = document.getElementById(inputId);
  if (!input) return;

  input.addEventListener('input', () => {
    const val = parseFloat(input.value);
    if (val < 0) input.value = '';
    if (val > 10000000) input.value = 10000000;
  });
}

// ── Account number match validation ──────────────────────────────────
function initAccountConfirmation(field1Id, field2Id) {
  const f1 = document.getElementById(field1Id);
  const f2 = document.getElementById(field2Id);
  if (!f1 || !f2) return;

  function checkMatch() {
    if (!f2.value) return;
    if (f1.value === f2.value) {
      setValid(f2);
    } else {
      setInvalid(f2, 'Account numbers do not match.');
    }
  }

  f1.addEventListener('input', checkMatch);
  f2.addEventListener('input', checkMatch);
}

// ── Registration form validation ──────────────────────────────────────
function initRegisterForm() {
  const form = document.getElementById('registerForm');
  if (!form) return;

  // Password strength
  initPasswordStrength('password', 'pwStrength');
  initPasswordToggle('password', 'pwToggle');
  initPasswordToggle('confirm_password', 'pwConfirmToggle');

  // Live email validation
  const emailField = document.getElementById('email');
  if (emailField) {
    emailField.addEventListener('blur', () => {
      if (emailField.value && !validateEmail(emailField.value)) {
        setInvalid(emailField, 'Please enter a valid email address.');
      } else if (emailField.value) {
        setValid(emailField);
      } else {
        clearValidation(emailField);
      }
    });
  }

  // Live phone validation
  const phoneField = document.getElementById('phone');
  if (phoneField) {
    phoneField.addEventListener('blur', () => {
      if (phoneField.value && !validatePhone(phoneField.value)) {
        setInvalid(phoneField, 'Enter a valid 10-digit Indian phone number.');
      } else if (phoneField.value) {
        setValid(phoneField);
      } else {
        clearValidation(phoneField);
      }
    });
  }

  // Confirm security fields
  const pw = document.getElementById('password');
  const pwConfirm = document.getElementById('confirm_password');
  if (pw && pwConfirm) {
    const checkPasswordMatch = () => {
      if (!pwConfirm.value) return clearValidation(pwConfirm);
      if (pw.value !== pwConfirm.value) setInvalid(pwConfirm, 'Passwords do not match.');
      else setValid(pwConfirm);
    };
    pw.addEventListener('input', checkPasswordMatch);
    pwConfirm.addEventListener('input', checkPasswordMatch);
  }

  const pin = document.getElementById('transaction_pin');
  const pinConfirm = document.getElementById('confirm_transaction_pin');
  if (pin && pinConfirm) {
    const checkPinMatch = () => {
      if (!pinConfirm.value) return clearValidation(pinConfirm);
      if (pin.value !== pinConfirm.value) setInvalid(pinConfirm, 'Transaction PINs do not match.');
      else setValid(pinConfirm);
    };
    pin.addEventListener('input', checkPinMatch);
    pinConfirm.addEventListener('input', checkPinMatch);
  }

  // DOB age check
  const dob = document.getElementById('date_of_birth');
  if (dob) {
    dob.addEventListener('change', () => {
      const born = new Date(dob.value);
      const today = new Date();
      const age = today.getFullYear() - born.getFullYear();
      if (age < 18) {
        setInvalid(dob, 'You must be at least 18 years old.');
      } else {
        setValid(dob);
      }
    });
  }

  // Form submit validation
  form.addEventListener('submit', e => {
    let valid = true;
    const required = form.querySelectorAll('[required]');
    required.forEach(field => {
      if (field.type === 'checkbox' && !field.checked) {
        field.focus();
        valid = false;
      } else if (field.type !== 'checkbox' && !field.value.trim()) {
        setInvalid(field, 'This field is required.');
        valid = false;
      }
    });
    if (pw && pwConfirm && pw.value !== pwConfirm.value) {
      setInvalid(pwConfirm, 'Passwords do not match.');
      valid = false;
    }
    if (pin && pinConfirm && pin.value !== pinConfirm.value) {
      setInvalid(pinConfirm, 'Transaction PINs do not match.');
      valid = false;
    }
    if (!valid) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  });
}

// ── Transfer form validation ──────────────────────────────────────────
function initTransferForm() {
  initAccountConfirmation('receiver_account', 'confirm_account');
  initAmountInput('amount');
}

// ── Login form validation ─────────────────────────────────────────────
function initLoginForm() {
  initPasswordToggle('password', 'pwToggle');
}

// ── Initialize on DOM ready ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initRegisterForm();
  initTransferForm();
  initLoginForm();
  initAmountInput('amount');
});
