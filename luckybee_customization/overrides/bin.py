import frappe

def update_stock_in_hand(doc,method=None):
    for item in doc.items:
        bin=frappe.get_doc('Bin',{'item_code':item.item_code})
        actual_qty=bin.actual_qty
        frappe.db.set_value('Item',item.item_code,'custom_stock_in_hand',actual_qty)


def set_warehouse_and_update_stock(doc,method=None):
    doc.db_set('update_stock',1)
    doc.db_set('set_warehouse','Finished Goods - B')