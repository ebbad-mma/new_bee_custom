import frappe
def check_image(doc,method=None):
    # if not doc.custom_image1 and not doc.custom_image2 and not doc.custom_image3 and not doc.custom_image4 and not doc.custom_image5:
    #     image_list=doc.custom_image_list
    #     for i in image_list:
    #         if i.view=='Front view':
    #             doc.db_set('custom_image1',i.image)
    #         else:
    #             doc.db_set('custom_image1',i.image)
    #create item details
    if doc.custom_asin_no:
        item=frappe.get_doc('Item Details',{'asin_no':doc.custom_asin_no})
        item.item=doc.name
        item.save()
    elif doc.custom_ean:
        item=frappe.get_doc('Item Details',{'ean':doc.custom_ean})
        item.item=doc.name
        item.save()
    elif doc.custom_fsn_no:
        item=frappe.get_doc('Item Details',{'fsn_no':doc.custom_fsn_no})
        item.item=doc.name
        item.save()



