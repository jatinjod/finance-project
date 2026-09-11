// frontend/js/auth.js
// Authentication utilities and helpers

function requireAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = 'login.html';
        return false;
    }
    return true;
}

function requireAdmin() {
    if (!requireAuth()) return false;
    const user = getStoredUser();
    if (user.role !== 'admin') {
        window.location.href = 'dashboard.html';
        return false;
    }
    return true;
}

function getStoredUser() {
    try {
        return JSON.parse(localStorage.getItem('user') || '{}');
    } catch {
        return {};
    }
}

function logout() {
    clearAuthData();
    window.location.href = 'login.html';
}

// ── Formatting Helpers ────────────────────────
function getUserInitials(name) {
    if (!name || typeof name !== 'string') return 'U';
    const parts = name.trim().split(' ').filter(Boolean);
    if (parts.length === 0) return 'U';
    if (parts.length === 1) return parts[0][0].toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function formatCurrency(amount) {
    const num = Number(amount);
    if (isNaN(num)) return '₹0';
    return '₹' + num.toLocaleString('en-IN', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });
}

function formatDate(str) {
    if (!str) return '—';
    try {
        const d = new Date(str);
        if (isNaN(d.getTime())) return str;
        return d.toLocaleDateString('en-IN', {
            day:   '2-digit',
            month: 'short',
            year:  'numeric'
        });
    } catch {
        return str;
    }
}

// ── UI Helpers ────────────────────────────────
function showToast(message, type = 'success') {
    const el = document.getElementById('toast');
    if (!el) {
        console.log(`Toast [${type}]:`, message);
        return;
    }
    el.querySelector('.toast-body').textContent = message;
    el.className = `toast align-items-center text-white bg-${type} border-0`;
    const instance = bootstrap.Toast.getOrCreateInstance(el, { delay: 3500 });
    instance.show();
}

function showAlert(containerId, message, type = 'danger') {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show mb-3" role="alert">
            <i class="bi bi-${type === 'danger' ? 'exclamation-circle'
                            : type === 'success' ? 'check-circle'
                            : 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>`;
}

function clearAlert(containerId) {
    const el = document.getElementById(containerId);
    if (el) el.innerHTML = '';
}

function setLoading(buttonId, loading, text = 'Save') {
    const btn = document.getElementById(buttonId);
    if (!btn) return;
    btn.disabled = loading;
    btn.innerHTML = loading
        ? `<span class="spinner-border spinner-border-sm me-1"></span>Loading...`
        : text;
}