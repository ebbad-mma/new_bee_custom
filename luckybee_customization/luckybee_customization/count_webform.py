import frappe

def stock_take_staff_web_form():
    # 1. Setup Custom DocPerm for Stock-take Staff on Item
    filters = {"parent": "Item", "role": "Stock-take Staff"}
    if not frappe.db.exists("Custom DocPerm", filters):
        dp = frappe.new_doc("Custom DocPerm")
        dp.parent = "Item"
        dp.parenttype = "DocType"
        dp.parentfield = "permissions"
        dp.role = "Stock-take Staff"
        dp.read = 1
        dp.write = 1
        dp.create = 0
        dp.delete = 0
        dp.insert(ignore_permissions=True)

    # 2. Setup Custom DocPerm for Stock-take Staff on Stock Reconciliation.
    # Narrow and deliberate: read/write/create/submit only, no cancel/amend/delete.
    # api/stock_recount.py relies on this so it can create+submit the recount
    # directly as the real session user, with no impersonation needed - see the
    # comment in submit_stock_recount for why frappe.set_user() is unsafe here.
    # Which item/warehouse/qty combinations are actually reachable is still fully
    # constrained by that API (ALLOWED_WAREHOUSES, eligibility checks), not by
    # this permission grant alone - a Stock-take Staff user with Desk access could
    # in principle create other Stock Reconciliations directly; that's accepted
    # as within their job function, matching how this role's whole purpose is
    # stock counting.
    filters = {"parent": "Stock Reconciliation", "role": "Stock-take Staff"}
    if not frappe.db.exists("Custom DocPerm", filters):
        dp = frappe.new_doc("Custom DocPerm")
        dp.parent = "Stock Reconciliation"
        dp.parenttype = "DocType"
        dp.parentfield = "permissions"
        dp.role = "Stock-take Staff"
        dp.read = 1
        dp.write = 1
        dp.create = 1
        dp.submit = 1
        dp.cancel = 0
        dp.amend = 0
        dp.delete = 0
        dp.insert(ignore_permissions=True)

    # 3. Create the Web Form
    form_name = "count-stock-take-staff"

    if frappe.db.exists("Web Form", form_name):
        frappe.delete_doc("Web Form", form_name)

    web_form = frappe.new_doc("Web Form")
    # Web Form (WebsiteGenerator) derives .name from a slug of .title - keep the
    # title's words matching form_name exactly (see asin-matching-staff for the
    # duplicate-word pitfall that produces the wrong slug).
    web_form.title = "Count (Stock-take Staff)"
    web_form.name = form_name
    web_form.route = "item-stock-take-staff"
    web_form.doc_type = "Item"
    web_form.is_standard = 1
    web_form.module = "luckybee_customization"
    web_form.login_required = 1
    web_form.allow_edit = 1
    web_form.allow_delete = 0
    web_form.show_sidebar = 0
    web_form.allow_multiple = 0
    web_form.published = 1
    web_form.apply_document_permissions = 1

    # Deliberately zero Item fields: Stock-take Staff's whitelist in item_hooks.py
    # is an empty set - this form never edits the Item doc directly, it only
    # reads item_code/name from the URL and drives a separate Stock
    # Reconciliation submission via api/stock_recount.py. The form's own
    # count_stock_take_staff.js (not the shared mobile_preview.js - there's
    # nothing about photos/product info relevant here) builds the whole UI.

    web_form.insert(ignore_permissions=True)
    frappe.db.commit()
    print("Stock-take Staff Web Form set up successfully!")

if __name__ == "__main__":
    stock_take_staff_web_form()
