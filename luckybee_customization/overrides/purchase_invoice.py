import frappe
import json
import time
from frappe.utils import today


@frappe.whitelist()
def search_and_insert_item(doc, description, hsn, qty, rate, per, disc_perc, disc, gst, mrp, lrp, brand, group, category, sub_category):
	doc = json.loads(doc)

	dict_itm = {}
	if description :

		#create UOM
		if not frappe.db.exists('UOM',{'uom_name': per}):
			uom=frappe.new_doc('UOM')
			uom.uom_name=per
			uom.enabled=1
			uom.insert()
		#calculate buying price
		if disc_perc: 
			rate = float(rate)
			disc_perc = float(disc_perc)
			discounted_price = rate - (rate * (disc_perc / 100))

			
		item_code_exist = frappe.db.exists('Item', {'item_name':description}, 'item_code')

		if not item_code_exist:
			item = frappe.new_doc("Item")
			# item.naming_series = 'L.#####'
			# item.item_code=custom_purchase_item
			item.stock_uom = per
			item.gst_hsn_code = ''
			item.item_name = description
			item.item_group = 'All Groups'
			item.custom_mrp = mrp
			item.gst_hsn_code = hsn
			item.custom_luckybee_brand = brand
			item.custom_group = group

			item.custom_category = category
			item.custom_category_sub = sub_category

			
			gst = ""
			frappe.log_error(f"{disc}")
			# if disc_perc:
			# --------------------comment for now-----------------
			if disc == "15.25":
				gst = "GST 18% - SR"
			elif disc == "10.71":
				gst = "GST 12% - SR"
			elif disc == "4.71":
				gst = "GST 5% - SR"
			row = item.append("taxes", {})
			row.item_tax_template = gst
			# --------------------comment for now-----------------


			item.opening_stock=rate
			item.standard_rate=rate
			item.size=qty
			item.save()
			item.custom_barcode = item.item_code
			barcode_row = item.append("barcodes", {})
			barcode_row.barcode = item.item_code
			item.save()
			# if disc_perc:
			create_item_price(item, lrp, discounted_price)
		else:
			item = frappe.get_doc("Item", item_code_exist)

			# if disc_perc:
			create_item_price(item, lrp, discounted_price)
			# frappe.log_error(title="item code ", message = f'item starts with: {(item.item_code).startswith("L1")}, length: { len(item.item_code)} , item:{ item_code_exist}')
			# frappe.log_error(title="MRP", message = f'item.custom_mrp: {item.custom_mrp}, mrp: {mrp}')
			if item and (item.item_code).startswith("L1") and len(item.item_code) == 6:
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
				if item.custom_sub_category != sub_category:
					item.custom_sub_category = sub_category
				if not item.custom_barcode:
					item.custom_barcode = item.item_code
					barcode_row = item.append("barcodes", {})
					barcode_row.barcode = item.item_code
				item.save()

				time.sleep(5)
		# if disc_perc:
			# dict_itm.update({"item_code": frappe.db.get_value("Item", {"item_name": description}, 'item_code'),
			# 				"qty": qty, "item_name": description, "uom": "Nos", "rate": discounted_price, "amount": int(qty)*float(discounted_price)})
		item_code, reviews_rating,last_purchase_rate = frappe.db.get_value("Item", {"item_name": description}, ['item_code', 'custom_reviews_rating','last_purchase_rate'])
		dict_itm.update({
							"item_code": item_code,
							"reviews_rating": reviews_rating,
							"qty": qty,
							"item_name": description,
							"uom": "Nos",
							"rate": discounted_price,
							"amount": int(qty)*float(discounted_price),
							"last_purchase_rate":last_purchase_rate,
							"last_purchase_rate":last_purchase_rate,
							"custom_mrp":mrp
						})
		# else:
		# 	item_code, reviews_rating,new_current,reviews_count = frappe.db.get_value("Item", {"item_name": description}, ['item_code', 'reviews_rating','new_current','reviews_count'])
		# 	dict_itm.update({
		# 						"item_code": item_code,
		# 						"reviews_rating": reviews_rating,
		# 						"qty": qty,
		# 						"item_name": description,
		# 						"uom": "Nos",
		# 						"new_current":float(new_current) if new_current else 0,
		# 						"custom_asin":custom_asin,
		# 						"rate":rate,
		# 						"custom_box_number":custom_box_number,
		# 						"custom_reviews_count":int(reviews_count)
		# 					})

			# dict_itm.update({"item_code",'reviews_rating': frappe.db.get_value("Item", {"item_name": description}, ['item_code','reviews_rating']),
			# 				"qty": qty, "item_name": description, "uom": "Nos"})
		
		# dict_itm.update({"item_code": frappe.db.get_value("Item", {"item_name": description}, 'item_code'),
		# 					"qty": qty, "item_name": description, "uom": "Nos", "rate": rate, "amount": int(qty)*int(rate)})
		return dict_itm






# ---------------------------create item price---------------------------------
def create_item_price(item, lrp=None, discounted_price=None):
	if not frappe.db.exists("Item Price", {"item_code": item.item_code, "price_list": "Standard Selling"}):
		frappe.log_error("not exists ss")
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
		frappe.log_error("not exists sb")
		item_price = frappe.new_doc("Item Price")
		item_price.item_code = item.item_code
		item_price.price_list = "Standard Buying"
		item_price.buying = 1
		item_price.item_name = item.item_name
		item_price.uom = item.stock_uom
		item_price.valid_from = today()
		item_price.price_list_rate = discounted_price
		item_price.save()

	else:
		# -----------------comment for now---------------------
		ip = frappe.get_doc("Item Price", {"item_code": item.item_code, "price_list": "Standard Selling"})
		frappe.log_error("IP",ip)
		if str(ip.price_list_rate) != str(lrp):
			ip.price_list_rate = lrp
			ip.save()
			for ipd in item.custom_item_price_details:
				if ip.name == ipd.item_price:
					ipd.rate = lrp
			# item.save()

		ip = frappe.get_doc("Item Price", {"item_code": item.item_code, "price_list": "Standard Buying"})
		if str(ip.price_list_rate) != str(discounted_price):
			ip.price_list_rate = discounted_price
			ip.save()
			for ipd in item.custom_item_price_details:
				if ip.name == ipd.item_price:
					ipd.rate = discounted_price
		item.save()
		frappe.log_error("iii",item.name)
		# -----------------comment for now---------------------
