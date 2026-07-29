import frappe
from frappe.utils import flt, cint

def execute(filters=None):
    filters = filters or {}
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 220},
        {"label": "Units 30d", "fieldname": "lb_units_30d", "fieldtype": "Int", "width": 90},
        {"label": "Units 90d", "fieldname": "lb_units_90d", "fieldtype": "Int", "width": 90},
        {"label": "Units 180d", "fieldname": "lb_units_180d", "fieldtype": "Int", "width": 90},
        {"label": "Units 365d", "fieldname": "lb_units_365d", "fieldtype": "Int", "width": 90},
        {"label": "Current Stock", "fieldname": "stock_qty", "fieldtype": "Float", "width": 110},
        {"label": "Days Cover", "fieldname": "lb_days_cover", "fieldtype": "Int", "width": 100},
        {"label": "Days Since Last Sale", "fieldname": "lb_days_since_sale", "fieldtype": "Int", "width": 150},
        {"label": "Days Since First Receipt", "fieldname": "lb_days_since_receipt", "fieldtype": "Int", "width": 160},
        {"label": "Sell-Through %", "fieldname": "lb_sell_through", "fieldtype": "Percent", "width": 110},
        {"label": "Stock Value", "fieldname": "lb_stock_value", "fieldtype": "Currency", "width": 120},
        {"label": "Velocity Band", "fieldname": "lb_velocity_band", "fieldtype": "Data", "width": 120},
    ]

def get_data(filters):
    conditions = ["it.is_stock_item = 1"]

    if filters.get("item_code"):
        conditions.append("it.name = %(item_code)s")
    if filters.get("lb_velocity_band"):
        conditions.append("it.lb_velocity_band = %(lb_velocity_band)s")
    if filters.get("item_group"):
        conditions.append("it.item_group = %(item_group)s")

    where_clause = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            it.name AS item_code,
            it.item_name,
            it.lb_units_30d,
            it.lb_units_90d,
            it.lb_units_180d,
            it.lb_units_365d,
            (SELECT SUM(actual_qty) FROM `tabBin` WHERE item_code = it.name) AS stock_qty,
            it.lb_days_cover,
            it.lb_days_since_sale,
            it.lb_days_since_receipt,
            it.lb_sell_through,
            it.lb_stock_value,
            it.lb_velocity_band
        FROM `tabItem` it
        {where_clause}
        ORDER BY it.lb_days_since_sale DESC, it.name ASC
    """

    raw_data = frappe.db.sql(query, filters, as_dict=True)
    out = []

    for row in raw_data:
        row["lb_units_30d"] = cint(row.lb_units_30d)
        row["lb_units_90d"] = cint(row.lb_units_90d)
        row["lb_units_180d"] = cint(row.lb_units_180d)
        row["lb_units_365d"] = cint(row.lb_units_365d)
        row["stock_qty"] = flt(row.stock_qty)
        row["lb_days_cover"] = cint(row.lb_days_cover) if row.lb_days_cover is not None else None
        row["lb_days_since_sale"] = cint(row.lb_days_since_sale) if row.lb_days_since_sale is not None else None
        row["lb_days_since_receipt"] = cint(row.lb_days_since_receipt) if row.lb_days_since_receipt is not None else None
        row["lb_sell_through"] = flt(row.lb_sell_through)
        row["lb_stock_value"] = flt(row.lb_stock_value)
        row["lb_velocity_band"] = row.lb_velocity_band or "Never Sold"
        out.append(row)

    return out
