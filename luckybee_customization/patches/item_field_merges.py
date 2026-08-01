import frappe

def execute():
    """
    A3.2 - complete the two pending merges. item_name is never read or
    written here (the merge is Amazon-into-Amazon only).
    """
    print("Executing Patch: item_field_merges...")

    # custom_amzon_item_name -> title. title_sales_rank_backfill already
    # copied it over everywhere title was previously blank; the remaining
    # 2,486 rows already carry the same text in both fields (custom_amzon_item_name
    # has mojibake encoding on a handful of rows, title has the clean version),
    # so there is nothing left to copy - just drop the now-redundant source field.
    if frappe.db.has_column("Item", "custom_amzon_item_name"):
        frappe.db.sql("""
            UPDATE `tabItem`
            SET title = custom_amzon_item_name
            WHERE (title IS NULL OR title = '')
              AND custom_amzon_item_name IS NOT NULL
              AND custom_amzon_item_name != ''
        """)
        frappe.db.commit()

        name = frappe.db.get_value("Custom Field", {"dt": "Item", "fieldname": "custom_amzon_item_name"})
        if name:
            frappe.delete_doc("Custom Field", name, ignore_permissions=True)

    # current_price -> sales_rank. Backfill the 137 items where sales_rank
    # was never populated but current_price was (same underlying Keepa value,
    # written by an older code path), then drop current_price.
    if frappe.db.has_column("Item", "current_price"):
        frappe.db.sql("""
            UPDATE `tabItem`
            SET sales_rank = current_price
            WHERE (sales_rank IS NULL OR sales_rank = '')
              AND current_price IS NOT NULL
              AND current_price != ''
        """)
        frappe.db.commit()

        name = frappe.db.get_value("Custom Field", {"dt": "Item", "fieldname": "current_price"})
        if name:
            frappe.delete_doc("Custom Field", name, ignore_permissions=True)

    frappe.clear_cache(doctype="Item")
    frappe.db.commit()
    print("Patch item_field_merges completed successfully.")
