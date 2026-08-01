import frappe

# A3.1 - dead/duplicate custom fields on Item. Each one was checked for:
#   - live code references anywhere under apps/ (none found beyond the
#     already-superseded field they duplicate)
#   - row counts (0-8 out of 8,017 items, i.e. leftover test/early data)
# Fields that ARE still referenced by working code (WooCommerce sync,
# purchase-flow lookups, the Keepa image writer) were hidden instead, in
# pricing_label_and_field_hides.py, rather than deleted here.
DEAD_FIELDS = [
    "article",
    "custom_fields",              # duplicate "Amazon Fields" Tab Break
    "custom_market_intelligence", # duplicate "Market Intelligence" Tab Break
    "old_barcode",
    "custom_test",
    "custom_list_price_highest",  # superseded by list_price_highest
    "custom_last_price",          # superseded by last_price
    "custom_category_root",       # superseded by category_root
    "custom_categories_tree",     # superseded by categories_tree
    "launchpad",
]

def execute():
    print("Executing Patch: item_dead_field_cleanup...")

    deleted_count = 0
    for fieldname in DEAD_FIELDS:
        name = frappe.db.get_value("Custom Field", {"dt": "Item", "fieldname": fieldname})
        if not name:
            continue
        frappe.delete_doc("Custom Field", name, ignore_permissions=True)
        deleted_count += 1

    frappe.clear_cache(doctype="Item")
    frappe.db.commit()
    print(f"Patch item_dead_field_cleanup completed successfully ({deleted_count} fields deleted).")
