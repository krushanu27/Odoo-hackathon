# DESIGN.md — Brightloop Subscription Management System

The visual and interaction design spec for the Brightloop subscription platform. Use it as the reference for every screen, component and style decision.

**Visual direction:** inspired by modern enterprise finance software such as zuora.com: deep navy surfaces, one confident accent color, large, calm headlines, generous whitespace, oversized metric numerals and clean data tables. We borrow the *feel*, not the brand. Do not reuse Zuora's logo, name, copy, illustrations or exact colors.

---

## 1. Design principles

1. **Numbers first.** This is a money product. Amounts, statuses and dates are the most important pixels on any screen. Make them big, aligned and easy to scan.
2. **Always show where things stand.** Every subscription and invoice shows its lifecycle state as a status badge and, on detail pages, as a stepper.
3. **One primary action per view.** Each page has at most one filled primary button. Everything else is secondary or a ghost button.
4. **Role-aware, not role-cluttered.** Hide what a role can't do instead of disabling it. Admin, Staff and Customer each see a UI that fits their job.
5. **Fast by default.** Every page should render in under 2 seconds with thousands of rows. Paginate on the server, show skeletons, never block the whole page on a spinner.
6. **Calm confidence.** Enterprise tone: no playful illustrations or loud colors. Use color only for meaning (status, action, alert).

---

## 2. Design tokens

Define all tokens as CSS custom properties on `:root`. Components never use raw hex values.

### 2.1 Color

#### Brand & neutrals

| Token | Hex | Use |
|---|---|---|
| `--color-navy-950` | `#0A1628` | Sidebar, auth-page brand panel, landing hero |
| `--color-navy-900` | `#10213A` | Sidebar hover, dark cards |
| `--color-navy-800` | `#1B3155` | Dark-surface borders, active nav item |
| `--color-primary-600` | `#2563EB` | Primary buttons, links, focus ring |
| `--color-primary-700` | `#1D4ED8` | Primary hover |
| `--color-primary-50` | `#EFF4FF` | Selected rows, active tab background |
| `--color-accent-500` | `#14C8A0` | Highlight on dark surfaces (metric glow, chart series 1, hero accent word) |
| `--color-gray-900` | `#0F172A` | Primary text |
| `--color-gray-600` | `#475569` | Secondary text, table headers |
| `--color-gray-400` | `#94A3B8` | Placeholder, disabled text |
| `--color-gray-200` | `#E2E8F0` | Borders, dividers |
| `--color-gray-100` | `#F1F5F9` | Table header background, input fill |
| `--color-gray-50` | `#F8FAFC` | App background |
| `--color-white` | `#FFFFFF` | Cards, modals, inputs |

#### Semantic

| Token | Text / icon | Background | Meaning |
|---|---|---|---|
| `success` | `#047857` | `#ECFDF5` | Active, Paid, Confirmed payment |
| `warning` | `#B45309` | `#FFFBEB` | Expiring soon, Due soon, Paused |
| `danger` | `#B91C1C` | `#FEF2F2` | Overdue, Cancelled, failed validation |
| `info` | `#1D4ED8` | `#EFF4FF` | Quotation, Confirmed (pre-active) |
| `neutral` | `#475569` | `#F1F5F9` | Draft, Closed |

**Rules**
- Text on white must meet WCAG AA, 4.5:1. All text tokens above pass.
- Never use color as the only signal. Badges always include a text label, and an icon where space allows.
- `--color-accent-500` is for dark surfaces and charts only. Never use it for body text on white.

### 2.2 Typography

- **Sans (UI + headings):** `Inter`, fallback `system-ui, -apple-system, "Segoe UI", sans-serif`
- **Mono (IDs, invoice numbers, amounts in tables):** `JetBrains Mono`, fallback `ui-monospace, monospace`
- Turn on tabular numbers for any numeric column with `font-variant-numeric: tabular-nums;`.

| Token | Size / line-height | Weight | Use |
|---|---|---|---|
| `display` | 56 / 64 | 700 | Landing hero only |
| `h1` | 32 / 40 | 700 | Page title |
| `h2` | 24 / 32 | 600 | Section title, modal title |
| `h3` | 18 / 28 | 600 | Card title |
| `metric` | 36 / 44 | 700 | KPI numbers on dashboard |
| `body` | 15 / 24 | 400 | Default text |
| `body-sm` | 13 / 20 | 400 | Table cells, helper text |
| `label` | 13 / 20 | 500 | Form labels, buttons |
| `eyebrow` | 12 / 16, `letter-spacing: 0.08em`, UPPERCASE | 600 | Section kicker above headings (e.g. `BILLING`) |

