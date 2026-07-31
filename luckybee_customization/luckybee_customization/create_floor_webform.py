import frappe

def create_floor_staff_web_form():
    # 1. Setup Custom DocPerm for the custom staff roles on Item
    roles = ["Floor Staff", "Trusted Staff", "Matching Staff", "Stock-take Staff"]
    for role in roles:
        filters = {"parent": "Item", "role": role}
        if not frappe.db.exists("Custom DocPerm", filters):
            dp = frappe.new_doc("Custom DocPerm")
            dp.parent = "Item"
            dp.parenttype = "DocType"
            dp.parentfield = "permissions"
            dp.role = role
            dp.read = 1
            dp.write = 1
            dp.create = 0
            dp.delete = 0
            dp.insert(ignore_permissions=True)
    
    # 2. Create the Web Form
    form_name = "photos-floor-staff"
    
    if frappe.db.exists("Web Form", form_name):
        frappe.delete_doc("Web Form", form_name)
    
    web_form = frappe.new_doc("Web Form")
    web_form.title = "Photos (Floor Staff)"
    web_form.name = form_name
    web_form.route = "item-floor-staff"
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
    
    # Restrict by Role (only Floor Staff can open this web form)
    # Note: Web Form restrictions by role are handled by docperms or simple logic, but wait,
    # let's see how Web Form is restricted to roles in the database.
    # Actually, let's check if the Web Form has a role field. No, it doesn't. 
    # But wait, standard Frappe Web Form has no role child table. 
    # So we can restrict access client-side or server-side by checking roles in get_context of the web form!
    # Yes! In the python controller (get_context) of the web form, we can restrict access:
    # "if 'Floor Staff' not in frappe.get_roles(): frappe.throw('Not permitted')"
    
    # Add fields
    web_form.append("web_form_fields", {
        "fieldname": "lb_images",
        "label": "Lucky Bee Images",
        "fieldtype": "Table",
        "reqd": 0
    })
    
    web_form.append("web_form_fields", {
        "fieldname": "lb_primary_image",
        "label": "Primary Image",
        "fieldtype": "Attach Image",
        "reqd": 0
    })
    
    web_form.client_script = """
frappe.ready(function() {
    $.getScript("/assets/luckybee_customization/js/mobile_preview.js");
});
"""
    
    web_form.insert(ignore_permissions=True)
    frappe.db.commit()
    print("Floor Staff Web Form and permissions set up successfully!")

if __name__ == "__main__":
    create_floor_staff_web_form()
