/**
 * NexaBank — Main JavaScript
 * Handles sidebar, theme toggle, toasts, and global utilities.
 */

// ── Theme Management ──────────────────────────────────────────────────
const ThemeManager = {
  init() {
    const renderedTheme = document.documentElement.getAttribute('data-theme');
    const theme = renderedTheme === 'dark' ? 'dark' : 'light';
    this.apply(theme);
    this.bindToggle();
  },

  apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('nexabank-theme', theme);

    // Sync with server if logged in
    const toggleBtn = document.getElementById('themeToggle');
    if (toggleBtn) {
      toggleBtn.dataset.theme = theme;
      toggleBtn.setAttribute('aria-pressed', String(theme === 'dark'));
    }
  },

  toggle() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    this.apply(next);

    this.persist(next).catch(error => console.error('Unable to save theme:', error));
  },

  persist(theme) {
    return fetch('/api/toggle-theme', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
      body: JSON.stringify({ theme })
    }).then(response => {
      if (!response.ok) throw new Error(`Theme update failed (${response.status})`);
    });
  },

  bindToggle() {
    const btn = document.getElementById('themeToggle');
    if (btn) btn.addEventListener('click', () => this.toggle());
  }
};


// ── Sidebar Management ────────────────────────────────────────────────
const Sidebar = {
  init() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const hamburger = document.getElementById('hamburgerBtn');

    if (!sidebar) return;

    document.body.classList.toggle(
      'sidebar-collapsed',
      localStorage.getItem('nexabank-sidebar') === 'collapsed'
    );
    if (hamburger) {
      const mobile = window.matchMedia('(max-width: 1024px)').matches;
      const expanded = mobile ? sidebar.classList.contains('open') : !document.body.classList.contains('sidebar-collapsed');
      hamburger.setAttribute('aria-expanded', String(expanded));
      hamburger.setAttribute(
        'aria-label',
        mobile ? 'Open navigation' : expanded ? 'Collapse sidebar' : 'Expand sidebar'
      );
    }
    hamburger?.addEventListener('click', () => {
      if (window.matchMedia('(max-width: 1024px)').matches) {
        this.open();
      } else {
        this.toggleCollapsed();
      }
    });
    overlay?.addEventListener('click', () => this.close());

    // Mark active nav item
    this.markActive();
    document.querySelectorAll('.sidebar-link').forEach(link => {
      link.title = link.textContent.trim();
    });
  },

  toggleCollapsed() {
    const collapsed = document.body.classList.toggle('sidebar-collapsed');
    localStorage.setItem('nexabank-sidebar', collapsed ? 'collapsed' : 'expanded');
    const button = document.getElementById('hamburgerBtn');
    if (button) {
      button.setAttribute('aria-expanded', String(!collapsed));
      button.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    }
  },

  open() {
    document.getElementById('sidebar')?.classList.add('open');
    document.getElementById('sidebarOverlay')?.classList.add('show');
    document.body.style.overflow = 'hidden';
    document.getElementById('hamburgerBtn')?.setAttribute('aria-expanded', 'true');
    document.getElementById('hamburgerBtn')?.setAttribute('aria-label', 'Close navigation');
  },

  close() {
    document.getElementById('sidebar')?.classList.remove('open');
    document.getElementById('sidebarOverlay')?.classList.remove('show');
    document.body.style.overflow = '';
    document.getElementById('hamburgerBtn')?.setAttribute('aria-expanded', 'false');
    document.getElementById('hamburgerBtn')?.setAttribute('aria-label', 'Open navigation');
  },

  markActive() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.sidebar-link').forEach(link => {
      const href = link.getAttribute('href');
      if (href && (currentPath === href || (href !== '/' && currentPath.startsWith(href)))) {
        link.classList.add('active');
        link.setAttribute('aria-current', 'page');
      } else {
        link.removeAttribute('aria-current');
      }
    });
  }
};


