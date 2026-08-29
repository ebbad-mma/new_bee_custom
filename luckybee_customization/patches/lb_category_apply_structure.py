"""Create Ashish's category structure as Item Groups and file the catalogue into it.

The WooCommerce connector matches a product to its storefront category by the
Item Group NAME. Mizanur has already built all 86 categories in WooCommerce
exactly as the structure document specifies, so once ERPNext uses the same names
the sync lands correctly with no mapping table on either side.

Two things this deliberately does NOT do:

  * It does not touch custom_category or custom_sub_category. Those stay as the
    record of how an item was classified before, which is what makes this
    reversible - and they are still the input to resolve().
  * It does not save the Item documents. Item has a before_save chain that
    includes sync_keepa_item, so saving 8,000 items would fire 8,000 Keepa
    lookups: hours of work, thousands of tokens, and a rate-limit wall. This
    writes item_group with a bulk UPDATE instead. `modified` is left alone so
    the whole catalogue does not appear to have been edited today.

Items it cannot place keep the group they already have and are reported at the
end rather than being guessed into a category.
"""

import frappe

from luckybee_customization.category_taxonomy import HOLDING_GROUP, STRUCTURE, resolve

ROOT = "All Item Groups"
BATCH = 400


def _ensure_group(name, parent, is_group):
	"""Create the Item Group, or correct its parent if it already exists."""
	existing = frappe.db.get_value(
		"Item Group", name, ["name", "parent_item_group", "is_group"], as_dict=True
	)

	if not existing:
		doc = frappe.new_doc("Item Group")
		doc.item_group_name = name
		doc.parent_item_group = parent
		doc.is_group = is_group
		doc.insert(ignore_permissions=True)
		return "created"

	# A leaf that already has children cannot be flattened - leave it be and say so.
	has_children = frappe.db.exists("Item Group", {"parent_item_group": name})
	target_is_group = 1 if (is_group or has_children) else 0

	if existing.parent_item_group == parent and existing.is_group == target_is_group:
		return "ok"

	doc = frappe.get_doc("Item Group", name)
	doc.parent_item_group = parent
	doc.is_group = target_is_group
	doc.save(ignore_permissions=True)
	return "reparented"


def execute():
	print("Executing Patch: lb_category_apply_structure...")

	# --- 1. the structure itself ------------------------------------------
	counts = {"created": 0, "reparented": 0, "ok": 0}
	# Where Product Finder and the purchase-invoice import now send anything they
	# cannot classify, instead of dropping it into the root of the tree.
	counts[_ensure_group(HOLDING_GROUP, ROOT, is_group=0)] += 1
	for main in STRUCTURE:
		counts[_ensure_group(main, ROOT, is_group=1)] += 1
	for main, subs in STRUCTURE.items():
		for sub in subs:
			counts[_ensure_group(sub, main, is_group=0)] += 1
	frappe.db.commit()
	print(f"  item groups: {counts['created']} created, "
		  f"{counts['reparented']} reparented, {counts['ok']} already correct")

	# --- 2. file the catalogue into it ------------------------------------
	items = frappe.get_all(
		"Item",
		fields=["name", "item_group", "custom_category", "custom_sub_category"],
	)

	by_target, unresolved = {}, []
	for item in items:
		target = resolve(item.custom_category, item.custom_sub_category)
		if not target:
			unresolved.append(item)
			continue
		if item.item_group == target:
			continue
		by_target.setdefault(target, []).append(item.name)

	moved = 0
	for target, names in by_target.items():
		for i in range(0, len(names), BATCH):
			chunk = names[i : i + BATCH]
			placeholders = ", ".join(["%s"] * len(chunk))
			frappe.db.sql(
				f"UPDATE `tabItem` SET item_group = %s WHERE name IN ({placeholders})",
				[target, *chunk],
			)
			moved += len(chunk)
		frappe.db.commit()

	print(f"  items refiled: {moved} into {len(by_target)} categories")
	print(f"  left as they were (could not be decided): {len(unresolved)}")

	frappe.clear_cache()
