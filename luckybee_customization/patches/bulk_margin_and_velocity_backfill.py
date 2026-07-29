import os
import json
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
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

    # 0. Ensure ROW_FORMAT=DYNAMIC on tabItem to prevent MariaDB row size too large error (1118)
    try:
        frappe.db.sql("ALTER TABLE `tabItem` ROW_FORMAT=DYNAMIC;")
    except Exception as e:
        print(f"Notice: ALTER TABLE ROW_FORMAT=DYNAMIC: {e}")

    # 1. Add missing columns directly to DB table tabItem individually
    fields_to_add = [
        ("lb_units_30d", "Int"),
        ("lb_units_90d", "Int"),
        ("lb_units_180d", "Int"),
        ("lb_units_365d", "Int"),
        ("lb_days_cover", "Int"),
        ("lb_days_since_sale", "Int"),
        ("lb_days_since_receipt", "Int"),
        ("lb_stock_value", "Currency"),
        ("lb_sell_through", "Float"),
        ("lb_margin_pct", "Float"),
        ("amz_delta_pct", "Float"),
        ("mrp_discount_pct", "Float"),
        ("lb_velocity_band", "Data"),
        ("lb_data_status", "Data"),
        ("amz_data_status", "Data"),
        ("lb_sub_category", "Link"),
        ("lb_category_type", "Data"),
        ("lb_lot_ref", "Data"),
        ("custom_legacy_barcode", "Data"),
        ("lb_primary_image", "Text"),
        ("lb_mrp_confirmed", "Check"),
        ("amz_last_synced", "Date"),
        ("lb_received_captured_on", "Date")
    ]

    for fname, ftype in fields_to_add:
        if not frappe.db.has_column("Item", fname):
            try:
                frappe.db.add_column("Item", fname, ftype)
            except Exception as ex:
                print(f"Warning adding column {fname}: {ex}")

    frappe.db.commit()

    # 2. Ensure Custom Field DocType records exist for Desk forms UI
    try:
        fixture_path = frappe.get_app_path("luckybee_customization", "fixtures", "custom_field.json")
        if os.path.exists(fixture_path):
            with open(fixture_path, "r") as f:
                custom_fields_list = json.load(f)
            item_fields = [df for df in custom_fields_list if df.get("dt") == "Item"]
            if item_fields:
                create_custom_fields({"Item": item_fields}, ignore_validate=True)
                frappe.db.commit()
    except Exception as e:
        print(f"Warning in patch syncing custom fields: {e}")

    # 3. Run Nightly Product Velocity Scoring Job
    refresh_velocity()

    # 4. Bulk Recalculate Margins across all Stock Items
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
