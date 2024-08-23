import frappe
import json

@frappe.whitelist()
def update_item(create_items,selected_item):
    create_items=json.loads(create_items)
    selected_items=json.loads(selected_item)
    # responses=json.loads(responses)
    selected_item=selected_items[0]
    # frappe.throw(f"{selected_item}")
    for i in create_items:
        asin_no=i['asin_no']
    # frappe.throw(f"{selected_item}")
    if not frappe.db.exists("Item",{'custom_asin_no':asin_no}):
        # create a new document
        doc = frappe.new_doc('Item')
        doc.item_group ='All Groups'
        doc.custom_asin_no =asin_no
        doc.insert()
        frappe.msgprint("Item created sucessfully")
    else:
        item_doc=frappe.get_doc("Item",{'custom_asin_no':asin_no})
        item_doc.custom_asin_no =asin_no
        item_doc.item_group='All Groups'
        item_doc.save()
        frappe.msgprint("Item updated sucessfully")
    return "Success"
        