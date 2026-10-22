/**
 * Registration-only KYC upload controls and progress reporting.
 * Selected documents stay in memory until the registration form is submitted.
 */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('registerForm');
  if (!form) return;

  const allowedTypes = {
    pdf: 'application/pdf',
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    png: 'image/png'
  };
  const progress = document.getElementById('registrationProgress');
  const progressBar = document.getElementById('registrationProgressBar');
  const progressLabel = document.getElementById('registrationProgressLabel');
  const progressValue = document.getElementById('registrationProgressValue');
  const errorsRegion = document.getElementById('registerServerErrors');

  function setUploadError(card, message) {
    const error = card.querySelector('[data-upload-error]');
    error.textContent = message;
    error.hidden = !message;
  }

  function revokePreview(card) {
    if (card.dataset.previewUrl) URL.revokeObjectURL(card.dataset.previewUrl);
    delete card.dataset.previewUrl;
    const preview = card.querySelector('[data-preview]');
    preview.replaceChildren();
    preview.hidden = true;
  }

  function clearFile(card) {
    const input = card.querySelector('input[type="file"]');
    input.value = '';
    card.querySelector('[data-file-details]').hidden = true;
    card.querySelector('[data-drop-target]').hidden = false;
    const status = card.querySelector('[data-upload-status]');
    status.textContent = 'Not Uploaded';
    status.className = 'kyc-status status-not-uploaded';
    setUploadError(card, '');
    revokePreview(card);
  }

  function showFile(card, file) {
    const input = card.querySelector('input[type="file"]');
    const extension = file.name.split('.').pop().toLowerCase();
    if (!Object.prototype.hasOwnProperty.call(allowedTypes, extension) ||
        file.type !== allowedTypes[extension]) {
      clearFile(card);
      setUploadError(card, 'Choose a PDF, JPG, JPEG, or PNG file with a matching file type.');
      return false;
    }
    if (file.size === 0 || file.size > 5 * 1024 * 1024) {
      clearFile(card);
      setUploadError(card, file.size === 0
        ? 'This file is empty. Choose a different document.'
        : 'Files must be 5 MB or smaller.');
      return false;
    }

    revokePreview(card);
    setUploadError(card, '');
    card.querySelector('[data-drop-target]').hidden = true;
    card.querySelector('[data-file-details]').hidden = false;
    card.querySelector('[data-file-name]').textContent = file.name;
    card.querySelector('[data-file-size]').textContent =
      `${(file.size / (1024 * 1024)).toFixed(2)} MB`;
    const status = card.querySelector('[data-upload-status]');
    status.textContent = 'Uploaded';
    status.className = 'kyc-status status-uploaded';

    if (file.type.startsWith('image/')) {
      const preview = card.querySelector('[data-preview]');
      const image = document.createElement('img');
      image.alt = `${card.querySelector('h2').textContent.trim()} preview`;
      image.src = URL.createObjectURL(file);
      card.dataset.previewUrl = image.src;
      preview.replaceChildren(image);
      preview.hidden = false;
    }
    return true;
  }

  document.querySelectorAll('[data-kyc-upload]').forEach(card => {
    const input = card.querySelector('input[type="file"]');
    const dropzone = card.querySelector('[data-drop-target]');

    card.querySelectorAll('[data-browse]').forEach(button => {
      button.addEventListener('click', () => input.click());
    });
    card.querySelector('[data-remove]').addEventListener('click', () => clearFile(card));
    input.addEventListener('change', () => {
      if (input.files[0]) showFile(card, input.files[0]);
    });

    dropzone.addEventListener('click', event => {
      if (event.target.closest('button')) return;
      input.click();
    });
    dropzone.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        input.click();
      }
    });
    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, event => {
        event.preventDefault();
        dropzone.classList.add('is-dragging');
      });
    });
    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, event => {
        event.preventDefault();
        dropzone.classList.remove('is-dragging');
      });
    });
    dropzone.addEventListener('drop', event => {
      const file = event.dataTransfer.files[0];
      if (!file) return;
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      showFile(card, file);
    });
  });

  function showServerErrors(messages) {
    errorsRegion.replaceChildren();
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger';
    alert.setAttribute('role', 'alert');
    const icon = document.createElement('i');
    icon.className = 'fa-solid fa-circle-exclamation';
    icon.setAttribute('aria-hidden', 'true');
    const list = document.createElement('ul');
    messages.forEach(message => {
      const item = document.createElement('li');
      item.textContent = message;
      list.appendChild(item);
    });
    alert.append(icon, list);
    errorsRegion.appendChild(alert);
    errorsRegion.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function resetProgress() {
    progress.hidden = true;
    progressBar.value = 0;
    progressLabel.textContent = 'Preparing secure upload…';
    progressValue.textContent = '0%';
    form.removeAttribute('aria-busy');
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = false;
    submitButton.classList.remove('is-loading');
    submitButton.removeAttribute('aria-label');
  }

  form.addEventListener('submit', event => {
    if (event.defaultPrevented) return;

    const missingDocuments = [...document.querySelectorAll('[data-kyc-upload]')]
      .filter(card => card.querySelector('input').dataset.required === 'true' &&
        !card.querySelector('input').files.length);
    missingDocuments.forEach(card => {
      const error = card.querySelector('[data-upload-error]');
      if (!error.textContent) setUploadError(card, 'This document is required.');
    });
    if (missingDocuments.length) {
      event.preventDefault();
      missingDocuments[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
      missingDocuments[0].querySelector('input').focus();
      return;
    }

    event.preventDefault();
    errorsRegion.replaceChildren();
    progress.hidden = false;
    progressBar.value = 0;
    progressLabel.textContent = 'Uploading documents securely…';
    progressValue.textContent = '0%';
    form.setAttribute('aria-busy', 'true');

    const xhr = new XMLHttpRequest();
    xhr.open('POST', form.action);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.responseType = 'json';
    xhr.timeout = 120000;
    xhr.upload.addEventListener('progress', uploadEvent => {
      if (!uploadEvent.lengthComputable) return;
      const percent = Math.round((uploadEvent.loaded / uploadEvent.total) * 100);
      progressBar.value = percent;
      progressValue.textContent = `${percent}%`;
      progressLabel.textContent = percent === 100
        ? 'Verifying documents securely…'
        : 'Uploading documents securely…';
    });
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300 && xhr.response?.redirect_url) {
        window.location.assign(xhr.response.redirect_url);
        return;
      }
      const messages = xhr.response?.errors || [
        xhr.status === 413
          ? 'The total upload exceeds the allowed request size. Each document must be 5 MB or smaller.'
          : 'We could not complete registration. Please review your details and try again.'
      ];
      resetProgress();
      showServerErrors(messages);
    });
    xhr.addEventListener('error', () => {
      resetProgress();
      showServerErrors(['A network error interrupted the upload. Your documents were not confirmed; please try again.']);
    });
    xhr.addEventListener('timeout', () => {
      resetProgress();
      showServerErrors(['The upload took too long. Please check your connection and try again.']);
    });
    xhr.send(new FormData(form));
  });
});
