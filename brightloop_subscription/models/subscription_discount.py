from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero


class SubscriptionDiscount(models.Model):
    """Discount rule created by an admin and applied automatically by the
    billing engine to every eligible invoice, until it expires or its usage
    limit is reached."""

    _name = "subscription.discount"
    _description = "Subscription Discount Rule"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")

    discount_type = fields.Selection(
        [("percentage", "Percentage"), ("fixed", "Fixed Amount")],
        required=True, default="percentage",
    )
    value = fields.Float(required=True, help="Percentage (e.g. 10 for 10%) or fixed amount.")

    applies_to = fields.Selection(
        [("subscription", "Whole Subscription"), ("products", "Specific Products")],
        required=True, default="subscription",
    )
    product_ids = fields.Many2many("product.product", string="Products")

    min_amount = fields.Monetary(string="Minimum Purchase", currency_field="currency_id")
    min_quantity = fields.Float(string="Minimum Quantity")
    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(string="End Date")
    max_uses = fields.Integer(string="Usage Limit", help="Maximum number of invoices. 0 means unlimited.")
    used_count = fields.Integer(string="Times Used", compute="_compute_used_count")

    _check_value = models.Constraint("CHECK(value > 0)", "Discount value must be positive.")
    _check_max_uses = models.Constraint("CHECK(max_uses >= 0)", "Usage limit cannot be negative.")

    @api.constrains("discount_type", "value")
    def _check_percentage(self):
        for rule in self:
            if rule.discount_type == "percentage" and rule.value > 100:
                raise ValidationError(self.env._("A percentage discount cannot exceed 100%."))

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rule in self:
            if rule.date_start and rule.date_end and rule.date_end < rule.date_start:
                raise ValidationError(self.env._("End date must be on or after the start date."))

    @api.constrains("applies_to", "product_ids")
    def _check_products(self):
        for rule in self:
            if rule.applies_to == "products" and not rule.product_ids:
                raise ValidationError(self.env._("Select at least one product for a product discount."))

    def _compute_used_count(self):
        """A use = one invoice that carries this discount and is not cancelled.
        Cancelling an invoice gives the use back."""
        groups = self.env["account.move.line"]._read_group(
            [("subscription_discount_id", "in", self.ids), ("parent_state", "!=", "cancel")],
            ["subscription_discount_id", "move_id"],
        )
        counts = defaultdict(int)
        for discount, _move in groups:
            counts[discount.id] += 1
        for rule in self:
            rule.used_count = counts.get(rule.id, 0)

    # ------------------------------------------------------------------------
    # Applying discounts during billing
    # ------------------------------------------------------------------------
    def _is_valid_on(self, date):
        self.ensure_one()
        if self.date_start and date < self.date_start:
            return False
        if self.date_end and date > self.date_end:
            return False
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        return True

    def _affected_lines(self, subscription):
        self.ensure_one()
        if self.applies_to == "subscription":
            return subscription.line_ids
        return subscription.line_ids.filtered(lambda l: l.product_id in self.product_ids)

    def _amount_for(self, lines):
        self.ensure_one()
        base = sum(lines.mapped("price_subtotal"))
        if base <= 0:
            return 0.0
        if self.min_amount and base < self.min_amount:
            return 0.0
        if self.min_quantity and sum(lines.mapped("quantity")) < self.min_quantity:
            return 0.0
        if self.discount_type == "percentage":
            return base * self.value / 100.0
        return min(self.value, base)

    @api.model
    def _get_invoice_discount_line_vals(self, subscription, invoice_date):
        """Negative invoice lines for every discount the subscription qualifies
        for on `invoice_date`. The discount is split across the tax groups of the
        affected lines so taxes are computed on the discounted amount."""
        rules = self.search([("company_id", "=", subscription.company_id.id)])
        # Usage counts change as invoices are created in this same run.
        rules.invalidate_recordset(["used_count"])
        if rules:
            # Serialise usage-limited discounts across parallel billing runs.
            self.env.cr.execute(
                "SELECT id FROM subscription_discount WHERE id IN %s FOR UPDATE", [tuple(rules.ids)]
            )
        vals_list = []
        remaining = sum(subscription.line_ids.mapped("price_subtotal"))
        rounding = subscription.currency_id.rounding
        for rule in rules:
            if not rule._is_valid_on(invoice_date):
                continue
            lines = rule._affected_lines(subscription)
            amount = min(rule._amount_for(lines), remaining)
            if float_is_zero(amount, precision_rounding=rounding):
                continue
            remaining -= amount
            base = sum(lines.mapped("price_subtotal"))
            by_taxes = defaultdict(float)
            for line in lines:
                by_taxes[tuple(sorted(line.tax_ids.ids))] += line.price_subtotal
            label = rule.name if rule.discount_type == "fixed" else f"{rule.name} ({rule.value:g}%)"
            for tax_ids, group_base in by_taxes.items():
                share = subscription.currency_id.round(amount * group_base / base)
                if float_is_zero(share, precision_rounding=rounding):
                    continue
                vals_list.append({
                    "name": self.env._("Discount: %s", label),
                    "quantity": 1.0,
                    "price_unit": -share,
                    "tax_ids": [(6, 0, list(tax_ids))],
                    "subscription_discount_id": rule.id,
                })
        return vals_list
