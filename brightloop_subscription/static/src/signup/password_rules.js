// Live password checklist on /web/signup and /web/reset_password.
// Same rules as PASSWORD_RULES in models/res_users.py (the server enforces them).
const RULES = {
    length: (p) => p.length > 8,
    upper: (p) => /[A-Z]/.test(p),
    lower: (p) => /[a-z]/.test(p),
    special: (p) => /[^A-Za-z0-9]/.test(p),
};

function setup() {
    const list = document.getElementById("bl_password_rules");
    const input = document.querySelector("form input[name='password']");
    if (!list || !input) {
        return;
    }
    // Odoo 19 wraps the field in an .input-group with the show/hide button;
    // keep the checklist below that group so the field keeps its full width.
    const group = input.closest(".input-group");
    if (group && group.contains(list)) {
        group.after(list);
    }
    const items = list.querySelectorAll("li[data-rule]");
    const update = () => {
        for (const item of items) {
            const ok = RULES[item.dataset.rule](input.value);
            item.classList.toggle("bl_ok", ok);
            item.setAttribute("aria-label", `${item.textContent.trim()}: ${ok ? "met" : "not met"}`);
        }
    };
    input.setAttribute("aria-describedby", "bl_password_rules");
    input.addEventListener("input", update);
    update();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
} else {
    setup();
}
