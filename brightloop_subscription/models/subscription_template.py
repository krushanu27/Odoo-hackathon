from odoo import api, fields, models


class SubscriptionTemplate(models.Model):
    """Reusable starting point for a quotation: plan, product lines and how
    long the resulting quotation stays valid."""

    _name = "subscription.template"
    _description = "Subscription Quotation Template"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    plan_id = fields.Many2one("subscription.plan", required=True)
    validity_days = fields.Integer(
        string="Valid For (days)", default=30, required=True,
        help="Quotations created from this template expire after this many days.",
    )
    line_ids = fields.One2many("subscription.template.line", "template_id", string="Product Lines", copy=True)
    note = fields.Html(string="Terms and Conditions")

    _check_validity = models.Constraint(
        "CHECK(validity_days > 0)", "Validity must be at least one day."
    )


class SubscriptionTemplateLine(models.Model):
    _name = "subscription.template.line"
    _description = "Subscription Template Line"
    _order = "template_id, sequence, id"

    template_id = fields.Many2one("subscription.template", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one("product.product", string="Product", required=True)
    name = fields.Char(string="Description")
    quantity = fields.Float(default=1.0, required=True, digits="Product Unit")

    _check_quantity = models.Constraint("CHECK(quantity > 0)", "Quantity must be positive.")

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id and not self.name:
            self.name = self.product_id.display_name
