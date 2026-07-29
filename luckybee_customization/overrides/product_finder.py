import frappe
import json

@frappe.whitelist()
def update_item(create_items,selected_item,item_to_be_update):
    create_items=json.loads(create_items)
    selected_items=json.loads(selected_item)
    selected_item=selected_items[0]
    created_item=""
    for i in create_items:
        asin_no=i['asin_no']
    if item_to_be_update=="":
        exist=frappe.db.exists('Item',{'custom_asin_no':asin_no})
        if exist:
            exists_item=frappe.get_doc('Item',{'custom_asin_no':asin_no})
            exists_item.custom_asin_no=asin_no
            exists_item.save()
            amz_itm_name=(exists_item.title or "")[1:140]
            frappe.db.set_value('Item',item_to_be_update,'item_name',amz_itm_name)
            created_item=exists_item.name
            frappe.msgprint("This ASIN item already exists. The item will be updated successfully.")
        else:
            doc = frappe.new_doc('Item')
            doc.item_group ='All Groups'
            doc.custom_asin_no =asin_no
            doc.insert()
            item_name=(doc.title or "")[1:140]
            doc.db_set('item_name',item_name)
            created_item=doc.name
            frappe.msgprint("Item created sucessfully")
    else:
        exists_item=frappe.get_doc('Item',item_to_be_update)
        exists_item.custom_asin_no=asin_no
        exists_item.save()
        amz_itm_name=(exists_item.title or "")[1:140]
        frappe.db.set_value('Item',item_to_be_update,'item_name',amz_itm_name)
        created_item=item_to_be_update
        frappe.msgprint("Item updated sucessfully")
    return {"item_name":created_item}
        