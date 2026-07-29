import frappe
from luckybee_customization.jobs import refresh_velocity
from luckybee_customization.item_hooks import calculate_margins

# Map of our custom field names to their correct varchar lengths
FIELD_LENGTHS = {
    "custom_fsn_no": 30,
    "custom_box_number": 30,
    "custom_item_detail": 50,
    "custom_asin_no": 30,
    "custom_barcode": 30,
    "custom_luckybee_brand": 40,
    "custom_group": 40,
    "lb_category_type": 30,
    "lb_sub_category": 40,
    "custom_legacy_barcode": 30,
    "lb_data_status": 40,
    "lb_velocity_band": 30,
    "lb_lot_ref": 40,
    "amz_data_status": 40,
}

def execute():
    """
    Patch 4: Bulk Margin & Velocity Backfill
    - Fixes MariaDB row-size-too-large (1118) by shrinking varchar columns
    - Adds missing velocity/margin columns individually
    - Updates Custom Field records so sync_all does not re-expand them
    - Runs velocity scoring and margin calculation
    """
    print("Executing Patch: bulk_margin_and_velocity_backfill...")

    # ── Step 0: Set ROW_FORMAT=DYNAMIC on tabItem ──────────────────────
    try:
        frappe.db.sql("ALTER TABLE `tabItem` ROW_FORMAT=DYNAMIC;")
    except Exception as e:
        print(f"Notice (ROW_FORMAT): {e}")

    # ── Step 1: Shrink existing oversized varchar columns in tabItem ───
    existing_cols = frappe.db.get_table_columns("Item") or []
    for col, length in FIELD_LENGTHS.items():
        if col in existing_cols:
            try:
                frappe.db.sql(f"ALTER TABLE `tabItem` MODIFY `{col}` varchar({length});")
            except Exception as ex:
                print(f"Notice (shrink {col}): {ex}")

    # ── Step 2: Update Custom Field records in DB to match lengths ─────
    #    This prevents sync_all -> updatedb from generating
    #    MODIFY varchar(140) queries that blow the 65535 row limit.
    for fieldname, length in FIELD_LENGTHS.items():
        frappe.db.sql(
            "UPDATE `tabCustom Field` SET `length` = %s "
            "WHERE `dt` = 'Item' AND `fieldname` = %s AND (`length` = 0 OR `length` IS NULL)",
            (length, fieldname)
        )

    frappe.db.commit()

    # ── Step 3: Add missing velocity/margin columns individually ───────
    new_columns = [
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
        ("lb_velocity_band", "varchar(30) DEFAULT NULL"),
        ("lb_data_status", "varchar(40) DEFAULT NULL"),
        ("amz_data_status", "varchar(40) DEFAULT NULL"),
        ("lb_sub_category", "varchar(40) DEFAULT NULL"),
        ("lb_category_type", "varchar(30) DEFAULT NULL"),
        ("lb_lot_ref", "varchar(40) DEFAULT NULL"),
        ("custom_legacy_barcode", "varchar(30) DEFAULT NULL"),
        ("lb_primary_image", "text DEFAULT NULL"),
        ("lb_mrp_confirmed", "tinyint(4) NOT NULL DEFAULT 0"),
        ("amz_last_synced", "date DEFAULT NULL"),
        ("lb_received_captured_on", "date DEFAULT NULL"),
    ]

    for fname, fsql in new_columns:
        if fname not in existing_cols:
            try:
                frappe.db.sql(f"ALTER TABLE `tabItem` ADD COLUMN `{fname}` {fsql};")
            except Exception as ex:
                print(f"Notice (add {fname}): {ex}")

    frappe.db.commit()

    # ── Step 4: Run velocity scoring ───────────────────────────────────
    refresh_velocity()

    # ── Step 5: Bulk recalculate margins ───────────────────────────────
    items = frappe.get_all(
        "Item", filters={"is_stock_item": 1},
        fields=["name", "last_purchase_rate", "custom_mrp", "valuation_rate", "last_price"],
    )
    print(f"Recalculating margin fields for {len(items)} stock items...")

    updated_count = 0
    for idx, item in enumerate(items):
        calculate_margins(item)
        frappe.db.set_value("Item", item.name, {
            "lb_margin_pct": item.lb_margin_pct,
            "amz_delta_pct": item.amz_delta_pct,
            "mrp_discount_pct": item.mrp_discount_pct,
        }, update_modified=False)
        updated_count += 1
        if (idx + 1) % 500 == 0:
            frappe.db.commit()

    frappe.db.commit()
    print(f"Patch bulk_margin_and_velocity_backfill completed successfully ({updated_count} items processed).")
