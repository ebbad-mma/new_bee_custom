import frappe
import json
import time
from frappe.utils import today
def safe_int(value, default=0):
	try:
		return int(value)
	except (TypeError, ValueError):
		return default

@frappe.whitelist()
def search_and_insert_item(doc,description, hsn, qty, rate, per, mrp, lrp, brand, group, category, sub_category,custom_asin,custom_box_number, custom_ean,disc):
	doc = json.loads(doc)

	dict_itm = {}
	if description :
		#create Brand
		if brand:
			if not frappe.db.exists('Brand',{'brand':brand}):
				br=frappe.new_doc('Brand')
				br.brand=brand
				br.insert()
		item_code_exist = frappe.db.get_value('Item', {'item_name':description}, 'item_code')
		if item_code_exist:
			item=frappe.get_doc('Item',{'item_name':description})
			supplierNrate={'last_supplier':[],"last_rate":[]}
			if item.custom_last_supplier:
				supplierNrate['last_supplier'].append(doc['supplier'])
				supplierNrate['last_rate'].append(float(rate))
				supplierNrate['last_supplier'].append(item.custom_last_supplier)
				supplierNrate['last_rate'].append(item.custom_last_supplier_purchase_rate)
				# if item.custom_last_supplier!=doc['supplier']:
				item.custom_last_supplier=doc['supplier']
				item.custom_last_supplier_purchase_rate=float(rate)
				
				for last_supplier,last_rate in zip(supplierNrate['last_supplier'], supplierNrate['last_rate']):
					item.append('custom_supplier_history', {'supplier': last_supplier, 'rate':last_rate})
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
		# if not item_code_exist:
		else:
			int_mrp=float(mrp)
			item = frappe.new_doc("Item")
			# item.naming_series = 'L.#####'
			item.item_code=item.naming_series
			# item.item_code=custom_purchase_item
			item.custom_last_supplier=doc['supplier']
			item.custom_last_supplier_purchase_rate=float(rate)
			item.stoc_uom = per
			item.gst_hsn_code = ''
			item.item_name = description
			item.item_group = 'All Groups'
			item.custom_mrp = mrp
			item.gst_hsn_code = hsn
			item.custom_luckybee_brand = brand
			item.brand = brand
			item.custom_group = group
			item.custom_category = category
			item.custom_sub_category = sub_category
			item.custom_asin_no = custom_asin
			item.custom_box_number=custom_box_number
			item.custom_ean = custom_ean
			# item.custon_fsn_no = custom_fsn
			
			gst = ""
			# if disc_perc:
			if disc == "15.25":
				gst = "GST 18% - SR"
			elif disc == "10.71":
				gst = "GST 12% - SR"
			elif disc == "4.71":
				gst = "GST 5% - SR"
			row = item.append("taxes", {})
			row.item_tax_template = gst

			# item.opening_stock=qty
			item.standard_rate=rate
			# item.size=qty
			item.insert(ignore_permissions=True)
			time.sleep(5)
			item.custom_barcode = item.item_code
			barcode_row = item.append("barcodes", {})
			barcode_row.barcode = item.item_code
			item.save()
			# if disc_perc:
			# 	create_item_price(item, lrp, discounted_price)
		int_mrp=float(mrp)
							
		item_code, reviews_rating,new_current,reviews_count,last_purchase_rate,last_price,list_price_highest= frappe.db.get_value("Item", {"item_name": description}, ['item_code', 'custom_reviews_rating','custom_new_current','custom_reviews_count','last_purchase_rate','custom_last_price','custom_list_price_highest'])
		# mrp=int(last_price) if int(last_price) > 0 else int(list_price_highest)
		last_price_safe = safe_int(last_price)
		list_price_highest_safe = safe_int(list_price_highest)
		mrp = last_price_safe if last_price_safe > 0 else list_price_highest_safe
		if reviews_count is not None:
			reviews_count=int(reviews_count)
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
							"custom_reviews_count":reviews_count,
							"last_purchase_rate":last_purchase_rate,
							"mrp":mrp
						})
	return dict_itm

# ---------------------------create item price---------------------------------
def create_item_price(item, lrp=None, discounted_price=None):
	if not frappe.db.exists("Item Price", {"item_code": item.item_code, "price_list": "Standard Selling"}):
		item_price = frappe.new_doc("Item Price")
		item_price.item_code = item.item_code
		item_price.price_list = "Standard Selling"
		item_price.selling = 1
		item_price.item_name = item.item_name
		item_price.uom = item.stock_uom
		item_price.valid_from = today()
		item_price.price_list_rate = lrp
		item_price.save()

	if not frappe.db.exists("Item Price", {"item_code": item.item_code, "price_list": "Standard Buying"}):
		item_price = frappe.new_doc("Item Price")
		item_price.item_code = item.item_code
		item_price.price_list = "Standard Buying"
		item_price.buying = 1
		item_price.item_name = item.item_name
		item_price.uom = item.stock_uom
		item_price.valid_from = today()
		item_price.price_list_rate = discounted_price
		item_price.save()

	if frappe.db.exists('Item',item.item_code):
		# -----------------comment for now---------------------
		ip = frappe.get_doc("Item Price", {"item_code": item.item_code, "price_list": "Standard Selling"})
		frappe.log_error(f"{ip.price_list_rate}'   '{lrp}")
		exists = any(d.price_list == 'Standard Selling' for d in item.custom_item_price_details)
		if not exists:
			item.append('custom_item_price_details',{'item_code': item.item_code,'uom':ip.uom,'item_price':ip.name,'rate':lrp,'price_list':'Standard Selling'})
			item.save()
		if str(ip.price_list_rate) != str(lrp):
			ip.price_list_rate = lrp
			ip.save()
			for ipd in item.custom_item_price_details:
				if ip.name == ipd.item_price:
					ipd.rate = lrp
			item.save()

		ip = frappe.get_doc("Item Price", {"item_code": item.item_code, "price_list": "Standard Buying"})
		frappe.log_error(f"{ip.price_list_rate}' ppp'{discounted_price}")
		exists = any(d.price_list == 'Standard Buying' for d in item.custom_item_price_details)
		if not exists:
			item.append('custom_item_price_details',{'item_code': item.item_code,'uom':ip.uom,'price_list':'Standard Buying','rate':float(discounted_price),'item_price':ip.name})
			item.save()
		if str(ip.price_list_rate) != str(discounted_price):
			ip.price_list_rate = discounted_price
			ip.save()
			for ipd in item.custom_item_price_details:
				if ip.name == ipd.item_price:
					ipd.rate = discounted_price
			item.save()
		# -----------------comment for now---------------------
