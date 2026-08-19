"""Move the Luckybee Connect fields onto the Loyalty Points section.

They were anchored on loyalty_program_tier, which happens to be the last field
before the Sales Team tab break - so the whole block landed inside Sales Team,
several tabs away from the loyalty data it belongs with. Referral standing is
read next to the points balance, not next to sales partners.

Dropping the block's own Section Break is what fixes it: the fields then join
the existing "Loyalty Points" section rather than opening a new one that Frappe
places after the tab boundary.
"""

import frappe


def execute():
	print("Executing Patch: connect_customer_placement...")

	# The section and column break exist only to hold the block apart; without
	# them the fields sit inside Loyalty Points where they belong.
	for fieldname in ("sec_lb_connect", "cb_lb_connect"):
		name = frappe.db.get_value("Custom Field",
								   {"dt": "Customer", "fieldname": fieldname})
		if name:
			frappe.delete_doc("Custom Field", name, force=1, ignore_permissions=True)

	# Re-chain the four onto the loyalty tier field, in order.
	order = [
		("lb_referral_code", "loyalty_program_tier"),
		("lb_referred_by", "lb_referral_code"),
		("lb_first_purchase_date", "lb_referred_by"),
		("lb_referral_bonus_paid", "lb_first_purchase_date"),
	]
	for fieldname, after in order:
		name = frappe.db.get_value("Custom Field",
								   {"dt": "Customer", "fieldname": fieldname})
		if name:
			frappe.db.set_value("Custom Field", name, "insert_after", after,
								update_modified=False)

	frappe.db.commit()
	frappe.clear_cache(doctype="Customer")
