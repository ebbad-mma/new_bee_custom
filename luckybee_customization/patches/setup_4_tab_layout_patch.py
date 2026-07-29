import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def execute():
    """
    Patch 5: Setup 4-Tab Item Layout Structure
    Reorganizes the Item doctype form into 4 distinct tabs:
    1. Details
    2. Pricing & Margin
    3. Market Intelligence
    4. Inventory & Operations
    """
    print("Executing Patch: setup_4_tab_layout_patch...")

    # Ensure Tab Break fields exist and have correct labels
    tab_configs = [
        ("details", "1. Details"),
        ("custom_pricing_margin_tab", "2. Pricing & Margin"),
        ("custom_market_intelligence_tab", "3. Market Intelligence"),
        ("custom_inventory_operations_tab", "4. Inventory & Operations")
    ]

    for fieldname, label in tab_configs:
        if frappe.db.exists("DocField", {"parent": "Item", "fieldname": fieldname}):
            make_property_setter("Item", fieldname, "label", label, "Data", validate_fields_for_doctype=False)
        elif frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": fieldname}):
            frappe.db.set_value("Custom Field", {"dt": "Item", "fieldname": fieldname}, "label", label)

    frappe.db.commit()
    print("Patch setup_4_tab_layout_patch completed successfully.")
