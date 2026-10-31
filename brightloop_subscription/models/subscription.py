import logging
import time
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)

STATES = [
    ("draft", "Draft"),
    ("quotation", "Quotation"),
    ("confirmed", "Confirmed"),
    ("active", "Active"),
    ("paused", "Paused"),
    ("closed", "Closed"),
]

# How many subscriptions the billing run processes per database transaction.
BILLING_BATCH_SIZE = 100


class Subscription(models.Model):
    _name = "subscription.subscription"
    _description = "Subscription"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Number", required=True, readonly=True, copy=False, default="New", index=True
    )
    partner_id = fields.Many2one(
        "res.partner", string="Customer", required=True, index=True, tracking=True
    )
    plan_id = fields.Many2one(
        "subscription.plan", required=True, index=True, tracking=True
    )
    user_id = fields.Many2one(
        "res.users", string="Salesperson", default=lambda self: self.env.user, tracking=True
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id", store=True)

    state = fields.Selection(
        STATES, default="draft", required=True, index=True, tracking=True, copy=False
    )

    # --- Dates ---------------------------------------------------------------
    date_start = fields.Date(
        string="Start Date", required=True, default=fields.Date.context_today, tracking=True
    )
    date_end = fields.Date(string="Expiry Date", tracking=True)
    # The billing engine selects on this column every run, so it is indexed.
    next_invoice_date = fields.Date(index=True, copy=False, tracking=True)

    payment_term_id = fields.Many2one("account.payment.term", string="Payment Terms")
    template_id = fields.Many2one("subscription.template", string="Quotation Template")
    validity_date = fields.Date(
        string="Quotation Valid Until", copy=False,
        help="After this date the quotation can no longer be confirmed.",
    )
    note = fields.Html(string="Terms and Conditions")

    # --- Lines and totals ---------------------------------------------------
    line_ids = fields.One2many("subscription.line", "subscription_id", string="Lines", copy=True)
    amount_untaxed = fields.Monetary(compute="_compute_amounts", store=True)
    amount_tax = fields.Monetary(string="Taxes", compute="_compute_amounts", store=True)
    amount_total = fields.Monetary(string="Total", compute="_compute_amounts", store=True)

    # --- Invoices -----------------------------------------------------------
    invoice_ids = fields.One2many("account.move", "subscription_id", string="Invoices")
    invoice_count = fields.Integer(compute="_compute_invoice_count")

    # --- Plan rules exposed to the view for button visibility ---------------
    plan_allow_pause = fields.Boolean(related="plan_id.allow_pause")
    plan_allow_close = fields.Boolean(related="plan_id.allow_close")
    plan_allow_renew = fields.Boolean(related="plan_id.allow_renew")

    # ------------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------------
    @api.depends("line_ids.price_subtotal", "line_ids.price_tax", "line_ids.price_total")
    def _compute_amounts(self):
        for sub in self:
            sub.amount_untaxed = sum(sub.line_ids.mapped("price_subtotal"))
            sub.amount_tax = sum(sub.line_ids.mapped("price_tax"))
            sub.amount_total = sum(sub.line_ids.mapped("price_total"))

    @api.depends("invoice_ids")
    def _compute_invoice_count(self):
        counts = {
            sub.id: count
            for sub, count in self.env["account.move"]._read_group(
                [("subscription_id", "in", self.ids)], ["subscription_id"], ["__count"]
            )
        }
        for sub in self:
            sub.invoice_count = counts.get(sub.id, 0)

    # ------------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------------
    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for sub in self:
            if sub.date_end and sub.date_end < sub.date_start:
                raise ValidationError(self.env._("Expiry date must be on or after the start date."))

    # ------------------------------------------------------------------------
    # Plan line: the plan fee is billed as its own line so it carries
    # quantity (seats) and taxes like any other line.
    # ------------------------------------------------------------------------
    def _plan_line_values(self):
        self.ensure_one()
        return {
            "name": self.plan_id.name,
            "price_unit": self.plan_id.price,
            "tax_ids": [Command.set(self.plan_id.tax_ids.ids)],
            "is_plan_line": True,
            "sequence": 0,
        }

    @api.onchange("plan_id")
    def _onchange_plan_id(self):
        if not self.plan_id:
            return
        plan_line = self.line_ids.filtered("is_plan_line")[:1]
        vals = self._plan_line_values()
        if plan_line:
            plan_line.update(vals)
        else:
            vals["quantity"] = self.plan_id.min_quantity
            self.line_ids = [Command.create(vals)]

    def _sync_plan_line(self):
        """Server-side guarantee that the plan line exists and matches the plan,
        for records created without the form (templates, imports, scripts)."""
        for sub in self:
            plan_line = sub.line_ids.filtered("is_plan_line")[:1]
            vals = sub._plan_line_values()
            if plan_line:
                plan_line.write(vals)
            else:
                vals.update(subscription_id=sub.id, quantity=sub.plan_id.min_quantity)
                self.env["subscription.line"].create(vals)

    def _template_values(self):
        """Plan, product lines, terms and validity taken from the template."""
        self.ensure_one()
        tmpl = self.template_id
        today = fields.Date.context_today(self)
        lines = []
        for tl in tmpl.line_ids:
            company = self.company_id or self.env.company
            lines.append(Command.create({
                "sequence": tl.sequence,
                "product_id": tl.product_id.id,
                "name": tl.name or tl.product_id.display_name,
                "quantity": tl.quantity,
                "price_unit": tl.product_id.lst_price,
                "tax_ids": [Command.set(tl.product_id.taxes_id.filtered(lambda t: t.company_id == company).ids)],
            }))
        vals = {
            "plan_id": tmpl.plan_id.id,
            "validity_date": today + relativedelta(days=tmpl.validity_days),
            "line_ids": [Command.clear()] + lines,
        }
        if tmpl.note:
            vals["note"] = tmpl.note
        return vals

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if not self.template_id:
            return
        self.update(self._template_values())
        self._onchange_plan_id()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("subscription.subscription") or "New"
        subs = super().create(vals_list)
        if self.env.context.get("bl_bulk_create"):
            return subs  # caller supplies complete lines (load test)
        for sub in subs.filtered(lambda s: s.template_id and not s.line_ids):
            sub.write(sub._template_values())
        subs._sync_plan_line()
        return subs

    def write(self, vals):
        res = super().write(vals)
        if "plan_id" in vals:
            self._sync_plan_line()
        return res

    # ------------------------------------------------------------------------
    # Lifecycle: Draft -> Quotation -> Confirmed -> Active -> (Paused) -> Closed
    # ------------------------------------------------------------------------
    def _ensure_state(self, allowed):
        for sub in self:
            if sub.state not in allowed:
                raise UserError(
                    self.env._("%(number)s is %(state)s; this action is not allowed in that state.",
                               number=sub.name,
                               state=dict(STATES)[sub.state])
                )

    def _validate_for_confirmation(self):
        for sub in self:
            if not sub.line_ids:
                raise UserError(self.env._("%s has no lines.", sub.name))
            if not sub.plan_id._is_available_on(sub.date_start):
                raise UserError(
                    self.env._("Plan %(plan)s is not available on %(date)s.",
                               plan=sub.plan_id.name, date=sub.date_start)
                )
            plan_line = sub.line_ids.filtered("is_plan_line")[:1]
            if plan_line and plan_line.quantity < sub.plan_id.min_quantity:
                raise UserError(
                    self.env._("Plan %(plan)s requires a minimum quantity of %(qty)s.",
                               plan=sub.plan_id.name, qty=sub.plan_id.min_quantity)
                )

    def action_send_quotation(self):
        self._ensure_state(["draft"])
        self._validate_for_confirmation()
        self.write({"state": "quotation"})

    def action_confirm(self):
        self._ensure_state(["draft", "quotation"])
        today = fields.Date.context_today(self)
        for sub in self:
            if sub.validity_date and sub.validity_date < today:
                raise UserError(
                    self.env._("Quotation %(number)s expired on %(date)s.",
                               number=sub.name, date=sub.validity_date)
                )
        self._validate_for_confirmation()
        self.write({"state": "confirmed"})

    def action_activate(self):
        self._ensure_state(["confirmed"])
        for sub in self:
            sub.write({
                "state": "active",
                # First invoice is due on the start date; the billing engine
                # advances this one period at a time.
                "next_invoice_date": sub.next_invoice_date or sub.date_start,
            })

    def action_pause(self):
        self._ensure_state(["active"])
        for sub in self:
            if not sub.plan_id.allow_pause:
                raise UserError(self.env._("Plan %s does not allow pausing.", sub.plan_id.name))
        self.write({"state": "paused"})

    def action_resume(self):
        """Resume billing from today: periods that fell inside the pause are
        not billed retroactively."""
        self._ensure_state(["paused"])
        today = fields.Date.context_today(self)
        for sub in self:
            vals = {"state": "active"}
            if sub.next_invoice_date and sub.next_invoice_date < today:
                vals["next_invoice_date"] = today
            sub.write(vals)

    def action_close(self):
        self._ensure_state(["active", "paused", "confirmed"])
        today = fields.Date.context_today(self)
        for sub in self:
            expired = sub.date_end and sub.date_end <= today
            if not expired and not sub.plan_id.allow_close:
                raise UserError(
                    self.env._("Plan %s does not allow closing before the expiry date.",
                               sub.plan_id.name)
                )
        self.write({"state": "closed"})

    def action_renew(self):
        """Extend the expiry date by one billing period and keep billing."""
        self._ensure_state(["active", "closed"])
        for sub in self:
            if not sub.plan_id.allow_renew:
                raise UserError(self.env._("Plan %s does not allow renewal.", sub.plan_id.name))
            if not sub.date_end:
                raise UserError(self.env._("%s has no expiry date to renew.", sub.name))
            vals = {"date_end": sub.date_end + sub.plan_id._get_period_delta(), "state": "active"}
            if not sub.next_invoice_date:
                vals["next_invoice_date"] = sub.date_end
            sub.write(vals)
            sub.message_post(body=self.env._("Renewed until %s.", vals["date_end"]))

    def action_reset_to_draft(self):
        self._ensure_state(["quotation"])
        self.write({"state": "draft"})

    # Actions a customer may trigger from the portal.
    PORTAL_ACTIONS = {"pause", "resume", "close", "renew"}

    def action_portal_request(self, action):
        """Entry point for portal buttons.

        Customers have read-only access. This method first proves the current
        user can see this subscription (record rules), then performs the action
        with elevated rights. The action method itself still enforces the plan's
        rules (pause allowed? early close allowed?), so the portal cannot do
        anything the backend would refuse."""
        self.ensure_one()
        if action not in self.PORTAL_ACTIONS:
            raise AccessError(self.env._("Action not allowed from the portal."))
        self.check_access("read")
        getattr(self.sudo(), f"action_{action}")()
        return True

    # ------------------------------------------------------------------------
    # Add-ons customers switch on and off (portal)
    # ------------------------------------------------------------------------
    ADDON_STATES = ("confirmed", "active", "paused")

    def _addon_products(self):
        return self.env["product.product"].sudo().search([
            ("product_tmpl_id.subscription_addon", "=", True),
            ("company_id", "in", (False, self.company_id.id)),
        ])

    def _portal_available_addons(self):
        """Add-ons the customer can switch on or off for this subscription, as
        plain values the portal can render (customers cannot read products)."""
        self.ensure_one()
        self.check_access("read")
        enabled = self.sudo().line_ids.filtered(lambda l: not l.is_plan_line).product_id
        return [
            {
                "id": product.id,
                "name": product.display_name,
                "description": product.description_sale or product.description or "",
                "price": product.lst_price,
                "enabled": product in enabled,
            }
            for product in self._addon_products()
        ]

    def action_portal_set_addon(self, product_id, enabled):
        """Switch an add-on on (one unit at list price) or off. The change is
        billed from the next invoice. Same pattern as action_portal_request:
        prove read access, validate, then act with elevated rights."""
        self.ensure_one()
        self.check_access("read")
        if self.state not in self.ADDON_STATES:
            raise UserError(self.env._("Add-ons can only be changed on a running subscription."))
        product = self.env["product.product"].sudo().browse(int(product_id)).exists()
        if not product or product not in self._addon_products():
            raise AccessError(self.env._("That product is not an available add-on."))
        sub = self.sudo()
        lines = sub.line_ids.filtered(lambda l: l.product_id == product and not l.is_plan_line)
        if enabled and not lines:
            self.env["subscription.line"].sudo().create({
                "subscription_id": sub.id,
                "product_id": product.id,
                "name": product.display_name,
                "quantity": 1.0,
                "price_unit": product.lst_price,
                "tax_ids": [Command.set(product.taxes_id.filtered(
                    lambda t: t.company_id == sub.company_id).ids)],
            })
            sub.message_post(body=self.env._("Add-on switched on: %s", product.display_name))
        elif not enabled and lines:
            lines.unlink()
            sub.message_post(body=self.env._("Add-on switched off: %s", product.display_name))
        return True

    def action_view_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Invoices"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("subscription_id", "=", self.id)],
            "context": {"default_move_type": "out_invoice", "create": False},
        }

    # ------------------------------------------------------------------------
    # Billing engine
    #
    # Guarantees:
    #  1. Never bills twice: each invoice records the period it covers, an
    #     existing invoice for a period is skipped, and a PostgreSQL UNIQUE
    #     constraint on (subscription, period start) is the final guard.
    #  2. Never skips a cycle: if a run is missed, the next run loops and
    #     bills every overdue period, one invoice per period.
    #  3. Scales and survives failures: subscriptions are processed in
    #     batches, each in its own savepoint; one bad subscription is logged
    #     and skipped without rolling back the others.
    # ------------------------------------------------------------------------
    def _billing_period_end(self, period_start):
        """Start of the next billing period after `period_start`.

        Periods are always counted from the subscription's start date
        (start + k periods), never chained from the previous period, so a
        subscription starting on the 31st bills on the 31st, or the last day
        of shorter months, instead of drifting to the 30th, then the 28th.
        """
        self.ensure_one()
        anchor = self.date_start
        if period_start < anchor:
            return anchor
        period = self.plan_id.billing_period
        if period in ("daily", "weekly"):
            step = 1 if period == "daily" else 7
            k = (period_start - anchor).days // step + 1
            return anchor + timedelta(days=step * k)
        months = 1 if period == "monthly" else 12
        k = ((period_start.year - anchor.year) * 12 + period_start.month - anchor.month) // months
        candidate = anchor + relativedelta(months=months * k)
        while candidate <= period_start:
            k += 1
            candidate = anchor + relativedelta(months=months * k)
        return candidate

    def _prepare_invoice_line_vals(self, period_start, period_end):
        """One invoice line per subscription line.
        Extension point: discounts add their lines here."""
        self.ensure_one()
        period_label = f"{fields.Date.to_string(period_start)} to {fields.Date.to_string(period_end)}"
        vals_list = [
            {
                "product_id": line.product_id.id or False,
                "name": f"{line.name} ({period_label})",
                "quantity": line.quantity,
                "price_unit": line.price_unit,
                "tax_ids": [Command.set(line.tax_ids.ids)],
            }
            for line in self.line_ids.sorted("sequence")
        ]
        vals_list += self.env["subscription.discount"]._get_invoice_discount_line_vals(self, period_start)
        return vals_list

    def _prepare_invoice_vals(self, period_start):
        self.ensure_one()
        period_end = self._billing_period_end(period_start)
        return {
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "invoice_date": period_start,
            "invoice_origin": self.name,
            "invoice_payment_term_id": self.payment_term_id.id or False,
            "invoice_user_id": self.user_id.id or False,
            "subscription_id": self.id,
            "subscription_period_start": period_start,
            "invoice_line_ids": [
                Command.create(vals)
                for vals in self._prepare_invoice_line_vals(period_start, period_end)
            ],
        }

    def _is_billable_period(self, period_start):
        self.ensure_one()
        return not self.date_end or period_start < self.date_end

    def _generate_due_invoices(self, today=None):
        """Create one draft invoice for every unbilled period of this
        subscription whose start is on or before `today`. Returns the invoices."""
        self.ensure_one()
        today = today or fields.Date.context_today(self)
        Move = self.env["account.move"]
        invoices = Move

        # Row lock: if another billing worker is already on this subscription,
        # skip it rather than racing it.
        self.env.cr.execute(
            "SELECT id FROM subscription_subscription WHERE id = %s FOR UPDATE SKIP LOCKED",
            [self.id],
        )
        if not self.env.cr.fetchone():
            return invoices
        self.invalidate_recordset(["next_invoice_date", "state"])

        while (
            self.state == "active"
            and self.next_invoice_date
            and self.next_invoice_date <= today
            and self._is_billable_period(self.next_invoice_date)
        ):
            period_start = self.next_invoice_date
            already_billed = Move.search_count([
                ("subscription_id", "=", self.id),
                ("subscription_period_start", "=", period_start),
            ], limit=1)
            if not already_billed:
                invoices |= Move.create(self._prepare_invoice_vals(period_start))
            self.next_invoice_date = self._billing_period_end(period_start)

        # Past expiry with nothing left to bill: stop scheduling.
        if self.next_invoice_date and not self._is_billable_period(self.next_invoice_date):
            self.next_invoice_date = False
        return invoices

    @api.model
    def _close_expired_subscriptions(self, today):
        expired = self.search([
            ("state", "in", ("active", "paused")),
            ("plan_id.auto_close", "=", True),
            ("date_end", "!=", False),
            ("date_end", "<=", today),
        ])
        if expired:
            expired.write({"state": "closed", "next_invoice_date": False})
            for sub in expired:
                sub.message_post(body=self.env._("Closed automatically on expiry."))
        return expired

    @api.model
    def _run_billing(self, today=None, commit=False, time_budget=None):
        """Bill every subscription that is due; returns the created invoices."""
        return self._run_billing_with_stats(today, commit, time_budget)[0]

    @api.model
    def _run_billing_with_stats(self, today=None, commit=False, time_budget=None):
        """Bill every subscription that is due. Called by the scheduled action
        (commit=True, time-boxed) and by tests (commit=False).

        With a time budget the run stops after the current batch once the budget
        is spent and queues the scheduled action to continue; because every batch
        is committed, no work is lost or repeated."""
        today = today or fields.Date.context_today(self)
        failed_ids = []
        created = self.env["account.move"]
        started = time.perf_counter()
        finished = True

        while True:
            if time_budget and time.perf_counter() - started > time_budget:
                finished = False
                break
            domain = [
                ("state", "=", "active"),
                ("next_invoice_date", "!=", False),
                ("next_invoice_date", "<=", today),
            ]
            if failed_ids:
                domain.append(("id", "not in", failed_ids))
            batch = self.search(domain, order="next_invoice_date, id", limit=BILLING_BATCH_SIZE)
            if not batch:
                break
            for sub in batch:
                try:
                    with self.env.cr.savepoint():
                        created |= sub._generate_due_invoices(today)
                        # Locked by another worker or nothing billable: don't
                        # pick it up again in this run.
                        if sub.next_invoice_date and sub.next_invoice_date <= today:
                            failed_ids.append(sub.id)
                except Exception:
                    _logger.exception("Billing failed for subscription %s", sub.name)
                    failed_ids.append(sub.id)
            if commit:
                self.env.cr.commit()

        closed = self._close_expired_subscriptions(today) if finished else self.browse()
        if commit:
            self.env.cr.commit()
        elapsed = time.perf_counter() - started
        _logger.info(
            "Subscription billing: %d invoices created, %d skipped/failed, %d closed in %.1fs%s",
            len(created), len(failed_ids), len(closed), elapsed, "" if finished else " (continuing)",
        )
        if not finished and commit:
            cron = self.env.ref("brightloop_subscription.cron_subscription_billing", raise_if_not_found=False)
            if cron:
                cron._trigger()
        return created, {"failed": len(failed_ids), "closed": len(closed),
                         "seconds": elapsed, "finished": finished}

    @api.model
    def _cron_run_billing(self):
        created, stats = self._run_billing_with_stats(commit=True, time_budget=60)
        if created:
            channel = self.env.ref("mail.channel_all_employees", raise_if_not_found=False)
            if channel:
                channel.sudo().message_post(
                    body=self.env._(
                        "Billing run: %(n)s invoices created in %(s).1f seconds%(more)s.",
                        n=len(created), s=stats.get("seconds", 0.0),
                        more="" if stats.get("finished", True) else self.env._(", continuing in the background"),
                    ),
                    message_type="comment", subtype_xmlid="mail.mt_comment",
                )
                self.env.cr.commit()
        return created

    def action_generate_invoices_now(self):
        """Manual trigger for one subscription (button for staff)."""
        invoices = self.env["account.move"]
        today = fields.Date.context_today(self)
        for sub in self:
            sub._ensure_state(["active"])
            invoices |= sub._generate_due_invoices(today)
        if not invoices:
            raise UserError(self.env._("Nothing is due for billing yet."))
        return self.action_view_invoices() if len(self) == 1 else True