On mobile (< 640px), scale `display` to 36/44 and `h1` to 26/34.

### 2.3 Spacing

4px base scale: `--space-1: 4px`, `2: 8px`, `3: 12px`, `4: 16px`, `5: 20px`, `6: 24px`, `8: 32px`, `10: 40px`, `12: 48px`, `16: 64px`, `24: 96px`.

- Card padding: `24px` (`16px` on mobile)
- Gap between cards: `24px`
- Page gutter: `32px` desktop, `16px` mobile
- Vertical gap between landing-page sections: `96px`

### 2.4 Radius, borders, elevation

| Token | Value | Use |
|---|---|---|
| `--radius-sm` | `6px` | Inputs, badges, small buttons |
| `--radius-md` | `10px` | Buttons, dropdowns |
| `--radius-lg` | `14px` | Cards, modals |
| `--radius-full` | `999px` | Pills, avatars |
| `--shadow-sm` | `0 1px 2px rgba(15,23,42,.06)` | Cards at rest |
| `--shadow-md` | `0 4px 12px rgba(15,23,42,.08)` | Dropdowns, hovered cards |
| `--shadow-lg` | `0 16px 40px rgba(15,23,42,.16)` | Modals, drawers |

Cards use a `1px solid var(--color-gray-200)` border plus `--shadow-sm`. They do not use heavy shadows.

### 2.5 Motion

- Duration: `150ms` for hover and focus, `200ms` for drawers and modals.
- Easing: `cubic-bezier(.2,.8,.2,1)`.
- Respect `prefers-reduced-motion`: disable transforms and keep only opacity changes.

### 2.6 Icons

Use **Lucide** line icons, 1.75px stroke, at 16px inside tables and buttons and 20px in navigation. Icons inherit `currentColor`.

---

## 3. Layout

### 3.1 Breakpoints

| Name | Min width |
|---|---|
| `sm` | 640px |
| `md` | 768px |
| `lg` | 1024px |
| `xl` | 1280px |

Content max-width is `1280px`. Forms max out at `720px`.

### 3.2 App shell (Admin & Staff)

```
┌────────────┬──────────────────────────────────────────────┐
│  LOGO      │  Top bar: page title · global search · 🔔 · avatar │
│            ├──────────────────────────────────────────────┤
│  Dashboard │                                              │
│  Subscript.│   Page content (gray-50 background)          │
│  Invoices  │   ┌ Page header: h1 + primary action ┐      │
│  Payments  │   │ Filters bar                       │      │
│  Customers │   │ Table / cards                     │      │
│  ───────── │   └───────────────────────────────────┘      │
│  Products  │                                              │
│  Plans     │                                              │
│  Templates │                                              │
│  Discounts │                                              │
│  Taxes     │                                              │
│  Users     │  (admin only)                                │
└────────────┴──────────────────────────────────────────────┘
```

- **Sidebar:** 248px wide on `navy-950`, white nav text at 72% opacity. The active item uses full opacity, a `navy-800` background and a 3px `accent-500` left bar. Below `lg` it collapses to a 64px icon-only rail, and below `md` it becomes an off-canvas drawer.
- **Group labels:** "Operations" covers Dashboard through Customers. "Catalog & Rules" covers Products through Taxes. "Settings" holds Users.
- **Top bar:** 64px tall on a white background with a bottom border.

### 3.3 Customer portal shell

There is no sidebar. Use a white top navigation bar with the logo and the links **My Subscriptions**, **Invoices**, **Payments** and **Profile**, plus an avatar menu. Content is centered at a 1080px max width. The portal should feel lighter and simpler than the internal app.

### 3.4 Auth shell

The layout is a split screen. The left 45% is a `navy-950` brand panel with the logo, a one-line value proposition, and a subtle accent gradient blob. The right side holds a white form panel with a 400px-wide form. Below `md` the brand panel is hidden.

---

## 4. Components

### 4.1 Buttons

