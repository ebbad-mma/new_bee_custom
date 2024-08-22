import frappe
import json

@frappe.whitelist()
def get_fields(purchase_invoice):
    # BRAND_NAMES= ("DECO PRIDE", "JAYPEE", "ELEGANTE", "CLAY", "YERA", "TREO", "SIGNORAWARE", "SUNWELL", "ROYALWARE", "CORELLE", "GARUDA", "VAYA", "ASSR", "STEHLEN", "JCPL", "MELOWARE", "MEYER", "MARVEL", "MILTON", "ROXX", "CELLO", "M/W",  "CROWN",  "TAJ", "YAMASIN", "OCEAN", "CORELLE", "STEELO")
    pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
    item_table= pi.items
    resp = {"is_asin" : pi.custom_is_asin}
    res_list= []
    for item in item_table:
        res = item.as_dict()
        item_doc = frappe.get_doc("Item", item.item_code)
        res["item_code"] = item.item_code
        # description = item.description        
        # brand = [b for b in BRAND_NAMES if b in description]
        # if brand:
        #     res["brand"] = brand[0]                
        res["brand"] = item_doc.brand
        if item_doc.custom_last_price:
            res['mrp'] = item_doc.custom_last_price
        elif item_doc.custom_list_price_highest:
            res['mrp'] = item_doc.custom_list_price_highest
        res["ean"] = item_doc.custom_ean
        res["subcategory"] = item_doc.custom_category_sub
        image_list = []
        for i in range(1,6+1):
            f = f"custom_image{i}"
            if item_doc.get(f) is not "":
                image_list.append(item_doc.get(f))
        res["images"] = image_list
        res_list.append(res)
    resp["res_list"] = res_list
    return resp

@frappe.whitelist()
def update_data(doc, item_name):    
    doc = json.loads(doc)
    item_doc = frappe.get_doc("Purchase Invoice Item", item_name)
    
    item_doc.qty = doc["purchase_quantity"]
    item_doc.received_qty = doc["received_quantity"]
    item_doc.brand = doc['custom_brand']
    item_doc.custom_mrp = doc['mrp']
    item_doc.rate= doc['custom_rate']    
    item_doc.description = doc['custom_description']
    item_doc.item_name = doc['custom_item_name']
    item_doc.save()

    item_main = frappe.get_doc("Item", doc['product'])
    item_main.custom_sub_category = doc['subcategory']
    item_main.save()
    # frappe.log_error("Incoming data", f"{item_data['received_qty']}, {item_doc.received_qty}")
    # frappe.log_error("Incoming data", f"{item_doc.as_dict()}, \nIncoming: {doc['received_quantity']}")
    # if qc == "No":
    #     QC = frappe.new_doc("Quality Check")
    #     QC.purchase_invoice = doc['purchase_invoice']
    #     QC.item_code = doc['product']
    #     QC.out_of = doc['purchase_quantity']
    #     QC.save()
    #     frappe.msgprint(f"Quality Check created for item: {QC.name}")
    return "data sent successfully"
    
@frappe.whitelist()
def get_item(item_code):
    item = frappe.get_doc("Item", item_code)
    # res = {}
    # res["item_code"] = item.item_code
    # res["brand"] = item.brand
    # res["description"] = item.description
    # res["item_name"] = item.item_name
    # res['custom_asin'] = item.custom_asin
    # res['received_qty'] = item.received_qty
    return item