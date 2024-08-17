import json
import frappe
from woocommerce import API
from frappe.utils import cint
from frappe import _


def get_woocommerce_settings():
    d = frappe.get_doc("WooCommerce Config")
    
    if d.woocommerce_url:
        d.api_secret = d.get_password(fieldname='api_secret')
        return d.as_dict()
    
    else:
        frappe.throw(_("woocommerce store URL is not configured on WooCommerce Config"), frappe.ValidationError)

@frappe.whitelist()
def publish_item(doc):
    doc = json.loads(doc)
    settings = get_woocommerce_settings()
    if cint(settings['verify_ssl']) == 1:
        verify_ssl = True
    else:
        verify_ssl = False  
    
    wcapi = API(
            url=settings['woocommerce_url'],
            consumer_key=settings['api_key'],
            consumer_secret=settings['api_secret'],
            verify_ssl=verify_ssl,
            wp_api=True,
            version="wc/v3",
            timeout=1000
    )
    # frappe.throw(f"{doc['image']}")
    # if not doc['custom_hidden']:
    if doc['custom_asin_no']:
        title=doc['custom_amzon_item_name']
    else:
        title=doc['item_name']
    data = {
        "name": doc['item_name'],
        "type": "simple",
        "regular_price": str(doc['custom_mrp']),
        "description": doc['description'],
        "short_description":title,            
        "categories": [
            {
                "id": 9
            },
            {
                "id": 14
            }
        ],
        "images": [
            {
                "src": doc['image']
                # "src":"https://media.istockphoto.com/id/1490616219/photo/portrait-of-handsome-young-man.webp?b=1&s=170667a&w=0&k=20&c=mGpQRe2EHXxXw-cDTESUFWTxnn3ORaOV3ncJYcNKFBA="
            }            
        ]
    }
    response = wcapi.post('products', data).json()
        # frappe.log_error("PRODUCT PUBLISH", f"{response}")
    # else:
    #     data = {
    #         "catalog_visibility": "visible",
    #         'status' : 'publish'
    #     }
    #     response = wcapi.post(f"products/{doc['woocommerce_product_id']}", data).json()

    frappe.log_error("PRODUCT PUBLISH", f"{response}")
    doct = frappe.get_doc("Item", doc['name'])
    doct.custom_published = 1
    doct.woocommerce_product_id = response['id']
    doct.custom_hidden = 0    
    doct.save()
    doct.reload()
    frappe.msgprint("Item has successfully published")
    # response = wcapi.delete('products/35459', params={'force': True}).json()
    # frappe.log_error("PRODUCT PUBLISH", f"{response}")
    return "Success: Item published"

@frappe.whitelist()
def unpublish_item(doc):
    doc = json.loads(doc)
    settings = get_woocommerce_settings()
    if cint(settings['verify_ssl']) == 1:
        verify_ssl = True
    else:
        verify_ssl = False
    
    wcapi = API(
            url=settings['woocommerce_url'],
            consumer_key=settings['api_key'],
            consumer_secret=settings['api_secret'],
            verify_ssl=verify_ssl,
            wp_api=True,
            version="wc/v3",
            timeout=1000
    )
    # response = wcapi.delete(f"products/{doc['woocommerce_product_id']}", params={'force': True}).json()
    data = {
        "catalog_visibility": "hidden",
        'status' : 'draft'
    }
    response = wcapi.post(f"products/{doc['woocommerce_product_id']}", data).json()
    frappe.log_error("PRODUCT UNPUBLISH", f"{response}")
    doct = frappe.get_doc("Item", doc['name'])
    doct.custom_published = 0
    doct.custom_hidden = 1
    doct.save()
    doct.reload()
    frappe.msgprint("Item has successfully unpublished")
    return "Success: Item unpublished"