import frappe

# Custom Field docs for these were already removed by item_dead_field_cleanup
# and item_field_merges. Frappe's schema sync only adds/alters columns, it
# never drops them, so the now-meaningless columns are still sitting in
# tabItem. Drop them for real now that both patches have run and their data
# has been copied out or confirmed dead.
ORPHANED_COLUMNS = [
    "article", "custom_fields", "custom_market_intelligence", "old_barcode",
    "custom_test", "custom_list_price_highest", "custom_last_price",
    "custom_category_root", "custom_categories_tree", "launchpad",
    "custom_amzon_item_name", "current_price",
]

def execute():
    print("Executing Patch: drop_orphaned_merge_and_dead_columns...")

    existing_cols = set(frappe.db.get_table_columns("Item"))
    dropped = 0
    for col in ORPHANED_COLUMNS:
        if col not in existing_cols:
            continue
        if frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": col}):
            # Still a live field somewhere - leave it alone.
            continue
        frappe.db.sql(f"ALTER TABLE `tabItem` DROP COLUMN `{col}`;")
        dropped += 1

    frappe.db.commit()
    print(f"Patch drop_orphaned_merge_and_dead_columns completed successfully ({dropped} columns dropped).")
