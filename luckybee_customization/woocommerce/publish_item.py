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
    data={}
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


    #fetch LRP from item price
    if frappe.db.exists('Item Price',{'item_code':doc['name']}):
        ip=frappe.get_doc('Item Price',{'item_code':doc['name'],'price_list':'Standard Selling'})
        lrp=ip.price_list_rate
        data.update({"sale_price":str(lrp)})

    #fetch stock quantity
    if frappe.db.exists('Bin',{'item_code':doc['name']}):
        bin=frappe.get_doc('Bin',{'item_code':doc['name']})
        qty=bin.actual_qty
        data.update({"stock_quantity":str(qty)})

    #fetch categories
    if 'categories' not in data:
        data['categories'] = []
    if doc.get('custom_category_root'):
        category_id = get_or_create_category(wcapi,doc['custom_category_root'])
        # frappe.throw(f"{category_id}")
        if category_id:
            data['categories'].append({'id': category_id})
        else:
            frappe.log_error(f"Failed to add root category '{doc['custom_category_root']}' to WooCommerce.")
    if doc.get('custom_category_sub'):
        category_id = get_or_create_category(wcapi,doc['custom_category_sub'])
        # frappe.throw(f"{category_id}")
        if category_id:
            data['categories'].append({'id': category_id})
        else:
            frappe.log_error(f"Failed to add root category '{doc['custom_category_root']}' to WooCommerce.")
    # if doc.get('custom_categories_tree'):
    #     data['categories'].append({'name':doc['custom_categories_tree'],'slug': doc['custom_categories_tree']})
    #     frappe.log_error('tree',data)

    #fetch asin
    if doc.get('custom_asin_no'):
        data.update({"sku":doc['custom_asin_no']})
        title=doc['custom_amzon_item_name']
    else:
        title=doc['item_name']


    #fetch images
    if 'images' not in data:
        data['images'] = []
    if doc.get('image'):
        data['images'].append({"src": doc['image']})
    if doc.get('custom_image1'):
        data['images'].append({'src':doc['custom_image1']})
    if doc.get('custom_image2'):
        data['images'].append({'src':doc['custom_image2']})
    if doc.get('custom_image3'):
        data['images'].append({'src':doc['custom_image3']})
    if doc.get('custom_image4'):
        data['images'].append({'src':doc['custom_image4']})
    if doc.get('custom_image5'):
        data['images'].append({'src':doc['custom_image5']})
    
    #fetch description from item details
    # Ensure 'short_description' is initialized
    if 'short_description' not in data:
        data['short_description'] = title

    # Check if 'Item Details' record exists for the given item
    if frappe.db.exists('Item Details', {'item': doc['name']}):
        item_d = frappe.get_doc('Item Details', {'item': doc['name']})

        # Initialize the description with any existing 'short_description' value
        descriptions = [data.get('short_description', '')]

        # Append each description feature if it exists
        for i in range(1, 7):  # Loop through desc_feature1 to desc_feature6
            desc_feature = getattr(item_d, f'desc_feature{i}', None)
            if desc_feature:
                descriptions.append(desc_feature)
        
        # Join descriptions with newline and update 'short_description'
        data['short_description'] = '\n'.join(descriptions)



    data.update({
        "name": doc['item_name'],
        "type": "simple",
        "regular_price":str(doc['custom_mrp']),
        "description": doc['description']
    })
    if doc.get('woocommerce_product_id'):
        exists = wcapi.get(f"products/{doc['woocommerce_product_id']}").json()
        if exists:
            # Determine if the product exists and update or create accordingly
            if exists.get('data', {}).get('status') == 404:
                response = wcapi.post('products', data).json()
                frappe.log_error("PRODUCT PUBLISH", f"{response}")
            else:
                response = wcapi.post(f"products/{doc['woocommerce_product_id']}", data).json()
                frappe.log_error("PRODUCT UPDATE", f"{response}")
    else:
        response = wcapi.post('products', data).json()
        frappe.log_error("PRODUCT PUBLISH", f"{response}")
    frappe.log_error("DATA",data)
    doct = frappe.get_doc("Item",doc['name'])
    doct.custom_published = 1
    doct.woocommerce_product_id = response['id']
    doct.custom_product_url = response['permalink']
    doct.save()
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