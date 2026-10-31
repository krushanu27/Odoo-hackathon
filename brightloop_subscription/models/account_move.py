from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    subscription_id = fields.Many2one(
        "subscription.subscription", index=True, readonly=True, copy=False
    )
    # Start of the billing period this invoice covers.
    subscription_period_start = fields.Date(readonly=True, copy=False)

    # Duplicate-invoice guard enforced by PostgreSQL: one invoice per
    # subscription per period. Ordinary invoices have NULLs here, and
    # PostgreSQL treats NULLs as distinct, so they are unaffected.
    _unique_subscription_period = models.Constraint(
        "UNIQUE(subscription_id, subscription_period_start)",
        "An invoice already exists for this subscription and billing period.",
    )
