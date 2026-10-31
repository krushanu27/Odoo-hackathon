# Team Workflow — Brightloop Subscriptions

Two people, one Odoo module (`brightloop_subscription`), deadline 17:00.
The rule that keeps us out of merge conflicts: **every file has one owner.**

## Who owns what

### Person A — Subscription & Billing core

| Area | Files |
|---|---|
| Plans | `models/subscription_plan.py`, `views/subscription_plan_views.xml` |
| Subscriptions + lines | `models/subscription.py`, `models/subscription_line.py`, `views/subscription_views.xml` |
| Quotation templates | `models/subscription_template.py`, `views/subscription_template_views.xml` |
| Invoice link + billing engine | `models/account_move.py`, `data/ir_cron.xml` |
| Discounts | `models/subscription_discount.py`, `views/subscription_discount_views.xml` |
| Sequences | `data/ir_sequence.xml` |
| Tests | `tests/` |

### Person B — Access, Customer side & Reporting

| Area | Files |
|---|---|
| Record rules (customers see only their own data) | `security/record_rules.xml` |
| Password policy (9+ chars, upper, lower, special) | `models/res_users.py`, `controllers/signup.py` |
| Customer portal | `controllers/portal.py`, `views/portal_templates.xml` |
| Financial dashboard | `models/subscription_dashboard.py`, `views/dashboard_views.xml`, `static/src/` |
| Demo data (products, variants, taxes, customers) | `data/demo_data.xml` |

### Shared files — owner: Person A

`__manifest__.py`, `models/__init__.py`, `controllers/__init__.py`,
`security/ir.model.access.csv`, `views/menus.xml`, `__init__.py`

Person B may add lines to these, but:
1. `git pull --rebase` first,
2. add **only your lines** (append; don't reorder or reformat),
3. commit that change **on its own** with a message like `shared: register portal controller`,
4. push immediately and tell Person A.

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

- Commit only code that **installs and upgrades without errors**. Never push a broken module; the other person's Odoo will break too.
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
