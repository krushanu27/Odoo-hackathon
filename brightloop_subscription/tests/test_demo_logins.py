from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDemoLogins(TransactionCase):
    def test_logins_have_the_right_roles(self):
        self.env["subscription.discount"].search([]).active = False
        plan = self.env["subscription.plan"].create({"name": "Login Plan", "price": 10.0})
        partner = self.env["res.partner"].create({"name": "Login Co", "email": "login.co@example.com"})
        sub = self.env["subscription.subscription"].create({"partner_id": partner.id, "plan_id": plan.id})
        sub.action_confirm()
        sub.action_activate()
        Loader = self.env["subscription.demo.loader"]
        staff, customer = Loader._create_demo_logins()
        staff2, customer2 = Loader._create_demo_logins()  # idempotent
        self.assertEqual((staff, customer), (staff2, customer2))
        self.assertTrue(staff.has_group("brightloop_subscription.group_subscription_staff"))
        self.assertFalse(staff.has_group("brightloop_subscription.group_subscription_admin"))
        self.assertFalse(staff.has_group("base.group_erp_manager"), "Staff must not manage users")
        self.assertTrue(customer.has_group("base.group_portal"))
        self.assertFalse(customer.has_group("base.group_user"))
        visible = self.env["subscription.subscription"].with_user(customer).search([])
        self.assertTrue(visible, "The demo customer must see at least one subscription")
        self.assertTrue(all(s.partner_id.commercial_partner_id == customer.partner_id.commercial_partner_id
                            for s in visible))
