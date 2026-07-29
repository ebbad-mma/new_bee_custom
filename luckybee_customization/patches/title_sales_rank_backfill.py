import frappe

def execute():
    """
    Patch 1: Title and Sales Rank Backfill (Prompt 2c)
    Idempotently ensures title absorbs custom_amzon_item_name if present,
    or falls back to item_name if title is empty.
    """
    print("Executing Patch: title_sales_rank_backfill...")
    
    # 1. Update title from custom_amzon_item_name if custom_amzon_item_name is populated and title is empty
    if frappe.db.has_column("Item", "custom_amzon_item_name"):
        frappe.db.sql("""
            UPDATE `tabItem`
            SET title = custom_amzon_item_name
            WHERE (title IS NULL OR title = '' OR title = item_name)
              AND custom_amzon_item_name IS NOT NULL
              AND custom_amzon_item_name != ''
        """)

    # 2. Fallback title to item_name where title is still NULL or empty
    frappe.db.sql("""
        UPDATE `tabItem`
        SET title = item_name
        WHERE (title IS NULL OR title = '')
    """)

    frappe.db.commit()
    print("Patch title_sales_rank_backfill completed successfully.")
