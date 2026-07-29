import os
import csv
import frappe

def execute():
    """
    Patch 2: Barcode Migration & Child Table Append (Prompt 3)
    Reads bundled barcode_assignment.csv, sets custom_barcode to LX code,
    and appends LX code to Item Barcode child table if missing.
    Idempotent: Skips if item already has target LX code / barcode row.
    """
    print("Executing Patch: barcode_migration...")
    
    app_path = frappe.get_app_path("luckybee_customization")
    csv_path = os.path.join(app_path, "data", "barcode_assignment.csv")
    
    if not os.path.exists(csv_path):
        print(f"Warning: {csv_path} not found. Skipping barcode_migration patch.")
        return

    updated_count = 0
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 4:
                continue
            
            # Format: STATUS, OLD_CODE, ITEM_NAME, LX_CODE, ...
            old_code = row[1].strip()
            lx_code = row[3].strip()

            if not lx_code.startswith("LX"):
                continue

            # Identify target item in DB (could be old_code or lx_code)
            item_code = frappe.db.get_value("Item", {"name": old_code}, "name") or frappe.db.get_value("Item", {"custom_barcode": lx_code}, "name")
            
            if not item_code:
                continue

            # 1. Update custom_barcode idempotently
            current_cb = frappe.db.get_value("Item", item_code, "custom_barcode")
            if current_cb != lx_code:
                frappe.db.set_value("Item", item_code, "custom_barcode", lx_code, update_modified=False)
                updated_count += 1

            # 2. Append LX barcode to Item Barcode child table if missing
            exists = frappe.db.exists("Item Barcode", {"parent": item_code, "barcode": lx_code})
            if not exists:
                b_doc = frappe.get_doc({
                    "doctype": "Item Barcode",
                    "parent": item_code,
                    "parentfield": "barcodes",
                    "parenttype": "Item",
                    "barcode": lx_code
                })
                b_doc.insert(ignore_permissions=True)

    frappe.db.commit()
    print(f"Patch barcode_migration completed successfully ({updated_count} items updated).")
