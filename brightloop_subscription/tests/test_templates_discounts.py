from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTemplatesDiscounts(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.partner = cls.env["res.partner"].create({"name": "Disc Customer"})
        cls.plan = cls.env["subscription.plan"].create({
            "name": "Seats", "price": 100.0, "billing_period": "monthly", "min_quantity": 1,
        })
        cls.addon = cls.env["product.product"].create({"name": "Add-on", "list_price": 50.0, "taxes_id": [(5, 0, 0)]})
        cls.Sub = cls.env["subscription.subscription"]
        cls.Discount = cls.env["subscription.discount"]

    def _billed_sub(self, seats=1, addon_qty=0):
        sub = self.Sub.create({"partner_id": self.partner.id, "plan_id": self.plan.id})
        sub.line_ids.filtered("is_plan_line").quantity = seats
        if addon_qty:
            self.env["subscription.line"].create({
                "subscription_id": sub.id, "product_id": self.addon.id,
                "name": "Add-on", "quantity": addon_qty, "price_unit": 50.0,
            })
        sub.action_confirm()
        sub.action_activate()
        self.Sub._run_billing(self.today)
        return sub.invoice_ids

    # --- templates -----------------------------------------------------------
    def test_template_fills_quotation(self):
        tmpl = self.env["subscription.template"].create({
            "name": "Bundle", "plan_id": self.plan.id, "validity_days": 15,
            "line_ids": [(0, 0, {"product_id": self.addon.id, "quantity": 3})],
        })
        sub = self.Sub.create({"partner_id": self.partner.id, "plan_id": self.plan.id, "template_id": tmpl.id})
        self.assertEqual(len(sub.line_ids), 2, "Plan line + template product line")
        self.assertEqual(sub.line_ids.filtered("product_id").quantity, 3)
        self.assertEqual(sub.validity_date, self.today + relativedelta(days=15))

    def test_expired_quotation_cannot_be_confirmed(self):
        sub = self.Sub.create({
            "partner_id": self.partner.id, "plan_id": self.plan.id,
            "validity_date": self.today - relativedelta(days=1),
        })
        with self.assertRaises(UserError):
            sub.action_confirm()

    # --- discounts -----------------------------------------------------------
    def test_percentage_discount_on_whole_subscription(self):
        self.Discount.create({"name": "Ten", "discount_type": "percentage", "value": 10})
        invoice = self._billed_sub(seats=2)          # 200
        self.assertAlmostEqual(invoice.amount_untaxed, 180.0)

    def test_min_quantity_not_met(self):
        self.Discount.create({"name": "Volume", "discount_type": "percentage", "value": 20, "min_quantity": 5})
        invoice = self._billed_sub(seats=2)
        self.assertAlmostEqual(invoice.amount_untaxed, 200.0)

    def test_fixed_discount_on_specific_product(self):
        self.Discount.create({
            "name": "Add-on promo", "discount_type": "fixed", "value": 30,
            "applies_to": "products", "product_ids": [(6, 0, self.addon.ids)],
        })
        invoice = self._billed_sub(seats=1, addon_qty=2)   # 100 + 100
        self.assertAlmostEqual(invoice.amount_untaxed, 170.0)

    def test_expired_discount_not_applied(self):
        self.Discount.create({
            "name": "Old", "discount_type": "percentage", "value": 50,
            "date_end": self.today - relativedelta(days=1),
        })
        invoice = self._billed_sub()
        self.assertAlmostEqual(invoice.amount_untaxed, 100.0)

    def test_usage_limit_stops_discount(self):
        rule = self.Discount.create({"name": "Once", "discount_type": "fixed", "value": 10, "max_uses": 1})
        first = self._billed_sub()
        second = self._billed_sub()
        self.assertAlmostEqual(first.amount_untaxed, 90.0)
        self.assertAlmostEqual(second.amount_untaxed, 100.0)
        rule.invalidate_recordset(["used_count"])
        self.assertEqual(rule.used_count, 1)
