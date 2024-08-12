import json
import datetime
import keepa
import frappe
from frappe import _
import re
from frappe.utils import today
from .scraper_utils import scrape, set_images, extract_pid_with_regex

def update_item(doc, event):
	accesskey = '4i9vbmksc3d9o67p6fd3s9aitdaaer17c604f3qrh93auu67fnh6pfucqvqltmjm'
	api = keepa.Keepa(accesskey)
	ASIN = [row.custom_asin for row in doc.items if row.custom_asin]
	if ASIN:
		try:
			products = api.query(ASIN, stats=30, rating=True, update=0, domain="IN", history=1)
			for i in range(len(ASIN)):
				item = frappe.get_doc("Item", {"custom_asin_no": ASIN[i]})
				if frappe.db.exists('Item Details',{'asin_no':doc.custom_asin_no}):
					item_detail=frappe.get_doc('Item Details',{'asin_no':doc.custom_asin_no})
				if item:
					item.custom_amzon_item_name = products[i]["title"]
					item_detail.title = products[i]["title"]
					if not frappe.db.exists('Brand',products[i]['brand']):
						# create a new brand if does not exists
						doc = frappe.new_doc('Brand')
						doc.brand =products[i]['brand']
						doc.insert()
						item.brand = products[i]['brand']
					else:
						item.brand = products[i]['brand']
					if products[i]["imagesCSV"]:
						item.image = "https://images-na.ssl-images-amazon.com/images/I/" + products[i]["imagesCSV"].split(',')[0]
						for ind,image_name in enumerate(products[i]["imagesCSV"].split(",")):
							field_name = f"custom_image{ind+1}"
							image_url = "https://images-na.ssl-images-amazon.com/images/I/" + image_name
							item.set(field_name,image_url)
					item_detail.manufacturer = products[i]["manufacturer"]
					if products[i]['listedSince']:
						epoch_time = (products[i]["listedSince"]+ 21564000) * 60000
						listed_since_date = datetime.datetime.utcfromtimestamp(epoch_time / 1000)
						item_detail.listed_since = listed_since_date.strftime("%Y-%m-%d")
					
					if products[i]["lastRatingUpdate"]:
						epoch_time = (products[i]["lastRatingUpdate"]+ 21564000) * 60
						last_rating_update = datetime.datetime.utcfromtimestamp(epoch_time)
						item_detail.latest_rating_time = last_rating_update.strftime("%Y-%m-%d")

					sales_ranks = products[i]["salesRanks"]
					sales_rank_reference = products[i]["salesRankReference"]
					if sales_ranks and sales_rank_reference:
						if str(sales_rank_reference) in sales_ranks:
							sales_rank_history = sales_ranks[str(sales_rank_reference)]
							item_detail.sales_rank = str(sales_rank_history[-1])
					item_detail.sales_rank_reference = products[i]['salesRankReference']
					item_detail.url_amazon = f'https://www.amazon.in/dp/{ASIN[i]}'
					if len(products[i]['csv']) > 0:
						if len(products[i]['csv']) >= 17:
							if products[i]['csv'][17]:
								item.custom_reviews_count = products[i]['csv'][17][-1]
						if len(products[i]['csv']) >= 16:
							if products[i]['csv'][16]:
								item.custom_reviews_rating = str(products[i]['csv'][16][-1]/10)
					item_detail.parent_asin = products[i]["parentAsin"]
					category_tree = []
					category_tree_dict = {}
					if products[i].get('categoryTree'):
						category_tree = [i.get("name") for i in products[i].get('categoryTree')]
						category_tree_dict = {i["catId"]:i["name"] for i in products[i]['categoryTree']}

					if category_tree:
						item.category_sub = category_tree[-1]
						item.custom_categories_tree = ", ".join(category_tree)
					if category_tree_dict:
						item.custom_category_root = category_tree_dict.get(products[0].get('rootCategory'))
					
					# item.ean =  re.findall('[0-9]+', json.dumps(products[i]['eanList'][0]))[0] if products[i]['eanList'] is not None else ''
					item.custom_ean =  products[i]['eanList'][0] if products[i]['eanList'] else ''

					item_detail.product_codes_upc = json.dumps(products[i]['upcList'])
					item_detail.launchpad = products[i]['launchpad']  # currently a data field, should be checkbox
					item_detail.product_codes_partnumber = products[i]['partNumber']
					frequently_bought_together = products[i]['frequentlyBoughtTogether']
					if isinstance(frequently_bought_together, (list, tuple)):
						item_detail.freq_bought_together = ", ".join(frequently_bought_together)
					else:
						item_detail.freq_bought_together = ""
					variations = products[i]['variations']
					if variations:
						v = [row.get('asin') for row in variations]
						if v:
							item_detail.variation_asins = ", ".join(v)
					asin_attributes = [row.get('attributes') for row in variations if row.get('asin')==ASIN[i] and row.get('attributes')]
					if asin_attributes:
						attr_dict = [row for row in asin_attributes[0]]
						if attr_dict:
							item.variation_attributes = f"{attr_dict[0].get('dimension')}: {attr_dict[0].get('value')}"
					item_detail.product_group = products[i]['productGroup']
					item_detail.number_of_items = products[i]['numberOfItems']
					item_detail.package_height = str(products[i]['packageHeight']/10)
					item_detail.package_length = str(products[i]['packageLength']/10)
					item_detail.package_width = str(products[i]['packageWidth']/10)
					item_detail.package_weight = products[i]['packageWeight']
					item_detail.package_quantity = products[i]['packageQuantity']
					pkg_dimension = str(products[i]['packageLength']/10 * products[i]['packageWidth']/10 * products[i]['packageHeight']/10)
					if products[i]['packageHeight']/10 > 0 and products[i]['packageLength']/10 > 0 and products[i]['packageWidth']/10 > 0:
						item_detail.package_dimension = f"{item_detail.package_length} x {item_detail.package_width} x {item_detail.package_height} cm (= {pkg_dimension}) cm\u00b3"
					item_detail.model = products[i]['model']
					item_detail.item_length = str(products[i]['itemLength']/10)
					item_detail.item_breadth = str(products[i]['itemWidth']/10)
					item_detail.item_height = str(products[i]['itemHeight']/10)
					item_detail.item_weight = products[i]['itemWeight']
					item_dimension = str(products[i]['itemLength']/10 * products[i]['itemWidth']/10 * products[i]['itemHeight']/10)
					if products[i]['itemLength']/10 > 0 and products[i]['itemWidth']/10 > 0 and products[i]['itemHeight']/10 > 0:
						item.length_dimension = f"{item_detail.item_length} x {item_detail.item_breadth} x {item_detail.item_height} cm (= {item_dimension} cm\u00b3)"
					item_detail.size = products[i]['size']
					item_detail.color = products[i]['color']
					item_detail.desc_feature = products[i]["description"]
					if products[0]['features'] and len(products[0]['features']) >= 5:
						item_detail.desc_feature1 = products[0]['features'][0]
						item_detail.desc_feature2 = products[0]['features'][1]
						item_detail.desc_feature3 = products[0]['features'][2]
						item_detail.desc_feature4 = products[0]['features'][3]
						item_detail.desc_feature5 = products[0]['features'][4]
					stats_parsed = products[i].get("stats_parsed")
					if stats_parsed:
						current = stats_parsed.get("current")
						avg30 = stats_parsed.get("avg30")
						avg90 = stats_parsed.get("avg90")
						avg180 = stats_parsed.get("avg180")
						lowest = stats_parsed.get("min")
						highest = stats_parsed.get("max")

						if current:
							item_detail.sales_rank_current_price = current.get("SALES")
							item.custom_last_price = current.get("LISTPRICE")
							item.custom_new_current = current.get("NEW")
						if avg30:
							item_detail.sales_30_days_avg = avg30.get("SALES")
							item_detail.list_price_30_days_avg = avg30.get("LISTPRICE")
							item_detail.new_30_days_avg = avg30.get("NEW")
						if avg90:
							item_detail.sales_90_days_avg = avg90.get("SALES")
							item_detail.list_price_90_days_avg = avg90.get("LISTPRICE")
							item_detail.new_90_days_avg = avg90.get("NEW")
						if avg180:
							item_detail.sales_180_days_avg = stats_parsed.get("avg180").get("SALES")
							item_detail.list_price_180_days_avg = stats_parsed.get("avg180").get("LISTPRICE")
							item_detail.new_180_days_avg = stats_parsed.get("avg180").get("NEW")
						if lowest:
							new_lowest = lowest.get("NEW")
							if new_lowest and len(new_lowest)==2:
								item_detail.new_lowest = new_lowest[1]
							lowest_listprice = lowest.get("LISTPRICE")
							if lowest_listprice and len(lowest_listprice)==2:
								item_detail.list_price_lowest = lowest_listprice[1]
						if highest:
							new_highest = lowest.get("NEW")
							if new_highest and len(new_highest)==2:
								item_detail.new_highest = new_highest[1]
							highest_listprice = highest.get("LISTPRICE")
							if highest_listprice and len(highest_listprice)==2:
								doc.list_price_highest = highest_listprice[1]
					if doc.custom_ean:
						item_detail.ean=doc.custom_ean
					item_detail.item=doc.name
					item_detail.save()
					item.save()
					# frappe.db.set_value("Item", item.name, "title", products[i]['title'])

		except Exception as e:
			frappe.throw(_("Found invalid ASIN"))
	
	else:
		EAN = [row.ean for row in item.items if row.ean]
		if EAN:
			if not frappe.db.exists('Item Details',{'asin_no':doc.custom_asin_no}):
				if not frappe.db.exists('Item Details',{'ean':doc.custom_ean}):
					item_det=frappe.new_doc('Item Details')
					item_det.ean=doc.custom_ean
					item_det.save()
			if frappe.db.exists('Item Details',{'ean':doc.custom_ean}):
					item_detail=frappe.get_doc('Item Details',{'asin_no':doc.custom_asin_no})
			try:
				products = api.query(EAN, stats=30, rating=True, update=0, domain="IN", history=1, product_code_is_asin=False)
				for i in range(len(EAN)):
					item = frappe.get_doc("Item", {"ean": EAN[i]})
					if item:
						item.custom_asin_no = products[i]['asin']
						item.custom_amzon_item_name = products[i]["title"]
						item.title = products[i]["title"]
						if not frappe.db.exists('Brand',products[i]['brand']):
						# create a new brand if does not exists
							doc = frappe.new_doc('Brand')
							doc.brand =products[i]['brand']
							doc.insert()
							item.brand = products[i]['brand']
						else:
							item.brand = products[i]['brand']
						if products[i]["imagesCSV"]:
							item.image = "https://images-na.ssl-images-amazon.com/images/I/" + products[i]["imagesCSV"].split(',')[0]
							
							for ind,image_name in enumerate(products[i]["imagesCSV"].split(",")):
								field_name = f"custom_image{ind+1}"
								image_url = "https://images-na.ssl-images-amazon.com/images/I/" + image_name
								item.set(field_name,image_url)
						item_detail.manufacturer = products[i]["manufacturer"]
						if products[i]['listedSince']:
							epoch_time = (products[i]["listedSince"]+ 21564000) * 60000
							listed_since_date = datetime.datetime.utcfromtimestamp(epoch_time / 1000)
							item_detail.listed_since = listed_since_date.strftime("%Y-%m-%d")
						
						if products[i]["lastRatingUpdate"]:
							epoch_time = (products[i]["lastRatingUpdate"]+ 21564000) * 60
							last_rating_update = datetime.datetime.utcfromtimestamp(epoch_time)
							item_detail.latest_rating_time = last_rating_update.strftime("%Y-%m-%d")
						
						sales_ranks = products[i]["salesRanks"]
						sales_rank_reference = products[i]["salesRankReference"]
						if sales_ranks and sales_rank_reference:
							if str(sales_rank_reference) in sales_ranks:
								sales_rank_history = sales_ranks[str(sales_rank_reference)]
								item_detail.sales_rank = str(sales_rank_history[-1])
						item_detail.sales_rank_reference = products[i]['salesRankReference']
						asin = products[i]["asin"]
						item_detail.url_amazon = f'https://www.amazon.in/dp/{asin}'
						if len(products[i]['csv']) > 0:
							if len(products[i]['csv']) >= 17:
								if products[i]['csv'][17]:
									item.custom_reviews_count = products[i]['csv'][17][-1]
							if len(products[i]['csv']) >= 16:
								if products[i]['csv'][16]:
									item.custom_reviews_rating = str(products[i]['csv'][16][-1]/10)
						item_detail.parent_asin= products[i]["parentAsin"]
						category_tree = []
						category_tree_dict = {}
						if products[i].get('categoryTree'):
							category_tree = [i.get("name") for i in products[i].get('categoryTree')]
							category_tree_dict = {i["catId"]:i["name"] for i in products[i]['categoryTree']}

						if category_tree:
							item.category_sub = category_tree[-1]
							item.custom_categories_tree = ", ".join(category_tree)
						if category_tree_dict:
							item.custom_category_root = category_tree_dict.get(products[0].get('rootCategory'))
						
						# item.ean =  re.findall('[0-9]+', json.dumps(products[i]['eanList'][0]))[0] if products[i]['eanList'] is not None else ''
						item.custom_ean =  products[i]['eanList'][0] if products[i]['eanList'] else ''

						item_detail.product_codes_upc  = json.dumps(products[i]['upcList'])
						item_detail.launchpad= products[i]['launchpad']  # currently a data field, should be checkbox
						item_detail.product_codes_partnumber = products[i]['partNumber']
						frequently_bought_together = products[i]['frequentlyBoughtTogether']
						if isinstance(frequently_bought_together, (list, tuple)):
							item_detail.freq_bought_together = ", ".join(frequently_bought_together)
						else:
							iitem_detail.freq_bought_together = ""
						variations = products[i]['variations']
						if variations:
							v = [row.get('asin') for row in variations]
							if v:
								item_detail.variation_asins = ", ".join(v)
						asin_attributes = [row.get('attributes') for row in variations if row.get('asin')==ASIN[i] and row.get('attributes')]
						if asin_attributes:
							attr_dict = [row for row in asin_attributes[0]]
							if attr_dict:
								item.variation_attributes = f"{attr_dict[0].get('dimension')}: {attr_dict[0].get('value')}"
						item_detail.product_group = products[i]['productGroup']
						item_detail.number_of_items = products[i]['numberOfItems']
						item_detail.package_height= str(products[i]['packageHeight']/10)
						item_detail.package_length = str(products[i]['packageLength']/10)
						item_detail.package_width = str(products[i]['packageWidth']/10)
						item_detail.package_weight = products[i]['packageWeight']
						item_detail.package_quantity = products[i]['packageQuantity']
						pkg_dimension = str(products[i]['packageLength']/10 * products[i]['packageWidth']/10 * products[i]['packageHeight']/10)
						if products[i]['packageHeight']/10 > 0 and products[i]['packageLength']/10 > 0 and products[i]['packageWidth']/10 > 0:
							item_detail.package_dimension = f"{item_detail.package_length} x {item_detail.package_width} x {item_detail.package_height} cm (= {pkg_dimension}) cm\u00b3"
						item_detail.model = products[i]['model']
						item_detail.item_length = str(products[i]['itemLength']/10)
						item_detail.item_breadth= str(products[i]['itemWidth']/10)
						item_detail.item_height  = str(products[i]['itemHeight']/10)
						item_detail.item_weight  = products[i]['itemWeight']
						item_dimension = str(products[i]['itemLength']/10 * products[i]['itemWidth']/10 * products[i]['itemHeight']/10)
						if products[i]['itemLength']/10 > 0 and products[i]['itemWidth']/10 > 0 and products[i]['itemHeight']/10 > 0:
							item_detail.length_dimension = f"{item_detail.item_length} x {item_detail.item_breadth} x {item_detail.item_height} cm (= {item_dimension} cm\u00b3)"
						item_detail.size = products[i]['size']
						item_detail.color = products[i]['color']
						item_detail.desc_feature = products[i]["description"]
						if products[0]['features'] and len(products[0]['features']) >= 5:
							item_detail.desc_feature1 = products[0]['features'][0]
							item_detail.desc_feature2 = products[0]['features'][1]
							item_detail.desc_feature3 = products[0]['features'][2]
							item_detail.desc_feature4 = products[0]['features'][3]
							item_detail.desc_feature5 = products[0]['features'][4]
						stats_parsed = products[i].get("stats_parsed")
						if stats_parsed:
							current = stats_parsed.get("current")
							avg30 = stats_parsed.get("avg30")
							avg90 = stats_parsed.get("avg90")
							avg180 = stats_parsed.get("avg180")
							lowest = stats_parsed.get("min")
							highest = stats_parsed.get("max")

							if current:
								item_detail.sales_rank_current_price = current.get("SALES")
								item.custom_last_price = current.get("LISTPRICE")
								item.custom_new_current = current.get("NEW")
							if avg30:
								item_detail.sales_30_days_avg = avg30.get("SALES")
								item_detail.list_price_30_days_avg = avg30.get("LISTPRICE")
								item_detail.new_30_days_avg = avg30.get("NEW")
							if avg90:
								item_detail.sales_90_days_avg = avg90.get("SALES")
								item_detail.list_price_90_days_avg = avg90.get("LISTPRICE")
								item_detail.new_90_days_avg = avg90.get("NEW")
							if avg180:
								item_detail.sales_180_days_avg = stats_parsed.get("avg180").get("SALES")
								item_detail.list_price_180_days_avg = stats_parsed.get("avg180").get("LISTPRICE")
								item_detail.new_180_days_avg = stats_parsed.get("avg180").get("NEW")
							if lowest:
								new_lowest = lowest.get("NEW")
								if new_lowest and len(new_lowest)==2:
									item_detail.new_lowest = new_lowest[1]
								lowest_listprice = lowest.get("LISTPRICE")
								if lowest_listprice and len(lowest_listprice)==2:
									item_detail.list_price_lowest = lowest_listprice[1]
							if highest:
								new_highest = lowest.get("NEW")
								if new_highest and len(new_highest)==2:
									item_detail.new_highest = new_highest[1]
								highest_listprice = highest.get("LISTPRICE")
								if highest_listprice and len(highest_listprice)==2:
									doc.list_price_highest = highest_listprice[1]
						if doc.custom_asin_no:
							item_detail.asin_no=doc.custom_asin_no			
						item_detail.save()
						item.save()
						# frappe.db.set_value("Item", item.name, "title", products[i]['title'])

			except Exception as e:
				frappe.throw(_("Found invalid EAN"))						

