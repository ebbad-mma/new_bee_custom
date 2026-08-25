"""Field-level protection for Item's cost, margin and supplier data.

Enforced from after_migrate rather than only from a patch, because
sync_fixtures runs after patches on every migrate and re-imports
fixtures/custom_field.json - which resets any permlevel a patch had just set.
The fixture file carries permlevel 1 as well, so the two agree, but this is what
makes it true regardless of import ordering.

A role grants access to a document, not to a field. "Can edit products but
cannot see what we paid" is not expressible with roles alone, which is why an
external contractor with product access could read every cost figure on an item.
"""

import frappe

PROTECTED = [
	"lb_actual_cost",
	"lb_margin_pct",
	"last_purchase_rate",
	"custom_last_supplier_purchase_rate",
	"valuation_rate",
	"custom_last_supplier",
	"custom_supplier_history",
	"supplier_items",
]

# Owner-Supervisor is already the senior tier elsewhere in this app - it is what
# the till's cost/margin panel is gated on - and the rest need cost for their own
# work. Every other role that can read an Item, including WooCommerce
# Integration and all the shop-floor roles, loses sight of these.
PRIVILEGED_ROLES = [
	"System Manager",
	"Owner-Supervisor",
	"Item Manager",
	"Accounts User",
	"Purchase User",
	"Stock Manager",
]

PERMLEVEL = 1


def enforce_item_field_permlevels():
	"""Idempotent; safe to run on every migrate."""
	changed = []

	for fieldname in PROTECTED:
		custom = frappe.db.get_value("Custom Field",
									 {"dt": "Item", "fieldname": fieldname}, "name")
		if custom:
			if frappe.db.get_value("Custom Field", custom, "permlevel") != PERMLEVEL:
				frappe.db.set_value("Custom Field", custom, "permlevel", PERMLEVEL,
									update_modified=False)
				changed.append(fieldname)
			continue

		if not frappe.get_meta("Item").has_field(fieldname):
			continue

		existing = frappe.db.get_value("Property Setter",
			{"doc_type": "Item", "field_name": fieldname, "property": "permlevel"}, "value")
		if str(existing) != str(PERMLEVEL):
			frappe.make_property_setter({
				"doctype": "Item",
				"fieldname": fieldname,
				"property": "permlevel",
				"value": PERMLEVEL,
				"property_type": "Int",
			}, is_system_generated=False)
			changed.append(fieldname)

	for role in PRIVILEGED_ROLES:
		if not frappe.db.exists("Role", role):
			continue
		if frappe.db.exists("Custom DocPerm",
							{"parent": "Item", "role": role, "permlevel": PERMLEVEL}):
			continue
		perm = frappe.new_doc("Custom DocPerm")
		perm.parent = "Item"
		perm.parenttype = "DocType"
		perm.parentfield = "permissions"
		perm.role = role
		perm.permlevel = PERMLEVEL
		perm.read = 1
		perm.write = 1
		perm.insert(ignore_permissions=True)
		changed.append(f"perm:{role}")

	if changed:
		frappe.db.commit()
		frappe.clear_cache(doctype="Item")
	return changed


# ---------------------------------------------------------------------------
# Item Price
# ---------------------------------------------------------------------------
# Hiding cost on Item is not enough on its own. `tabItem Price` holds 5,634
# buying rows alongside 8,012 selling ones, and a buying row IS a supplier
# purchase rate - so a contractor with plain Item Price read reads purchase data
# without ever opening an Item. The connector only ever publishes selling
# prices, so the role is scoped to those.

SELLING_ONLY_ROLES = {"WooCommerce Integration"}


def _selling_only(user=None):
	"""True when this user should see selling prices and nothing else."""
	user = user or frappe.session.user
	if user == "Administrator":
		return False
	roles = set(frappe.get_roles(user))
	if not (roles & SELLING_ONLY_ROLES):
		return False
	# Someone who also holds a buying/costing role is not the contractor, and
	# narrowing them here would quietly break their own work.
	return not (roles & set(PRIVILEGED_ROLES))


def item_price_query_conditions(user=None):
	"""permission_query_conditions hook - scopes list/report views."""
	if not _selling_only(user):
		return ""
	return "`tabItem Price`.`selling` = 1"


def item_price_has_permission(doc, ptype=None, user=None):
	"""has_permission hook - the single-document counterpart of the above.

	The query condition only filters lists; without this, a direct link to a
	buying price still opens.
	"""
	if not _selling_only(user):
		return True
	return bool(doc.get("selling"))
