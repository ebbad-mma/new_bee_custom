import frappe

def create_trusted_staff_web_form():
    # 1. Setup Custom DocPerm for Trusted Staff on Item
    filters = {"parent": "Item", "role": "Trusted Staff"}
    if not frappe.db.exists("Custom DocPerm", filters):
        dp = frappe.new_doc("Custom DocPerm")
        dp.parent = "Item"
        dp.parenttype = "DocType"
        dp.parentfield = "permissions"
        dp.role = "Trusted Staff"
        dp.read = 1
        dp.write = 1
        dp.create = 0
        dp.delete = 0
        dp.insert(ignore_permissions=True)
    
    # 2. Create the Web Form
    form_name = "product-info-trusted-staff"
    
    if frappe.db.exists("Web Form", form_name):
        frappe.delete_doc("Web Form", form_name)
    
    web_form = frappe.new_doc("Web Form")
    web_form.title = "Product Info (Trusted Staff)"
    web_form.name = form_name
    web_form.route = "item-trusted-staff"
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
        {"fieldname": "custom_luckybee_brand", "label": "Brand", "fieldtype": "Data", "reqd": 0},
        {"fieldname": "custom_mrp", "label": "MRP", "fieldtype": "Currency", "reqd": 0},
        {"fieldname": "ean", "label": "EAN Barcode", "fieldtype": "Data", "reqd": 0},
        {"fieldname": "default_manufacturer_part_no", "label": "Product Code", "fieldtype": "Data", "reqd": 0},
        {"fieldname": "lb_images", "label": "Lucky Bee Images", "fieldtype": "Table", "options": "Lucky Bee Images", "reqd": 0},
        {"fieldname": "lb_primary_image", "label": "Primary Image", "fieldtype": "Attach Image", "reqd": 0}
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
    print("Trusted Staff Web Form set up successfully!")

if __name__ == "__main__":
    create_trusted_staff_web_form()
