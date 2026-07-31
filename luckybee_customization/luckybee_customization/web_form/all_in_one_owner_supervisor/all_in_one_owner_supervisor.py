import frappe

def get_context(context):
	# Restrict access to authorized roles for Form 5 (All-in-one). Deliberately
	# narrower than Forms 1-3: this form exposes every editable Item field at
	# once (it relies on Owner-Supervisor being a bypass role in
	# item_hooks.py::validate_role_field_permissions), so none of the other
	# individual staff roles (Floor/Trusted/Matching/Stock-take Staff) may load it -
	# they'd otherwise see and could submit fields well outside their whitelist.
	user_roles = set(frappe.get_roles())
	allowed_roles = {"Owner-Supervisor", "System Manager", "Administrator"}
	if not (user_roles & allowed_roles):
		frappe.throw(frappe._("You do not have permission to view this form."), frappe.PermissionError)
