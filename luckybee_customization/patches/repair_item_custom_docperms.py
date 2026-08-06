"""Repair the permissions our own web-form setup silently broke.

create_floor_webform.py added a single Custom DocPerm (Floor Staff) to Item.
Frappe treats Custom DocPerm as a REPLACEMENT, not an addition - see
Meta.set_custom_permissions: "Reset `permissions` with Custom DocPerm if
exists". So that one row silently revoked every standard Item permission:
Item Manager, Stock Manager, Stock User, Purchase User, Sales User, Accounts
User, Maintenance User and Manufacturing User all lost their access.

It went unnoticed because every mobile-forms user also happens to hold Floor
Staff, and the owner logs in as a System Manager, which bypasses the check.

Two things to put right, and they need doing together:

  1. Restore the standard grants by copying the doctype's own DocPerm rows into
     Custom DocPerm for any (role, permlevel) not already present. Once custom
     permissions exist for a doctype the standard ones are never consulted
     again, so the custom set has to be complete rather than a delta.

  2. Give the four staff roles their own explicit Item grant instead of relying
     on them also carrying Floor Staff, and give Stock-take Staff and
     Owner-Supervisor the Stock Reconciliation grant the Count form needs -
     without it "Update Stock" fails for the very role whose whole job it is.
"""

import frappe

# read/write on Item, never create or delete - the mobile forms only ever edit
# items that already exist.
ITEM_STAFF_ROLES = [
	"Floor Staff",
	"Trusted Staff",
	"Matching Staff",
	"Stock-take Staff",
	"Owner-Supervisor",
]

# The Count form creates and submits a Stock Reconciliation; it must never
# cancel, amend or delete one.
STOCK_RECO_ROLES = ["Stock-take Staff", "Owner-Supervisor"]


def _existing_keys(doctype):
	return {
		(d.role, d.permlevel or 0)
		for d in frappe.get_all(
			"Custom DocPerm", filters={"parent": doctype}, fields=["role", "permlevel"]
		)
	}


def backfill_standard_perms(doctype):
	"""Copy the doctype's standard DocPerm rows into Custom DocPerm.

	Only runs where custom permissions already exist - otherwise the standard
	ones are still live and copying them in would be pointless churn.
	"""
	existing = _existing_keys(doctype)
	if not existing:
		return 0

	restored = 0
	for std in frappe.get_all("DocPerm", filters={"parent": doctype}, fields=["*"]):
		key = (std.get("role"), std.get("permlevel") or 0)
		if key in existing:
			continue
		doc = frappe.new_doc("Custom DocPerm")
		doc.update({k: v for k, v in std.items()
					if k not in ("name", "parent", "parenttype", "parentfield",
								 "doctype", "creation", "modified", "owner",
								 "modified_by", "idx")})
		doc.parent = doctype
		doc.parenttype = "DocType"
		doc.parentfield = "permissions"
		doc.insert(ignore_permissions=True)
		restored += 1
	return restored


def grant(doctype, role, **flags):
	name = frappe.db.get_value(
		"Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0})
	if name:
		doc = frappe.get_doc("Custom DocPerm", name)
	else:
		doc = frappe.new_doc("Custom DocPerm")
		doc.parent = doctype
		doc.parenttype = "DocType"
		doc.parentfield = "permissions"
		doc.role = role
		doc.permlevel = 0
	doc.update(flags)
	doc.save(ignore_permissions=True) if not doc.is_new() else doc.insert(ignore_permissions=True)


def execute():
	print("Executing Patch: repair_item_custom_docperms...")

	restored_item = backfill_standard_perms("Item")
	restored_reco = backfill_standard_perms("Stock Reconciliation")

	for role in ITEM_STAFF_ROLES:
		grant("Item", role, read=1, write=1, create=0, delete=0)

	# Only meaningful once Stock Reconciliation has custom perms at all;
	# granting here creates that set, so backfill the standard rows first.
	if not _existing_keys("Stock Reconciliation"):
		# No custom perms yet - adding ours would wipe the standard grants, so
		# copy those in first and only then add ours.
		for std in frappe.get_all("DocPerm", filters={"parent": "Stock Reconciliation"}, fields=["*"]):
			doc = frappe.new_doc("Custom DocPerm")
			doc.update({k: v for k, v in std.items()
						if k not in ("name", "parent", "parenttype", "parentfield",
									 "doctype", "creation", "modified", "owner",
									 "modified_by", "idx")})
			doc.parent = "Stock Reconciliation"
			doc.parenttype = "DocType"
			doc.parentfield = "permissions"
			doc.insert(ignore_permissions=True)

	for role in STOCK_RECO_ROLES:
		grant("Stock Reconciliation", role,
			  read=1, write=1, create=1, submit=1, cancel=0, amend=0, delete=0)

	frappe.clear_cache()
	frappe.db.commit()
	print(f"  restored {restored_item} standard Item perms, "
		  f"{restored_reco} standard Stock Reconciliation perms")
