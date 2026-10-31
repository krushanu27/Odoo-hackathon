from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.partner = cls.env["res.partner"].create({"name": "Dash Customer"})
        cls.plan = cls.env["subscription.plan"].create({
            "name": "Dash Plan", "price": 1000.0, "billing_period": "monthly",
        })
        # Isolate from discount rules that exist in the database being tested.
        cls.env["subscription.discount"].search([]).active = False
        Sub = cls.env["subscription.subscription"]
        cls.sub = Sub.create({
            "partner_id": cls.partner.id, "plan_id": cls.plan.id,
            "date_start": cls.today - relativedelta(months=2),
        })
        cls.sub.action_confirm()
        cls.sub.action_activate()
        Sub._run_billing(cls.today)
        cls.invoices = cls.sub.invoice_ids.sorted("subscription_period_start")
        cls.invoices.action_post()
        # Oldest fully paid, middle half paid, newest unpaid.
        Register = cls.env["account.payment.register"]
        Register.with_context(active_model="account.move", active_ids=cls.invoices[0].ids).create({})._create_payments()
        Register.with_context(active_model="account.move", active_ids=cls.invoices[1].ids).create(
            {"amount": 500.0})._create_payments()

    def test_figures(self):
        data = self.env["subscription.dashboard"].get_dashboard_data({"partner_id": self.partner.id})
        self.assertEqual(data["subscriptions"]["active"], 1)
        self.assertAlmostEqual(data["subscriptions"]["mrr"], 1000.0)
        self.assertAlmostEqual(data["revenue"]["invoiced"], 3000.0)
        self.assertAlmostEqual(data["revenue"]["collected"], 1500.0)
        self.assertAlmostEqual(data["revenue"]["outstanding"], 1500.0)
        self.assertEqual(data["invoices"]["paid"], 1)
        self.assertEqual(data["invoices"]["outstanding"], 2)
        self.assertAlmostEqual(data["payments"]["total"], 1500.0)
        self.assertEqual(len(data["trend"]), 6)

    def test_portal_user_cannot_read_dashboard(self):
        portal = new_test_user(self.env, login="dash_portal", password="Dash#Pass123", groups="base.group_portal")
        with self.assertRaises(AccessError):
            self.env["subscription.dashboard"].with_user(portal).get_dashboard_data()
