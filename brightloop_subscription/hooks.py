from odoo import Command


def post_init_hook(env):
    """Give the default administrator our Subscription Admin role on install.

    Odoo 19 renamed res.users.groups_id to group_ids, so we pick whichever
    field exists instead of hardcoding one version's name.
    """
    admin_group = env.ref("brightloop_subscription.group_subscription_admin")
    admin_user = env.ref("base.user_admin", raise_if_not_found=False)
    if not admin_user:
        return
    field = "group_ids" if "group_ids" in admin_user._fields else "groups_id"
    admin_user.sudo().write({field: [Command.link(admin_group.id)]})
