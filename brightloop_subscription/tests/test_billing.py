from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBilling(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})
        cls.plan = cls.env["subscription.plan"].create({
            "name": "Test Monthly",
            "price": 100.0,
            "billing_period": "monthly",
            "min_quantity": 1,
            "allow_pause": True,
            "auto_close": True,
        })
        cls.Sub = cls.env["subscription.subscription"]

    def _active_sub(self, start, end=None):
        sub = self.Sub.create({
            "partner_id": self.partner.id,
            "plan_id": self.plan.id,
            "date_start": start,
            "date_end": end,
        })
        sub.action_confirm()
        sub.action_activate()
        return sub

    def test_bills_current_period(self):
        sub = self._active_sub(self.today)
        self.Sub._run_billing(self.today)
        self.assertEqual(sub.invoice_count, 1)
        invoice = sub.invoice_ids
        self.assertEqual(invoice.partner_id, self.partner)
        self.assertEqual(invoice.amount_untaxed, 100.0)
        self.assertEqual(sub.next_invoice_date, self.today + relativedelta(months=1))

    def test_no_duplicates_on_rerun(self):
        sub = self._active_sub(self.today)
        self.Sub._run_billing(self.today)
        self.Sub._run_billing(self.today)
        self.Sub._run_billing(self.today)
        self.assertEqual(sub.invoice_count, 1)

    def test_catches_up_missed_periods(self):
        start = self.today - relativedelta(months=2)
        sub = self._active_sub(start)
        self.Sub._run_billing(self.today)
        self.assertEqual(sub.invoice_count, 3, "Two missed periods plus the current one")
        periods = sorted(sub.invoice_ids.mapped("subscription_period_start"))
        self.assertEqual(periods, [start, start + relativedelta(months=1), start + relativedelta(months=2)])

    def test_paused_not_billed_and_resume_skips_pause(self):
        sub = self._active_sub(self.today - relativedelta(months=3))
        sub.next_invoice_date = self.today - relativedelta(months=2)
        sub.action_pause()
        self.Sub._run_billing(self.today)
        self.assertEqual(sub.invoice_count, 0)
        sub.action_resume()
        self.assertEqual(sub.next_invoice_date, self.today)
        self.Sub._run_billing(self.today)
        self.assertEqual(sub.invoice_count, 1)

    def test_stops_at_expiry_and_auto_closes(self):
        start = self.today - relativedelta(months=2)
        sub = self._active_sub(start, end=start + relativedelta(months=1))
        self.Sub._run_billing(self.today)
        self.assertEqual(sub.invoice_count, 1, "Only the period before expiry is billed")
        self.assertEqual(sub.state, "closed")

    def test_many_subscriptions_in_one_run(self):
        subs = self.Sub
        for _ in range(150):  # more than one batch
            subs |= self._active_sub(self.today)
        self.Sub._run_billing(self.today)
        self.assertTrue(all(s.invoice_count == 1 for s in subs))
