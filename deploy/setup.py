# Runs once in `odoo shell` right after the database is created.
import os

env["ir.config_parameter"].set_param("ir_attachment.location", "db")
env["ir.attachment"].force_storage()
inr = env.ref("base.INR")
inr.active = True
env.ref("base.main_company").write({
    "name": "Brightloop Software",
    "country_id": env.ref("base.in").id,
    "currency_id": inr.id,
})
if os.environ.get("ADMIN_PASSWORD"):
    env.ref("base.user_admin").password = os.environ["ADMIN_PASSWORD"]
env.cr.commit()
print("==> Database prepared")
