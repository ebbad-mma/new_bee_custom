import frappe
import json
import time
from frappe.utils import today


@frappe.whitelist()
def search_and_insert_item(doc, description, hsn, qty, rate, per, mrp, lrp, brand, group, category, sub_category,custom_asin,custom_box_number,custom_ean,custom_synced,amount):
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
			item.item_name = description
			item.item_group = 'All Groups'
			item.custom_mrp = mrp
			item.gst_hsn_code = hsn
			item.custom_luckybee_brand = brand
			item.custom_group = group
			item.custom_category = category
			item.custom_category_sub = sub_category
			item.custom_asin_no = custom_asin
			item.custom_box_number=custom_box_number
			item.ean = custom_ean
			item.append('item_defaults',{'company':'Samyak Resources','default_warehouse':'Stores - SR'})
			# item.custon_fsn_no = custom_fsn
			item.insert(ignore_permissions=True)
			# time.sleep(5)
			item.custom_barcode = item.item_code
			barcode_row = item.append("barcodes", {})
			barcode_row.barcode = item.item_code
			item.save()
			# time.sleep(5)
			# if disc_perc:
			# 	create_item_price(item, lrp, discounted_price)
			# if disc_perc:
			# 	create_item_price(item, lrp, discounted_price)
		else:	
			item=frappe.get_doc('Item',{'item_name':description})
			if item:
				if not mrp=="":
					if item.custom_mrp and float(mrp) > 0 and float(item.custom_mrp) != float(mrp) :
						item.custom_mrp = mrp
				if item.gst_hsn_code != hsn:
					item.gst_hsn_code = hsn
				if item.custom_luckybee_brand != brand:
					item.custom_luckybee_brand = brand
				if item.custom_group != group:
					item.custom_group = group
				if item.custom_category != category:
					item.custom_category = category
				if item.custom_category_sub != sub_category:
					item.custom_category_sub = sub_category
				if not item.custom_barcode:
					item.custom_barcode = item.item_code
					barcode_row = item.append("barcodes", {})
					barcode_row.barcode = item.item_code
			item.save()
			time.sleep(5)				
		item_code, reviews_rating,new_current,reviews_count,last_purchase_rate,last_price,list_price_highest,brand,custom_image1,custom_amzon_item_name=frappe.db.get_value("Item", {"item_name": description}, ['item_code', 'custom_reviews_rating','custom_new_current','custom_reviews_count','last_purchase_rate','custom_last_price','custom_list_price_highest','brand','custom_image1','custom_amzon_item_name'])
		# Convert to integers if possible, otherwise set to 0
		last_price_int = int(last_price) if last_price is not None and int(last_price) > 0 else 0
		list_price_highest_int = int(list_price_highest) if list_price_highest is not None and int(list_price_highest) > 0 else 0
		# Determine mrp based on the above logic
		mrp = last_price_int if last_price_int > 0 else list_price_highest_int
		# if len(custom_amzon_item_name)>140:
		# custom_amzon_item_name=custom_amzon_item_name[0:140]
		# mrp=int(last_price) if int(last_price) > 0 else int(list_price_highest)
		dict_itm.update({
							"item_code": item_code,
							"reviews_rating": reviews_rating,
							"qty": qty,
							"item_name": description,
							"uom": "Nos",
							"new_current":float(new_current) if new_current else 0,
							"custom_asin":custom_asin,
							"rate":rate,
							"custom_box_number":custom_box_number,
							"custom_reviews_count":int(reviews_count or 0),
							"last_purchase_rate":last_purchase_rate,
							"mrp":mrp,
							"brand":brand,
							"custom_image1":custom_image1,
							"custom_amzon_item_name":custom_amzon_item_name,
							"amount":float(amount),
							"uom":per
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
			margin_amount = float(i.get('custom_margin_in_amount'))
			rate = float(i.get('rate'))

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