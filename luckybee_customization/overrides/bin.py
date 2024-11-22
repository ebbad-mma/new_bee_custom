import frappe
from .sales_invoice import update_stock_in_item_master
def update_stock_in_hand(doc,method=None):
    update_stock_in_item_master(doc)


def set_warehouse_and_update_stock(doc,method=None):
    doc.db_set('update_stock',1)
    default_warehouse=frappe.db.get_single_value('Luckybee Settings','default_warehouse')
    if default_warehouse:
        doc.db_set('set_warehouse',default_warehouse)
    else:
        frappe.throw("You have not selected any warehouse in Luckybee settings. Please select a warehouse there or in the Purchase Invoice itself.")



def create_item_price(doc):
    for item in doc.get('items'):
        if not frappe.db.exists("Item Price", {"item_code": item.item_code, "price_list": "Standard Selling"}):
            item_price = frappe.new_doc("Item Price")
            item_price.item_code = item.item_code
            item_price.price_list = "Standard Selling"
            item_price.selling = 1
            item_price.item_name = item.item_name
            item_price.uom = item.uom
            item_price.valid_from = today()
            item_price.price_list_rate = item.custom_lrp
            item_price.save()

        if not frappe.db.exists("Item Price", {"item_code": item.item_code, "price_list": "Standard Buying"}):
            item_price = frappe.new_doc("Item Price")
            item_price.item_code = item.item_code
            item_price.price_list = "Standard Buying"
            item_price.buying = 1
            item_price.item_name = item.item_name
            item_price.uom = item.uom
            item_price.valid_from = today()
            item_price.price_list_rate = item.rate
            item_price.save()

        if frappe.db.exists('Item',item.item_code):
            # -----------------comment for now---------------------
            saved_item=frappe.get_doc('Item',item.item_code)
            ip = frappe.get_doc("Item Price", {"item_code": item.item_code, "price_list": "Standard Selling"})
            if str(ip.price_list_rate) != str(item.custom_lrp):
                ip.price_list_rate = item.custom_lrp
                ip.save()
            exists = any(d.price_list == 'Standard Selling' for d in saved_item.custom_item_price_details)
            if not exists:
                saved_item.append('custom_item_price_details',{'item_code': item.item_code,'uom':ip.uom,'item_price':ip.name,'rate':item.custom_lrp,'price_list':'Standard Selling'})
                # saved_item.save()

            ip = frappe.get_doc("Item Price", {"item_code": item.item_code, "price_list": "Standard Buying"})
            if str(ip.price_list_rate) != str(item.rate):
                ip.price_list_rate = item.rate
                ip.save()
            exists = any(d.price_list == 'Standard Buying' for d in saved_item.custom_item_price_details)
            if not exists:
                saved_item.append('custom_item_price_details',{'item_code': item.item_code,'uom':ip.uom,'price_list':'Standard Buying','rate':float(item.rate),'item_price':ip.name})
            saved_item.save()
            


def enqueue_create_item_price(doc, method=None):
    frappe.enqueue(
        'luckybee_customization.overrides.bin.create_item_price',
        queue='long',
        timeout=6000,
        doc=doc
    )

