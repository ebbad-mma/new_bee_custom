import frappe

def create_owner_supervisor_web_form():
    # 1. Setup Custom DocPerm for Owner-Supervisor on Item. Owner-Supervisor is a
    # bypass role in item_hooks.py::validate_role_field_permissions (skips the
    # per-field whitelist entirely), but that only governs which *fields* can
    # change once a save is already permitted - it does not grant the underlying
    # Item read/write doctype permission a Web Form needs to load and save at
    # all. No user currently holds this role and it had zero standing Item
    # permission before this grant (checked live) - without it, Form 5 would
    # 403 immediately for an Owner-Supervisor-only user, same class of gap Form 4
    # had for Stock Reconciliation before its own Custom DocPerm was added.
    filters = {"parent": "Item", "role": "Owner-Supervisor"}
    if not frappe.db.exists("Custom DocPerm", filters):
        dp = frappe.new_doc("Custom DocPerm")
        dp.parent = "Item"
        dp.parenttype = "DocType"
        dp.parentfield = "permissions"
        dp.role = "Owner-Supervisor"
        dp.read = 1
        dp.write = 1
        dp.create = 0
        dp.delete = 0
        dp.insert(ignore_permissions=True)

    # 2. Setup Custom DocPerm for Owner-Supervisor on Stock Reconciliation, matching
    # the narrow grant given to Stock-take Staff in create_count_webform.py (read/
    # write/create/submit only, no cancel/amend/delete) - needed for this form's
    # optional stock-count section, which reuses api/stock_recount.py verbatim.
    filters = {"parent": "Stock Reconciliation", "role": "Owner-Supervisor"}
    if not frappe.db.exists("Custom DocPerm", filters):
        dp = frappe.new_doc("Custom DocPerm")
        dp.parent = "Stock Reconciliation"
        dp.parenttype = "DocType"
        dp.parentfield = "permissions"
        dp.role = "Owner-Supervisor"
        dp.read = 1
        dp.write = 1
        dp.create = 1
        dp.submit = 1
        dp.cancel = 0
        dp.amend = 0
        dp.delete = 0
        dp.insert(ignore_permissions=True)

    # 3. Create the Web Form
    form_name = "all-in-one-owner-supervisor"

    if frappe.db.exists("Web Form", form_name):
        frappe.delete_doc("Web Form", form_name)

    web_form = frappe.new_doc("Web Form")
    # Web Form (WebsiteGenerator) derives .name from a slug of .title - keep the
    # title's words matching form_name exactly (see asin-matching-staff for the
    # duplicate-word pitfall that produces the wrong slug).
    web_form.title = "All-in-one (Owner-Supervisor)"
    web_form.name = form_name
    web_form.route = "item-owner-supervisor"
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

    # Owner-Supervisor bypasses item_hooks.py's per-field whitelist entirely, so
    # this form combines every field the other three Item-editing forms expose
    # between them (Photos + Product Info + ASIN). The stock count itself is
    # NOT an Item field - it's handled entirely by the form's own client script
    # via api/stock_recount.py, same as Form 4, and stays optional/off-by-default.
    fields = [
        {"fieldname": "custom_luckybee_brand", "label": "Brand", "fieldtype": "Data", "reqd": 0},
        {"fieldname": "custom_mrp", "label": "MRP", "fieldtype": "Currency", "reqd": 0},
        {"fieldname": "ean", "label": "EAN Barcode", "fieldtype": "Data", "reqd": 0},
        {"fieldname": "default_manufacturer_part_no", "label": "Product Code", "fieldtype": "Data", "reqd": 0},
        {"fieldname": "custom_asin_no", "label": "ASIN", "fieldtype": "Data", "reqd": 0},
        {"fieldname": "lb_images", "label": "Lucky Bee Images", "fieldtype": "Table", "options": "Lucky Bee Images", "reqd": 0},
        {"fieldname": "lb_primary_image", "label": "Primary Image", "fieldtype": "Attach Image", "reqd": 0},
    ]

    for f in fields:
        web_form.append("web_form_fields", f)

    web_form.insert(ignore_permissions=True)
    frappe.db.commit()
    print("Owner-Supervisor Web Form set up successfully!")

if __name__ == "__main__":
    create_owner_supervisor_web_form()
