from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError

STATES = [
    ("draft", "Draft"),
    ("quotation", "Quotation"),
    ("confirmed", "Confirmed"),
    ("active", "Active"),
    ("paused", "Paused"),
    ("closed", "Closed"),
]


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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("subscription.subscription") or "New"
        subs = super().create(vals_list)
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
        self._ensure_state(["paused"])
        self.write({"state": "active"})

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