def sync_keepa_item(doc, event):
	accesskey = '4i9vbmksc3d9o67p6fd3s9aitdaaer17c604f3qrh93auu67fnh6pfucqvqltmjm'
	api = keepa.Keepa(accesskey)
	if doc.custom_asin_no:
		ASIN = [doc.custom_asin_no]
		if ASIN:
			if not frappe.db.exists('Item Details',{'asin_no':doc.custom_asin_no}):
				item_det=frappe.new_doc('Item Details')
				item_det.asin_no=doc.custom_asin_no
				item_det.save()
			if frappe.db.exists('Item Details',{'asin_no':doc.custom_asin_no}):
					item_detail=frappe.get_doc('Item Details',{'asin_no':doc.custom_asin_no})
			try:
				products = api.query(ASIN, stats=30, rating=True, update=0, domain="IN", history=1)
			except Exception as e:
				frappe.throw(_(f"Invalid ASIN: {doc.custom_asin_no}"))
			else:
				for i in range(len(ASIN)):
					if not frappe.db.exists('Brand',products[i]['brand']):
						# create a new brand if does not exists
						n_doc = frappe.new_doc('Brand')
						n_doc.brand =products[i]['brand']
						n_doc.insert()
						doc.brand = products[i]['brand']
					else:
						doc.brand = products[i]['brand']
					if products[i]["imagesCSV"]:
						doc.image = "https://images-na.ssl-images-amazon.com/images/I/" + products[i]["imagesCSV"].split(',')[0]
						
						for ind,image_name in enumerate(products[i]["imagesCSV"].split(",")):
							field_name = f"custom_image{ind+1}"
							image_url = "https://images-na.ssl-images-amazon.com/images/I/" + image_name
							doc.set(field_name,image_url)

					item_detail.manufacturer = products[i]["manufacturer"]
					if products[i]['listedSince']:
						epoch_time = (products[i]["listedSince"]+ 21564000) * 60000
						listed_since_date = datetime.datetime.utcfromtimestamp(epoch_time / 1000)
						item_detail.listed_since = listed_since_date.strftime("%Y-%m-%d")
					
					if products[i]["lastRatingUpdate"]:
						epoch_time = (products[i]["lastRatingUpdate"]+ 21564000) * 60
						last_rating_update = datetime.datetime.utcfromtimestamp(epoch_time)
						item_detail.latest_rating_time = last_rating_update.strftime("%Y-%m-%d")

					sales_ranks = products[i]["salesRanks"]
					sales_rank_reference = products[i]["salesRankReference"]
					if sales_ranks and sales_rank_reference:
						if str(sales_rank_reference) in sales_ranks:
							sales_rank_history = sales_ranks[str(sales_rank_reference)]
							item_detail.sales_rank = str(sales_rank_history[-1])
					item_detail.sales_rank_reference = products[i]['salesRankReference']
					item_detail.url_amazon = f'https://www.amazon.in/dp/{doc.custom_asin_no}'
					if len(products[i]['csv']) > 0:
						if len(products[i]['csv']) >= 17:
							if products[i]['csv'][17]:
								doc.custom_reviews_count = products[i]['csv'][17][-1]
						if len(products[i]['csv']) >= 16:
							if products[i]['csv'][16]:
								doc.custom_reviews_rating = str(products[i]['csv'][16][-1]/10)
					item_detail.parent_asin = products[i]["parentAsin"]
					category_tree = []
					category_tree_dict = {}
					if products[i].get('categoryTree'):
						category_tree = [i.get("name") for i in products[i].get('categoryTree')]
						category_tree_dict = {i["catId"]:i["name"] for i in products[i]['categoryTree']}

					if category_tree:
						doc.category_sub = category_tree[-1]
						doc.custom_categories_tree = ", ".join(category_tree)
					if category_tree_dict:
						doc.custom_category_root = category_tree_dict.get(products[0].get('rootCategory'))
					
					# doc.ean =  re.findall('[0-9]+', json.dumps(products[i]['eanList'][0]))[0] if products[i]['eanList'] is not None else ''
					doc.custom_ean =  products[i]['eanList'][0] if products[i]['eanList'] else ''

					item_detail.product_codes_upc = json.dumps(products[i]['upcList'])
					item_detail.launchpad = products[i]['launchpad']  # currently a data field, should be checkbox
					item_detail.product_codes_partnumber = products[i]['partNumber']
					frequently_bought_together = products[i]['frequentlyBoughtTogether']
					if isinstance(frequently_bought_together, (list, tuple)):
						item_detail.freq_bought_together = ", ".join(frequently_bought_together)
					else:
						item_detail.freq_bought_together = ""
					variations = products[i]['variations']
					asin_attributes = []
					if variations:
						v = [row.get('asin') for row in variations]
						if v:
							item_detail.variation_asins = ", ".join(v)
						asin_attributes = [row.get('attributes') for row in variations if row.get('asin')==doc.custom_asin_no and row.get('attributes')]
					if asin_attributes:
						attr_dict = [row for row in asin_attributes[0]]
						if attr_dict:
							item_detail.variation_attributes = f"{attr_dict[0].get('dimension')}: {attr_dict[0].get('value')}"
					item_detail.product_group = products[i]['productGroup']
					item_detail.number_of_items = products[i]['numberOfItems']
					item_detail.package_height = str(products[i]['packageHeight']/10)
					item_detail.package_length = str(products[i]['packageLength']/10)
					item_detail.package_width = str(products[i]['packageWidth']/10)
					item_detail.package_weight = products[i]['packageWeight']
					item_detail.package_quantity = products[i]['packageQuantity']
					pkg_dimension = str(products[i]['packageLength']/10 * products[i]['packageWidth']/10 * products[i]['packageHeight']/10)
					if products[i]['packageHeight']/10 > 0 and products[i]['packageLength']/10 > 0 and products[i]['packageWidth']/10 > 0:
						item_detail.package_dimension = f"{item_detail.package_length} x {item_detail.package_width} x {item_detail.package_height} cm (= {pkg_dimension}) cm\u00b3"
					item_detail.model = products[i]['model']
					item_detail.item_length = str(products[i]['itemLength']/10)
					item_detail.item_breadth = str(products[i]['itemWidth']/10)
					item_detail.item_height = str(products[i]['itemHeight']/10)
					item_detail.item_weight = products[i]['itemWeight']
					item_dimension = str(products[i]['itemLength']/10 * products[i]['itemWidth']/10 * products[i]['itemHeight']/10)
					if products[i]['itemLength']/10 > 0 and products[i]['itemWidth']/10 > 0 and products[i]['itemHeight']/10 > 0:
						item_detail.length_dimension = f"{item_detail.item_length} x {item_detail.item_breadth} x {item_detail.item_height} cm (= {item_dimension} cm\u00b3)"
					item_detail.size = products[i]['size']
					item_detail.color = products[i]['color']
					item_detail.desc_feature = products[i]["description"]
					item_detail.title = products[i]["title"]
					doc.custom_amzon_item_name = products[i]["title"]
					if products[0]['features'] and len(products[0]['features']) >= 5:
						item_detail.desc_feature1 = products[0]['features'][0]
						item_detail.desc_feature2 = products[0]['features'][1]
						item_detail.desc_feature3 = products[0]['features'][2]
						item_detail.desc_feature4 = products[0]['features'][3]
						item_detail.desc_feature5 = products[0]['features'][4]
					stats_parsed = products[i].get("stats_parsed")
					if stats_parsed:
						current = stats_parsed.get("current")
						avg30 = stats_parsed.get("avg30")
						avg90 = stats_parsed.get("avg90")
						avg180 = stats_parsed.get("avg180")
						lowest = stats_parsed.get("min")
						highest = stats_parsed.get("max")
						if current:
							item_detail.sales_rank_current_price = current.get("SALES")
							doc.custom_last_price = current.get("LISTPRICE")
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
							item_detail.sales_180_days_avg = stats_parsed.get("avg180").get("SALES")
							item_detail.list_price_180_days_avg = stats_parsed.get("avg180").get("LISTPRICE")
							item_detail.new_180_days_avg = stats_parsed.get("avg180").get("NEW")
						if lowest:
							new_lowest = lowest.get("NEW")
							if new_lowest and len(new_lowest)==2:
								item_detail.new_lowest = new_lowest[1]
							lowest_listprice = lowest.get("LISTPRICE")
							if lowest_listprice and len(lowest_listprice)==2:
								item_detail.list_price_lowest = lowest_listprice[1]
						if highest:
							new_highest = lowest.get("NEW")
							if new_highest and len(new_highest)==2:
								item_detail.new_highest = new_highest[1]
							highest_listprice = highest.get("LISTPRICE")
							if highest_listprice and len(highest_listprice)==2:
								doc.list_price_highest = highest_listprice[1]
				if doc.custom_ean:
					item_detail.ean=doc.custom_ean
				item_detail.save()
				doc.custom_item_detail=item_detail.name
				frappe.msgprint(_("Item(s) has been synced with keepa"))

	elif doc.custom_ean:
		EAN = [doc.custom_ean]
		if EAN:
			if not doc.custom_asin_no:
				if not frappe.db.exists('Item Details',{'ean':doc.custom_ean}):
					item_det=frappe.new_doc('Item Details')
					item_det.ean=doc.custom_ean
					item_det.save()
			if frappe.db.exists('Item Details',{'ean':doc.custom_ean}):
				item_detail=frappe.get_doc('Item Details',{'ean':doc.custom_ean})
			try:
				products = api.query(EAN, stats=30, rating=True, update=0, domain="IN", history=1,product_code_is_asin=False)
			except Exception as e:
				frappe.throw(_(f"Invalid EAN: {doc.custom_ean}"))
			else:
				for i in range(len(EAN)):
					if not frappe.db.exists('Brand',products[i]['brand']):
						# create a new brand if does not exists
						n_doc = frappe.new_doc('Brand')
						n_doc.brand =products[i]['brand']
						n_doc.insert()
						doc.brand = products[i]['brand']
					else:
						doc.brand = products[i]['brand']
					if products[i]["imagesCSV"]:
						doc.image = "https://images-na.ssl-images-amazon.com/images/I/" + products[i]["imagesCSV"].split(',')[0]
						for ind,image_name in enumerate(products[i]["imagesCSV"].split(",")):
							field_name = f"custom_image{ind+1}"
							image_url = "https://images-na.ssl-images-amazon.com/images/I/" + image_name
							doc.set(field_name,image_url)
					item_detail.manufacturer = products[i]["manufacturer"]
					if products[i]['listedSince']:
						epoch_time = (products[i]["listedSince"]+ 21564000) * 60000
						listed_since_date = datetime.datetime.utcfromtimestamp(epoch_time / 1000)
						item_detail.listed_since = listed_since_date.strftime("%Y-%m-%d")
					
					if products[i]["lastRatingUpdate"]:
						epoch_time = (products[i]["lastRatingUpdate"]+ 21564000) * 60
						last_rating_update = datetime.datetime.utcfromtimestamp(epoch_time)
						item_detail.latest_rating_time = last_rating_update.strftime("%Y-%m-%d")
					
					sales_ranks = products[i]["salesRanks"]
					sales_rank_reference = products[i]["salesRankReference"]
					if sales_ranks and sales_rank_reference:
						if str(sales_rank_reference) in sales_ranks:
							sales_rank_history = sales_ranks[str(sales_rank_reference)]
							item_detail.sales_rank = str(sales_rank_history[-1])
					item_detail.sales_rank_reference = products[i]['salesRankReference']
					doc.custom_asin_no = products[i]["asin"]
					item_detail.url_amazon = f'https://www.amazon.in/dp/{doc.custom_asin_no}'
					if len(products[i]['csv']) > 0:
						if len(products[i]['csv']) >= 17:
							if products[i]['csv'][17]:
								doc.custom_reviews_count = products[i]['csv'][17][-1]
						if len(products[i]['csv']) >= 16:
							if products[i]['csv'][16]:
								doc.custom_reviews_rating = str(products[i]['csv'][16][-1]/10)
					item_detail.parent_asin = products[i]["parentAsin"]					
					category_tree = []
					category_tree_dict = {}
					if products[i].get('categoryTree'):
						category_tree = [i.get("name") for i in products[i].get('categoryTree')]
						category_tree_dict = {i["catId"]:i["name"] for i in products[i]['categoryTree']}

					if category_tree:
						doc.category_sub = category_tree[-1]
						doc.custom_categories_tree = ", ".join(category_tree)
					if category_tree_dict:
						doc.custom_category_root = category_tree_dict.get(products[0].get('rootCategory'))
					
					# doc.ean =  re.findall('[0-9]+', json.dumps(products[i]['eanList'][0]))[0] if products[i]['eanList'] is not None else ''
					doc.custom_ean =  products[i]['eanList'][0] if products[i]['eanList'] else ''

					item_detail.product_codes_upc = json.dumps(products[i]['upcList'])
					item_detail.launchpad = products[i]['launchpad']  # currently a data field, should be checkbox
					item_detail.product_codes_partnumber = products[i]['partNumber']
					frequently_bought_together = products[i]['frequentlyBoughtTogether']
					if isinstance(frequently_bought_together, (list, tuple)):
						item_detail.freq_bought_together = ", ".join(frequently_bought_together)
					else:
						item_detail.freq_bought_together = ""
					variations = products[i]['variations']
					asin_attributes = []
					if variations:
						v = [row.get('asin') for row in variations]
						if v:
							item_detail.variation_asins = ", ".join(v)
						asin_attributes = [row.get('attributes') for row in variations if row.get('asin')==doc.custom_asin_no and row.get('attributes')]
					if asin_attributes:
						attr_dict = [row for row in asin_attributes[0]]
						if attr_dict:
							doc.variation_attributes = f"{attr_dict[0].get('dimension')}: {attr_dict[0].get('value')}"
					item_detail.product_group = products[i]['productGroup']
					item_detail.number_of_items = products[i]['numberOfItems']
					item_detail.package_height = str(products[i]['packageHeight']/10)
					item_detail.package_length = str(products[i]['packageLength']/10)
					item_detail.package_width = str(products[i]['packageWidth']/10)
					item_detail.package_weight = products[i]['packageWeight']
					item_detail.package_quantity = products[i]['packageQuantity']
					pkg_dimension = str(products[i]['packageLength']/10 * products[i]['packageWidth']/10 * products[i]['packageHeight']/10)
					if products[i]['packageHeight']/10 > 0 and products[i]['packageLength']/10 > 0 and products[i]['packageWidth']/10 > 0:
						item_detail.package_dimention = f"{item_detail.package_length} x {item_detail.package_width} x {item_detail.package_height} cm (= {pkg_dimension}) cm\u00b3"
					item_detail.model = products[i]['model']
					item_detail.item_length = str(products[i]['itemLength']/10)
					item_detail.item_breadth = str(products[i]['itemWidth']/10)
					item_detail.item_height = str(products[i]['itemHeight']/10)
					item_detail.item_weight = products[i]['itemWeight']
					item_dimension = str(products[i]['itemLength']/10 * products[i]['itemWidth']/10 * products[i]['itemHeight']/10)
					if products[i]['itemLength']/10 > 0 and products[i]['itemWidth']/10 > 0 and products[i]['itemHeight']/10 > 0:
						item_detail.length_dimension = f"{item_detail.item_length} x {item_detail.item_breadth} x {item_detail.item_height} cm (= {item_dimension} cm\u00b3)"
					item_detail.size = products[i]['size']
					item_detail.color = products[i]['color']
					item_detail.desc_feature = products[i]["description"]
					item_detail.title = products[i]["title"]
					doc.custom_amzon_item_name = products[i]["title"]
					if products[0]['features'] and len(products[0]['features']) >= 5:
						item_detail.desc_feature1 = products[0]['features'][0]
						item_detail.desc_feature2 = products[0]['features'][1]
						item_detail.desc_feature3 = products[0]['features'][2]
						item_detail.desc_feature4 = products[0]['features'][3]
						item_detail.desc_feature5 = products[0]['features'][4]
					stats_parsed = products[i].get("stats_parsed")
					if stats_parsed:
						current = stats_parsed.get("current")
						avg30 = stats_parsed.get("avg30")
						avg90 = stats_parsed.get("avg90")
						avg180 = stats_parsed.get("avg180")
						lowest = stats_parsed.get("min")
						highest = stats_parsed.get("max")
						if current:
							item_detail.sales_rank_current_price= current.get("SALES")
							doc.custom_last_price = current.get("LISTPRICE")
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
							item_detail.sales_180_days_avg = stats_parsed.get("avg180").get("SALES")
							item_detail.list_price_180_days_avg = stats_parsed.get("avg180").get("LISTPRICE")
							item_detail.new_180_days_avg = stats_parsed.get("avg180").get("NEW")
						if lowest:
							new_lowest = lowest.get("NEW")
							if new_lowest and len(new_lowest)==2:
								item_detail.new_lowest = new_lowest[1]
							lowest_listprice = lowest.get("LISTPRICE")
							if lowest_listprice and len(lowest_listprice)==2:
								item_detail.list_price_lowest = lowest_listprice[1]
						if highest:
							new_highest = lowest.get("NEW")
							if new_highest and len(new_highest)==2:
								item_detail.new_highest = new_highest[1]
							highest_listprice = highest.get("LISTPRICE")
							if highest_listprice and len(highest_listprice)==2:
								doc.list_price_highest = highest_listprice[1]
				# item_detail.item=doc.name	
				if doc.custom_asin_no:
					item_detail.asin_no=doc.custom_asin_no			
				item_detail.save()
				frappe.msgprint(_("Item(s) has been synced with keepa"))
	
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
		data = scrape(fsn)

		doc.item_name = data['title']
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

		doc.custom_model_fk = data['specifications'].get('General', {}).get('Model Name', "")
		dims = data['specifications'].get("Dimensions", {})
		item_detail.length_breadth = dims.get('Width', "")
		item_detail.length_height = dims.get('Height', "")

		doc.custom_mrp = data['price']
		item_detail.title_flipkart = data['title']
		item_detail.fsn_no = doc.custom_fsn_no
		item_detail.specification = str(data['general'])
		item_detail.save()
		doc.custom_item_detail=item_detail.name

			# doc.save()
			# doc.reload()
			
			# for i in range(min(len(data['multiple_images']), 6-1)):
			# 	f = f"custom_image{i+2}"
			# 	frappe.db.set_value("Item", doc.name, f, data['multiple_images'][i])			
			# 	frappe.db.commit()
			# 	frappe.log_error(f"{f} url" ,f"{doc.name}\n{f}\n{ data['multiple_images'][i]}")

