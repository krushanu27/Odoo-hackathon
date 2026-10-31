// Shared app shell: sidebar, top bar and icons for the Admin/Staff pages.
(function () {
  const ICON = {
    Dashboard: 'M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z',
    Subscriptions: 'M17 2l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 22l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3',
    Invoices: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8M16 17H8',
    Payments: 'M2 5h20v14H2zM2 10h20M6 15h4',
    Customers: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
    Products: 'M21 8l-9-5-9 5v8l9 5 9-5zM3 8l9 5 9-5M12 13v8',
    Plans: 'M12 2 2 7l10 5 10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
    Templates: 'M8 8h12v12H8zM4 16V4h12',
    Discounts: 'M19 5 5 19M6.5 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5M17.5 20a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5',
    Taxes: 'M5 2v20l3-2 2 2 2-2 2 2 2-2 3 2V2l-3 2-2-2-2 2-2-2-2 2zM9 8h6M9 12h6M9 16h4',
    Users: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8M4 21v-1a6 6 0 0 1 9-5.2M19 15v6M16 18h6',
    Search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16M21 21l-4.3-4.3',
    Bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0'
  };
  const HREF = { Dashboard: 'dashboard.html', Subscriptions: 'subscription.html', Invoices: 'invoices.html' };

  // Staff never see catalog, rules or user management (hidden, not disabled).
  const GROUPS = {
    admin: [
      ['Operations', ['Dashboard', 'Subscriptions', 'Invoices', 'Payments', 'Customers']],
      ['Catalog & rules', ['Products', 'Plans', 'Templates', 'Discounts', 'Taxes']],
      ['Settings', ['Users']]
    ],
    staff: [['Operations', ['Dashboard', 'Subscriptions', 'Invoices', 'Payments', 'Customers']]]
  };

  const icon = (name, size = 20) =>
    `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${ICON[name]}"></path></svg>`;

  const LOGO = '<svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true"><rect width="28" height="28" rx="8" fill="#14C8A0"></rect><circle cx="14" cy="14" r="6.5" fill="none" stroke="#0A1628" stroke-width="3"></circle><circle cx="14" cy="7.5" r="2.6" fill="#FFFFFF"></circle></svg>';

  const sidebar = document.getElementById('sidebar');
  if (sidebar) {
    const active = sidebar.dataset.active;
    const groups = GROUPS[sidebar.dataset.role] || GROUPS.admin;
    sidebar.setAttribute('aria-label', 'Main');
    sidebar.innerHTML =
      `<a class="logo" href="index.html">${LOGO}Brightloop</a>` +
      groups.map(([label, items]) =>
        `<div class="nav-group"><div class="nav-label">${label}</div>` +
        items.map((n) =>
          `<a class="nav-item${n === active ? ' active' : ''}" href="${HREF[n] || '#'}"${n === active ? ' aria-current="page"' : ''}>${icon(n)}${n}</a>`
        ).join('') + '</div>'
      ).join('');
  }

  const topbar = document.getElementById('topbar');
  if (topbar) {
    const { user, role, initials, crumb } = topbar.dataset;
    const left = crumb
      ? `<nav aria-label="Breadcrumb" class="small" style="display:flex;gap:8px;align-items:center;font-size:14px">${crumb}</nav>`
      : `<label class="search">${icon('Search', 16)}<span class="sr-only">Search</span><input type="search" placeholder="Search subscriptions, invoices, customers"></label>`;
    topbar.innerHTML = `${left}
      <div style="display:flex;align-items:center;gap:16px">
        <button type="button" class="btn btn-secondary icon-btn" aria-label="Notifications">${icon('Bell', 18)}</button>
        <div class="user"><div class="avatar">${initials}</div><div><strong>${user}</strong><span class="role">${role}</span></div></div>
      </div>`;
  }

  window.Shell = { icon, LOGO };
})();
