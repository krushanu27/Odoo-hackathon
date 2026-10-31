import re

from odoo import models
from odoo.exceptions import UserError

# Problem statement: more than eight characters, with an uppercase letter,
# a lowercase letter and a special character.
PASSWORD_RULES = [
    (lambda p: len(p) > 8, "more than 8 characters"),
    (lambda p: re.search(r"[A-Z]", p), "an uppercase letter"),
    (lambda p: re.search(r"[a-z]", p), "a lowercase letter"),
    (lambda p: re.search(r"[^A-Za-z0-9]", p), "a special character"),
]


class ResUsers(models.Model):
    _inherit = "res.users"

    @staticmethod
    def _password_policy_errors(password):
        return [label for check, label in PASSWORD_RULES if not check(password or "")]

    def _set_password(self):
        """Every way of setting a password (signup, reset link, change-password
        dialog, admin edit) ends here, so the rule is enforced in one place."""
        for user in self:
            if not user.password:
                continue
            missing = self._password_policy_errors(user.password)
            if missing:
                raise UserError(
                    self.env._("Password must contain %s.", ", ".join(missing))
                )
        return super()._set_password()
