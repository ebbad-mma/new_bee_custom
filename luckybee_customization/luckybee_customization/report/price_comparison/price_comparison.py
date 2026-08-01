import frappe
from frappe.utils import flt

def execute(filters=None):
    filters = filters or {}
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    include_amz = filters.get("include_amazon_benchmarks", "Yes") == "Yes"

    cols = [
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 220},
        {"label": "LB Category", "fieldname": "custom_category", "fieldtype": "Link", "options": "Item Group", "width": 140},
        {"label": "True Cost", "fieldname": "cost", "fieldtype": "Currency", "width": 110},
        {"label": "Selling Price", "fieldname": "selling_price", "fieldtype": "Currency", "width": 120},
        {"label": "MRP", "fieldname": "custom_mrp", "fieldtype": "Currency", "width": 110},
    ]

    if include_amz:
        cols.extend([
            {"label": "AMZ Price", "fieldname": "amz_price", "fieldtype": "Currency", "width": 110},
        ])

    cols.extend([
        {"label": "Margin %", "fieldname": "lb_margin_pct", "fieldtype": "Percent", "width": 100},
    ])

    if include_amz:
        cols.extend([
            {"label": "vs AMZ %", "fieldname": "amz_delta_pct", "fieldtype": "Percent", "width": 100},
            {"label": "Review Rating", "fieldname": "reviews_rating", "fieldtype": "Float", "width": 110},
        ])

    cols.extend([
        {"label": "Current Stock", "fieldname": "stock_qty", "fieldtype": "Float", "width": 110},
    ])

    return cols

def get_data(filters):
    conditions = []
    if filters.get("item_code"):
        conditions.append("it.name = %(item_code)s")
    if filters.get("custom_category"):
        conditions.append("it.custom_category = %(custom_category)s")
    if filters.get("item_group"):
        conditions.append("it.item_group = %(item_group)s")

    where_clause = " AND ".join(conditions)
    if where_clause:
        where_clause = "WHERE " + where_clause

    query = f"""
        SELECT
            it.name AS item_code,
            it.item_name,
            it.custom_category,
            it.last_purchase_rate,
            it.custom_mrp,
            it.valuation_rate,
            COALESCE(NULLIF(it.amz_best_price, 0), it.last_price) AS amz_price,
            it.lb_margin_pct,
            it.amz_delta_pct,
            it.reviews_rating,
            (SELECT price_list_rate FROM `tabItem Price` WHERE item_code = it.name AND price_list = 'Standard Selling' AND price_list_rate > 0 ORDER BY valid_from DESC LIMIT 1) AS selling_price,
            (SELECT price_list_rate FROM `tabItem Price` WHERE item_code = it.name AND price_list = 'Standard Buying' AND price_list_rate > 0 ORDER BY valid_from DESC LIMIT 1) AS buying_price,
            (SELECT SUM(actual_qty) FROM `tabBin` WHERE item_code = it.name) AS stock_qty
        FROM `tabItem` it
        {where_clause}
        ORDER BY it.name ASC
    """

    raw_data = frappe.db.sql(query, filters, as_dict=True)
    out = []

    for row in raw_data:
        buying_p = flt(row.buying_price)
        mrp = flt(row.custom_mrp)
        lpr = flt(row.last_purchase_rate)
        val_rate = flt(row.valuation_rate)

        if buying_p and mrp and abs(buying_p - mrp) < 0.01:
            cost = lpr or val_rate or 0.0
        else:
            cost = buying_p or lpr or val_rate or 0.0

        row["cost"] = cost if cost > 0 else None
        row["selling_price"] = flt(row.selling_price) if row.selling_price else None
        row["custom_mrp"] = mrp if mrp > 0 else None
        row["amz_price"] = flt(row.amz_price) if row.amz_price else None
        row["amz_delta_pct"] = flt(row.amz_delta_pct) if (row.amz_delta_pct is not None and row.amz_price) else None
        row["lb_margin_pct"] = flt(row.lb_margin_pct) if row.lb_margin_pct is not None else None
        row["reviews_rating"] = flt(row.reviews_rating) if row.reviews_rating else None
        row["stock_qty"] = flt(row.stock_qty)

        out.append(row)

    return out
