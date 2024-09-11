import frappe

# --------------helper function to update stock in item master on submit------------------
def update_stock_in_item_master(doc):
    for item in doc.items:
        if frappe.db.exists('Bin',{'item_code':item.item_code}):
            actual_qty=frappe.db.get_value('Bin',{'item_code':item.item_code},'actual_qty')
            frappe.db.set_value('Item',item.item_code,'custom_stock_in_hand',actual_qty)

def update_stock_in_hand_in_item_master_on_si_submit(doc,method=None):
    update_stock_in_item_master(doc)

    

