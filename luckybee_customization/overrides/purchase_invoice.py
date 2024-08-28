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
		#create Brand
		if not frappe.db.exists('Brand',{'brand':brand}):
			br=frappe.new_doc('Brand')
			br.brand=brand
			br.insert()
		#calculate buying price
		if disc_perc: 
			rate = float(rate)
			disc_perc = float(disc_perc)
			discounted_price = rate - (rate * (disc_perc / 100))

			
		item_code_exist = frappe.db.exists('Item', {'item_name':description}, 'item_code')
		if item_code_exist:
			item=frappe.get_doc('Item',{'item_name':description})
			supplierNrate={'last_supplier':[],"last_rate":[]}
			if brand=='ASSR':
				if not frappe.db.exists('Brand','TREO'):
					b=frappe.new_doc('Brand')
					b.brand='TREO'
					b.insert()
				item.brand='TREO'
				item.custom_luckybee_brand='TREO'
			if brand=="CLAY":
				if not frappe.db.exists('Brand','CLAY CRAFT'):
					b=frappe.new_doc('Brand')
					b.brand='CLAY CRAFT'
					b.insert()
				item.brand='CLAY CRAFT'
				item.custom_luckybee_brand='CLAY CRAFT'
			else:
				item.brand=brand
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
			# frappe.log_error("obefore change",f"{item.opening_stock} {item.name}")
			# item.opening_stock+=float(qty)
			# frappe.log_error("before save",f"{item.opening_stock} {item.name}")
			item.save()


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
			item.custom_last_supplier=doc['supplier']
			item.custom_last_supplier_purchase_rate=float(rate)
			item.append('item_defaults',{'company':'Samyak Resources','default_warehouse':'Stores - SR'})
			# item.append('custom_supplier_history',{'supplier':doc['supplier'],'rate':float(rate)})
			if brand=='ASSR':
				if not frappe.db.exists('Brand','TREO'):
					b=frappe.new_doc('Brand')
					b.brand='TREO'
					b.insert()
				item.brand='TREO'
				item.custom_luckybee_brand='TREO'
			if brand=="CLAY":
				if not frappe.db.exists('Brand','TREO'):
					b=frappe.new_doc('Brand')
					b.brand='TREO'
					b.insert()
				item.brand='CLAY CRAFT'
				item.custom_luckybee_brand='CLAY CRAFT'
			else:
				item.brand=brand
			item.custom_luckybee_brand = brand
			item.custom_group = group

			item.custom_category = category
			item.custom_category_sub = sub_category

			
			gst = ""
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


			# item.opening_stock=qty
			item.standard_rate=rate
			item.size=qty
			item.insert()
			item.custom_barcode = item.item_code
			barcode_row = item.append("barcodes", {})
			barcode_row.barcode = item.item_code
			item.save()
			# if disc_perc:
			# create_item_price(item, lrp, discounted_price)
		else:
			item = frappe.get_doc("Item", item_code_exist)

			# if disc_perc:
			# create_item_price(item, lrp, discounted_price)
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
							"uom": per,
							"rate": discounted_price,
							"amount": int(qty)*float(discounted_price),
							"last_purchase_rate":last_purchase_rate,
							"last_purchase_rate":last_purchase_rate,
							"custom_mrp":mrp
						})
		return dict_itm

