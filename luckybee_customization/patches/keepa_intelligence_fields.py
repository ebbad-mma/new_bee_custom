import frappe

# B1/B2/C1 - new Item fields for the Keepa expansion, placed per Part C's
# tab/section table. field() creates-or-updates so this patch is safe to
# extend later.
def field(dt, fieldname, insert_after, **kwargs):
    name = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": fieldname})
    if name:
        doc = frappe.get_doc("Custom Field", name)
    else:
        doc = frappe.new_doc("Custom Field")
        doc.dt = dt
        doc.fieldname = fieldname
        doc.insert_after = insert_after
    doc.update(kwargs)
    doc.module = "luckybee_customization"
    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)
    return doc.name

def execute():
    print("Executing Patch: keepa_intelligence_fields...")

    # Tab 2 Pricing & Margin - Amazon Benchmark, current (visible)
    field("Item", "sec_amz_benchmark_current", "mrp_discount_pct",
          fieldtype="Section Break", label="Amazon Benchmark - Current")
    field("Item", "amz_best_price", "sec_amz_benchmark_current",
          fieldtype="Currency", label="AMZ Best Price")
    field("Item", "column_break_amz_benchmark_current", "amz_best_price",
          fieldtype="Column Break")
    field("Item", "amz_best_price_source", "column_break_amz_benchmark_current",
          fieldtype="Select", label="AMZ Best Price Source",
          options="\nBuy Box: Current\nNew: Current\nBuy Box: 30 days avg.\nNew: 30 days avg.\nNew: 90 days avg.\nNew: 180 days avg.\nList Price: Current")

    # Tab 2 Pricing & Margin - Amazon Benchmark, history (collapsed)
    field("Item", "sec_amz_benchmark_history", "amz_best_price_source",
          fieldtype="Section Break", label="Amazon Benchmark - History", collapsible=1)
    field("Item", "amz_buybox_current", "sec_amz_benchmark_history",
          fieldtype="Currency", label="AMZ Buy Box Current")
    field("Item", "amz_buybox_30d", "amz_buybox_current",
          fieldtype="Currency", label="AMZ Buy Box 30d Avg")
    field("Item", "column_break_amz_benchmark_history", "amz_buybox_30d",
          fieldtype="Column Break")
    field("Item", "amz_price_drop_30d", "column_break_amz_benchmark_history",
          fieldtype="Percent", label="AMZ Price Drop 30d")

    # Tab 3 Market Intelligence - Categories & Keywords
    field("Item", "sec_categories_keywords", "product_category",
          fieldtype="Section Break", label="Categories & Keywords")
    field("Item", "amz_search_keywords", "sec_categories_keywords",
          fieldtype="Small Text", label="AMZ Search Keywords")

    # Tab 3 Market Intelligence - Demand Signals
    field("Item", "sec_demand_signals", "sales_rank_sub",
          fieldtype="Section Break", label="Demand Signals")
    field("Item", "amz_monthly_sold", "sec_demand_signals",
          fieldtype="Int", label="AMZ Monthly Sold")
    field("Item", "column_break_demand_signals", "amz_monthly_sold",
          fieldtype="Column Break")
    field("Item", "amz_monthly_sold_date", "column_break_demand_signals",
          fieldtype="Date", label="AMZ Monthly Sold Date")

    frappe.clear_cache(doctype="Item")
    frappe.db.commit()
    print("Patch keepa_intelligence_fields completed successfully.")
