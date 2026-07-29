import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def execute():
    """
    Patch 5: Setup 4-Tab Item Layout Structure
    Configures exact 4 tabs:
    1. Details
    2. Pricing & Margin
    3. Market Intelligence
    4. Inventory & Operations
    Hides all other standard and custom tab breaks.
    """
    print("Executing Patch: setup_4_tab_layout_patch...")

    primary_tabs = {
        "details": "1. Details",
        "pricing_tab": "2. Pricing & Margin",
        "keepa_description_feature": "3. Market Intelligence",
        "inventory_section": "4. Inventory & Operations"
    }

    for fieldname, label in primary_tabs.items():
        make_property_setter("Item", fieldname, "label", label, "Data", validate_fields_for_doctype=False)
        make_property_setter("Item", fieldname, "hidden", 0, "Check", validate_fields_for_doctype=False)

    tabs_to_hide = [
        "custom_amazon_fields",
        "custom_item_images",
        "dashboard_tab",
        "variants_section",
        "accounting",
        "uom_tab",
        "purchasing_tab",
        "sales_details",
        "item_tax_section_break",
        "quality_tab",
        "manufacturing",
        "custom_supplier_history_tab"
    ]

    for fieldname in tabs_to_hide:
        make_property_setter("Item", fieldname, "hidden", 1, "Check", validate_fields_for_doctype=False)

    frappe.db.commit()
    print("Patch setup_4_tab_layout_patch completed successfully.")
