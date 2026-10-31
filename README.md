# Brightloop Subscriptions

A subscription management system for **Brightloop Software**, built as an Odoo 19 module
(`brightloop_subscription`). It runs the whole life of a subscription business — products and
plans, quotations, recurring invoices, discounts, payments, a customer portal and a finance
dashboard — in one place.

## Architecture in one sentence

We **reuse Odoo where it is already strong** (invoices, taxes, payments, reconciliation, product
variants, portal, signup) and **build what the problem needs and Odoo Community lacks**
(plans, subscriptions, the recurring billing engine, discounts, the dashboard).

| Capability | Native Odoo | Built in this module |
|---|---|---|
| Signup, password reset | `auth_signup` | Password policy: more than 8 characters, upper, lower, special |
| Roles | Groups, record rules | Subscription **Staff** and **Admin** groups; customers are Portal users. Only admins can create users (native) |
| Products & variants | Attributes with `price_extra` (Brand: Odoo **+560**) | — (configuration) |
| Taxes | `account.tax` | Applied on subscription lines and every generated invoice |
| Plans | — | `subscription.plan` |
| Quotation templates | — | `subscription.template` |
| Subscriptions & lifecycle | — | `subscription.subscription`: Draft → Quotation → Confirmed → Active (⇄ Paused) → Closed |
| Recurring invoicing | `ir.cron`, `account.move` | Billing engine (below) |
| Invoice lifecycle | Draft → Posted → Paid; confirm, cancel, send, print | Invoice ↔ subscription link |
| Discounts | — | `subscription.discount`, applied automatically by the billing engine |
| Payments | Register Payment: method, amount, date, memo, partial payments, reconciliation | — |
| Customer portal | Portal framework, `/my/invoices` | My Subscriptions pages and permitted actions |
| Finance dashboard | — | `subscription.dashboard.get_dashboard_data()` + dashboard UI |

## Data model

```
subscription.plan ──< subscription.subscription >── res.partner (customer)
        │                    │  └──< subscription.line >── product.product (variant)
        │                    └──< account.move (invoice) ──< account.move.line
        │                                                       └── subscription.discount
        └──< subscription.template ──< subscription.template.line
```

- **subscription.line** carries quantity, unit price, taxes and amounts. The plan fee is its own line
  (quantity = seats) so it is taxed and discounted like any product.
- **account.move** gains `subscription_id` and `subscription_period_start` — the billing period an
  invoice covers.

## The billing engine (`models/subscription.py`)

A daily scheduled job bills every subscription whose `next_invoice_date` has arrived.

- **Never bills twice.** Each invoice records its period. The engine skips periods already billed,
  a row lock (`FOR UPDATE SKIP LOCKED`) stops two workers taking the same subscription, and a
  PostgreSQL `UNIQUE (subscription_id, subscription_period_start)` constraint is the final guard.
- **Never skips a cycle.** If runs were missed, the next run creates one invoice per missed period.
- **No date drift.** Periods are counted from the start date (start + k periods), so a subscription
  that starts on the 31st bills on the 31st, or the last day of shorter months.
- **Handles hundreds at once.** Batches of 100, each subscription in its own savepoint: one bad
  record is logged and skipped without rolling back the rest.
- **Lifecycle aware.** Paused subscriptions are not billed and resume without back-billing; expired
  ones on auto-close plans are closed.

## Discounts (`models/subscription_discount.py`)

Admin-only rules: fixed or percentage; whole subscription or specific products; minimum purchase,
minimum quantity, start/end dates, usage limit. The billing engine adds every eligible discount to
the invoice as its own line, split across tax groups so taxes are computed on the discounted
amount. A rule stops applying when it expires or its usage limit is reached; cancelling an invoice
returns the use.

## Security

- Customers (portal) can **read only their own** subscriptions and lines (record rules); Odoo already
  restricts invoices the same way.
- Customers never write directly. Portal buttons call `action_portal_request()`, which checks the
  customer can see the subscription, allows only pause / resume / close / renew, and still enforces
  the plan's rules.
- Every password change — signup, reset link, change-password, admin edit — passes one policy check.

## Performance

Dashboard figures are single SQL aggregates (`_read_group`), never Python loops over records.
Columns the engine and lists filter on (`state`, `next_invoice_date`, `partner_id`, `plan_id`,
`subscription_id`) are indexed. **Configuration → Performance Test** creates 2,000 subscriptions,
bills them, and reports the time for a list page, a filtered search and the dashboard.

## Tests

21 automated tests (`brightloop_subscription/tests/`): billing (current period, no duplicates,
catch-up, pause/resume, expiry and auto-close, 150 subscriptions in one run), security (isolation,
no direct writes, portal actions, whitelist, password policy), templates, discounts (percentage,
minimum quantity, product-specific, expiry, usage limit) and dashboard figures.

## Running it

```powershell
# 1. Odoo 19 + PostgreSQL in Docker (docker-compose.yml mounts this repo as /mnt/extra-addons)
docker compose up -d
# 2. Open http://localhost:8069, create database "brightloop" (country India, no demo data),
#    install Invoicing, then Brightloop Subscriptions from Apps.
# 3. Subscriptions → Configuration → Load Demo Data
```

Upgrade, run all tests, restart and push in one command:

```powershell
powershell -ExecutionPolicy Bypass -File tools\dev.ps1 all "commit message"
```

## Demo walkthrough (one billing month at Brightloop)

1. **New customer signs up** — `/web/signup`; weak passwords are refused.
2. **Launching a plan** — Brightloop CRM with Brand variant (Odoo +560); plans daily → yearly with
   per-plan pause/close/renew/auto-close rules.
3. **Quote to subscription** — pick *Enterprise Bundle* template → Send Quotation → Confirm → Activate.
4. **Billing day** — run the scheduled job: invoices with customer, lines, GST, totals and discounts;
   run again — no duplicates.
5. **A better price** — the 10%-for-10-seats rule appears on the invoice on its own.
6. **Money comes in** — Register Payment (bank/cash, partial); paid / outstanding / overdue filters.
7. **Customer portal** — a customer sees only their own subscriptions and invoices.
8. **Finance lead** — dashboard: active subscriptions, MRR, collected, outstanding, overdue, trend.

## Team

- **Backend & database** — models, billing engine, security, dashboard data, tests.
- **UI** — backend screens, customer portal, signup page, dashboard UI.

See `TEAM.md` for the file-ownership rules and the contract between the two layers.
