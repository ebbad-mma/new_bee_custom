import frappe

def execute():
    """
    Patch 3: MRP-as-Cost Cleanup & Selling Rate Sync (Prompt 5)
    1. Removes invalid Standard Buying Item Price records where buying price equals MRP.
    2. Syncs Item standard_rate with active Standard Selling Item Price rate.
    Idempotent: Only acts on records matching the criteria.
    """
    print("Executing Patch: mrp_as_cost_and_selling_rate_sync...")

    # 1. Clean up invalid Standard Buying Item Prices where rate == custom_mrp
    invalid_buying = frappe.db.sql("""
        SELECT ip.name, ip.item_code
        FROM `tabItem Price` ip
        JOIN `tabItem` it ON ip.item_code = it.name
        WHERE ip.price_list = 'Standard Buying'
          AND it.custom_mrp IS NOT NULL
          AND it.custom_mrp > 0
          AND ABS(ip.price_list_rate - it.custom_mrp) < 0.01
    """, as_dict=True)

    cleaned_buying = 0
    for row in invalid_buying:
        frappe.delete_doc("Item Price", row.name, force=True)
        cleaned_buying += 1

    print(f"  Cleaned up {cleaned_buying} invalid MRP-as-cost Standard Buying prices.")

    # 2. Sync standard_rate with Standard Selling Item Price
    selling_rates = frappe.db.sql("""
        SELECT ip.item_code, ip.price_list_rate
        FROM `tabItem Price` ip
        WHERE ip.price_list = 'Standard Selling' AND ip.price_list_rate > 0
        ORDER BY ip.valid_from DESC
    """, as_dict=True)

    # De-duplicate to get latest rate per item
    rate_map = {}
    for r in selling_rates:
        if r.item_code not in rate_map:
            rate_map[r.item_code] = float(r.price_list_rate)

    synced_count = 0
    for item_code, rate in rate_map.items():
        curr_rate = frappe.db.get_value("Item", item_code, "standard_rate")
        if curr_rate is None or abs(float(curr_rate) - rate) > 0.01:
            frappe.db.set_value("Item", item_code, "standard_rate", rate, update_modified=False)
            synced_count += 1

    frappe.db.commit()
    print(f"Patch mrp_as_cost_and_selling_rate_sync completed successfully ({synced_count} items synced).")
