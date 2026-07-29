import frappe

def get_price(item_code, price_list):
    r = frappe.db.sql("""
        SELECT price_list_rate
        FROM `tabItem Price`
        WHERE item_code=%s AND price_list=%s AND price_list_rate > 0
        ORDER BY valid_from DESC
        LIMIT 1
    """, (item_code, price_list))
    return float(r[0][0]) if r else 0.0

def true_cost(doc):
    lpr = float(doc.last_purchase_rate) if doc.last_purchase_rate else 0.0
    ip = get_price(doc.name, "Standard Buying")
    mrp = float(doc.custom_mrp) if doc.custom_mrp else 0.0

    if ip and mrp and abs(ip - mrp) < 0.01:
        # MRP loaded as cost - reject buying Item Price and fall back to last_purchase_rate
        return lpr or None

    return ip or lpr or None

def calculate_margins(doc, method=None):
    selling = get_price(doc.name, "Standard Selling")
    cost = true_cost(doc)

    if selling and cost:
        doc.lb_margin_pct = round((selling - cost) / cost * 100.0, 2)
    else:
        doc.lb_margin_pct = None

    try:
        amz = float(doc.last_price) if doc.last_price else 0.0
    except (ValueError, TypeError):
        amz = 0.0

    if amz and selling:
        doc.amz_delta_pct = round((selling - amz) / amz * 100.0, 2)
    else:
        doc.amz_delta_pct = None

    mrp = float(doc.custom_mrp) if doc.custom_mrp else 0.0
    if mrp and selling:
        doc.mrp_discount_pct = round((mrp - selling) / mrp * 100.0, 2)
    else:
        doc.mrp_discount_pct = None
