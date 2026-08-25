"""Repair: standard permissions silently revoked by woocommerce_integration_role.

Frappe treats Custom DocPerm as a REPLACEMENT, not an addition. get_all_perms()
collects every standard DocPerm, then drops the ones whose doctype appears in
Custom DocPerm at all:

    for p in perms:
        if p.parent not in doctypes_with_custom_perms:
            custom_perms.append(p)

So the first Custom DocPerm row written against a doctype revokes every standard
permission on it, for every role. Frappe's own add_permission() calls
setup_custom_perms() first, which copies the standard rows across before adding
anything - the earlier patch inserted Custom DocPerm rows directly and skipped
that step.

The damage was invisible because nobody had exercised the affected doctypes
under a non-Administrator account: System Manager had lost Error Log,
WooCommerce Config, Ecommerce Item and both integration logs; Stock User and
Sales User had lost Bin, Item Group, Brand and UOM; Purchase Master Manager and
Sales Master Manager had lost Item Price.

This copies back any standard DocPerm whose (role, permlevel) has no Custom
DocPerm counterpart. It deliberately does NOT touch existing Custom DocPerm rows
- several of those doctypes were customised long before this app, and the
WooCommerce role's own rows are correct as they stand.
"""

import frappe

# The doctypes the role patch wrote to. Any that already had Custom DocPerm rows
# before it ran (Item, Warehouse, File, Country) are unaffected but harmless to
# re-check - the query only ever adds what is missing.
DOCTYPES = [
	"Item", "Item Price", "Item Group", "Brand", "Item Attribute", "UOM",
	"Bin", "Warehouse", "File", "Item Details", "Country",
	"WooCommerce Config", "woocommerce Log", "Ecommerce Item",
	"Ecommerce Integration Log", "Error Log",
]


def execute():
	print("Executing Patch: restore_standard_docperms...")
	restored = {}

	for doctype in DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		# No Custom DocPerm at all means the standard rows are still in force.
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype}):
			continue

		existing = {
			(r.role, r.permlevel)
			for r in frappe.get_all(
				"Custom DocPerm", filters={"parent": doctype}, fields=["role", "permlevel"]
			)
		}

		added = []
		for std in frappe.get_all("DocPerm", fields="*", filters={"parent": doctype}):
			if (std.role, std.permlevel) in existing:
				continue
			if std.role and not frappe.db.exists("Role", std.role):
				continue
			perm = frappe.new_doc("Custom DocPerm")
			perm.update(std)
			# name/creation/modified belong to the DocPerm row, not the new one.
			perm.name = None
			perm.insert(ignore_permissions=True)
			added.append(f"{std.role}(L{std.permlevel})")

		if added:
			restored[doctype] = added

	frappe.db.commit()
	frappe.clear_cache()

	if restored:
		for doctype, roles in restored.items():
			print(f"  {doctype}: restored {len(roles)} -> {', '.join(roles)}")
	else:
		print("  nothing to restore")