| Variant | Style |
|---|---|
| Primary | `primary-600` background, white text; hover `primary-700` |
| Secondary | White background, `gray-200` border, `gray-900` text; hover `gray-50` |
| Ghost | Transparent, `gray-600` text; hover `gray-100` |
| Danger | `danger` text color as background, white text; used only in confirm dialogs |
| On-dark | White background, `navy-950` text; used on the landing page and auth brand panel |

- Sizes: `sm` 32px, `md` 40px (default), `lg` 48px. Use 16px horizontal padding and `--radius-md`.
- Loading state: replace the label with a spinner and keep the button width so the layout doesn't jump.
- Focus: `outline: 2px solid var(--color-primary-600); outline-offset: 2px;`.

### 4.2 Status badges

Badges are pill-shaped (`--radius-full`), use `body-sm` at weight 500, have a 6px dot on the left, and use the semantic background and text colors.

**Subscription states**

| State | Tone |
|---|---|
| Draft | neutral |
| Quotation | info |
| Confirmed | info |
| Active | success |
| Paused | warning |
| Closed | neutral (dot hollow) |

**Invoice states**

| State | Tone |
|---|---|
| Draft | neutral |
| Confirmed | info |
| Paid | success |
| Overdue *(derived: Confirmed + past due date)* | danger |
| Cancelled | danger (strikethrough-free, dot hollow) |

### 4.3 Lifecycle stepper

Show the stepper at the top of every subscription and invoice detail page.

```
● Draft ── ● Quotation ── ◉ Confirmed ── ○ Active ── ○ Closed
```

Completed steps are filled with `primary-600`. The current step is a ring with a bold label. Future steps are `gray-400`. Each step shows the date it was reached as a tooltip or caption. Under `md`, collapse the stepper to "Step 3 of 5 · Confirmed".

### 4.4 Data table

Data tables are the most important component in the app.

- **Header row:** `gray-100` background, `label` text in `gray-600`, sticky on scroll.
- **Rows:** 52px tall (40px in compact mode), a `gray-200` bottom border, and a `gray-50` hover background. The whole row is clickable and opens the detail page.
- **Numeric columns:** right-aligned, monospace, tabular numbers. Currency is formatted in the user's locale, for example `₹ 12,450.00`.
- **ID columns:** monospace in `primary-600` (for example `SUB-000123` or `INV-2026-0042`).
- **Selection:** a checkbox column, with a bulk-action bar that slides in above the table ("3 selected · Confirm · Send · Export").
- **Pagination:** server-side, defaulting to 25 rows with options for 25, 50 and 100. Show "Showing 1–25 of 3,482".
- **Loading:** show 8 skeleton rows. Never blank the table while it re-fetches. Keep the old rows at 60% opacity instead.
- **Empty state:** a centered icon, a one-line explanation and a primary action, for example "No invoices yet. Generate invoices from active subscriptions."
- **Mobile:** below `md`, each row becomes a stacked card with ID and status at the top, then the amount in large type, then key dates.

### 4.5 Filters bar

The filters bar sits above every list. It contains:
- a search input (debounced 300ms),
- filter chips such as `Status ▾`, `Plan ▾`, `Date range ▾` and `Customer ▾`,
- "Clear all", and
- a saved-view dropdown on the right.

Active filters appear as removable chips. Sync filter state to the URL query string so views can be shared and bookmarked.

### 4.6 KPI / metric card

```
┌──────────────────────────┐
│ ACTIVE SUBSCRIPTIONS     │  ← eyebrow, gray-600
│ 1,284                    │  ← metric, gray-900
│ ▲ 4.2% vs last month     │  ← body-sm, success/danger
└──────────────────────────┘
```

- The dashboard has four cards in a row: **Active Subscriptions**, **Revenue (this period)**, **Outstanding**, and **Overdue Invoices**. The Overdue card's value uses `danger` text.
- Clicking a card opens the matching list with the filter already applied.

### 4.7 Forms

- Labels sit above fields. Required fields get a `*` in `danger`.
- Inputs are 40px tall with a `gray-200` border and `--radius-sm`. On focus the border turns `primary-600` and gets a 3px `primary-50` ring.
- Help text goes below the field in `body-sm` `gray-600`. Errors replace the help text in `danger` with an icon.
- Validate on blur, then live once the user has touched a field.
- Long forms (Product, Plan, Subscription) use titled section cards and a **sticky footer action bar** with Cancel (ghost) and Save (primary).
- Money inputs have a currency prefix and are right-aligned. Percentage inputs have a `%` suffix.

