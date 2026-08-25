"""Give the connector role Item Price back, now that it can be scoped safely.

Item Price was granted to WooCommerce Integration by the original role patch,
then removed by hand on production: 5,634 of its 13,646 rows are BUYING prices,
i.e. supplier purchase rates, and a plain read grant handed those over. Removing
the doctype was the only mitigation available without a deploy.

With item_field_security's permission_query_conditions / has_permission hooks in
place the role can be scoped to selling rows, so the grant is safe to restore -
the connector does need selling prices, and the query condition now filters the
buying ones out of both list views and direct document access.

Runs after the hooks exist, so re-granting is not a regression.
"""

import frappe
from frappe.permissions import setup_custom_perms

ROLE = "WooCommerce Integration"
DOCTYPE = "Item Price"


def execute():
	print("Executing Patch: woocommerce_item_price_selling_only...")

	if not frappe.db.exists("Role", ROLE):
		print(f"  {ROLE} absent - nothing to do")
		return

	if frappe.db.exists("Custom DocPerm", {"parent": DOCTYPE, "role": ROLE, "permlevel": 0}):
		print("  grant already present")
		return

	# Custom DocPerm replaces the standard rows for a doctype rather than adding
	# to them, so the standard ones must be copied across first.
	setup_custom_perms(DOCTYPE)

	perm = frappe.new_doc("Custom DocPerm")
	perm.parent = DOCTYPE
	perm.parenttype = "DocType"
	perm.parentfield = "permissions"
	perm.role = ROLE
	perm.permlevel = 0
	perm.read = 1
	perm.write = perm.create = perm.delete = 0
	perm.report = 1
	perm.export = perm.share = perm.print = perm.email = 0
	perm.insert(ignore_permissions=True)

	frappe.db.commit()
	frappe.clear_cache()
	print("  Item Price re-granted, scoped to selling rows by the hook")
