from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestAddons(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["subscription.discount"].search([]).active = False
        cls.plan = cls.env["subscription.plan"].create({"name": "Addon Plan", "price": 100.0})
        cls.addon = cls.env["product.product"].create({
            "name": "Test Add-on", "list_price": 40.0, "subscription_addon": True, "taxes_id": [(5, 0, 0)],
        })
        cls.not_addon = cls.env["product.product"].create({"name": "Not An Add-on", "list_price": 10.0})
        cls.customer = new_test_user(cls.env, login="addon_cust", password="Addon#Pass1", groups="base.group_portal")
        other = cls.env["res.partner"].create({"name": "Someone Else"})
        Sub = cls.env["subscription.subscription"]
        cls.own = Sub.create({"partner_id": cls.customer.partner_id.id, "plan_id": cls.plan.id})
        cls.other = Sub.create({"partner_id": other.id, "plan_id": cls.plan.id})
        (cls.own | cls.other).action_confirm()
        (cls.own | cls.other).action_activate()

    def test_switch_on_and_off(self):
        as_customer = self.own.with_user(self.customer)
        as_customer.action_portal_set_addon(self.addon.id, True)
        self.assertIn(self.addon, self.own.line_ids.product_id)
        self.assertAlmostEqual(self.own.amount_untaxed, 140.0)
        offered = {a["id"]: a["enabled"] for a in as_customer._portal_available_addons()}
        self.assertTrue(offered[self.addon.id])
        as_customer.action_portal_set_addon(self.addon.id, False)
        self.assertNotIn(self.addon, self.own.line_ids.product_id)
        self.assertAlmostEqual(self.own.amount_untaxed, 100.0)

    def test_switching_on_twice_adds_one_line(self):
        as_customer = self.own.with_user(self.customer)
        as_customer.action_portal_set_addon(self.addon.id, True)
        as_customer.action_portal_set_addon(self.addon.id, True)
        self.assertEqual(len(self.own.line_ids.filtered(lambda l: l.product_id == self.addon)), 1)

    def test_non_addon_product_refused(self):
        with self.assertRaises(AccessError):
            self.own.with_user(self.customer).action_portal_set_addon(self.not_addon.id, True)

    def test_other_customers_subscription_refused(self):
        with self.assertRaises(AccessError):
            self.other.with_user(self.customer).action_portal_set_addon(self.addon.id, True)

    def test_closed_subscription_refused(self):
        self.own.plan_id.allow_close = True
        self.own.action_close()
        with self.assertRaises(UserError):
            self.own.with_user(self.customer).action_portal_set_addon(self.addon.id, True)
