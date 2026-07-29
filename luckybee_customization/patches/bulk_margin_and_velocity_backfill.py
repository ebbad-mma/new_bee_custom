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
        frappe.db.sql("ALTER TABLE `tabItem` ROW_FORMAT=DYNAMIC ENGINE=InnoDB;")
    except Exception as e:
        print(f"Notice: ALTER TABLE ROW_FORMAT=DYNAMIC: {e}")

    # 1. Add missing columns directly to DB table tabItem individually via raw SQL
    existing_columns = frappe.db.get_table_columns("Item") or []

    fields_to_add_sql = [
        ("lb_units_30d", "int(11) NOT NULL DEFAULT 0"),
        ("lb_units_90d", "int(11) NOT NULL DEFAULT 0"),
        ("lb_units_180d", "int(11) NOT NULL DEFAULT 0"),
        ("lb_units_365d", "int(11) NOT NULL DEFAULT 0"),
        ("lb_days_cover", "int(11) DEFAULT NULL"),
        ("lb_days_since_sale", "int(11) DEFAULT NULL"),
        ("lb_days_since_receipt", "int(11) DEFAULT NULL"),
        ("lb_stock_value", "decimal(21,9) NOT NULL DEFAULT 0.0"),
        ("lb_sell_through", "decimal(21,9) DEFAULT NULL"),
        ("lb_margin_pct", "decimal(21,9) DEFAULT NULL"),
        ("amz_delta_pct", "decimal(21,9) DEFAULT NULL"),
        ("mrp_discount_pct", "decimal(21,9) DEFAULT NULL"),
        ("lb_velocity_band", "varchar(40) DEFAULT NULL"),
        ("lb_data_status", "varchar(40) DEFAULT NULL"),
        ("amz_data_status", "varchar(40) DEFAULT NULL"),
        ("lb_sub_category", "varchar(40) DEFAULT NULL"),
        ("lb_category_type", "varchar(40) DEFAULT NULL"),
        ("lb_lot_ref", "varchar(40) DEFAULT NULL"),
        ("custom_legacy_barcode", "varchar(40) DEFAULT NULL"),
        ("lb_primary_image", "text DEFAULT NULL"),
        ("lb_mrp_confirmed", "tinyint(4) NOT NULL DEFAULT 0"),
        ("amz_last_synced", "date DEFAULT NULL"),
        ("lb_received_captured_on", "date DEFAULT NULL")
    ]

    for fname, fsql in fields_to_add_sql:
        if fname not in existing_columns:
            try:
                frappe.db.sql(f"ALTER TABLE `tabItem` ADD COLUMN `{fname}` {fsql};")
            except Exception as ex:
                print(f"Warning adding column {fname} via SQL: {ex}")

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
        print(f"Notice: Syncing custom fields: {e}")

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
