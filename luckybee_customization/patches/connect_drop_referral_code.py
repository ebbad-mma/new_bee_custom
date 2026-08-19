"""Remove the referral code field - the mobile number is the referral.

The client settled it: a customer gives their number, staff confirm the name,
and that is the referral. Nothing to issue, nothing to remember, and no code to
lose. The field never held a value, so nothing is lost by removing it - leaving
it would only invite someone to start filling in a second, competing identifier.
"""

import frappe


def execute():
	print("Executing Patch: connect_drop_referral_code...")

	filled = frappe.db.sql(
		"SELECT COUNT(*) FROM `tabCustomer` WHERE IFNULL(lb_referral_code,'') <> ''"
	)[0][0] if frappe.db.has_column("Customer", "lb_referral_code") else 0

	if filled:
		# Never silently discard data. If codes were issued after all, keep the
		# field and let somebody decide what to do with them.
		frappe.log_error(
			f"lb_referral_code holds {filled} values, so it was left in place. "
			f"Remove it by hand once those have been dealt with.",
			"Luckybee Connect")
		return

	name = frappe.db.get_value("Custom Field",
							   {"dt": "Customer", "fieldname": "lb_referral_code"})
	if name:
		frappe.delete_doc("Custom Field", name, force=1, ignore_permissions=True)
		frappe.db.commit()
		frappe.clear_cache(doctype="Customer")
