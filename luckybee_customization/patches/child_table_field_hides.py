import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

# The last 14 entries on the scope workbook's "13. Full Hides" sheet. They were
# read as missing because they are not Item fields at all - they sit on the
# Item Default child grid (and barcode_type on Item Barcode), which is why the
# earlier Item-only pass could not reach them.
CHILD_HIDES = {
    "Item Default": [
        "deferred_expense_account", "deferred_revenue_account", "default_discount_account",
        "default_inventory_account", "inventory_account_currency", "buying_cost_center",
        "selling_cost_center", "default_provisional_account", "purchase_expense_account",
        "purchase_expense_contra_account", "default_cogs_account", "expense_account",
        "default_supplier",
    ],
    "Item Barcode": ["barcode_type"],
}

def execute():
    print("Executing Patch: child_table_field_hides...")

    count = 0
    for doctype, fieldnames in CHILD_HIDES.items():
        meta = frappe.get_meta(doctype)
        for fieldname in fieldnames:
            if not meta.get_field(fieldname):
                print(f"  skip {doctype}.{fieldname}: not on this doctype")
                continue
            make_property_setter(doctype, fieldname, "hidden", "1", "Check")
            count += 1
        frappe.clear_cache(doctype=doctype)

    frappe.db.commit()
    print(f"Patch child_table_field_hides completed successfully ({count} fields hidden).")
