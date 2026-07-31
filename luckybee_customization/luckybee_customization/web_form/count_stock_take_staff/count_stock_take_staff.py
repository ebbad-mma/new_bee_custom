import frappe

def get_context(context):
	# Restrict access to authorized roles for Form 4 (Stock Count)
	user_roles = set(frappe.get_roles())
	allowed_roles = {"Stock-take Staff", "Owner-Supervisor", "System Manager", "Administrator"}
	if not (user_roles & allowed_roles):
		frappe.throw(frappe._("You do not have permission to view this form."), frappe.PermissionError)
