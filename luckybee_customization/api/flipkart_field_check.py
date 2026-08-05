"""One-off diagnostic: did the Flipkart fields survive the deploy?

patches/item_dead_field_cleanup_batch2 used to list custom_url, custom_fsn_no
and custom_box_number for deletion. Deleting a Custom Field also dropped its
column, which destroys the stored values - and because woocommerceconnector
ships all three in its own fixtures, and sync_fixtures() runs after patches
during migrate, the fields reappear immediately afterwards. The form therefore
looks correct while the data is gone, which is exactly the failure mode that is
easy to miss.

Run on production to see the current state:

    bench --site <site> execute \
        luckybee_customization.api.flipkart_field_check.check_flipkart_fields

Then run the same thing against a restore of the pre-deploy backup and compare
the populated counts. If the backup has values and production reads 0, the data
needs restoring from that backup - column by column, not a whole-database
rollback, which would discard everything else done since.
"""

import frappe

PROTECTED = ["custom_url", "custom_fsn_no", "custom_box_number"]


@frappe.whitelist()
def check_flipkart_fields():
	meta = frappe.get_meta("Item")
	columns = set(frappe.db.get_table_columns("Item"))

	out = {"total_items": frappe.db.count("Item"), "fields": {}}

	for fieldname in PROTECTED:
		info = {
			"field_defined": bool(meta.get_field(fieldname)),
			"column_exists": fieldname in columns,
			"populated": None,
		}
		if info["column_exists"]:
			info["populated"] = frappe.db.sql(
				f"SELECT COUNT(*) FROM `tabItem` WHERE IFNULL(`{fieldname}`, '') != ''"
			)[0][0]
		out["fields"][fieldname] = info

	# Item Details carries the Flipkart side too - worth seeing alongside.
	if frappe.db.exists("DocType", "Item Details"):
		id_columns = set(frappe.db.get_table_columns("Item Details"))
		out["item_details"] = {
			f: (frappe.db.sql(
				f"SELECT COUNT(*) FROM `tabItem Details` WHERE IFNULL(`{f}`, '') != ''"
			)[0][0] if f in id_columns else "column missing")
			for f in ("fsn_no", "url", "flipkart_item_url", "title_flipkart")
		}

	out["patch_ran"] = bool(frappe.db.exists(
		"Patch Log", {"patch": ["like", "%item_dead_field_cleanup_batch2%"]}))

	return out
