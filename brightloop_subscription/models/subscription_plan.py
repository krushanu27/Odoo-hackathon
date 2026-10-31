from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

# One place that defines how long a billing period is.
# The billing engine and expiry calculations both read from here,
# so the rule is never duplicated.
PERIOD_DELTAS = {
    "daily": relativedelta(days=1),
    "weekly": relativedelta(weeks=1),
    "monthly": relativedelta(months=1),
    "yearly": relativedelta(years=1),
}


class SubscriptionPlan(models.Model):
    _name = "subscription.plan"
    _description = "Subscription Plan"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text()

    # --- Pricing -----------------------------------------------------------
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    price = fields.Monetary(
        currency_field="currency_id",
        required=True,
        help="Recurring fee per unit (e.g. per seat) for each billing period.",
    )
    tax_ids = fields.Many2many(
        "account.tax",
        string="Taxes",
        domain=[("type_tax_use", "=", "sale")],
        help="Taxes applied to the plan fee on every invoice.",
    )
    billing_period = fields.Selection(
        [
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
            ("yearly", "Yearly"),
        ],
        required=True,
        default="monthly",
    )
    min_quantity = fields.Integer(string="Minimum Quantity", default=1, required=True)

    # --- Availability window ----------------------------------------------
    date_start = fields.Date(string="Available From")
    date_end = fields.Date(string="Available Until")

    # --- Lifecycle rules (decided plan by plan, per the problem statement) --
    auto_close = fields.Boolean(
        string="Close Automatically",
        help="Subscriptions on this plan close on their own when they reach their expiry date.",
    )
    allow_close = fields.Boolean(
        string="Allow Early Closure",
        help="The subscription can be closed before its expiry date.",
    )
    allow_pause = fields.Boolean(string="Allow Pause")
    allow_renew = fields.Boolean(string="Allow Renewal", default=True)

    _check_price = models.Constraint(
        "CHECK(price >= 0)",
        "A plan's price cannot be negative.",
    )
    _check_min_quantity = models.Constraint(
        "CHECK(min_quantity >= 1)",
        "Minimum quantity must be at least 1.",
    )

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for plan in self:
            if plan.date_start and plan.date_end and plan.date_end < plan.date_start:
                raise ValidationError(
                    self.env._("'Available Until' must be on or after 'Available From'.")
                )

    def _get_period_delta(self):
        """Length of one billing period for this plan."""
        self.ensure_one()
        return PERIOD_DELTAS[self.billing_period]

    def _is_available_on(self, date):
        """True if a new subscription may start on this plan at `date`."""
        self.ensure_one()
        if self.date_start and date < self.date_start:
            return False
        if self.date_end and date > self.date_end:
            return False
        return True