### 4.8 Line-items editor

Used on subscriptions, quotation templates and invoices.

| Product (searchable select) | Variant | Qty | Unit price | Taxes (multi-chip) | Discount | Amount | ✕ |
|---|---|---|---|---|---|---|---|

- Use inline editable cells, with an "+ Add line" ghost button below the table.
- A totals panel sits right-aligned below the lines: **Untaxed amount**, **Discount** (shown in `success` as a negative, with the rule name as a caption), **Taxes** (grouped by tax name) and **Total** (h3, bold).
- If the quantity is below the plan's minimum, show an inline error on the Qty cell, for example "Minimum 5 for this plan".

### 4.9 Other components

- **Modal:** 480px wide (720px for large modals) with `--radius-lg` and `--shadow-lg`. Use modals only for confirmations and short forms. Destructive confirms must state the consequence, for example "Cancel INV-2026-0042? This cannot be undone."
- **Drawer:** 480px wide, slides in from the right. Use it for quick views (customer preview, payment entry) without leaving the list.
- **Toast:** appears bottom-right and auto-dismisses after 5s. Success toasts can include an Undo action where one makes sense.
- **Tabs:** underline style with a 2px `primary-600` active bar.
- **Timeline / activity log:** a vertical line with dots, on subscription and invoice detail pages (for example "Invoice INV-…-0042 created by Billing run · 1 Nov 2026").
- **Avatar:** initials on a deterministic pastel background.
- **Tooltip:** `navy-950` background, white `body-sm` text, 6px radius.

---

## 5. Screens

Each screen maps to a scene in the problem statement.

### 5.1 Auth: "A new customer signs up"

- **Sign up:** name, email and password, with an optional company field.
  - A live **password checklist** under the field ticks green as each rule is met: *more than 8 characters · uppercase letter · lowercase letter · special character*. The submit button stays disabled until every rule passes.
  - If the email is already registered, show an inline error: "An account with this email already exists. Sign in or reset your password."
- **Sign in:** email and password, a "Forgot password?" link, and a show/hide toggle on the password field.
- **Forgot password:** email field. The confirmation screen always reads "If an account exists for this email, a reset link is on its way", whether or not the email exists, so it doesn't reveal registered addresses.
- **Reset password:** new password with the same checklist, plus a confirm field.

### 5.2 Dashboard: "The finance lead, at the end of the month" (Admin & Staff)

1. Page header: "Overview", with a date-range picker (This month / Last month / Quarter / Custom) on the right.
2. The four KPI cards (§4.6).
3. A row with two panels:
   - **Revenue chart** (2/3 width): a bar chart of collected payments per month, with an outstanding-amount line overlaid. Use `accent-500` for collected and `primary-600` for outstanding.
   - **Subscriptions by state** (1/3 width): a donut chart using the badge colors, with the legend as a clickable list.
4. **Overdue invoices** table showing the top 10 sorted by days overdue, with a "Days overdue" column in `danger` and a "Record payment" action per row.
5. **Renewals due in 30 days** list.

### 5.3 Subscriptions: "Turning a quote into a subscription"

- **List:** Number, Customer, Plan, Start, Expiry, Next invoice, Recurring amount, Status.
  - Above the table, add tabs: All · Quotations · Active · Paused · Closed.
- **Create:** Step 1 is an optional **"Start from template"** picker showing template cards with the plan, line count and validity days. Picking one prefills everything. After that the form has these sections:
  - Customer
  - Plan
  - Dates: start; expiry is auto-filled from the plan and can be edited
  - Payment terms
  - Lines (§4.8)
- **Detail:** stepper, header with the number and status, and context actions that depend on state:

  | State | Primary action | Secondary actions |
  |---|---|---|
  | Draft | Send quotation | Edit, Delete |
  | Quotation | Confirm | Edit |
  | Confirmed | Activate | — |
  | Active | Create invoice | Pause, Renew, Close (each shown only if the plan allows it) |
  | Paused | Resume | Close |

  Tabs: **Lines · Invoices · Payments · Activity**.

