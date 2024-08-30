import json
import frappe
import re
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


def make_slug_to_find_category(category_name):
    # Replace spaces and special characters with a hyphen
    return re.sub(r'[^\w]+', '-', category_name).strip('-').lower()

# Function to get or create category in WooCommerce
def get_or_create_category(wcapi,category_name):
    frappe.log_error("cat",category_name.lower())
    slug_finder=make_slug_to_find_category(category_name)
    # First, try to fetch the category ID by searching for the category name
    response = wcapi.get("products/categories",params={"search":slug_finder}).json()
    if response!=[]:
        return response[0]['id']

    # If category is not found, create it
    category_data = {
        "name": category_name,
        "slug": category_name.lower().replace(' ', '-')
    }
    create_response = wcapi.post("products/categories", category_data).json()
    frappe.log_error("Category Created", create_response)

    if create_response.get('id'):
        return create_response['id']
    else:
        frappe.log_error("Category Creation Failed", create_response)
        return None

@frappe.whitelist()
def publish_item(doc):
    data = {}
    doc = json.loads(doc)
    settings = get_woocommerce_settings()
    verify_ssl = cint(settings['verify_ssl']) == 1
    
    wcapi = API(
        url=settings['woocommerce_url'],
        consumer_key=settings['api_key'],
        consumer_secret=settings['api_secret'],
        verify_ssl=verify_ssl,
        wp_api=True,
        version="wc/v3",
        timeout=1000
    )

    # Fetch LRP and stock quantity in one go
    item_data = frappe.db.get_value(
        'Item Price', {'item_code': doc['name'], 'price_list': 'Standard Selling'},
        ['price_list_rate'], as_dict=True
    )
    bin_data = frappe.db.get_value(
        'Bin', {'item_code': doc['name']},
        ['actual_qty'], as_dict=True
    )
    if item_data:
        data.update({"sale_price": str(item_data['price_list_rate'])})
    if bin_data:
        data.update({"stock_quantity": str(bin_data['actual_qty'])})

    # Prepare categories
    data['categories'] = []
    for category_key in ['custom_category_root', 'custom_category_sub']:
        if doc.get(category_key):
            category_id = get_or_create_category(wcapi, doc[category_key])
            if category_id:
                data['categories'].append({'id': category_id})
            else:
                frappe.log_error(f"Failed to add category '{doc[category_key]}' to WooCommerce.")

    # Prepare SKU, title, and images
    data.update({
        "sku": doc.get('custom_asin_no', ''),
        "name": doc.get('custom_amzon_item_name', doc['item_name']),
        "images": [{"src": doc[img]} for img in ['image', 'custom_image1', 'custom_image2', 'custom_image3', 'custom_image4', 'custom_image5'] if doc.get(img)],
        "type": "simple",
        "regular_price": str(doc['custom_mrp']),
        "description": doc.get('description', ''),
        "short_description": doc.get('item_name')
    })

    # Fetch and append Item Details if exists
    if frappe.db.exists('Item Details', {'item': doc['name']}):
        item_d = frappe.get_doc('Item Details', {'item': doc['name']})
        descriptions = [data['short_description']]
        descriptions += [getattr(item_d, f'desc_feature{i}', '') for i in range(1, 7) if getattr(item_d, f'desc_feature{i}', '')]
        data['short_description'] = '\n'.join(filter(None, descriptions))

    # Create or update the product in WooCommerce
    response = wcapi.post('products', data).json() if not doc.get('woocommerce_product_id') else wcapi.put(f"products/{doc['woocommerce_product_id']}", data).json()
    frappe.log_error("PRODUCT PUBLISH/UPDATE", f"{response}")

    # Update local Item Doc
    if response.get('id'):
        doct = frappe.get_doc("Item", doc['name'])
        doct.custom_published = 1
        doct.woocommerce_product_id = response['id']
        doct.custom_product_url = response['permalink']
        doct.save()

    frappe.msgprint("Item has successfully published")
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
    response = wcapi.delete(f"products/{doc['woocommerce_product_id']}", params={'force': True}).json()
    # data = {
    #     "catalog_visibility": "hidden",
    #     'status' : 'draft'
    # }
    # # response = wcapi.post(f"products/{doc['woocommerce_product_id']}", data).json()
    frappe.log_error("PRODUCT UNPUBLISH", f"{response}")
    doct = frappe.get_doc("Item", doc['name'])
    doct.custom_published = 0
    doct.woocommerce_product_id=None
    doct.custom_product_url=None
    doct.save()
    doct.reload()
    frappe.msgprint("Item has successfully unpublished")
    return "Success: Item unpublished"