import frappe
from .bin import create_item_price

#run on submit
def remove_unselected_item_from_item_master(doc, method=None):
    try:
        # Fetch all items from the Supplier Quotation
        sq_item = [i['item_code'] for i in frappe.get_list('Supplier Quotation Item', 
                                                            filters={'parent': doc.ref_sq}, 
                                                            fields=['item_code'])]
        # Get all item codes from the Purchase Order
        po_items = [j.item_code for j in doc.get('items')]

        # Find items not in the Purchase Order
        remove_items = [item for item in sq_item if item not in po_items]

        for r_item in remove_items:
            # Check custom_sq_item flag
            if frappe.db.get_value('Item', r_item, 'custom_sq_item') == 1:
                frappe.db.set_value('Item', r_item, 'custom_sq_item', 0)
            else:
                # Remove item details and item if exists
                if frappe.db.exists('Item Details', {'item': r_item}):
                    frappe.db.delete('Item Details', {'item': r_item})
                if frappe.db.exists('Item', r_item):
                    frappe.db.delete('Item', r_item)

        # Reset the custom_sq_item flag for all SQ items
        for untick_item in sq_item:
            if frappe.db.exists('Item', untick_item):
                frappe.db.set_value('Item', untick_item, 'custom_sq_item', 0)
                
    except Exception as e:
        frappe.log_error(f"Error in removing unselected items: {str(e)}", "Remove Unselected Items Error")
    # try:
    #     sq_doc=frappe.get_doc('Supplier Quotation',doc.ref_sq)
    #     create_item_price(sq_doc)
    # except Exception as e:
    #     frappe.log_error(f"Error in creating price:",str(e))


            


