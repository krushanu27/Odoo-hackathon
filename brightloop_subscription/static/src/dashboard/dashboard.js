import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

// Colours for "subscriptions by state" (DESIGN.md chart palette).
const STATE_COLORS = {
    active: "#14C8A0",
    quotations: "#2563EB",
    confirmed: "#93B4F5",
    paused: "#F59E0B",
    closed: "#94A3B8",
};

function rangeFor(key) {
    const today = DateTime.local();
    switch (key) {
        case "this_month":
            return [today.startOf("month"), today];
        case "last_month": {
            const last = today.minus({ months: 1 });
            return [last.startOf("month"), last.endOf("month")];
        }
        case "quarter":
            return [today.startOf("quarter"), today];
        case "year":
            return [today.startOf("year"), today];
        default:
            return [null, null];
    }
}

export class SubscriptionDashboard extends Component {
    static template = "brightloop_subscription.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            error: null,
            data: null,
            plans: [],
            range: "this_month",
            planId: "",
        });
        this.ranges = [
            { key: "this_month", label: _t("This month") },
            { key: "last_month", label: _t("Last month") },
            { key: "quarter", label: _t("Quarter") },
            { key: "year", label: _t("Year") },
            { key: "all", label: _t("All time") },
        ];
        onWillStart(async () => {
            this.state.plans = await this.orm.searchRead("subscription.plan", [], ["name"]);
            await this.load();
        });
    }

    get filters() {
        const [from, to] = rangeFor(this.state.range);
        const filters = {};
        if (from) {
            filters.date_from = from.toISODate();
            filters.date_to = to.toISODate();
        }
        if (this.state.planId) {
            filters.plan_id = parseInt(this.state.planId, 10);
        }
        return filters;
    }

    async load() {
        this.state.loading = true;
        this.state.error = null;
        try {
            this.state.data = await this.orm.call("subscription.dashboard", "get_dashboard_data", [], {
                filters: this.filters,
            });
        } catch (e) {
            this.state.error = e.data?.message || e.message || _t("The dashboard could not be loaded.");
        } finally {
            this.state.loading = false;
        }
    }

    setRange(key) {
        this.state.range = key;
        this.load();
    }

    onPlanChange(ev) {
        this.state.planId = ev.target.value;
        this.load();
    }

    // ---------------------------------------------------------------- format
    money(amount) {
        const { symbol, position } = this.state.data.currency;
        const value = (amount || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        return position === "after" ? `${value} ${symbol}` : `${symbol} ${value}`;
    }

    compactMoney(amount) {
        const { symbol, position } = this.state.data.currency;
        const value = (amount || 0).toLocaleString(undefined, {
            notation: "compact",
            maximumFractionDigits: 1,
        });
        return position === "after" ? `${value} ${symbol}` : `${symbol}${value}`;
    }

    count(n) {
        return (n || 0).toLocaleString();
    }

    formatDate(iso) {
        return DateTime.fromISO(iso).toFormat("d LLL yyyy");
    }

    // ------------------------------------------------------------ chart data
    get trendBars() {
        const trend = this.state.data.trend;
        const max = Math.max(1, ...trend.map((t) => t.invoiced));
        return trend.map((t) => ({
            month: t.month,
            collectedHeight: Math.round((t.collected / max) * 200),
            outstandingHeight: Math.round(((t.invoiced - t.collected) / max) * 200),
            title: `${t.month}: ${this.money(t.collected)} ${_t("collected")}, ${this.money(t.invoiced - t.collected)} ${_t("outstanding")}`,
        }));
    }

    get trendSummary() {
        return this.state.data.trend
            .map((t) => `${t.month}: ${this.money(t.collected)} ${_t("collected of")} ${this.money(t.invoiced)}`)
            .join("; ");
    }

    get stateRows() {
        const s = this.state.data.subscriptions;
        return [
            { key: "active", label: _t("Active"), value: s.active, filter: "filter_active" },
            { key: "quotations", label: _t("Quotations"), value: s.quotations, filter: "filter_quotes" },
            { key: "confirmed", label: _t("Confirmed"), value: s.confirmed, filter: "filter_confirmed" },
            { key: "paused", label: _t("Paused"), value: s.paused, filter: "filter_paused" },
            { key: "closed", label: _t("Closed"), value: s.closed, filter: "filter_closed" },
        ].map((r) => ({ ...r, color: STATE_COLORS[r.key] }));
    }

    get donutStyle() {
        const rows = this.stateRows;
        const total = rows.reduce((sum, r) => sum + r.value, 0);
        if (!total) {
            return "background: #E2E8F0";
        }
        let start = 0;
        const stops = rows.map((r) => {
            const end = start + (r.value / total) * 100;
            const stop = `${r.color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
            start = end;
            return stop;
        });
        return `background: conic-gradient(${stops.join(", ")})`;
    }

    get maxMethodAmount() {
        return Math.max(1, ...this.state.data.payments.by_method.map((p) => p.amount));
    }

    // --------------------------------------------------------------- actions
    openSubscriptions(filter) {
        this.action.doAction("brightloop_subscription.subscription_action", {
            additionalContext: filter ? { [`search_default_${filter}`]: 1 } : {},
        });
    }

    openInvoices(filter) {
        this.action.doAction("brightloop_subscription.action_subscription_invoices", {
            additionalContext: filter ? { [`search_default_${filter}`]: 1 } : {},
        });
    }

    openPayments() {
        this.action.doAction("brightloop_subscription.action_subscription_payments");
    }

    openInvoice(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("brightloop_subscription.dashboard", SubscriptionDashboard);
