"""Separate writing a product name from approving it.

Ashish's instruction: Udit drafts the names, Ashish approves. Udit already has
write on Item, so he can edit the name fields - but pb_publish_status sat at
permlevel 0 alongside them, which meant he could also mark his own work Ready to
Publish. An approval anyone can grant themselves is not an approval.

So the approval field moves to its own permission level. Udit keeps write on
everything else and can still SEE whether an item is approved; only the roles
Ashish holds can change it.

Level 2, not 1: level 1 is already the cost and supplier data, and the two must
stay separate. Whoever approves product copy has no business seeing margins
because of it, and the buyer who sees cost should not thereby gain approval
rights. Reusing level 1 would silently couple them.
"""

import frappe
from frappe.permissions import setup_custom_perms

FIELD = "pb_publish_status"
PERMLEVEL = 2

# (role, read, write)
GRANTS = [
	("Owner-Supervisor", 1, 1),   # Ashish approves
	("System Manager", 1, 1),
	("Trusted Staff", 1, 0),      # Udit drafts, and can see the decision
	("Item Manager", 1, 0),
]


def execute():
	print("Executing Patch: lb_name_approval_permissions...")

	cf = frappe.db.get_value("Custom Field", {"dt": "Item", "fieldname": FIELD})
	if not cf:
		print(f"  {FIELD} not present - nothing to protect")
		return

	if frappe.db.get_value("Custom Field", cf, "permlevel") != PERMLEVEL:
		frappe.db.set_value("Custom Field", cf, "permlevel", PERMLEVEL,
							update_modified=False)
		print(f"  {FIELD} moved to permlevel {PERMLEVEL}")

	# Custom DocPerm REPLACES the standard rows for a doctype rather than adding
	# to them, so the standard ones must exist as custom rows first.
	setup_custom_perms("Item")

	added = []
	for role, read, write in GRANTS:
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
		perm.read = read
		perm.write = write
		perm.insert(ignore_permissions=True)
		added.append(f"{role}(r={read},w={write})")

	frappe.db.commit()
	frappe.clear_cache()
	print(f"  level-{PERMLEVEL} grants added: {added or 'none (already present)'}")
