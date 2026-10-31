# Demo Script — Brightloop Subscriptions (≈ 6 minutes)

Story: **one billing month at Brightloop Software**, scene by scene, exactly as the
problem statement tells it.

## Before you start (5 min before)

- Main browser window: logged in as **Admin**, on the **Subscriptions → Dashboard**.
- Private window: logged out, on `http://localhost:8069/web/login` (for signup and the customer).
- Second private window (or after logout): customer `customer6@brightloop.demo` / `Customer#2026` (Acme Ltd).
- Staff login ready: `staff@brightloop.demo` / `Staff#Demo2026`.
- Discuss → #general open in a tab (performance numbers are posted there).

---

## 0. Opening line (15 s)

> "Brightloop runs subscriptions on spreadsheets: renewals get missed, invoices go out wrong,
> and nobody knows the recurring revenue. We built one Odoo module that runs the whole month
> — plans, quotes, automatic billing, discounts, payments, a customer portal and a finance
> dashboard."

## 1. A new customer signs up (40 s)

1. Private window → **Sign up**. Type a weak password like `abc` — the checklist under the field stays unticked.
2. Type `Brightloop#2026` — all four rules tick.

> "Each email can have one account; the password rules are enforced on the server for signup,
> reset and admin edits — the checklist is just the friendly face."

3. Mention roles: **Admin** controls everything; **Staff** works day to day; **Customers** use the portal.
   (Optional: log in as Staff and show the Configuration menu is gone.)

## 2. Launching a plan (40 s)

1. **Configuration → Products → Brightloop CRM → Attributes & Variants** — Brand: **Odoo +560**.
2. **Configuration → Plans** — Daily, Weekly, Monthly, Yearly plans; open one and show
   **Close automatically / Allow early closure / Allow pause / Allow renewal**.

> "Pricing and rules are configuration, not code: the admin decides plan by plan."

## 3. Quote → subscription (60 s)

1. **Subscriptions → New** → customer **Kaveri Coffee Roasters**, **Quotation Template: Enterprise Bundle**.
   Plan, lines, taxes and **Valid Until** fill themselves.
2. **Send Quotation → Confirm → Activate**. Point at the status bar: Draft → Quotation → Confirmed → Active.

> "An expired quotation can't be confirmed, and minimum quantities are enforced."

## 4. Billing day (60 s)

1. On that subscription click **Invoice Now** → the invoice list opens; open the invoice: customer,
   lines with the period, **GST 18%**, and **Discount** lines added automatically
   (Volume 10% for 10+ seats, the Launch Offer, the Analytics promo).
2. Click **Invoice Now** again → *"Nothing is due for billing yet."*

> "Nothing is billed twice: each invoice records its period, and the database itself has a
> unique constraint on subscription + period. If billing missed a run, the next one catches
> up one invoice per period. It runs as a daily scheduled job in batches."

3. Show **Discuss → #general**: *"2,000 subscriptions… list 5 ms, search 5 ms, dashboard 13 ms"* and
   *"Billing run: 800 invoices created in 66.6 seconds"*.

## 5. A customer asks for a better price (30 s)

1. **Configuration → Discounts** — percentage / fixed, minimum quantity or purchase, dates, usage limit, whole subscription or specific products.

> "The admin creates the rule once; it appears on every eligible invoice by itself and stops
> when it expires or runs out."

## 6. The money comes in (40 s)

1. On the invoice: **Confirm → Register Payment** → Bank, part of the amount, today → **Partially Paid**.
2. **Billing → Invoices** → filters **Paid / Outstanding / Overdue**.

## 7. The customer portal (60 s)

1. Log in as **Acme Ltd** (`customer6@brightloop.demo`). **My Account → Subscriptions** — only Acme's.
2. Open it: plan, next invoice, lines, invoices with status.
3. **Add-ons → Analytics → Switch on** → total goes ₹2,400 → ₹2,990. Switch it off again.
4. **Pause** → "not billed until you resume" → **Resume**.

> "Customers only ever see their own records — enforced by database record rules, not by
> hiding buttons. Every portal action is re-checked on the server."

## 8. The finance lead at month end (40 s)

1. Back to Admin → **Subscriptions → Dashboard**: active subscriptions, **MRR**, collected,
   outstanding, overdue, 6-month trend, payments by method.
2. Change the period filter; click **Overdue** → the overdue invoices list.

> "What used to take days at quarter end is one screen, and it stays fast with thousands of
> subscriptions."

## Close (15 s)

> "27 automated tests cover billing, security, discounts, add-ons and the dashboard — they
> caught two real billing bugs today. Everything is in one Odoo module on GitHub."

---

## If something goes wrong

| Problem | Do this |
|---|---|
| A page shows an error | Refresh once; move on to the next scene and come back |
| "Invoice Now" says nothing is due | Use a subscription you just activated, or show an existing invoice from **Billing → Invoices** |
| Portal login fails | Admin → Configuration → **Create Demo Logins** shows the customer login again |
| Odoo not responding | `cd C:\dev\brightloop\addons` → `docker compose restart odoo`, wait 20 s |

## Likely judge questions

- **Why Odoo Community and not the Subscriptions app?** It's Enterprise-only; we reuse Odoo's invoicing, taxes, payments, variants and portal, and build only what's missing.
- **How do you prevent duplicate invoices?** Period recorded on each invoice, skip-if-billed check, row lock against parallel runs, and a PostgreSQL unique constraint as the final guard.
- **What if the scheduler was down for a week?** The next run bills every missed period, one invoice each.
- **How do you know it scales?** Performance Test with 2,000 subscriptions: list 5 ms, search 5 ms, dashboard 13 ms; billing ≈ 12 invoices/s in background batches.
- **How is customer data protected?** Portal users have read-only access filtered by record rules to their own company; actions go through one server method that re-checks access and plan rules.
