import os
import csv
import frappe

def execute():
    print("Executing Patch: legacy_barcode_backfill...")

    app_path = frappe.get_app_path("luckybee_customization")
    csv_path = os.path.join(app_path, "data", "barcode_assignment.csv")

    if not os.path.exists(csv_path):
        print(f"Warning: {csv_path} not found. Skipping legacy_barcode_backfill patch.")
        return

    updated_count = 0
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 4:
                continue

            old_code = row[1].strip()
            lx_code = row[3].strip()

            if not lx_code.startswith("LX") or not old_code:
                continue

            item_code = frappe.db.get_value("Item", {"custom_barcode": lx_code}, "name")
            if not item_code:
                continue

            current_legacy = frappe.db.get_value("Item", item_code, "custom_legacy_barcode")
            if current_legacy != old_code:
                frappe.db.set_value("Item", item_code, "custom_legacy_barcode", old_code, update_modified=False)
                updated_count += 1

    frappe.db.commit()
    print(f"Patch legacy_barcode_backfill completed successfully ({updated_count} items updated).")
