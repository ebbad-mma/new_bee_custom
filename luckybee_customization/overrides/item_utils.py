import frappe
from frappe.utils import cint
from woocommerce import API

from luckybee_customization.woocommerce.publish_item import get_woocommerce_settings,make_slug_to_find_category,get_or_create_category
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
        item.amazon_item_url=f"https://www.amazon.in/dp/{doc.custom_asin_no}"
        item.item=doc.name
        item.save()
    elif doc.custom_ean:
        item=frappe.get_doc('Item Details',{'ean':doc.custom_ean})
        item.item=doc.name
        item.save()
    elif doc.custom_fsn_no:
        item=frappe.get_doc('Item Details',{'fsn_no':doc.custom_fsn_no})
        item.flipkart_item_url=f"https://www.flipkart.com/product/p/itme?pid={doc.custom_fsn_no}"
        item.item=doc.name
        item.save()
    else:
        pass


def update_item_in_woocom():
    frappe.log_error("Run function of Woocom update")
    items_list=frappe.db.sql('''SELECT name
                                FROM `tabItem`
                                WHERE DATE(modified) = CURDATE() and custom_published=1;
                                ''',as_dict=1)
    frappe.log_error("woo up",items_list)
    for i in items_list:
        doc=frappe.get_doc('Item',i['name'])
    
        data={}
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
        if frappe.db.exists('Item Price',{'item_code':doc.name}):
            ip=frappe.get_doc('Item Price',{'item_code':doc.name,'price_list':'Standard Selling'})
            lrp=ip.price_list_rate
            data.update({"sale_price":str(lrp)})

        #fetch stock quantity
        if frappe.db.exists('Bin',{'item_code':doc.name}):
            bin=frappe.get_doc('Bin',{'item_code':doc.name})
            qty=bin.actual_qty
            data.update({"stock_quantity":str(qty)})

        #fetch categories
        if 'categories' not in data:
            data['categories'] = []
        if doc.custom_category_root:
            category_id = get_or_create_category(wcapi,doc.custom_category_root)
            # frappe.throw(f"{category_id}")
            if category_id:
                data['categories'].append({'id': category_id})
            else:
                frappe.log_error(f"Failed to add root category '{doc['custom_category_root']}' to WooCommerce.")
        if doc.custom_category_sub:
            category_id = get_or_create_category(wcapi,doc.custom_category_sub)
            # frappe.throw(f"{category_id}")
            if category_id:
                data['categories'].append({'id': category_id})
            else:
                frappe.log_error(f"Failed to add root category '{doc['custom_category_root']}' to WooCommerce.")
        # if doc.get('custom_categories_tree'):
        #     data['categories'].append({'name':doc['custom_categories_tree'],'slug': doc['custom_categories_tree']})
        #     frappe.log_error('tree',data)

        #fetch asin
        if doc.custom_asin_no:
            data.update({"sku":doc.custom_asin_no})
            title=doc.custom_amzon_item_name
        else:
            title=doc.item_name


        #fetch images
        if 'images' not in data:
            data['images'] = []
        if doc.image:
            data['images'].append({"src": doc.image})
        if doc.custom_image1:
            data['images'].append({'src':doc.custom_image1})
        if doc.custom_image2:
            data['images'].append({'src':doc.custom_image2})
        if doc.custom_image3:
            data['images'].append({'src':doc.custom_image3})
        if doc.custom_image4:
            data['images'].append({'src':doc.custom_image4})
        if doc.custom_image5:
            data['images'].append({'src':doc.custom_image5})
        
        #fetch description from item details
        # Ensure 'short_description' is initialized
        if 'short_description' not in data:
            data['short_description'] = title

        # Check if 'Item Details' record exists for the given item
        if frappe.db.exists('Item Details', {'item': doc.name}):
            item_d = frappe.get_doc('Item Details', {'item': doc.name})

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
            "name": doc.item_name,
            "type": "simple",
            "regular_price":str(doc.custom_mrp),
            "description": doc.description
        })
        if doc.woocommerce_product_id:
            exists = wcapi.get(f"products/{doc.woocommerce_product_id}").json()
            if exists:
                # Determine if the product exists and update or create accordingly
                if exists.get('data', {}).get('status') == 404:
                    response = wcapi.post('products', data).json()
                    frappe.log_error("PRODUCT PUBLISH", f"{response}")
                else:
                    response = wcapi.put(f"products/{doc.woocommerce_product_id}", data).json()
                    frappe.log_error("PRODUCT UPDATE", f"{response}")
        else:
            response = wcapi.post('products', data).json()
            # frappe.log_error("PRODUCT PUBLISH", f"{response}")
        # frappe.log_error("Response",response)
        # doc.db_set('custom_published',1)
        # doc.db_set('woocommerce_product_id',response['id'])
        # doc.db_set('custom_product_url',response['permalink'])
        return "Success: Item published"






