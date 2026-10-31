# Team Workflow — Brightloop Subscriptions

Two people, one Odoo module (`brightloop_subscription`), deadline 17:00.
Split by layer: **Person A = backend and database**, **Person B = UI**.
The rule that keeps us out of merge conflicts: **every file has one owner.**

## Who owns what

### Person A — Backend & Database

Everything that decides *what the data is* and *what is allowed*.

| Area | Files |
|---|---|
| Models (plans, subscriptions, lines, templates, discounts, invoice link) | `models/*.py` |
| Password policy (9+ chars, upper, lower, special) | `models/res_users.py` |
| Billing engine (scheduled job) | `data/ir_cron.xml` + methods in `models/subscription.py` |
| Sequences | `data/ir_sequence.xml` |
| Roles & permissions | `security/security.xml`, `security/ir.model.access.csv` |
| Record rules (customers see only their own data) | `security/record_rules.xml` |
| Dashboard numbers (fast aggregate queries) | `models/subscription_dashboard.py` |
| Demo/seed data | `data/demo_data.xml` |
| Tests | `tests/` |

### Person B — UI

Everything the user *sees and clicks*.

| Area | Files |
|---|---|
| Backend screens (list, form, search, kanban) | `views/*_views.xml` |
| Menus | `views/menus.xml` |
| Customer portal pages | `views/portal_templates.xml` |
| Portal routes (render pages, call model methods) | `controllers/portal.py` |
| Signup page tweaks (password rules shown to the user) | `views/auth_templates.xml` |
| Financial dashboard UI | `static/src/` (OWL component, CSS) + `views/dashboard_views.xml` |
| Styling | `static/src/scss/` |

### Shared files — owner: Person A

`__manifest__.py`, `__init__.py`, `models/__init__.py`, `controllers/__init__.py`

Person B may add lines to these, but:
1. `git pull --rebase` first,
2. add **only your lines** (append; don't reorder or reformat),
3. commit that change **on its own** (e.g. `shared: register portal views`),
4. push immediately and tell Person A.

## The contract between layers

The UI never contains business rules. Buttons and portal routes **call model
methods**; the model decides whether the action is allowed.

| UI action | Calls (Person A provides) |
|---|---|
| Send quotation / Confirm / Activate | `action_send_quotation()`, `action_confirm()`, `action_activate()` |
| Pause / Resume / Close / Renew (backend or portal) | `action_pause()`, `action_resume()`, `action_close()`, `action_renew()` |
| Show/hide Pause, Close, Renew | fields `plan_allow_pause`, `plan_allow_close`, `plan_allow_renew` |
| Invoices smart button | `action_view_invoices()`, field `invoice_count` |
| Dashboard tiles | `subscription.dashboard.get_dashboard_data(filters)` *(coming)* |

When Person A adds or renames a field or method, post it in chat with the exact
name. Person B never adds fields to models; ask Person A.

## Git routine (no branches — no time for PRs)

```powershell
# Before starting any piece of work
git pull --rebase

# After each working, tested piece (aim for every 30–45 min)
git add .
git commit -m "area: what changed"
git pull --rebase
git push
```

- Commit only code that **installs and upgrades without errors**. A broken push breaks the other person's Odoo too.
- If `git pull --rebase` reports a conflict, stop and ask before resolving.

## Loading a teammate's changes into your Odoo

```powershell
git pull --rebase
docker compose restart odoo
```
Then in Odoo: **Apps → Brightloop Subscriptions → Upgrade**.
(Python changes need the restart; XML-only changes need just the Upgrade.)

## Checkpoints

| Time | Checkpoint |
|---|---|
| 12:30 | Both pull, upgrade, and click through each other's work |
| 14:45 | Billing + portal working end to end |
| 15:45 | **Feature freeze** — bug fixes only |
| 16:15 | Demo data loaded, demo rehearsal |
