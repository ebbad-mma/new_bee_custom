import frappe
from frappe.utils import cint
from woocommerce import API

from luckybee_customization.woocommerce.publish_item import get_woocommerce_settings,make_slug_to_find_category,get_or_create_category
def get_linked_item_details(doc, identifier_filter):
	# Prefer the Item Details record already linked to this item (item is unique on Item Details).
	# Looking up by identifier (ean/asin_no/fsn_no) first and blindly repointing .item onto it can
	# collide with a different record that's already linked to this item, raising a raw MySQL
	# IntegrityError instead of updating the right row.
	existing_for_item = frappe.db.get_value('Item Details', {'item': doc.name})
	if existing_for_item:
		return frappe.get_doc('Item Details', existing_for_item)
	if frappe.db.exists('Item Details', identifier_filter):
		return frappe.get_doc('Item Details', identifier_filter)
	return None

def check_image(doc,method=None):
	# if not doc.custom_image1 and not doc.custom_image2 and not doc.custom_image3 and not doc.custom_image4 and not doc.custom_image5:
	#     image_list=doc.custom_image_list
	#     for i in image_list:
	#         if i.view=='Front view':
	#             doc.db_set('custom_image1',i.image)
	#         else:
	#             doc.db_set('custom_image1',i.image)
	#create item details
	update_stock_in_hand_in_item_master(doc)
	if doc.custom_asin_no:
		item_details = get_linked_item_details(doc, {'asin_no': doc.custom_asin_no})
		if item_details:
			item_details.amazon_item_url = f"https://www.amazon.in/dp/{doc.custom_asin_no}"
			item_details.asin_no = doc.custom_asin_no
			item_details.item = doc.name
			item_details.save(ignore_permissions=True)
	elif doc.ean:
		item_details = get_linked_item_details(doc, {'ean': doc.ean})
		if item_details:
			item_details.ean = doc.ean
			item_details.item = doc.name
			item_details.save(ignore_permissions=True)
	elif doc.get("custom_fsn_no"):
		item_details = get_linked_item_details(doc, {'fsn_no': doc.get("custom_fsn_no")})
		if item_details:
			item_details.flipkart_item_url = f"https://www.flipkart.com/product/p/itme?pid={doc.get('custom_fsn_no')}"
			item_details.fsn_no = doc.get("custom_fsn_no")
			item_details.item = doc.name
			item_details.save(ignore_permissions=True)
	else:
		pass


def update_item_in_woocom():
	frappe.log_error("Run function of Woocom update")
	items_list=frappe.db.sql('''SELECT name
								FROM `tabItem`
								WHERE DATE(modified) = CURDATE() and custom_published=1;
								''',as_dict=1)
	if not items_list:
		frappe.log_error("No item to update")
		return
	frappe.log_error("Item need to be update in luckybee site",items_list)
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
		if doc.category_root:
			category_id = get_or_create_category(wcapi,doc.category_root)
			# frappe.throw(f"{category_id}")
			if category_id:
				data['categories'].append({'id': category_id})
			else:
				frappe.log_error(f"Failed to add root category '{doc['category_root']}' to WooCommerce.")
		if doc.lb_sub_category:
			category_id = get_or_create_category(wcapi,doc.lb_sub_category)
			# frappe.throw(f"{category_id}")
			if category_id:
				data['categories'].append({'id': category_id})
			else:
				frappe.log_error(f"Failed to add sub category '{doc['lb_sub_category']}' to WooCommerce.")
		# if doc.get('categories_tree'):
		#     data['categories'].append({'name':doc['categories_tree'],'slug': doc['categories_tree']})
		#     frappe.log_error('tree',data)

		#fetch asin
		if doc.custom_asin_no:
			data.update({"sku":doc.custom_asin_no})
			title=doc.title
		else:
			title=doc.item_name


		#fetch images
		if 'images' not in data:
			data['images'] = []
		if doc.image:
			data['images'].append({"src": doc.image})
		if doc.lb_primary_image:
			data['images'].append({'src':doc.lb_primary_image})
		
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



# -----------------------HELPER FUNCTION  TO UPDATE STOCK IN HAND FIELD IN ITEM MASTER---------------
def update_stock_in_hand_in_item_master(doc):
	pass

