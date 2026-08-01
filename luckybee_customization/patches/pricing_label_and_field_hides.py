import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

# A4.1 - "LB Actual Cost" was duplicated onto the standard last_purchase_rate
# field. lb_actual_cost (the computed cost used by the margin engine) keeps
# the name; last_purchase_rate reverts to its own label.
LABEL_FIXES = [
    ("last_purchase_rate", "Last Purchase Rate"),
]

# A5.3 - leftover field, siblings are already hidden.
# A3.3 - fields still wired into live code (WooCommerce sync, purchase-flow
# lookups, Keepa image sync) so they cannot be deleted like the dead fields
# in item_dead_field_cleanup.py, but they clutter the Item form and were
# never meant to be user-facing.
HIDE_FIELDS = [
    "custom_product_link_html",
    "woocommerce_id",
    "woocommerce_product_id",
    "sync_qty_with_woocommerce",
    "sync_with_woocommerce",
    "woocommerce_description",
    "stock_keeping_unit",
    "custom_ean",
    "custom_category_sub",
    "custom_last_supplier",
    "custom_last_supplier_purchase_rate",
    "custom_reviews_rating",
    "custom_reviews_count",
    "custom_new_current",
    "custom_stock_in_hand",
    "custom_product_url",
    "custom_image1",
    "custom_image2",
    "custom_image3",
    "custom_image4",
    "custom_image5",
]

def execute():
    print("Executing Patch: pricing_label_and_field_hides...")

    for fieldname, label in LABEL_FIXES:
        make_property_setter("Item", fieldname, "label", label, "Data")

    for fieldname in HIDE_FIELDS:
        make_property_setter("Item", fieldname, "hidden", "1", "Check")

    frappe.clear_cache(doctype="Item")
    frappe.db.commit()
    print(f"Patch pricing_label_and_field_hides completed successfully ({len(LABEL_FIXES)} label(s), {len(HIDE_FIELDS)} field(s) hidden).")
