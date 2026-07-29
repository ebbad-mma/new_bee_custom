import frappe
from luckybee_customization.jobs import refresh_velocity
from luckybee_customization.item_hooks import calculate_margins

def execute():
    """
    Patch 4: Bulk Margin & Velocity Backfill
    Executes initial catalog-wide velocity scoring job and recalculates margin fields
    for all stock items on Frappe Cloud setup.
    Idempotent: Safe to re-run; scoring and margin formulas produce deterministic results.
    """
    print("Executing Patch: bulk_margin_and_velocity_backfill...")

    # 1. Run Nightly Product Velocity Scoring Job
    refresh_velocity()

    # 2. Bulk Recalculate Margins across all Stock Items
    items = frappe.get_all("Item", filters={"is_stock_item": 1}, fields=["name", "last_purchase_rate", "custom_mrp", "valuation_rate", "last_price"])
    print(f"Recalculating margin fields for {len(items)} stock items...")

    updated_count = 0
    for idx, item in enumerate(items):
        calculate_margins(item)
        frappe.db.set_value("Item", item.name, {
            "lb_margin_pct": item.lb_margin_pct,
            "amz_delta_pct": item.amz_delta_pct,
            "mrp_discount_pct": item.mrp_discount_pct
        }, update_modified=False)
        updated_count += 1

        if (idx + 1) % 500 == 0:
            frappe.db.commit()

    frappe.db.commit()
    print(f"Patch bulk_margin_and_velocity_backfill completed successfully ({updated_count} items processed).")
