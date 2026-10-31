from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan = cls.env["subscription.plan"].create({
            "name": "Sec Plan", "price": 10.0, "billing_period": "monthly",
            "allow_pause": True,
        })
        cls.portal_user = new_test_user(cls.env, login="cust_a", password="Cust#Pass123", groups="base.group_portal")
        cls.other_partner = cls.env["res.partner"].create({"name": "Other Customer"})
        Sub = cls.env["subscription.subscription"]
        cls.own_sub = Sub.create({"partner_id": cls.portal_user.partner_id.id, "plan_id": cls.plan.id})
        cls.other_sub = Sub.create({"partner_id": cls.other_partner.id, "plan_id": cls.plan.id})
        (cls.own_sub | cls.other_sub).action_confirm()
        (cls.own_sub | cls.other_sub).action_activate()

    def test_customer_sees_only_own_subscriptions(self):
        visible = self.env["subscription.subscription"].with_user(self.portal_user).search([])
        self.assertEqual(visible, self.own_sub)

    def test_customer_cannot_write_directly(self):
        with self.assertRaises(AccessError):
            self.own_sub.with_user(self.portal_user).write({"state": "closed"})

    def test_customer_portal_action_on_own(self):
        self.own_sub.with_user(self.portal_user).action_portal_request("pause")
        self.assertEqual(self.own_sub.state, "paused")

    def test_customer_portal_action_on_other_is_refused(self):
        with self.assertRaises(AccessError):
            self.other_sub.with_user(self.portal_user).action_portal_request("pause")
        self.assertEqual(self.other_sub.state, "active")

    def test_portal_action_whitelist(self):
        with self.assertRaises(AccessError):
            self.own_sub.with_user(self.portal_user).action_portal_request("confirm")

    def test_password_policy(self):
        for weak in ["Short#1", "alllowercase#1", "ALLUPPERCASE#1", "NoSpecial123"]:
            with self.assertRaises(UserError, msg=weak):
                self.portal_user.write({"password": weak})
        self.portal_user.write({"password": "Strong#Pass1"})  # accepted