// ── Toast Notifications ───────────────────────────────────────────────
const Toast = {
  container: null,

  init() {
    this.container = document.getElementById('toastContainer');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toastContainer';
      this.container.className = 'toast-container';
      document.body.appendChild(this.container);
    }

    // Auto-show server-side flash messages
    document.querySelectorAll('.flash-message').forEach(el => {
      const type = el.dataset.type || 'info';
      const msg = el.dataset.message;
      if (msg) this.show(msg, type);
    });
  },

  show(message, type = 'info', duration = 5000) {
    const icons = {
      success: 'fa-circle-check',
      danger: 'fa-circle-exclamation',
      warning: 'fa-triangle-exclamation',
      info: 'fa-circle-info'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icon = document.createElement('i');
    icon.className = `fa-solid ${icons[type] || icons.info} toast-icon`;
    icon.setAttribute('aria-hidden', 'true');

    const body = document.createElement('div');
    body.className = 'toast-body';
    const text = document.createElement('div');
    text.className = 'toast-msg';
    text.textContent = message;
    body.appendChild(text);

    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'toast-close';
    close.setAttribute('aria-label', 'Dismiss notification');
    close.textContent = '×';
    close.addEventListener('click', () => toast.remove());

    toast.append(icon, body, close);

    this.container.appendChild(toast);
    setTimeout(() => toast.remove(), duration);
  }
};


// ── Alert Dismissal ───────────────────────────────────────────────────
function initAlerts() {
  document.querySelectorAll('.alert-close').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.alert')?.remove();
    });
  });
}

function initFormLoadingStates() {
  document.querySelectorAll('form[method="post"]').forEach(form => {
    form.addEventListener('submit', event => {
      const confirmation = form.dataset.confirm;
      if (confirmation) {
        if (form.dataset.confirmed === 'true') {
          delete form.dataset.confirmed;
        } else {
          event.preventDefault();
          if (window.confirm(confirmation)) {
            form.dataset.confirmed = 'true';
            form.requestSubmit(event.submitter);
          }
          return;
        }
      }

      queueMicrotask(() => {
        if (event.defaultPrevented) return;
        const submitButton = form.querySelector('button[type="submit"], button:not([type])');
        if (!submitButton || submitButton.disabled) return;
        submitButton.disabled = true;
        submitButton.classList.add('is-loading');
        submitButton.setAttribute('aria-label', `${submitButton.textContent.trim()} — submitting`);
        form.setAttribute('aria-busy', 'true');
      });
    });
  });
}


// ── Modal Management ──────────────────────────────────────────────────
const Modal = {
  open(id) {
    const modal = document.getElementById(id);
    if (modal) {
      modal.classList.add('show');
      document.body.style.overflow = 'hidden';
    }
  },

  close(id) {
    const modal = document.getElementById(id);
    if (modal) {
      modal.classList.remove('show');
      document.body.style.overflow = '';
    }
  },

  init() {
    // Close on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', e => {
        if (e.target === overlay) {
          overlay.classList.remove('show');
          document.body.style.overflow = '';
        }
      });
    });

    // Escape key
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.show').forEach(m => {
          m.classList.remove('show');
          document.body.style.overflow = '';
        });
      }
    });
  }
};


// ── Utility: Get CSRF Token ───────────────────────────────────────────
function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}


// ── Number formatting ─────────────────────────────────────────────────
function formatCurrency(amount) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2
  }).format(amount);
}


// ── Copy to clipboard ─────────────────────────────────────────────────
function copyToClipboard(text) {
  if (!navigator.clipboard?.writeText) {
    Toast.show('Clipboard access is unavailable in this browser.', 'warning');
    return;
  }
  navigator.clipboard.writeText(text)
    .then(() => Toast.show('Copied to clipboard.', 'success'))
    .catch(error => {
      console.error('Unable to copy to clipboard:', error);
      Toast.show('Could not copy to clipboard. Please try again.', 'danger');
    });
}

function initCopyButtons() {
  document.querySelectorAll('[data-copy]').forEach(button => {
    button.addEventListener('click', () => copyToClipboard(button.dataset.copy));
  });
}


// ── Topbar scroll effect (landing) ────────────────────────────────────
function initLandingNav() {
  const nav = document.querySelector('.landing-nav');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 60);
  });
}

// ── Initialize all ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  ThemeManager.init();
  Sidebar.init();
  Toast.init();
  Modal.init();
  initAlerts();
  initFormLoadingStates();
  initCopyButtons();
  initLandingNav();
});
