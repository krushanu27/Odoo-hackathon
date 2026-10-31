{
    "name": "Brightloop Subscriptions",
    "version": "19.0.1.9.0",
    "summary": "Subscription plans, recurring billing, discounts and customer portal",
    "description": """
Subscription Management System for Brightloop Software.
Built on native Odoo Invoicing (invoices, taxes, payments) and Portal.
    """,
    "author": "Team Brightloop",
    "category": "Sales/Subscriptions",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "product",
        "account",
        "portal",
        "auth_signup",
    ],
    "data": [
        # Security first: groups must exist before access rules reference them
        "security/security.xml",
        "security/ir.model.access.csv",
        "security/record_rules.xml",
        # Data
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        # Views: each file defines its own window action
        "views/subscription_plan_views.xml",
        "views/subscription_views.xml",
        # Menus: reference the actions above
        "views/menus.xml",
        # Load after menus: they add items under Configuration
        "views/subscription_template_views.xml",
        "views/subscription_discount_views.xml",
        "data/demo_actions.xml",
        "data/settings.xml",
        "views/product_views.xml",
        # UI: load after menus.xml, they add items under the app and Configuration
        "views/dashboard_views.xml",
        "views/billing_views.xml",
        "views/portal_templates.xml",
        "views/auth_templates.xml",
        "views/account_move_views.xml",
        "views/theme_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "brightloop_subscription/static/src/scss/tokens.scss",
            "brightloop_subscription/static/src/scss/backend_theme.scss",
            "brightloop_subscription/static/src/dashboard/*",
        ],
        "web.assets_frontend": [
            "brightloop_subscription/static/src/scss/tokens.scss",
            "brightloop_subscription/static/src/scss/portal.scss",
            "brightloop_subscription/static/src/signup/password_rules.js",
        ],
    },
    "post_init_hook": "post_init_hook",
    "application": True,
    "installable": True,
}
