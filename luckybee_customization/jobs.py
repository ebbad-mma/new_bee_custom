import frappe
from frappe.utils import today, add_days, getdate
from luckybee_customization.item_hooks import true_cost

def classify(days_cover, days_since_sale_val, u365, stock, total_sales_ever, total_receipts_ever):
    has_receipt = (total_receipts_ever > 0) or (stock > 0)
    has_zero_sales = (total_sales_ever == 0)

    # Never Sold: item has stock received (or stock > 0) but zero sales ever
    if has_zero_sales and has_receipt:
        return "Never Sold"

    # Dead: days_cover > 365 OR no sale in the last 180 days
    if (days_cover is not None and days_cover > 365) or (days_since_sale_val is not None and days_since_sale_val > 180):
        return "Dead"

    # Days cover classification
    if days_cover is not None:
        if days_cover < 30:
            return "Fast"
        elif 30 <= days_cover <= 90:
            return "Healthy"
        elif 90 < days_cover <= 365:
            return "Slow"

    # Fallback for sold items with 0 stock (where cover is None because stock = 0)
    if days_since_sale_val is not None and days_since_sale_val <= 180:
        return "Fast"

    return "Dead"

def refresh_velocity():
    print("=" * 60)
    print("STARTING NIGHTLY PRODUCT-VELOCITY SCORING JOB")
    print("=" * 60)

    today_date = getdate(today())

    dt_30 = add_days(today_date, -30)
    dt_90 = add_days(today_date, -90)
    dt_180 = add_days(today_date, -180)
    dt_365 = add_days(today_date, -365)

    print("Pre-fetching bulk metrics across database...")

    # 1. Stock Map (sum actual_qty from Bin)
    stock_res = frappe.db.sql("""
        SELECT item_code, SUM(actual_qty)
        FROM `tabBin`
        GROUP BY item_code
    """)
    stock_map = {r[0]: float(r[1] or 0.0) for r in stock_res}

    # 2. Units Sold Map (30d, 90d, 180d, 365d, total_ever)
    def get_sales_map(from_date=None):
        if from_date:
            res = frappe.db.sql("""
                SELECT sii.item_code, SUM(sii.qty)
                FROM `tabSales Invoice Item` sii
                JOIN `tabSales Invoice` si ON sii.parent = si.name
                WHERE sii.docstatus = 1 AND si.posting_date >= %s
                GROUP BY sii.item_code
            """, from_date)
        else:
            res = frappe.db.sql("""
                SELECT sii.item_code, SUM(sii.qty)
                FROM `tabSales Invoice Item` sii
                WHERE sii.docstatus = 1
                GROUP BY sii.item_code
            """)
        return {r[0]: float(r[1] or 0.0) for r in res}

    u30_map = get_sales_map(dt_30)
    u90_map = get_sales_map(dt_90)
    u180_map = get_sales_map(dt_180)
    u365_map = get_sales_map(dt_365)
    total_sales_map = get_sales_map(None)

    # 3. Total Receipts Ever Map (from Stock Ledger Entry)
    receipts_res = frappe.db.sql("""
        SELECT item_code, SUM(actual_qty)
        FROM `tabStock Ledger Entry`
        WHERE actual_qty > 0
        GROUP BY item_code
    """)
    total_receipts_map = {r[0]: float(r[1] or 0.0) for r in receipts_res}

    # 4. Last Sale Date Map
    last_sale_res = frappe.db.sql("""
        SELECT sii.item_code, MAX(si.posting_date)
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON sii.parent = si.name
        WHERE sii.docstatus = 1
        GROUP BY sii.item_code
    """)
    last_sale_map = {r[0]: getdate(r[1]) for r in last_sale_res if r[1]}

    # 5. First Receipt Date Map
    first_receipt_res = frappe.db.sql("""
        SELECT item_code, MIN(posting_date)
        FROM `tabStock Ledger Entry`
        WHERE actual_qty > 0
        GROUP BY item_code
    """)
    first_receipt_map = {r[0]: getdate(r[1]) for r in first_receipt_res if r[1]}

    print("Pre-fetching complete. Processing items...")

    items = frappe.get_all("Item", filters={"is_stock_item": 1}, fields=["name", "last_purchase_rate", "custom_mrp", "valuation_rate"])
    print(f"Total stock items to score: {len(items)}")

    updated_count = 0

    for idx, item in enumerate(items):
        it = item.name

        u30 = u30_map.get(it, 0.0)
        u90 = u90_map.get(it, 0.0)
        u180 = u180_map.get(it, 0.0)
        u365 = u365_map.get(it, 0.0)
        stock = stock_map.get(it, 0.0)

        total_sales_ever = total_sales_map.get(it, 0.0)
        total_receipts_ever = total_receipts_map.get(it, 0.0)

        # Days Cover = stock / (u90 / 90.0), or fallback to u365 if u90 == 0
        if u90 > 0:
            daily_run_rate = u90 / 90.0
            cover = round(stock / daily_run_rate, 2)
        elif u365 > 0:
            daily_run_rate = u365 / 365.0
            cover = round(stock / daily_run_rate, 2)
        else:
            cover = None

        # Days since sale
        last_sale_dt = last_sale_map.get(it)
        days_since_sale = (today_date - last_sale_dt).days if last_sale_dt else None

        # Days since receipt
        first_receipt_dt = first_receipt_map.get(it)
        days_since_receipt = (today_date - first_receipt_dt).days if first_receipt_dt else None

        # Sell-Through = total_sales_ever / total_receipts_ever * 100
        if total_receipts_ever > 0:
            sell_through_val = round((total_sales_ever / total_receipts_ever) * 100.0, 2)
        else:
            sell_through_val = None

        # Valuation & Stock Value
        cost = true_cost(item) or float(item.valuation_rate or 0.0)
        stock_val = round(stock * cost, 2)

        # Band
        band = classify(cover, days_since_sale, u365, stock, total_sales_ever, total_receipts_ever)

        # Update Item record directly
        frappe.db.set_value("Item", it, {
            "lb_units_30d": int(u30),
            "lb_units_90d": int(u90),
            "lb_units_180d": int(u180),
            "lb_units_365d": int(u365),
            "lb_days_cover": int(round(cover)) if cover is not None else None,
            "lb_velocity_band": band,
            "lb_days_since_sale": int(days_since_sale) if days_since_sale is not None else None,
            "lb_days_since_receipt": int(days_since_receipt) if days_since_receipt is not None else None,
            "lb_sell_through": sell_through_val,
            "lb_stock_value": stock_val,
        }, update_modified=False)

        updated_count += 1

        if (idx + 1) % 1000 == 0:
            frappe.db.commit()
            print(f"  ... processed {idx + 1}/{len(items)} items")

    frappe.db.commit()

    print("\n" + "=" * 60)
    print(f"PRODUCT-VELOCITY SCORING JOB COMPLETED ({updated_count} items updated)")
    print("=" * 60)

if __name__ == "__main__":
    refresh_velocity()
