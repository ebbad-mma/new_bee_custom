import frappe

def create_matching_staff_web_form():
    # 1. Setup Custom DocPerm for Matching Staff on Item
    filters = {"parent": "Item", "role": "Matching Staff"}
    if not frappe.db.exists("Custom DocPerm", filters):
        dp = frappe.new_doc("Custom DocPerm")
        dp.parent = "Item"
        dp.parenttype = "DocType"
        dp.parentfield = "permissions"
        dp.role = "Matching Staff"
        dp.read = 1
        dp.write = 1
        dp.create = 0
        dp.delete = 0
        dp.insert(ignore_permissions=True)

    # 2. Create the Web Form
    form_name = "asin-matching-staff"

    if frappe.db.exists("Web Form", form_name):
        frappe.delete_doc("Web Form", form_name)

    web_form = frappe.new_doc("Web Form")
    # Web Form (WebsiteGenerator) derives .name from a slug of .title, ignoring any
    # explicit .name assignment - keep the title's words matching form_name exactly.
    web_form.title = "ASIN (Matching Staff)"
    web_form.name = form_name
    web_form.route = "item-matching-staff"
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

    fields = [
        {"fieldname": "custom_asin_no", "label": "ASIN", "fieldtype": "Data", "reqd": 0},
    ]

    for f in fields:
        web_form.append("web_form_fields", f)

    web_form.client_script = """
frappe.ready(function() {
    $.getScript("/assets/luckybee_customization/js/mobile_preview.js");
});
"""

    web_form.insert(ignore_permissions=True)
    frappe.db.commit()
    print("Matching Staff Web Form set up successfully!")

if __name__ == "__main__":
    create_matching_staff_web_form()
