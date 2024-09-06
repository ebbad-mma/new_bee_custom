import frappesafe_float_conversion
import json
import time
from frappe.utils import today
def safe_float_conversion(rate, default_value=0.0):
    try:
        rate_cleaned = rate.replace(',', '')
        return float(rate_cleaned)
    except ValueError:
        frappe.msgprint(f"Could not convert rate '{rate}' to float.")
        return default_value

@frappe.whitelist()
def search_and_insert_item(doc, description, hsn, qty, rate, per,disc1,disc2,disc3, disc, mrp, brand, group, category, sub_category,custom_asin,custom_box_number,custom_ean,custom_synced,amount):
	doc = json.loads(doc)
	custom_synced=int(custom_synced)
	dict_itm = {}
	if description and custom_synced==0:
		if not frappe.db.exists('Item',{'item_name':description}):
			item = frappe.new_doc("Item")
			item.naming_series = 'SQ.#####'
			# item.custom_sq_items=1
			# item.item_code=custom_purchase_item
			item.stoc_uom = per
			item.gst_hsn_code = ''
			if len(description)>130:
				description=description[:130]
			else:
				description=description
			item.item_name=description
			item.item_group = 'All Groups'
			item.custom_mrp = mrp
			item.gst_hsn_code = hsn
			item.custom_luckybee_brand = brand
			item.custom_group = group
			item.custom_category = category
			item.custom_category_sub = sub_category
			item.custom_asin_no = custom_asin
			item.custom_box_number=custom_box_number
			item.custom_last_supplier=doc['supplier']
			item.custom_last_supplier_purchase_rate=safe_float_conversion(rate)
			item.ean = custom_ean
			item.append('item_defaults',{'company':'Samyak Resources','default_warehouse':'Stores - SR'})
			item.insert(ignore_permissions=True)
			item.custom_barcode = item.item_code
			barcode_row = item.append("barcodes", {})
			barcode_row.barcode = item.item_code
			item.save()
			item_name=item.name
			
		else:	
			item_code_exist = frappe.db.get_value('Item', {'item_name': description}, 'item_code')
			if item_code_exist:
				item_name=item_code_exist
				# Initialize the supplier and rate lists
				supplierNrate = {'last_supplier': [], 'last_rate': []}

				# Fetch the existing supplier and rate information
				custom_last_supplier, custom_last_supplier_purchase_rate = frappe.db.get_value(
					'Item', item_code_exist, ['custom_last_supplier', 'custom_last_supplier_purchase_rate']
				)

				# Update the supplier history
				if custom_last_supplier:
					supplierNrate['last_supplier'].append(doc['supplier'])
					supplierNrate['last_rate'].append(safe_float_conversion(rate))
					supplierNrate['last_supplier'].append(custom_last_supplier)
					supplierNrate['last_rate'].append(custom_last_supplier_purchase_rate)

					# Update the last supplier information
					frappe.db.set_value('Item', item_code_exist, {
						'custom_last_supplier': doc['supplier'],
						'custom_last_supplier_purchase_rate': safe_float_conversion(rate)
					})

					for last_supplier, last_rate in zip(supplierNrate['last_supplier'], supplierNrate['last_rate']):
						child = frappe.get_doc({
							'doctype': 'Supplier History',  # Replace with your actual child doctype name
							'parent': item_code_exist,
							'parentfield': 'custom_supplier_history',  # Field name for the child table
							'parenttype': 'Item',
							'supplier': last_supplier,
							'rate': last_rate
						})
						child.insert(ignore_permissions=True)
				frappe.db.set_value('Item', item_code_exist, {
					'custom_mrp': mrp,
					'gst_hsn_code': hsn,
					'custom_luckybee_brand': brand,
					'brand': brand,
					'custom_group': group,
					'custom_category': category,
					'custom_category_sub': sub_category,
					'custom_barcode': item_code_exist,
					'custom_last_supplier': doc['supplier'],
					'custom_last_supplier_purchase_rate': safe_float_conversion(rate)
				})				
		item_code, reviews_rating,new_current,reviews_count,last_purchase_rate,last_price,list_price_highest,brand,custom_image1,custom_amzon_item_name=frappe.db.get_value("Item", {"item_name": description}, ['item_code', 'custom_reviews_rating','custom_new_current','custom_reviews_count','last_purchase_rate','custom_last_price','custom_list_price_highest','brand','custom_image1','custom_amzon_item_name'])
		# get item details to calculatelrp 
		if frappe.db.exists('Item Details',{'item':item_name}):
			avg_30, avg_90 = frappe.db.get_value(
													'Item Details', 
													{'item': item_name}, 
													['list_price_30_days_avg', 'list_price_90_days_avg']
												) or (None, None)
		# Convert to integers if possible, otherwise set to 0
		last_price_int = int(last_price) if last_price is not None and int(last_price) > 0 else 0
		list_price_highest_int = int(list_price_highest) if list_price_highest is not None and int(list_price_highest) > 0 else 0
		dict_itm.update({
							"item_code": item_code,
							"reviews_rating": reviews_rating,
							"qty": qty,
							"item_name": description,
							"uom": "Nos",
							"new_current":safe_float_conversion(new_current) if new_current else 0,
							"avg_30":safe_float_conversion(avg_30) if avg_30 else 0,
							"avg_90":safe_float_conversion(avg_90) if avg_90 else 0,
							"custom_asin":custom_asin,
							"rate":rate,
							"custom_box_number":custom_box_number,
							"custom_reviews_count":int(reviews_count or 0),
							"last_purchase_rate":last_purchase_rate,
							"mrp":safe_float_conversion(mrp),
							"brand":brand,
							"custom_image1":custom_image1,
							"custom_amzon_item_name":custom_amzon_item_name,
							"amount":safe_float_conversion(amount),
							"uom":per,
							"gst_disc":disc,
							"disc1":disc1,
							"disc2":disc2,
							"disc3":disc3
						})
	else:
		dict_itm.update({})
# doc.save()
	return dict_itm










@frappe.whitelist()
def get_total_margin(sq_items, name):
	try:
		margin_dict = {}
		sq_items = json.loads(sq_items)
		frappe.log_error("sq",sq_items)
		for i in sq_items:
			frappe.log_error("i",i)
			box_number = i.get('custom_box_number')
			frappe.log_error("bo",box_number)
			margin_amount = safe_float_conversion(i.get('custom_margin_in_amount'))
			rate = safe_float_conversion(i.get('rate'))

			# Update margin and rate for each box number
			if box_number in margin_dict:
				margin_dict[box_number]['total_margin'] += margin_amount
				margin_dict[box_number]['rate'] += rate
			else:
				margin_dict[box_number] = {'total_margin': margin_amount, 'rate': rate}
		margin_list = []
		for k, v in margin_dict.items():
			margin_percentage = round((v['total_margin'] / v['rate']) * 100, 2)
			margin_list.append({'box_number': k, 'total_margin': v['total_margin'], 'rate': v['rate'], 'margin_':margin_percentage})
		# Get the parent document
		parent_doc = frappe.get_doc('Supplier Quotation',name)
		# Clear existing child table entries
		parent_doc.set('custom_decision_maker', [])
		# Add new entries to the child table
		frappe.log_error("list",margin_list)
		for margin in margin_list:
			parent_doc.append('custom_decision_maker',margin)
		# Save the parent document
		parent_doc.save()

		return {'status': 'success', 'message': 'Margin details updated successfully'}

	except Exception as e:
		return {'status': 'failed', 'message': str(e)}


	


# def delete(doc,method=None):
# 	frappe.db.sql('''DELETE FROM `tabItem` WHERE name="SQ00026"''')