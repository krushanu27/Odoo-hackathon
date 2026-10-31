from urllib.parse import urlencode

from odoo import fields, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

# Drafts are internal work in progress; customers see everything from the quotation on.
PORTAL_DOMAIN = [("state", "!=", "draft")]

SORT_ORDERS = {
    "date": "date_start desc, id desc",
    "name": "name desc",
    "state": "state, id desc",
}


class SubscriptionPortal(CustomerPortal):
    """Customer pages for subscriptions.

    Customers are read-only: lists use a plain search() so record rules limit
    them to their own subscriptions, and buttons go through
    action_portal_request(), which re-checks access and the plan's rules.
    """

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "subscription_count" in counters:
            Subscription = request.env["subscription.subscription"]
            values["subscription_count"] = (
                Subscription.search_count(PORTAL_DOMAIN) if Subscription.has_access("read") else 0
            )
        return values

    def _get_portal_subscription(self, subscription_id):
        """The subscription if the current user may see it, else an empty recordset."""
        return request.env["subscription.subscription"].search(
            [("id", "=", subscription_id)] + PORTAL_DOMAIN, limit=1
        )

    @http.route(
        ["/my/subscriptions", "/my/subscriptions/page/<int:page>"],
        type="http", auth="user", website=True,
    )
    def portal_my_subscriptions(self, page=1, sortby="date", **kw):
        _ = request.env._
        Subscription = request.env["subscription.subscription"]
        if sortby not in SORT_ORDERS:
            sortby = "date"
        pager = portal_pager(
            url="/my/subscriptions",
            url_args={"sortby": sortby},
            total=Subscription.search_count(PORTAL_DOMAIN),
            page=page,
            step=self._items_per_page,
        )
        subscriptions = Subscription.search(
            PORTAL_DOMAIN, order=SORT_ORDERS[sortby], limit=self._items_per_page, offset=pager["offset"]
        )
        values = self._prepare_portal_layout_values()
        values.update({
            "subscriptions": subscriptions,
            "page_name": "subscription",
            "pager": pager,
            "default_url": "/my/subscriptions",
            "searchbar_sortings": {
                "date": {"label": _("Newest")},
                "name": {"label": _("Number")},
                "state": {"label": _("Status")},
            },
            "sortby": sortby,
        })
        return request.render("brightloop_subscription.portal_my_subscriptions", values)

    @http.route("/my/subscriptions/<int:subscription_id>", type="http", auth="user", website=True)
    def portal_my_subscription(self, subscription_id, message=None, error=None, **kw):
        subscription = self._get_portal_subscription(subscription_id)
        if not subscription:
            return request.redirect("/my/subscriptions")
        # Odoo's own portal rules already limit invoices to the customer's own.
        invoices = request.env["account.move"].search(
            [("subscription_id", "=", subscription.id), ("state", "=", "posted")],
            order="invoice_date desc, id desc",
        )
        values = self._prepare_portal_layout_values()
        addons = (
            subscription._portal_available_addons()
            if subscription.state in subscription.ADDON_STATES else []
        )
        values.update({
            "subscription": subscription,
            "invoices": invoices,
            "addons": addons,
            "today": fields.Date.context_today(subscription),
            "page_name": "subscription",
            "message": message,
            "error": error,
        })
        return request.render("brightloop_subscription.portal_my_subscription", values)

    @http.route(
        "/my/subscriptions/<int:subscription_id>/<string:action>",
        type="http", auth="user", website=True, methods=["POST"],
    )
    def portal_subscription_action(self, subscription_id, action, **kw):
        _ = request.env._
        subscription = self._get_portal_subscription(subscription_id)
        if not subscription:
            return request.redirect("/my/subscriptions")
        done = {
            "pause": _("Your subscription is paused. It will not be billed until you resume it."),
            "resume": _("Your subscription is active again."),
            "close": _("Your subscription is closed."),
            "renew": _("Your subscription has been renewed."),
        }
        url = f"/my/subscriptions/{subscription.id}"
        if action not in done:
            return request.redirect(f"{url}?{urlencode({'error': _('That action is not available.')})}")
        try:
            subscription.action_portal_request(action)
        except (UserError, AccessError) as e:
            return request.redirect(f"{url}?{urlencode({'error': e.args[0] if e.args else str(e)})}")
        return request.redirect(f"{url}?{urlencode({'message': done[action]})}")

    @http.route(
        "/my/subscriptions/<int:subscription_id>/addon/<int:product_id>/<string:mode>",
        type="http", auth="user", website=True, methods=["POST"],
    )
    def portal_subscription_addon(self, subscription_id, product_id, mode, **kw):
        """Switch an add-on on or off. The model checks access, the subscription
        state and that the product really is an add-on."""
        _ = request.env._
        subscription = self._get_portal_subscription(subscription_id)
        if not subscription:
            return request.redirect("/my/subscriptions")
        url = f"/my/subscriptions/{subscription.id}"
        if mode not in ("on", "off"):
            return request.redirect(f"{url}?{urlencode({'error': _('That action is not available.')})}")
        try:
            subscription.action_portal_set_addon(product_id, mode == "on")
        except (UserError, AccessError) as e:
            return request.redirect(f"{url}?{urlencode({'error': e.args[0] if e.args else str(e)})}")
        message = (_("Add-on switched on. It is billed from your next invoice.") if mode == "on"
                   else _("Add-on switched off. It is no longer billed from your next invoice."))
        return request.redirect(f"{url}?{urlencode({'message': message})}")