def create_selling_price(doc,event):
	for item in doc.items:
		if item.rate > 0:
			item_price_exists = frappe.db.get_all("Item Price", {"item_code": item.item_code, "selling": 1, "price_list": "Standard Selling"})
			if not item_price_exists:
				item_master = frappe.get_doc("Item", item.item_code)
				item_price = frappe.new_doc("Item Price")
				item_price.item_code = item.item_code
				item_price.price_list = "Standard Selling"
				item_price.selling = 1
				item_price.item_name = item_master.item_name
				item_price.uom = item_master.stock_uom
				item_price.valid_from = today()
				item_price.currency = frappe.db.get_value("Company", doc.company, "default_currency")
				selling_rate = item.rate + ( 0.05 * item.rate)  # Calculate selling rate with a 5% margin
				item_price.price_list_rate = round(selling_rate, 9) # Format the selling rate to end with 9
				item_price.save()


def create_item_price(doc, event):
	if frappe.db.exists("Item", {"name": doc.name}):
		if doc.custom_mrp != frappe.db.get_value("Item", doc.name, "custom_mrp"):
			item_price = frappe.new_doc("Item Price")
			item_price.item_code = doc.item_code
			item_price.price_list = "Standard Selling"
			item_price.selling = 1
			item_price.item_name = doc.item_name
			item_price.uom = doc.stock_uom
			item_price.valid_from = today()
			item_price.price_list_rate = float(doc.custom_mrp) -  (0.05 * float(doc.custom_mrp))  # Calculate selling rate with a 5% margin
			item_price.save()