### 5.4 Invoices: "Billing day"

- **List:** Number, Customer, Subscription, Invoice date, Due date, Total, Amount due, Status.
  - Above the table, add tabs: All · Draft · Confirmed · Paid · Overdue.
- **"Run billing" primary action** (Admin & Staff). A modal shows a preview: "142 subscriptions are due for billing today · 0 already invoiced for this period (skipped)" followed by a "Generate 142 draft invoices" button. Afterwards, a results toast links to the filtered list. The preview makes the *nothing billed twice or skipped* rule visible.
- **Detail:** a document-style layout on a white "paper" card, 820px max width, mirroring the printed invoice: company block, customer block, lines, tax breakdown, totals, payment history.
  - Actions: **Confirm**, **Send**, **Print / PDF**, **Record payment**, **Cancel**. Show only those valid for the current state.
- **Print stylesheet:** hide the shell and print just the paper card in black on white.

### 5.5 Payments: "The money comes in"

- **List:** Date, Invoice, Customer, Method (icon + label: Bank transfer, Card, UPI, Cash, Cheque), Amount, Note.
- **Record payment drawer:** invoice (searchable, showing the amount due), method, amount (prefilled with the amount due; partial payments allowed), date (defaults to today), note.
  - After saving, the invoice badge updates to **Paid** when fully paid. Otherwise it shows "Partially paid · ₹X due" as secondary text.

### 5.6 Catalog (Admin): "Launching a new plan"

- **Products:** list + form with name, type, sales price, cost price and notes.
  - A **Variants** section has attribute rows (e.g. *Brand*) with values and a **price extra**, for example "Odoo · + ₹560". A preview line shows the computed price: "Base ₹2,000 + Odoo ₹560 = ₹2,560".
- **Plans:** form with price, billing period (segmented control: Daily · Weekly · Monthly · Yearly), minimum quantity and an availability date range.
  - A **Plan options** card holds toggles, each with a one-line explanation: *Auto-close at end date*, *Can be closed early*, *Can be paused*, *Can be renewed*.
- **Quotation templates:** name, validity in days, plan, and default lines (§4.8).
- **Taxes:** name, type (percentage or fixed), rate and an active toggle.
- **Discounts** ("A customer asks for a better price"): name, type (segmented: Fixed amount · Percentage), value, minimum purchase *or* minimum quantity, start and end dates, usage limit, and scope (radio: *Specific products* with a product multi-select, or *Whole subscription*).
  - In the list, show a usage progress bar ("37 / 100 used") and a status badge: Scheduled, Active, Expired, or Exhausted.

The discount and catalog screens are visible to Admin only. Staff never see the menu entries.

### 5.7 Users & customers

- **Customers** (Admin & Staff): list + detail with tabs for Subscriptions, Invoices and Payments, and an outstanding-balance callout.
- **Users** (Admin only): staff list with an "Invite staff" primary button. Only the admin sees this page.

### 5.8 Customer portal: "Customers manage their own subscriptions"

- **My Subscriptions:** a card grid. Each card shows the plan name, status badge, next billing date and recurring amount in `metric` style, with actions such as View, Pause or Renew, shown only where the plan allows them.
- **Invoices:** a table with a **Download PDF** action. Unpaid invoices are highlighted with a `warning` left border.
- **Profile:** contact details and change password.
- The portal shows only the logged-in customer's own records. Never render internal data such as cost price, other customers, or staff notes.

### 5.9 Public landing page (optional, for the demo)

This is a Zuora-style structure, with original content.

1. **Hero:** `navy-950` background. An `eyebrow` reading "SUBSCRIPTION BILLING", a `display` headline ("Run every plan, renewal and invoice in one place") with one word in `accent-500`, a sub-headline, and two CTAs: Get started (on-dark) and Sign in (ghost, white).
   - On the right, a tilted dashboard screenshot with a soft accent glow behind it.
2. **Pain → fix strip:** five small cards built from the PDF's "How things run today" list. Each shows the old way struck through in `gray-400` and the new way in `gray-900`, for example ~~Renewals remembered by whoever notices~~ → Automatic renewals.
3. **Feature grid:** six cards (Plans & variants, Quotes to subscriptions, Automated billing, Taxes & discounts, Payments tracking, Revenue dashboard), each with an icon, title and two-line description.
4. **Stats band:** three oversized metrics on a white background, for example "0 missed renewals · 1-click billing runs · < 2s per page".
5. **CTA band:** `navy-950` background with a headline and a primary button.
6. **Footer:** a minimal four-column footer.

