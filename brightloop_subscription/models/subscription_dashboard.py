from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError

# Factor that turns one billing period's amount into a monthly amount (MRR).
MONTHLY_FACTOR = {"daily": 30.0, "weekly": 52.0 / 12.0, "monthly": 1.0, "yearly": 1.0 / 12.0}


class SubscriptionDashboard(models.AbstractModel):
    """Numbers for the finance dashboard.

    Every figure is a single SQL aggregate (_read_group), never a Python loop
    over records, so the dashboard stays fast with thousands of subscriptions.
    """

    _name = "subscription.dashboard"
    _description = "Subscription Financial Dashboard"

    @api.model
    def get_dashboard_data(self, filters=None):
        """Filters (all optional): date_from, date_to ("YYYY-MM-DD", applied to
        invoice dates), plan_id, partner_id."""
        if not (self.env.is_superuser() or self.env.user.has_group("brightloop_subscription.group_subscription_staff")):
            raise AccessError(self.env._("Only Brightloop staff can view the dashboard."))
        filters = filters or {}
        today = fields.Date.context_today(self)
        date_from = fields.Date.to_date(filters.get("date_from")) if filters.get("date_from") else None
        date_to = fields.Date.to_date(filters.get("date_to")) if filters.get("date_to") else None
        plan_id = filters.get("plan_id")
        partner_id = filters.get("partner_id")

        Sub = self.env["subscription.subscription"]
        Move = self.env["account.move"]

        # ---------------- subscriptions ----------------
        sub_domain = []
        if plan_id:
            sub_domain.append(("plan_id", "=", plan_id))
        if partner_id:
            sub_domain.append(("partner_id", "child_of", partner_id))

        by_state = {state: count for state, count in Sub._read_group(sub_domain, ["state"], ["__count"])}
        mrr = 0.0
        for plan, untaxed in Sub._read_group(
            sub_domain + [("state", "=", "active")], ["plan_id"], ["amount_untaxed:sum"]
        ):
            mrr += (untaxed or 0.0) * MONTHLY_FACTOR.get(plan.billing_period, 1.0)
        top_plans = [
            {"plan_id": plan.id, "plan": plan.display_name, "active": count}
            for plan, count in Sub._read_group(
                sub_domain + [("state", "=", "active")], ["plan_id"], ["__count"], order="__count desc", limit=5
            )
        ]

        # ---------------- invoices ----------------
        # Invoiced / collected / paid follow the date range. Outstanding and
        # overdue are always "as of today" across all dates: money still owed
        # does not stop being owed because it was invoiced last quarter.
        base_domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("subscription_id", "!=", False),
        ]
        if plan_id:
            base_domain.append(("subscription_id.plan_id", "=", plan_id))
        if partner_id:
            base_domain.append(("partner_id", "child_of", partner_id))
        inv_domain = list(base_domain)
        if date_from:
            inv_domain.append(("invoice_date", ">=", date_from))
        if date_to:
            inv_domain.append(("invoice_date", "<=", date_to))

        [[invoiced, period_residual, inv_count]] = Move._read_group(
            inv_domain, [], ["amount_total_signed:sum", "amount_residual_signed:sum", "__count"]
        )
        invoiced, period_residual = invoiced or 0.0, period_residual or 0.0

        open_domain = base_domain + [("payment_state", "in", ("not_paid", "partial"))]
        [[outstanding, open_count]] = Move._read_group(open_domain, [], ["amount_residual_signed:sum", "__count"])
        overdue_domain = open_domain + [("invoice_date_due", "<", today)]
        [[overdue_amount, overdue_count]] = Move._read_group(
            overdue_domain, [], ["amount_residual_signed:sum", "__count"]
        )
        paid_count = {
            state: count for state, count in Move._read_group(inv_domain, ["payment_state"], ["__count"])
        }.get("paid", 0)
        draft_count = Move.search_count([
            ("move_type", "=", "out_invoice"), ("state", "=", "draft"), ("subscription_id", "!=", False),
        ])

        overdue_list = [
            {
                "id": inv.id,
                "number": inv.name,
                "customer": inv.partner_id.display_name,
                "due_date": fields.Date.to_string(inv.invoice_date_due),
                "days_overdue": (today - inv.invoice_date_due).days,
                "amount_due": inv.amount_residual_signed,
            }
            for inv in Move.search(overdue_domain, order="invoice_date_due asc", limit=10)
        ]

        # ---------------- payments ----------------
        pay_domain = [("payment_type", "=", "inbound"), ("state", "not in", ("draft", "canceled", "rejected"))]
        if date_from:
            pay_domain.append(("date", ">=", date_from))
        if date_to:
            pay_domain.append(("date", "<=", date_to))
        if partner_id:
            pay_domain.append(("partner_id", "child_of", partner_id))
        payments_by_method = [
            {"method": journal.display_name, "count": count, "amount": amount or 0.0}
            for journal, count, amount in self.env["account.payment"]._read_group(
                pay_domain, ["journal_id"], ["__count", "amount:sum"], order="amount:sum desc"
            )
        ]

        # ---------------- 6-month trend ----------------
        start = (date_to or today).replace(day=1) - relativedelta(months=5)
        trend_domain = base_domain + [
            ("invoice_date", ">=", start), ("invoice_date", "<=", date_to or today),
        ]
        trend_raw = {
            month: (total or 0.0, res or 0.0)
            for month, total, res in Move._read_group(
                trend_domain, ["invoice_date:month"], ["amount_total_signed:sum", "amount_residual_signed:sum"]
            )
        }
        trend = []
        for i in range(6):
            month = start + relativedelta(months=i)
            total, res = next(
                (v for k, v in trend_raw.items() if k and k.year == month.year and k.month == month.month),
                (0.0, 0.0),
            )
            trend.append({"month": month.strftime("%b %Y"), "invoiced": total, "collected": total - res})

        return {
            "currency": {
                "symbol": self.env.company.currency_id.symbol,
                "position": self.env.company.currency_id.position,
            },
            "subscriptions": {
                "active": by_state.get("active", 0),
                "paused": by_state.get("paused", 0),
                "quotations": by_state.get("draft", 0) + by_state.get("quotation", 0),
                "confirmed": by_state.get("confirmed", 0),
                "closed": by_state.get("closed", 0),
                "total": sum(by_state.values()),
                "mrr": mrr,
                "top_plans": top_plans,
            },
            "revenue": {
                "invoiced": invoiced,
                "collected": invoiced - period_residual,
                "outstanding": outstanding or 0.0,
                "overdue": overdue_amount or 0.0,
            },
            "invoices": {
                "posted": inv_count,
                "paid": paid_count,
                "outstanding": open_count,
                "overdue": overdue_count,
                "draft": draft_count,
                "overdue_list": overdue_list,
            },
            "payments": {
                "by_method": payments_by_method,
                "total": sum(p["amount"] for p in payments_by_method),
                "count": sum(p["count"] for p in payments_by_method),
            },
            "trend": trend,
        }
