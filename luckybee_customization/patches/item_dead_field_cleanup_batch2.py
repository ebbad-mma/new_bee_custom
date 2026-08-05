import frappe

# Second batch of the scope workbook's "3. Delete & Merge" list (31 fields).
# Batch 1 removed 8; the client then reclassified the four WooCommerce toggles
# to hide-not-delete, leaving 19. These 15 are the ones the reference check
# cleared - see the module docstring in item_dead_field_cleanup.py for batch 1.
#
# Held back deliberately (NOT in this list):
#   woocommerce_description, stock_keeping_unit
#       Shipped as woocommerceconnector fixtures, so deletion is undone on the
#       next migrate, and sync_products.py reads them (including raw SQL over
#       tabItem.woocommerce_description). Same "needed when the website goes
#       live" reasoning the client applied to the other WooCommerce fields.
#   custom_last_supplier, custom_last_supplier_purchase_rate
#       asin_purchase_invoice.py reads both via frappe.db.get_value, which
#       raises OperationalError 1054 once the column is gone. Removing that
#       block changes purchase-flow behaviour, so it needs its own change.
#   custom_url, custom_fsn_no, custom_box_number
#       REMOVED from this list. These three are on the project's never-touch
#       list - they are tied to the still-active Flipkart receiving flow, and
#       the standing instruction is not to delete, rename, repoint or hide
#       them. Deleting them here also dropped their columns, which destroys
#       the data outright; the fields then silently reappear because
#       woocommerceconnector ships them in its own fixtures and sync_fixtures
#       runs after patches, so the form looks correct afterwards while the
#       values are gone. Left in place deliberately - do not re-add.
DEAD_FIELDS = [
    "custom_product_url",
    "custom_category_sub",
    "custom_ean",                # dead twin of ean
    "custom_reviews_rating",     # dead twin of reviews_rating
    "custom_reviews_count",      # dead twin of reviews_count
    "custom_new_current",        # dead twin of new_current
    "custom_stock_in_hand",      # live qty lives in Bin
    "custom_image1",
    "custom_image2",
    "custom_image3",
    "custom_image4",
    "custom_image5",
]

def execute():
    print("Executing Patch: item_dead_field_cleanup_batch2...")

    deleted = 0
    for fieldname in DEAD_FIELDS:
        name = frappe.db.get_value("Custom Field", {"dt": "Item", "fieldname": fieldname})
        if not name:
            continue
        frappe.delete_doc("Custom Field", name, ignore_permissions=True)
        deleted += 1

    frappe.clear_cache(doctype="Item")
    frappe.db.commit()

    # Frappe never drops the underlying column on field deletion, so do it here
    # rather than leaving 15 orphaned columns behind.
    existing = set(frappe.db.get_table_columns("Item"))
    dropped = 0
    for fieldname in DEAD_FIELDS:
        if fieldname not in existing:
            continue
        if frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": fieldname}):
            continue
        frappe.db.sql(f"ALTER TABLE `tabItem` DROP COLUMN `{fieldname}`;")
        dropped += 1

    frappe.db.commit()
    print(f"Patch item_dead_field_cleanup_batch2 completed successfully "
          f"({deleted} fields deleted, {dropped} columns dropped).")
