import frappe
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
def search_and_insert_item(doc, description, hsn, qty, rate, per, disc1,disc2,disc3, disc, gst, mrp, lrp, brand, group, category, sub_category,item_index):
	frappe.log_error("Mrp",mrp)
	frappe.log_error(f"{disc1}-{disc2}-{disc3}-{disc}")
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
		if brand:
			if not frappe.db.exists('Brand',{'brand':brand}):
				br=frappe.new_doc('Brand')
				br.brand=brand
				br.insert()
		

		item_code_exist = frappe.db.exists('Item', {'item_name':description}, 'item_code')
		if item_code_exist:
			#brand
			new_brand=""
			if brand=='ASSR':
				if not frappe.db.exists('Brand','TREO'):
					b=frappe.new_doc('Brand')
					b.brand='TREO'
					b.insert()
				new_brand='TREO'
			if brand=="CLAY":
				if not frappe.db.exists('Brand','CLAY CRAFT'):
					b=frappe.new_doc('Brand')
					b.brand='CLAY CRAFT'
					b.insert()
				new_brand='CLAY CRAFT'
			else:
				new_brand=brand

			#last supplier history
			supplierNrate={'last_supplier':[],"last_rate":[]}
			# Fetch the existing supplier and rate information
			custom_last_supplier, custom_last_supplier_purchase_rate = frappe.db.get_value(
				'Item', item_code_exist, ['custom_last_supplier', 'custom_last_supplier_purchase_rate']
			)

			# Update the supplier history
			if custom_last_supplier:
				# supplierNrate['last_supplier'].append(doc['supplier'])
				# supplierNrate['last_rate'].append(safe_float_conversion(str(rate)))
				supplierNrate['last_supplier'].append(custom_last_supplier)
				supplierNrate['last_rate'].append(custom_last_supplier_purchase_rate)

				# Update the last supplier information
				frappe.db.set_value('Item', item_code_exist, {
					'custom_last_supplier': doc['supplier'],
					'custom_last_supplier_purchase_rate':safe_float_conversion(str(rate))
				})



				# Step 2: Insert new supplier entries first
				for last_supplier, last_rate in zip(supplierNrate['last_supplier'], supplierNrate['last_rate']):
					new_entry = frappe.get_doc({
						'doctype': 'Supplier History',  # Replace with your actual child doctype name
						'parent': item_code_exist,
						'parentfield': 'custom_supplier_history',  # Field name for the child table
						'parenttype': 'Item',
						'supplier': last_supplier,
						'rate': last_rate
					})
					new_entry.insert(ignore_permissions=True)

			#set tax template
			gst = ""
			disc=str(disc)
			# if disc_perc:
			if disc == "15.25":
				gst = "GST 18% - SR"
			elif disc == "10.71":
				gst = "GST 12% - SR"
			elif disc == "4.71":
				gst = "GST 5% - SR"
			# Clear existing taxes and add new tax entry manually
			frappe.db.sql('DELETE FROM `tabItem Tax` WHERE parent=%s', item_code_exist)
			tax_entry = frappe.get_doc({
				'doctype': 'Item Tax',  # Replace with your child table doctype
				'parent': item_code_exist,
				'parentfield': 'taxes',
				'parenttype': 'Item',
				'item_tax_template': gst
			})
			tax_entry.insert(ignore_permissions=True)


			# update multiple values
			frappe.db.set_value('Item',item_code_exist, {
				'custom_mrp':safe_float_conversion(str(mrp)),
				'gst_hsn_code':hsn,
				'custom_luckybee_brand':new_brand,
				'brand':new_brand,
				'custom_group':group,
				'custom_category':category,
				'custom_category_sub':sub_category,
				'custom_barcode':item_code_exist,
				'custom_last_supplier':doc['supplier'],
				'custom_last_supplier_purchase_rate':safe_float_conversion(str(rate))

			})
			

		if not item_code_exist:
			frappe.log_error("new")
			item = frappe.new_doc("Item")
			# item.naming_series = 'L.#####'
			# item.item_code=custom_purchase_item
			item.stock_uom = per
			item.gst_hsn_code = ''
			if len(description)>130:
				description=description[:130]
			else:
				description=description
			item.item_name=description
			item.item_group = 'All Groups'
			item.custom_mrp = mrp
			item.gst_hsn_code = hsn
			item.custom_last_supplier=doc['supplier']
			item.custom_last_supplier_purchase_rate=safe_float_conversion(str(rate))
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

			disc=str(disc)
			gst = ""
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
		item_code, reviews_rating,last_purchase_rate = frappe.db.get_value("Item", {"item_name": description}, ['item_code', 'custom_reviews_rating','last_purchase_rate'])
		dict_itm.update({
							"item_code": item_code,
							"reviews_rating": reviews_rating,
							"qty": qty,
							"item_name": description,
							"uom": per,
							"rate": rate,
							"amount": int(qty)*safe_float_conversion(str(rate)),
							"last_purchase_rate":last_purchase_rate,
							"last_purchase_rate":last_purchase_rate,
							"custom_mrp":mrp,
							"gst_disc":disc,
							"disc1":disc1,
							"disc2":disc2,
							"disc3":disc3,
							"gst_template":gst,
							"item_index":int(item_index),
							"group":group,
							"category":category,
							"sub_category":sub_category
						})
		frappe.log_error("dict",dict_itm)
		return dict_itm

