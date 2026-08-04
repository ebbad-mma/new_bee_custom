import frappe

@frappe.whitelist()
def get_supplier_history(item_code, limit=50):
    """Purchase history for an item, read straight from submitted Purchase
    Invoices.

    The custom_supplier_history child table it replaces only ever filled from
    the purchase-invoice import screen, and only for items that already had a
    previous supplier recorded - so it held 1 row site-wide while the invoices
    themselves covered 5,386 items. Reading the invoices means no backfill, no
    drift, and dates (which the child table had no field for).
    """
    if not frappe.has_permission("Item", "read", doc=item_code):
        frappe.throw(frappe._("Not permitted"), frappe.PermissionError)

    return frappe.db.sql(
        """
        SELECT
            pi.supplier,
            pi.supplier_name,
            pii.rate,
            pii.qty,
            pi.posting_date,
            pi.name AS invoice
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pii.item_code = %(item_code)s AND pi.docstatus = 1
        ORDER BY pi.posting_date DESC, pi.creation DESC
        LIMIT %(limit)s
        """,
        {"item_code": item_code, "limit": frappe.utils.cint(limit) or 50},
        as_dict=True,
    )
