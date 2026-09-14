// frontend/js/sidebar.js — Sidebar renderer

function renderSidebar(active) {
    const user = getStoredUser();

    const links = [
        ['dashboard',    'bi-speedometer2',     'Dashboard',          'dashboard.html'],
        ['income',       'bi-arrow-down-circle', 'Income',             'income.html'],
        ['expense',      'bi-arrow-up-circle',   'Expenses',           'expense.html'],
        ['transactions', 'bi-clock-history',     'Transactions',       'transactions.html'],
        ['budget',       'bi-wallet2',           'Budget',              'budget.html'],
        ['savings',      'bi-piggy-bank',        'Savings',              'savings.html'],
        ['reports',      'bi-bar-chart-line',    'Reports',              'reports.html'],
        ['ai',           'bi-robot',             'AI Insights',           'ai_insights.html'],
        ['chat',         'bi-chat-dots',         'AI Chat',              'ai_chat.html'],
        ['planner',      'bi-graph-up-arrow',    'Investment Planner',    'investment_planner.html'],
        ['profile',      'bi-person-circle',     'Profile',              'profile.html']
    ];

    const nav = links.map(([key, icon, label, href]) =>
        `<a href="${href}" class="${active === key ? 'active' : ''}">
            <i class="bi ${icon}"></i>${label}
        </a>`
    ).join('');

    const adminNav = user.role === 'admin'
        ? `<div class="sidebar-section mt-2">Admin</div>
           <a href="admin.html" class="${active === 'admin' ? 'active' : ''}">
               <i class="bi bi-shield-check"></i>Admin Panel
           </a>`
        : '';

    const el = document.getElementById('sidebar');

    if (!el) return;

    el.innerHTML = `
        <div class="sidebar-brand">
            <h5>💰 FinanceAI</h5>
            <small>Smart Money Management</small>
        </div>

        <div class="sidebar-nav">
            <div class="sidebar-section">Menu</div>
            ${nav}
            ${adminNav}
        </div>

        <div class="sidebar-footer">
            <div class="sidebar-user">
                <div class="user-avatar">${getUserInitials(user.name)}</div>

                <div>
                    <div style="color:#e2e8f0;font-weight:600;font-size:.82rem">
                        ${user.name || 'User'}
                    </div>

                    <div style="font-size:.72rem">
                        ${user.email || ''}
                    </div>
                </div>
            </div>

            <button
                onclick="confirmLogout()"
                class="btn btn-sm w-100 mt-3"
                style="background:rgba(255,255,255,.08);color:#94a3b8;border:none">
                <i class="bi bi-box-arrow-left me-1"></i>Logout
            </button>
        </div>
    `;

    setupMobileMenu();
}

function setupMobileMenu() {
    const topbar = document.querySelector('.topbar');

    if (!topbar) return;

    let menuBtn = document.querySelector('.mobile-menu-btn');

    if (!menuBtn) {
        menuBtn = document.createElement('button');
        menuBtn.className = 'mobile-menu-btn';
        menuBtn.innerHTML = '<i class="bi bi-list"></i>';
        menuBtn.setAttribute('aria-label', 'Open menu');

        // Button ko topbar ke andar rakho
        topbar.insertBefore(menuBtn, topbar.firstChild);
    }

    menuBtn.onclick = toggleMobileSidebar;

    document.querySelectorAll('.sidebar-nav a').forEach(link => {
        link.addEventListener('click', () => {
            const sidebar = document.getElementById('sidebar');

            if (sidebar) {
                sidebar.classList.remove('mobile-open');
            }
        });
    });
}

function toggleMobileSidebar() {
    const sidebar = document.getElementById('sidebar');

    if (!sidebar) return;

    sidebar.classList.toggle('mobile-open');
}

async function loadNotifBadge() {
    const badge = document.getElementById('notifBadge');

    if (!badge) return;

    const res = await API.get('/api/notifications?is_read=false');
    const count = res?.unread_count || 0;

    badge.textContent = count;
    badge.style.display = count > 0 ? 'inline-block' : 'none';
}

function confirmLogout() {
    const confirmed = confirm(
        "Are you sure you want to logout?"
    );

    if (!confirmed) {
        return;
    }

    logout();
}