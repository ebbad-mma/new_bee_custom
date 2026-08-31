"""Condition on the Item - Fresh / Open box / Surplus.

Drives the condition badge and the "Fresh only" filter on the storefront. It has
to live here rather than in WooCommerce: ERPNext is the master, and tagging
~5,000 products by hand in WordPress would put the truth in the wrong system and
guarantee the two drift apart.

Everything already in the catalogue is backfilled to "Fresh". That is the safe
default - open box and surplus are deliberate states someone sets, whereas
ordinary stock is fresh by definition, so backfilling to anything else would
mislabel the entire catalogue.
"""

import frappe

FIELDNAME = "lb_condition"
OPTIONS = "Fresh\nOpen box\nSurplus"
DEFAULT = "Fresh"


def execute():
	print("Executing Patch: lb_item_condition_field...")

	if not frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": FIELDNAME}):
		frappe.get_doc({
			"doctype": "Custom Field",
			"dt": "Item",
			"fieldname": FIELDNAME,
			"label": "Condition",
			"fieldtype": "Select",
			"options": OPTIONS,
			"default": DEFAULT,
			"in_standard_filter": 1,
			"insert_after": "item_group",
			"description": "Fresh = brand new, factory sealed. "
						   "Open box = returned, checked and working. "
						   "Surplus = overstock or clearance.",
			"module": "luckybee_customization",
		}).insert(ignore_permissions=True)
		print("  created the Condition field")
	else:
		print("  Condition field already present")

	# Bulk UPDATE, not save() - Item's before_save chain calls sync_keepa_item,
	# so saving 8,000 rows would fire 8,000 Keepa lookups.
	frappe.db.sql(
		f"""UPDATE `tabItem` SET `{FIELDNAME}` = %s
			WHERE IFNULL(`{FIELDNAME}`, '') = ''""",
		(DEFAULT,),
	)
	frappe.db.commit()
	frappe.clear_cache(doctype="Item")
	print(f"  backfilled to '{DEFAULT}': {frappe.db.count('Item', {FIELDNAME: DEFAULT})} items")
