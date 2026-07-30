import frappe

def execute():
    """
    Patch 5: Setup 4-Tab Item Layout Structure & lb_actual_cost Field
    - Adds stored field lb_actual_cost
    - Configures 4 primary tabs plus the native Connections tab
    - Hides all other 12 standard and custom tab breaks
    - Establishes named section breaks and collapse/hidden states
    """
    print("Executing Patch: setup_4_tab_layout_patch...")

    # 0. Ensure lb_actual_cost column exists in tabItem
    existing_cols = frappe.db.get_table_columns("Item") or []
    if "lb_actual_cost" not in existing_cols:
        try:
            frappe.db.sql("ALTER TABLE `tabItem` ADD COLUMN `lb_actual_cost` decimal(21,9) DEFAULT NULL;")
        except Exception as e:
            print(f"Notice adding lb_actual_cost: {e}")

    # 1. Update primary tabs in DB
    primary_tabs = {
        "details": "1. Details",
        "pricing_tab": "2. Pricing & Margin",
        "keepa_description_feature": "3. Market Intelligence",
        "inventory_section": "4. Inventory & Operations"
    }

    for fname, label in primary_tabs.items():
        frappe.db.sql("UPDATE `tabDocField` SET `label`=%s, `hidden`=0 WHERE `parent`='Item' AND `fieldname`=%s", (label, fname))
        frappe.db.sql("UPDATE `tabCustom Field` SET `label`=%s, `hidden`=0 WHERE `dt`='Item' AND `fieldname`=%s", (label, fname))

    # 2. Hide extra tabs in DB
    tabs_to_hide = [
        "custom_amazon_fields",
        "custom_item_images",
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

    for fname in tabs_to_hide:
        frappe.db.sql("UPDATE `tabDocField` SET `hidden`=1 WHERE `parent`='Item' AND `fieldname`=%s", (fname,))
        frappe.db.sql("UPDATE `tabCustom Field` SET `hidden`=1 WHERE `dt`='Item' AND `fieldname`=%s", (fname,))

    # 3. Create or update Section Break custom fields
    section_breaks = [
        ("sec_performance", "Performance", "details", 1, 0),
        ("sec_identity", "Identity", "sec_performance", 0, 0),
        ("sec_classification", "Classification", "sec_identity", 0, 0),
        ("sec_identifiers", "Identifiers", "sec_classification", 0, 0),
        ("sec_product_images", "Product Images", "sec_identifiers", 0, 0),
        ("sec_receiving_capture", "Receiving Capture", "sec_product_images", 0, 0),

        ("sec_live_prices", "Live Prices", "pricing_tab", 0, 0),
        ("sec_cost_mrp", "Cost & MRP", "sec_live_prices", 0, 0),
        ("sec_computed_margins", "Computed Margins", "sec_cost_mrp", 0, 0),
        ("sec_quality_signal", "Quality Signal", "sec_computed_margins", 0, 0),
        ("sec_amazon_benchmark", "Amazon Benchmark", "sec_quality_signal", 1, 0),
        ("sec_supplier_history", "Supplier History", "sec_amazon_benchmark", 1, 0),

        ("sec_data_status", "Data Status", "keepa_description_feature", 0, 0),
        ("sec_demand", "Demand", "sec_data_status", 0, 0),
        ("sec_listing_content", "Listing Content", "sec_demand", 0, 0),
        ("sec_categories_keywords", "Categories & Keywords", "sec_listing_content", 0, 0),
        ("sec_attributes", "Attributes", "sec_categories_keywords", 0, 0),
        ("sec_competitive_codes", "Competitive / Codes", "sec_attributes", 1, 0),

        ("sec_stock", "Stock", "inventory_section", 0, 0),
        ("sec_child_tables", "Child Tables", "sec_stock", 0, 0),
        ("sec_buying_selling", "Buying / Selling", "sec_child_tables", 1, 0),
        ("sec_dimensions", "Dimensions", "sec_buying_selling", 1, 0),
        ("sec_tax_accounts", "Tax & Accounts", "sec_dimensions", 1, 0),
        ("sec_hidden_legacy", "Hidden Legacy", "sec_tax_accounts", 0, 1),
    ]

    for fname, label, insert_after, collapsible, hidden in section_breaks:
        if not frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": fname}):
            try:
                cf = frappe.new_doc("Custom Field")
                cf.dt = "Item"
                cf.fieldname = fname
                cf.label = label
                cf.fieldtype = "Section Break"
                cf.insert_after = insert_after
                cf.collapsible = collapsible
                cf.hidden = hidden
                cf.insert(ignore_permissions=True)
            except Exception as e:
                print(f"Notice inserting section {fname}: {e}")
        else:
            frappe.db.sql(
                "UPDATE `tabCustom Field` SET `label`=%s, `insert_after`=%s, `collapsible`=%s, `hidden`=%s WHERE `dt`='Item' AND `fieldname`=%s",
                (label, insert_after, collapsible, hidden, fname)
            )

    frappe.db.commit()
    frappe.clear_cache(doctype="Item")
    print("Patch setup_4_tab_layout_patch completed successfully.")
