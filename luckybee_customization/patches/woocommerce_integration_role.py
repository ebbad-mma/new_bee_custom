"""A scoped role for the external WooCommerce developer.

The brief: he configures the connector and the product sync, and must not reach
purchase data, accounts or the till. So this grants the doctypes the connector
actually uses for product sync - taken from the connector's own source, not
guessed - and nothing else.

Deliberately excluded even though the connector code touches them: Sales Order,
Sales Invoice, Customer, Address and Delivery Note. Those belong to the ORDER
sync (WooCommerce -> ERPNext), which is not in this scope, and Sales Invoice is
where the till's takings live. If order sync is added later this role needs
revisiting rather than the user being handed a broader one.

Nothing here grants System Manager, and no Buying, Accounts or POS doctype
appears at all.

IMPORTANT, and recorded here because a role alone does not achieve it: every
field on Item sits at permlevel 0, so Item read exposes lb_actual_cost,
lb_margin_pct, last_purchase_rate, valuation_rate, the supplier history and both
competitor prices. Genuinely hiding those needs field-level permissions, which
is a separate change affecting all fourteen roles that read Item.
"""

import frappe

ROLE = "WooCommerce Integration"

# doctype -> (read, write, create, delete)
PERMISSIONS = {
	# --- the products themselves ---------------------------------------
	"Item": (1, 1, 0, 0),
	"Item Price": (1, 0, 0, 0),
	"Item Group": (1, 0, 0, 0),
	"Brand": (1, 0, 0, 0),
	"Item Attribute": (1, 0, 0, 0),
	"UOM": (1, 0, 0, 0),
	# Stock levels the storefront publishes; Bin is read-only everywhere anyway.
	"Bin": (1, 0, 0, 0),
	"Warehouse": (1, 0, 0, 0),
	# Product images.
	"File": (1, 1, 1, 0),
	# The mapped Amazon/Flipkart content lives here.
	"Item Details": (1, 0, 0, 0),
	"Country": (1, 0, 0, 0),

	# --- the connector's own configuration ------------------------------
	# Tax rules, warehouse mapping and product categories are child tables of
	# this - they inherit its permissions, so granting them separately does
	# nothing and only makes the role look wider than it is.
	"WooCommerce Config": (1, 1, 0, 0),
		"woocommerce Log": (1, 0, 0, 0),

	# --- diagnosing a sync ----------------------------------------------
	"Ecommerce Item": (1, 1, 0, 0),
	"Ecommerce Integration Log": (1, 0, 0, 0),
	"Error Log": (1, 0, 0, 0),
}


def execute():
	print("Executing Patch: woocommerce_integration_role...")

	if not frappe.db.exists("Role", ROLE):
		role = frappe.new_doc("Role")
		role.role_name = ROLE
		role.desk_access = 1
		# Not an approver of anything, and never a default for new users.
		role.is_custom = 1
		role.insert(ignore_permissions=True)

	created, skipped = [], []
	for doctype, (read, write, create, delete) in PERMISSIONS.items():
		if frappe.db.get_value("DocType", doctype, "istable"):
			# A child table takes its permissions from its parent; a row here
			# would be inert and misleading in an access record.
			skipped.append(doctype + " (child table)")
			continue
		if not frappe.db.exists("DocType", doctype):
			# The connector apps differ between sites; a missing doctype is not
			# a reason to abandon the rest of the role.
			skipped.append(doctype)
			continue
		if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": ROLE,
											   "permlevel": 0}):
			continue
		perm = frappe.new_doc("Custom DocPerm")
		perm.parent = doctype
		perm.parenttype = "DocType"
		perm.parentfield = "permissions"
		perm.role = ROLE
		perm.permlevel = 0
		perm.read, perm.write, perm.create, perm.delete = read, write, create, delete
		perm.report = 1
		perm.export = 0        # no bulk extraction of the catalogue
		perm.share = 0
		perm.print = 0
		perm.email = 0
		perm.insert(ignore_permissions=True)
		created.append(doctype)

	frappe.db.commit()
	frappe.clear_cache()
	print(f"  granted on {len(created)} doctypes; {len(skipped)} absent: {skipped}")
