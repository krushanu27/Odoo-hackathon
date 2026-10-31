{
    "name": "Brightloop Subscriptions",
    "version": "19.0.1.4.0",
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
    ],
    "post_init_hook": "post_init_hook",
    "application": True,
    "installable": True,
}
