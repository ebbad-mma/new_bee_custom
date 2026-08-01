import frappe
from luckybee_customization.receiving import recompute_status

def execute():
    print("Executing Patch: lb_data_status_backfill...")

    item_codes = frappe.get_all("Item", pluck="name")
    updated_count = 0

    for idx, item_code in enumerate(item_codes):
        doc = frappe.get_doc("Item", item_code)
        before = doc.lb_data_status
        recompute_status(doc)

        if doc.lb_data_status != before:
            frappe.db.set_value("Item", item_code, {
                "lb_data_status": doc.lb_data_status,
                "lb_received_captured_on": doc.lb_received_captured_on,
            }, update_modified=False)
            updated_count += 1

        if (idx + 1) % 500 == 0:
            frappe.db.commit()
            print(f"...{idx + 1}/{len(item_codes)} processed")

    frappe.db.commit()
    print(f"Patch lb_data_status_backfill completed successfully ({updated_count} items updated).")
