import frappe
from frappe.utils import today

def flag_items(doc, method=None):
    """
    Hooked on Purchase Receipt on_submit.
    Flags received items as needing receiving capture.
    """
    if not doc.items:
        return

    for row in doc.items:
        if not row.item_code:
            continue
        frappe.db.set_value("Item", row.item_code, "lb_data_status", "Needs Receiving Capture")

    frappe.db.commit()

def recompute_status(doc, method=None):
    """
    Hooked on Item before_save.
    Recomputes lb_data_status based on completeness of receiving essentials.
    """
    essentials_met = all([
        bool(doc.get("lb_images")) and bool(doc.lb_primary_image),
        bool(doc.lb_mrp_confirmed),
        any(b for b in doc.get("barcodes", []) if b.barcode),
        any(b for b in doc.get("barcodes", []) if getattr(b, "type", None) == "Supplier" or getattr(b, "barcode_type", None) == "Supplier"),
        bool(doc.custom_luckybee_brand),
        bool(doc.lb_category_type),
        bool(doc.lb_lot_ref),
    ])

    if essentials_met:
        doc.lb_data_status = "Complete"
        if not doc.lb_received_captured_on:
            doc.lb_received_captured_on = today()
    elif doc.lb_data_status != "Needs Receiving Capture":
        doc.lb_data_status = "Partial"
