import frappe
import json
import time
from frappe.utils import today
from frappe.model.document import Document
def safe_int(value, default=0):
	try:
		return int(value)
	except (TypeError, ValueError):
		return default
def safe_float_conversion(rate, default_value=0.0):
    try:
        rate_cleaned = rate.replace(',', '')
        return float(rate_cleaned)
    except ValueError:
        frappe.msgprint(f"Could not convert rate '{rate}' to float.")
        return default_value



@frappe.whitelist()
def search_and_insert_item(doc,description, hsn, qty, rate, per, mrp, lrp, brand, group, category, sub_category,custom_asin,custom_box_number, custom_ean,disc, disc1,disc2,disc3,amount,item_index):
	frappe.log_error('MRP',mrp)
	doc = json.loads(doc)
	item_name=''
	dict_itm = {}
	if description :
		#create Brand
		if brand:
			if not frappe.db.exists('Brand',{'brand':brand}):
				br=frappe.new_doc('Brand')
				br.brand=brand
				br.insert()
		
		mrp=safe_float_conversion(str(mrp))
		frappe.log_error("int",mrp)
		item_code_exist = frappe.db.get_value('Item', {'item_name':description}, 'item_code')
		if not item_code_exist:
			item = frappe.new_doc("Item")
			# item.naming_series = 'L.#####'
			item.item_code=item.naming_series
			# item.item_code=custom_purchase_item
			item.custom_last_supplier=doc['supplier']
			item.custom_last_supplier_purchase_rate=safe_float_conversion(str(rate))
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
			item.brand = brand
			item.custom_group = group
			item.custom_category = category
			item.custom_sub_category = sub_category
			item.custom_asin_no = custom_asin
			item.custom_box_number=custom_box_number
			item.custom_ean = custom_ean
			item.append('item_defaults',{'company':'Samyak Resources','default_warehouse':'Stores - SR'})
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
					# supplierNrate['last_supplier'].append(doc['supplier'])
					# supplierNrate['last_rate'].append(safe_float_conversion(str(rate)))
					supplierNrate['last_supplier'].append(custom_last_supplier)
					supplierNrate['last_rate'].append(custom_last_supplier_purchase_rate)

					# Update the last supplier information
					frappe.db.set_value('Item', item_code_exist, {
						'custom_last_supplier': doc['supplier'],
						'custom_last_supplier_purchase_rate':safe_float_conversion(str(rate))
					})

					# for last_supplier, last_rate in zip(supplierNrate['last_supplier'], supplierNrate['last_rate']):
					# 	child = frappe.get_doc({
					# 		'doctype': 'Supplier History',  # Replace with your actual child doctype name
					# 		'parent': item_code_exist,
					# 		'parentfield': 'custom_supplier_history',  # Field name for the child table
					# 		'parenttype': 'Item',
					# 		'supplier': last_supplier,
					# 		'rate': last_rate,
					# 		'idx': 1 
					# 	})
					# 	child.insert(ignore_permissions=True)
					# Step 1: Fetch all existing child entries for the specific parent (item_code_exist)
					old_entries = frappe.get_all(
						'Supplier History',  # Replace with your actual child doctype name
						filters={'parent': item_code_exist, 'parenttype': 'Item'},
						fields=['name', 'supplier', 'rate'],
						order_by='idx'  # Fetch them in their existing order
					)

					# Step 2: Insert new supplier entries first
					new_entries = []
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
						new_entries.append(new_entry)

					# Step 3: Delete old entries
					for entry in old_entries:
						frappe.delete_doc('Supplier History', entry['name'], ignore_permissions=True)

					# Step 4: Reinsert old entries after the new entries
					for entry in old_entries:
						child = frappe.get_doc({
							'doctype': 'Supplier History',  # Replace with your actual child doctype name
							'parent': item_code_exist,
							'parentfield': 'custom_supplier_history',  # Field name for the child table
							'parenttype': 'Item',
							'supplier': entry['supplier'],
							'rate': entry['rate']
						})
						child.insert(ignore_permissions=True)

				# Set the tax template based on the discount
				gst = ""
				disc = str(disc)
				if disc == "15.25":
					gst = "GST 18% - SR"
				elif disc == "10.71":
					gst = "GST 12% - SR"
				elif disc == "4.71":
					gst = "GST 5% - SR"

				# Clear existing tax entries and add new ones
				frappe.db.sql('DELETE FROM `tabItem Tax` WHERE parent=%s', item_code_exist)
				tax_entry = frappe.get_doc({
					'doctype': 'Item Tax',  # Replace with your actual child table doctype
					'parent': item_code_exist,
					'parentfield': 'taxes',
					'parenttype': 'Item',
					'item_tax_template': gst
				})
				tax_entry.insert(ignore_permissions=True)

				# Update multiple values
				frappe.db.set_value('Item', item_code_exist, {
					'custom_mrp': safe_float_conversion(str(mrp)),
					'gst_hsn_code': hsn,
					'custom_luckybee_brand': brand,
					'brand': brand,
					'custom_group': group,
					'custom_category': category,
					'custom_category_sub': sub_category,
					'custom_barcode': item_code_exist,
					'custom_last_supplier': doc['supplier'],
					'custom_last_supplier_purchase_rate': safe_float_conversion(str(rate))
				})


		result = frappe.db.get_value("Item", {"item_name": description}, ['item_code', 'custom_reviews_rating', 'custom_new_current', 'custom_reviews_count', 'custom_last_supplier_purchase_rate', 'custom_last_price', 'custom_list_price_highest'])
		frappe.log_error('RESULT',f"{result}///{description}")			
		item_code, reviews_rating,new_current,reviews_count,last_purchase_rate,last_price,list_price_highest= frappe.db.get_value("Item", {"item_name": description}, ['item_code', 'custom_reviews_rating','custom_new_current','custom_reviews_count','custom_last_supplier_purchase_rate','custom_last_price','custom_list_price_highest'])
		# mrp=int(last_price) if int(last_price) > 0 else int(list_price_highest)
		last_price_safe = safe_int(last_price)
		list_price_highest_safe = safe_int(list_price_highest)
		# mrp = last_price_safe if last_price_safe > 0 else list_price_highest_safe
		if reviews_count is not None:
			reviews_count=int(reviews_count)
		
		# get item details to calculatelrp 
		avg_30, avg_90 = None, None
		if frappe.db.exists('Item Details',{'item':item_name}):
			avg_30, avg_90 = frappe.db.get_value(
													'Item Details', 
													{'item': item_name}, 
													['list_price_30_days_avg', 'list_price_90_days_avg']
												) or (None, None)
		dict_itm.update({
							"item_code": item_code,
							"reviews_rating": reviews_rating,
							"qty": qty,
							"item_name": description,
							"uom":per,
							"new_current":safe_float_conversion(str(new_current)) if new_current else 0,
							"avg_30":safe_float_conversion(str(avg_30)) if avg_30 else 0,
							"avg_90":safe_float_conversion(str(avg_90)) if avg_90 else 0,
							"custom_asin":custom_asin,
							"rate":rate,
							"custom_box_number":custom_box_number,
							"custom_reviews_count":reviews_count,
							"last_purchase_rate":last_purchase_rate,
							"mrp":safe_float_conversion(str(mrp)),
							"amount":safe_float_conversion(str(amount)),
							"gst_disc":disc,
							"disc1":disc1,
							"disc2":disc2,
							"disc3":disc3,
							"gst_template":gst,
							"item_index":int(item_index)
						})
		frappe.log_error("dict",dict_itm)
	return dict_itm

