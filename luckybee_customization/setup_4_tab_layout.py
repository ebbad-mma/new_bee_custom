import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def execute():
    """
    Sets up the exact 4-tab Item form structure:
    Tab 1: Details
    Tab 2: Pricing & Margin
    Tab 3: Market Intelligence
    Tab 4: Inventory & Operations
    """
    print("Setting up 4-tab Item form structure...")

    # Hide extra standard/custom tabs that are not part of the 4-tab structure
    hidden_tabs = [
        "keepa_description_feature",
        "custom_amazon_fields",
        "custom_item_images",
        "inventory_section",
        "variants_section",
        "accounting",
        "uom_tab",
        "purchasing_tab",
        "sales_details",
        "item_tax_section_break",
        "quality_tab",
        "manufacturing",
    ]

    for tab_name in hidden_tabs:
        if frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": tab_name}):
            frappe.db.set_value("Custom Field", {"dt": "Item", "fieldname": tab_name}, "hidden", 1)
        elif frappe.db.exists("DocField", {"parent": "Item", "fieldname": tab_name}):
            make_property_setter("Item", tab_name, "hidden", 1, "Check", validate_fields_for_doctype=False)

    frappe.db.commit()
    print("4-tab layout setup completed successfully.")

if __name__ == "__main__":
    frappe.connect()
    execute()
