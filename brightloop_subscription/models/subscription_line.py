from odoo import api, fields, models


class SubscriptionLine(models.Model):
    _name = "subscription.line"
    _description = "Subscription Line"
    _order = "subscription_id, sequence, id"

    subscription_id = fields.Many2one(
        "subscription.subscription", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(default=10)
    is_plan_line = fields.Boolean()

    # Variant (product.product), so a "Brand: Odoo" choice and its +560 extra
    # flow through natively via lst_price.
    product_id = fields.Many2one("product.product", string="Product")
    name = fields.Char(string="Description", required=True)
    quantity = fields.Float(default=1.0, required=True, digits="Product Unit")
    price_unit = fields.Float(string="Unit Price", required=True, default=0.0, digits="Product Price")
    tax_ids = fields.Many2many(
        "account.tax", string="Taxes", domain=[("type_tax_use", "=", "sale")]
    )

    currency_id = fields.Many2one(related="subscription_id.currency_id", store=True)
    price_subtotal = fields.Monetary(string="Amount", compute="_compute_amounts", store=True)
    price_tax = fields.Monetary(compute="_compute_amounts", store=True)
    price_total = fields.Monetary(compute="_compute_amounts", store=True)

    _check_quantity = models.Constraint("CHECK(quantity > 0)", "Quantity must be positive.")

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if not self.product_id:
            return
        self.name = self.product_id.display_name
        self.price_unit = self.product_id.lst_price  # includes variant extra
        company = self.subscription_id.company_id or self.env.company
        self.tax_ids = self.product_id.taxes_id.filtered(lambda t: t.company_id == company)

    @api.depends("quantity", "price_unit", "tax_ids")
    def _compute_amounts(self):
        for line in self:
            if line.tax_ids:
                res = line.tax_ids.compute_all(
                    line.price_unit,
                    currency=line.currency_id,
                    quantity=line.quantity,
                    product=line.product_id,
                    partner=line.subscription_id.partner_id,
                )
                line.price_subtotal = res["total_excluded"]
                line.price_total = res["total_included"]
            else:
                line.price_subtotal = line.price_total = line.quantity * line.price_unit
            line.price_tax = line.price_total - line.price_subtotal
