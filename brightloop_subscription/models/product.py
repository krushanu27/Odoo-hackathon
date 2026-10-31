from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    subscription_addon = fields.Boolean(
        string="Subscription Add-on",
        help="Customers can switch this product on or off on their own subscriptions from the portal.",
    )