---

## 6. Role-based visibility

| Area | Admin | Staff | Customer |
|---|---|---|---|
| Dashboard | ✔ | ✔ | — |
| Subscriptions | Full | Create / edit / transition | Own only (portal) |
| Invoices | Full | Full except delete | Own only, view & download |
| Payments | Full | Record & view | Own only, view |
| Customers | Full | View & edit | Own profile |
| Products, Plans, Templates | Full | View only (no nav entry; used inside pickers) | — |
| Discounts, Taxes | Full | — | — |
| Users (add staff) | ✔ | — | — |

Hide navigation entries and action buttons the current role cannot use. Do not show them disabled.

---

## 7. Performance & states

- **Under 2 seconds** for every page. Paginate, filter and sort on the server, and pre-aggregate dashboard numbers into a single endpoint.
- Show skeletons on first load and keep stale data visible while re-fetching.
- Every list and panel defines a **loading**, **empty**, **error** (with Retry) and **no-permission** state.
- Debounce search (300ms) and cancel stale requests.
- Lazy-load the chart library on the dashboard only.

---

## 8. Accessibility

- WCAG 2.1 AA contrast for all text and UI controls.
- Everything is keyboard reachable with a visible focus ring. Modals trap focus and close on `Esc`.
- Every status badge carries a text label. Charts get a "View as table" toggle.
- Form errors are linked with `aria-describedby`, and the page announces the error count on submit.
- Include a "Skip to content" link in both shells.
- Hit targets are at least 40×40px (44px on touch).

---

## 9. Content & formatting

- **Voice:** clear, short, specific. Write "Invoice sent to priya@acme.com", not "Operation successful".
- **Buttons:** verb first ("Record payment", "Generate invoices").
- **Dates:** `31 Oct 2026` in tables. Relative dates ("in 3 days", "12 days overdue") as secondary text.
- **Currency:** two decimals, locale grouping, symbol prefix. Negative discounts are shown as `− ₹500.00`.
- **IDs:** `SUB-000123`, `INV-2026-0042`, `PAY-2026-0107`, `QT-0009`.

---

## 10. CSS token starter

```css
:root {
  /* brand */
  --color-navy-950: #0A1628;
  --color-navy-900: #10213A;
  --color-navy-800: #1B3155;
  --color-primary-50: #EFF4FF;
  --color-primary-600: #2563EB;
  --color-primary-700: #1D4ED8;
  --color-accent-500: #14C8A0;

  /* neutrals */
  --color-gray-900: #0F172A;
  --color-gray-600: #475569;
  --color-gray-400: #94A3B8;
  --color-gray-200: #E2E8F0;
  --color-gray-100: #F1F5F9;
  --color-gray-50:  #F8FAFC;
  --color-white:    #FFFFFF;

  /* semantic */
  --color-success: #047857;  --color-success-bg: #ECFDF5;
  --color-warning: #B45309;  --color-warning-bg: #FFFBEB;
  --color-danger:  #B91C1C;  --color-danger-bg:  #FEF2F2;
  --color-info:    #1D4ED8;  --color-info-bg:    #EFF4FF;
  --color-neutral: #475569;  --color-neutral-bg: #F1F5F9;

  /* type */
  --font-sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;

  /* shape */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-full: 999px;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, .06);
  --shadow-md: 0 4px 12px rgba(15, 23, 42, .08);
  --shadow-lg: 0 16px 40px rgba(15, 23, 42, .16);

  /* motion */
  --ease: cubic-bezier(.2, .8, .2, 1);
  --dur-fast: 150ms;
  --dur-base: 200ms;
}

body {
  font-family: var(--font-sans);
  font-size: 15px;
  line-height: 24px;
  color: var(--color-gray-900);
  background: var(--color-gray-50);
}
```

If the project uses Tailwind, map these tokens in `tailwind.config` under `theme.extend.colors`, `borderRadius`, `boxShadow` and `fontFamily` rather than hard-coding hex values in class names.
