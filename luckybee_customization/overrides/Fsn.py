import frappe
import json
import time
from frappe.utils import today


@frappe.whitelist()
def search_and_insert_item(doc,description,fsn, qty, rate, per, mrp, lrp):
	doc = json.loads(doc)
	dict_itm = {}
	if description :

		#create UOM
		if not frappe.db.exists('UOM',{'uom_name': per}):
			uom=frappe.new_doc('UOM')
			uom.uom_name=per
			uom.enabled=1
			uom.insert()

		item_code_exist = frappe.db.exists('Item', {'item_name':description}, 'item_code')
		if item_code_exist:
			item=frappe.get_doc('Item',{'item_name':description})
			supplierNrate={'last_supplier':[],"last_rate":[]}
			if item.custom_last_supplier:
				supplierNrate['last_supplier'].append(doc['supplier'])
				supplierNrate['last_rate'].append(float(rate))
				supplierNrate['last_supplier'].append(item.custom_last_supplier)
				supplierNrate['last_rate'].append(item.custom_last_supplier_purchase_rate)
				item.custom_last_supplier=doc['supplier']
				item.custom_last_supplier_purchase_rate=float(rate)
				for last_supplier,last_rate in zip(supplierNrate['last_supplier'], supplierNrate['last_rate']):
					item.append('custom_supplier_history', {'supplier': last_supplier, 'rate':last_rate})
			item.save()


		if not item_code_exist:
			item = frappe.new_doc("Item")
			item.stock_uom = per
			item.item_name = description
			item.item_group = 'All Groups'
			item.custom_mrp = mrp
			item.custom_fsn_no = fsn
			item.custom_last_supplier=doc['supplier']	

			item.standard_rate=rate
			item.save()
			item.custom_barcode = item.item_code
			barcode_row = item.append("barcodes", {})
			barcode_row.barcode = item.item_code
			item.save()
			if item and (item.item_code).startswith("L1") and len(item.item_code) == 6:
				if item.custom_mrp and float(mrp) > 0 and float(item.custom_mrp) != float(mrp) :
					item.custom_mrp = mrp
				if not item.custom_barcode:
					item.custom_barcode = item.item_code
					barcode_row = item.append("barcodes", {})
					barcode_row.barcode = item.item_code
				item.save()

				time.sleep(5)
		item_code, reviews_rating,last_purchase_rate = frappe.db.get_value("Item", {"item_name": description}, ['item_code', 'custom_reviews_rating','last_purchase_rate'])
		dict_itm.update({
							"item_code": item_code,
							"qty": qty,
							"item_name": description,
							"uom":per,
							"custom_mrp":mrp
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
