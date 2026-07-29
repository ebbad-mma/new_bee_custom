import json
import datetime
import keepa
import frappe
from frappe import _
import re
from frappe.utils import today
from .scraper_utils import scrape, set_images, extract_pid_with_regex
					

def sync_keepa_item(doc, event):
	accesskey = '4i9vbmksc3d9o67p6fd3s9aitdaaer17c604f3qrh93auu67fnh6pfucqvqltmjm'
	api = keepa.Keepa(accesskey)
	if doc.custom_asin_no:
		ASIN = [doc.custom_asin_no]
		if ASIN:
			if not frappe.db.exists('Item Details', {'asin_no': doc.custom_asin_no}):
				item_det = frappe.new_doc('Item Details')
				item_det.asin_no = doc.custom_asin_no
				item_det.save()
			if frappe.db.exists('Item Details', {'asin_no': doc.custom_asin_no}):
				item_detail = frappe.get_doc('Item Details', {'asin_no': doc.custom_asin_no})
			try:
				products = api.query(ASIN, stats=30, rating=True, update=0, domain="IN", history=1)
			except Exception as e:
				frappe.log_error(f"Invalid ASIN: {doc.custom_asin_no}")
				return
			else:
				for i in range(len(ASIN)):
					prod = products[i] if i < len(products) and isinstance(products[i], dict) else {}
					if not prod:
						continue
					brand_name = prod.get('brand')
					if brand_name:
						if not frappe.db.exists('Brand', {'brand': brand_name}):
							n_doc = frappe.new_doc('Brand')
							n_doc.brand = brand_name
							n_doc.insert()
						doc.brand = brand_name

					images_csv = prod.get("imagesCSV")
					images_list = []
					if images_csv:
						images_list = [img.strip() for img in images_csv.split(',') if img.strip()]
					elif prod.get("images"):
						for img_obj in prod["images"]:
							if isinstance(img_obj, dict):
								img_file = img_obj.get("l") or img_obj.get("m")
								if img_file:
									images_list.append(img_file)
							elif isinstance(img_obj, str) and img_obj.strip():
								images_list.append(img_obj.strip())

					if images_list:
						doc.image = "https://images-na.ssl-images-amazon.com/images/I/" + images_list[0]
						for ind, image_name in enumerate(images_list):
							field_name = f"custom_image{ind+1}"
							image_url = "https://images-na.ssl-images-amazon.com/images/I/" + image_name
							doc.set(field_name, image_url)

					item_detail.manufacturer = prod.get("manufacturer")
					listed_since = prod.get("listedSince")
					if listed_since:
						epoch_time = (listed_since + 21564000) * 60000
						listed_since_date = datetime.datetime.utcfromtimestamp(epoch_time / 1000)
						item_detail.listed_since = listed_since_date.strftime("%Y-%m-%d")
					
					last_rating_update = prod.get("lastRatingUpdate")
					if last_rating_update:
						epoch_time = (last_rating_update + 21564000) * 60
						last_rating_update_dt = datetime.datetime.utcfromtimestamp(epoch_time)
						item_detail.latest_rating_time = last_rating_update_dt.strftime("%Y-%m-%d")

					sales_ranks = prod.get("salesRanks")
					sales_rank_reference = prod.get("salesRankReference")
					if sales_ranks and sales_rank_reference:
						if str(sales_rank_reference) in sales_ranks:
							sales_rank_history = sales_ranks[str(sales_rank_reference)]
							if sales_rank_history:
								item_detail.sales_rank = str(sales_rank_history[-1])
					item_detail.sales_rank_reference = sales_rank_reference
					item_detail.url_amazon = f'https://www.amazon.in/dp/{doc.custom_asin_no}'
					
					csv_data = prod.get('csv') or []
					if len(csv_data) > 0:
						if len(csv_data) >= 18 and csv_data[17]:
							doc.reviews_count = csv_data[17][-1]
						if len(csv_data) >= 17 and csv_data[16]:
							doc.reviews_rating = str(csv_data[16][-1]/10)
					
					item_detail.parent_asin = prod.get("parentAsin")
					category_tree = []
					category_tree_dict = {}
					if prod.get('categoryTree'):
						category_tree = [c.get("name") for c in prod.get('categoryTree') if isinstance(c, dict) and c.get("name")]
						category_tree_dict = {c["catId"]: c["name"] for c in prod.get('categoryTree') if isinstance(c, dict) and "catId" in c and "name" in c}

					if category_tree:
						doc.category_sub = category_tree[-1]
						doc.categories_tree = ", ".join(category_tree)
					if category_tree_dict and prod.get('rootCategory'):
						doc.category_root = category_tree_dict.get(prod.get('rootCategory'))

					ean_list = prod.get('eanList')
					if ean_list:
						doc.ean = ean_list[0]

					if prod.get('upcList') is not None:
						item_detail.product_codes_upc = json.dumps(prod.get('upcList'))
					item_detail.launchpad = prod.get('launchpad')
					item_detail.product_codes_partnumber = prod.get('partNumber')
					frequently_bought_together = prod.get('frequentlyBoughtTogether')
					if isinstance(frequently_bought_together, (list, tuple)):
						item_detail.freq_bought_together = ", ".join(frequently_bought_together)
					else:
						item_detail.freq_bought_together = ""
					
					variations = prod.get('variations') or []
					asin_attributes = []
					if variations:
						v = [row.get('asin') for row in variations if isinstance(row, dict) and row.get('asin')]
						if v:
							item_detail.variation_asins = ", ".join(v)
						asin_attributes = [row.get('attributes') for row in variations if isinstance(row, dict) and row.get('asin')==doc.custom_asin_no and row.get('attributes')]
					if asin_attributes:
						attr_dict = [row for row in asin_attributes[0]]
						if attr_dict and isinstance(attr_dict[0], dict):
							item_detail.variation_attributes = f"{attr_dict[0].get('dimension')}: {attr_dict[0].get('value')}"
					
					item_detail.product_group = prod.get('productGroup')
					item_detail.number_of_items = prod.get('numberOfItems')
					
					pkg_h = prod.get('packageHeight')
					pkg_l = prod.get('packageLength')
					pkg_w = prod.get('packageWidth')
					if pkg_h is not None and pkg_l is not None and pkg_w is not None:
						item_detail.package_height = str(pkg_h / 10)
						item_detail.package_length = str(pkg_l / 10)
						item_detail.package_width = str(pkg_w / 10)
						pkg_dimension = str((pkg_l / 10) * (pkg_w / 10) * (pkg_h / 10))
						if (pkg_h / 10) > 0 and (pkg_l / 10) > 0 and (pkg_w / 10) > 0:
							item_detail.package_dimension = f"{item_detail.package_length} x {item_detail.package_width} x {item_detail.package_height} cm (= {pkg_dimension}) cm\u00b3"
					
					item_detail.package_weight = prod.get('packageWeight')
					item_detail.package_quantity = prod.get('packageQuantity')
					item_detail.model = prod.get('model')

					item_h = prod.get('itemHeight')
					item_l = prod.get('itemLength')
					item_w = prod.get('itemWidth')
					if item_h is not None and item_l is not None and item_w is not None:
						item_detail.item_length = str(item_l / 10)
						item_detail.item_breadth = str(item_w / 10)
						item_detail.item_height = str(item_h / 10)
						item_dimension = str((item_l / 10) * (item_w / 10) * (item_h / 10))
						if (item_l / 10) > 0 and (item_w / 10) > 0 and (item_h / 10) > 0:
							item_detail.length_dimension = f"{item_detail.item_length} x {item_detail.item_breadth} x {item_detail.item_height} cm (= {item_dimension} cm\u00b3)"
					
					item_detail.item_weight = prod.get('itemWeight')
					item_detail.size = prod.get('size')
					item_detail.color = prod.get('color')
					item_detail.desc_feature = prod.get("description") or ""
					if hasattr(doc, "desc_feature"):
						doc.desc_feature = prod.get("description") or ""
					item_detail.title = prod.get("title") or ""
					doc.title = prod.get("title") or ""
					
					features = prod.get('features') or []
					for f_idx in range(min(5, len(features))):
						setattr(item_detail, f"desc_feature{f_idx+1}", features[f_idx])
						if hasattr(doc, f"desc_feature_{f_idx+1}"):
							setattr(doc, f"desc_feature_{f_idx+1}", features[f_idx])

					stats_parsed = prod.get("stats_parsed")
					if stats_parsed:
						current = stats_parsed.get("current")
						avg30 = stats_parsed.get("avg30")
						avg90 = stats_parsed.get("avg90")
						avg180 = stats_parsed.get("avg180")
						lowest = stats_parsed.get("min")
						highest = stats_parsed.get("max")
						if current:
							item_detail.sales_rank_current_price = current.get("SALES")
							doc.last_price = current.get("LISTPRICE")
							doc.custom_new_current = current.get("NEW")
						if avg30:
							item_detail.sales_30_days_avg = avg30.get("SALES")
							item_detail.list_price_30_days_avg = avg30.get("LISTPRICE")
							item_detail.new_30_days_avg = avg30.get("NEW")
						if avg90:
							item_detail.sales_90_days_avg = avg90.get("SALES")
							item_detail.list_price_90_days_avg = avg90.get("LISTPRICE")
							item_detail.new_90_days_avg = avg90.get("NEW")
						if avg180:
							item_detail.sales_180_days_avg = avg180.get("SALES")
							item_detail.list_price_180_days_avg = avg180.get("LISTPRICE")
							item_detail.new_180_days_avg = avg180.get("NEW")
						if lowest:
							new_lowest = lowest.get("NEW")
							if new_lowest and len(new_lowest)==2:
								item_detail.new_lowest = new_lowest[1]
							lowest_listprice = lowest.get("LISTPRICE")
							if lowest_listprice and len(lowest_listprice)==2:
								item_detail.list_price_lowest = lowest_listprice[1]
						if highest:
							new_highest = highest.get("NEW")
							if new_highest and len(new_highest)==2:
								item_detail.new_highest = new_highest[1]
							highest_listprice = highest.get("LISTPRICE")
							if highest_listprice and len(highest_listprice)==2:
								doc.list_price_highest = highest_listprice[1]
				if doc.ean:
					item_detail.ean = doc.ean
				item_detail.save()
				doc.custom_item_detail = item_detail.name

	elif doc.ean:
		EAN = [doc.ean]
		if EAN:
			if not doc.custom_asin_no:
				if not frappe.db.exists('Item Details', {'ean': doc.ean}):
					item_det = frappe.new_doc('Item Details')
					item_det.ean = doc.ean
					item_det.save()
			if frappe.db.exists('Item Details', {'ean': doc.ean}):
				item_detail = frappe.get_doc('Item Details', {'ean': doc.ean})
			try:
				products = api.query(EAN, stats=30, rating=True, update=0, domain="IN", history=1, product_code_is_asin=False)
			except Exception as e:
				frappe.log_error(f"Invalid EAN: {doc.ean}")
				return
			
			if not products or not isinstance(products, list):
				frappe.log_error(f"No products found for {doc.ean}")
				return
			else:
				for i in range(len(EAN)):
					prod = products[i] if i < len(products) and isinstance(products[i], dict) else {}
					if not prod:
						continue
					brand_name = prod.get('brand')
					if brand_name:
						if not frappe.db.exists('Brand', {'brand': brand_name}):
							n_doc = frappe.new_doc('Brand')
							n_doc.brand = brand_name
							n_doc.insert()
						doc.brand = brand_name
					else:
						doc.brand = brand_name

					images_csv = prod.get("imagesCSV")
					if images_csv:
						images_list = [img.strip() for img in images_csv.split(',') if img.strip()]
						if images_list:
							doc.image = "https://images-na.ssl-images-amazon.com/images/I/" + images_list[0]
							for ind, image_name in enumerate(images_list):
								field_name = f"custom_image{ind+1}"
								image_url = "https://images-na.ssl-images-amazon.com/images/I/" + image_name
								doc.set(field_name, image_url)
					
					item_detail.manufacturer = prod.get("manufacturer")
					listed_since = prod.get("listedSince")
					if listed_since:
						epoch_time = (listed_since + 21564000) * 60000
						listed_since_date = datetime.datetime.utcfromtimestamp(epoch_time / 1000)
						item_detail.listed_since = listed_since_date.strftime("%Y-%m-%d")
					
					last_rating_update = prod.get("lastRatingUpdate")
					if last_rating_update:
						epoch_time = (last_rating_update + 21564000) * 60
						last_rating_update_dt = datetime.datetime.utcfromtimestamp(epoch_time)
						item_detail.latest_rating_time = last_rating_update_dt.strftime("%Y-%m-%d")
					
					sales_ranks = prod.get("salesRanks")
					sales_rank_reference = prod.get("salesRankReference")
					if sales_ranks and sales_rank_reference:
						if str(sales_rank_reference) in sales_ranks:
							sales_rank_history = sales_ranks[str(sales_rank_reference)]
							if sales_rank_history:
								item_detail.sales_rank = str(sales_rank_history[-1])
					item_detail.sales_rank_reference = sales_rank_reference
					doc.custom_asin_no = prod.get("asin") or doc.custom_asin_no
					item_detail.url_amazon = f'https://www.amazon.in/dp/{doc.custom_asin_no}'
					
					csv_data = prod.get('csv') or []
					if len(csv_data) > 0:
						if len(csv_data) >= 18 and csv_data[17]:
							doc.reviews_count = csv_data[17][-1]
						if len(csv_data) >= 17 and csv_data[16]:
							doc.reviews_rating = str(csv_data[16][-1]/10)
					
					item_detail.parent_asin = prod.get("parentAsin")
					category_tree = []
					category_tree_dict = {}
					if prod.get('categoryTree'):
						category_tree = [c.get("name") for c in prod.get('categoryTree') if isinstance(c, dict) and c.get("name")]
						category_tree_dict = {c["catId"]: c["name"] for c in prod.get('categoryTree') if isinstance(c, dict) and "catId" in c and "name" in c}

					if category_tree:
						doc.category_sub = category_tree[-1]
						doc.categories_tree = ", ".join(category_tree)
					if category_tree_dict and prod.get('rootCategory'):
						doc.category_root = category_tree_dict.get(prod.get('rootCategory'))
					
					ean_list = prod.get('eanList')
					if ean_list:
						doc.ean = ean_list[0]

					if prod.get('upcList') is not None:
						item_detail.product_codes_upc = json.dumps(prod.get('upcList'))
					item_detail.launchpad = prod.get('launchpad')
					item_detail.product_codes_partnumber = prod.get('partNumber')
					frequently_bought_together = prod.get('frequentlyBoughtTogether')
					if isinstance(frequently_bought_together, (list, tuple)):
						item_detail.freq_bought_together = ", ".join(frequently_bought_together)
					else:
						item_detail.freq_bought_together = ""
					
					variations = prod.get('variations') or []
					asin_attributes = []
					if variations:
						v = [row.get('asin') for row in variations if isinstance(row, dict) and row.get('asin')]
						if v:
							item_detail.variation_asins = ", ".join(v)
						asin_attributes = [row.get('attributes') for row in variations if isinstance(row, dict) and row.get('asin')==doc.custom_asin_no and row.get('attributes')]
					if asin_attributes:
						attr_dict = [row for row in asin_attributes[0]]
						if attr_dict and isinstance(attr_dict[0], dict):
							doc.variation_attributes = f"{attr_dict[0].get('dimension')}: {attr_dict[0].get('value')}"
					
					item_detail.product_group = prod.get('productGroup')
					item_detail.number_of_items = prod.get('numberOfItems')
					
					pkg_h = prod.get('packageHeight')
					pkg_l = prod.get('packageLength')
					pkg_w = prod.get('packageWidth')
					if pkg_h is not None and pkg_l is not None and pkg_w is not None:
						item_detail.package_height = str(pkg_h / 10)
						item_detail.package_length = str(pkg_l / 10)
						item_detail.package_width = str(pkg_w / 10)
						pkg_dimension = str((pkg_l / 10) * (pkg_w / 10) * (pkg_h / 10))
						if (pkg_h / 10) > 0 and (pkg_l / 10) > 0 and (pkg_w / 10) > 0:
							item_detail.package_dimention = f"{item_detail.package_length} x {item_detail.package_width} x {item_detail.package_height} cm (= {pkg_dimension}) cm\u00b3"
					
					item_detail.model = prod.get('model')
					item_h = prod.get('itemHeight')
					item_l = prod.get('itemLength')
					item_w = prod.get('itemWidth')
					if item_h is not None and item_l is not None and item_w is not None:
						item_detail.item_length = str(item_l / 10)
						item_detail.item_breadth = str(item_w / 10)
						item_detail.item_height = str(item_h / 10)
						item_dimension = str((item_l / 10) * (item_w / 10) * (item_h / 10))
						if (item_l / 10) > 0 and (item_w / 10) > 0 and (item_h / 10) > 0:
							item_detail.length_dimension = f"{item_detail.item_length} x {item_detail.item_breadth} x {item_detail.item_height} cm (= {item_dimension} cm\u00b3)"
					
					item_detail.size = prod.get('size')
					item_detail.color = prod.get('color')
					item_detail.desc_feature = prod.get("description") or ""
					item_detail.title = prod.get("title") or ""
					doc.title = prod.get("title") or ""

					features = prod.get('features') or []
					for f_idx in range(min(5, len(features))):
						setattr(item_detail, f"desc_feature{f_idx+1}", features[f_idx])

					stats_parsed = prod.get("stats_parsed")
					if stats_parsed:
						current = stats_parsed.get("current")
						avg30 = stats_parsed.get("avg30")
						avg90 = stats_parsed.get("avg90")
						avg180 = stats_parsed.get("avg180")
						lowest = stats_parsed.get("min")
						highest = stats_parsed.get("max")
						if current:
							item_detail.sales_rank_current_price = current.get("SALES")
							doc.last_price = current.get("LISTPRICE")
							doc.custom_new_current = current.get("NEW")
						if avg30:
							item_detail.sales_30_days_avg = avg30.get("SALES")
							item_detail.list_price_30_days_avg = avg30.get("LISTPRICE")
							item_detail.new_30_days_avg = avg30.get("NEW")
						if avg90:
							item_detail.sales_90_days_avg = avg90.get("SALES")
							item_detail.list_price_90_days_avg = avg90.get("LISTPRICE")
							item_detail.new_90_days_avg = avg90.get("NEW")
						if avg180:
							item_detail.sales_180_days_avg = avg180.get("SALES")
							item_detail.list_price_180_days_avg = avg180.get("LISTPRICE")
							item_detail.new_180_days_avg = avg180.get("NEW")
						if lowest:
							new_lowest = lowest.get("NEW")
							if new_lowest and len(new_lowest)==2:
								item_detail.new_lowest = new_lowest[1]
							lowest_listprice = lowest.get("LISTPRICE")
							if lowest_listprice and len(lowest_listprice)==2:
								item_detail.list_price_lowest = lowest_listprice[1]
						if highest:
							new_highest = highest.get("NEW")
							if new_highest and len(new_highest)==2:
								item_detail.new_highest = new_highest[1]
							highest_listprice = highest.get("LISTPRICE")
							if highest_listprice and len(highest_listprice)==2:
								doc.list_price_highest = highest_listprice[1]

					if doc.custom_asin_no:
						item_detail.asin_no = doc.custom_asin_no
					item_detail.save()
				# frappe.msgprint(_("Item(s) has been synced with keepa"))
	
	elif doc.custom_url or doc.custom_fsn_no:
		if doc.custom_url:
			if not frappe.db.exists('Item Details', {'url': doc.custom_url}):
				item_det = frappe.new_doc('Item Details')
				item_det.url = doc.custom_url
				item_det.fsn_no = doc.custom_fsn_no
				item_det.save()
			if frappe.db.exists('Item Details', {'fsn_no': doc.custom_fsn_no}):
				item_detail = frappe.get_doc('Item Details', {'fsn_no': doc.custom_fsn_no})
		if doc.custom_fsn_no:
			if not frappe.db.exists('Item Details', {'fsn_no': doc.custom_fsn_no}):
				item_det = frappe.new_doc('Item Details')
				item_det.url = doc.custom_url
				item_det.fsn_no = doc.custom_fsn_no
				item_det.save()
			if frappe.db.exists('Item Details', {'fsn_no': doc.custom_fsn_no}):
				item_detail = frappe.get_doc('Item Details', {'fsn_no': doc.custom_fsn_no})

		category_names = frappe.db.get_list("Item Category", fields=['category_name'], pluck='category_name')

		if doc.custom_url:
			fsn = extract_pid_with_regex(doc.custom_url)
		else:
			fsn = doc.custom_fsn_no

		doc.custom_fsn_no = fsn
		frappe.log_error("FSN",fsn)
		data = scrape(fsn)
		frappe.log_error("FSN DATA",data)

		doc.item_name = data['title'][0:130]
		doc.description = data['description']
		item_detail.set('item_groups', [])

		for category in data['categories']:
			if category not in category_names:
				cat = frappe.new_doc("Item Category")
				cat.category_name = category
				cat.insert()
				item_detail.append("item_groups", {
					'item_group': cat.name
				})
			else:
				item_category_id = frappe.db.get_value('Item Category', {'category_name': category})
				item_detail.append('item_groups', {
					'item_group': item_category_id
				})

		doc.image = data['image_url']
		set_images(doc, data['multiple_images'])

		item_detail.model_flipkart = data['specifications'].get('General', {}).get('Model Name', "")
		dims = data['specifications'].get("Dimensions", {})
		item_detail.length_breadth = dims.get('Width', "")
		item_detail.length_height = dims.get('Height', "")

		doc.custom_mrp = data['price']
		item_detail.title_flipkart = data['title']
		item_detail.flipkart_rating = data['rating']
		reviews=data['reviews'].split(" ")[0]
		item_detail.flipkart_reviews_count =reviews
		item_detail.flipkart_ratings_count = data['ratings']
		item_detail.fsn_no = doc.custom_fsn_no
		item_detail.flipkart_dis_per =data['discount']
		item_detail.spec_html_data = str(data['general'])
		item_detail.save()
		doc.custom_item_detail=item_detail.name

