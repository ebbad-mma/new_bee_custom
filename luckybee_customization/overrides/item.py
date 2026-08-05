import json
import datetime
import keepa
import frappe
from frappe import _
import re
from frappe.utils import today
from .scraper_utils import scrape, set_images, extract_pid_with_regex
from luckybee_customization.item_hooks import mark_system_field_modified

STOP_WORDS = {
	"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
	"in", "into", "is", "it", "of", "on", "or", "our", "that", "the", "this",
	"to", "with", "your",
}

def normalize_raw_price(raw):
	"""Keepa's stats_parsed only scales/rescales values it recognizes as
	part of the indexed price arrays (current, avg30, ...). buyBoxPrice and
	buyBoxPrice30 are plain top-level ints - still in paise, and -1/-2 means
	"no offer" - so they need the same treatment done by hand.
	"""
	if raw is None or raw < 0:
		return None
	return raw / 100.0

def resolve_best_price(stats_parsed):
	"""B1.1 fallback chain: Buy Box current -> New current -> Buy Box 30d
	avg -> New 30d avg -> New 90d avg -> New 180d avg -> List Price current.
	Buy Box current requires the `offers` param on the Keepa query (token
	cost); if it's ever disabled, those two steps just come back empty and
	the chain still works.

	On -1 ("no offer available", i.e. out of stock / discontinued): the keepa
	library's own parser already drops any negative value before we see it
	(_normalize_value returns None for v < 0, and the key is then omitted from
	stats_parsed entirely), so -1 can never reach these fields. The
	normalize_raw_price() guard above covers buyBoxPrice/buyBoxPrice30, which
	are plain top-level ints the library does not touch. Verified end-to-end
	against the installed keepa parser with an all -1 payload.

	The 90d/180d steps matter because a product can be out of stock now while
	still having a real, useful average from earlier in the window.
	"""
	current = (stats_parsed or {}).get("current") or {}
	avg30 = (stats_parsed or {}).get("avg30") or {}
	avg90 = (stats_parsed or {}).get("avg90") or {}
	avg180 = (stats_parsed or {}).get("avg180") or {}
	buybox_current = normalize_raw_price((stats_parsed or {}).get("buyBoxPrice"))
	buybox_30d = normalize_raw_price((stats_parsed or {}).get("buyBoxPrice30"))

	chain = [
		(buybox_current, "Buy Box: Current"),
		(current.get("NEW"), "New: Current"),
		(buybox_30d, "Buy Box: 30 days avg."),
		(avg30.get("NEW"), "New: 30 days avg."),
		(avg90.get("NEW"), "New: 90 days avg."),
		(avg180.get("NEW"), "New: 180 days avg."),
		(current.get("LISTPRICE"), "List Price: Current"),
	]
	# `if v` also filters 0, which is not a real offer price either.
	best_price, best_price_source = next(((v, s) for v, s in chain if v), (None, None))

	price_drop_30d = None
	new_30d, new_current = avg30.get("NEW"), current.get("NEW")
	if new_30d and new_current:
		price_drop_30d = round((new_30d - new_current) / new_30d * 100.0, 2)

	return {
		"amz_best_price": best_price,
		"amz_best_price_source": best_price_source,
		"amz_buybox_current": buybox_current,
		"amz_buybox_30d": buybox_30d,
		"amz_price_drop_30d": price_drop_30d,
	}

# Fields we refuse to blank out on a sync that came back with no offer at all.
# B1: "When current is -1 but a previously stored real price exists, KEEP the
# stored price, do not overwrite it." A discontinued product would otherwise
# lose a perfectly good last-known price the first time it went out of stock,
# and every margin/vs-Amazon figure derived from it would go with it.
PRICE_FIELDS_TO_PRESERVE = ("amz_best_price", "amz_best_price_source")

def apply_best_price(doc, resolved):
	"""Write the resolved price block onto the Item, preserving the last known
	price when this pull produced none.

	The remaining fields (buybox current/30d, price drop) are point-in-time
	diagnostics, so they are written as-is - reporting a stale "current" Buy
	Box price would be actively misleading, unlike keeping a last-known best
	price that is explicitly labelled by its source.
	"""
	for fieldname, value in resolved.items():
		if value is None and fieldname in PRICE_FIELDS_TO_PRESERVE and doc.get(fieldname):
			continue
		doc.set(fieldname, value)
		mark_system_field_modified(doc, fieldname)

# Item Details fieldname -> Item fieldname. The two doctypes each carry
# their own historical typo (variation_attribtutes on Item Details,
# package_dimention on Item), so these deliberately do not line up 1:1.
ITEM_DETAIL_TO_ITEM = {
	"manufacturer": "manufacturer",
	"listed_since": "listed_since",
	"sales_rank": "sales_rank",
	"sales_rank_reference": "sales_rank_ref",
	"url_amazon": "amazon_url",
	"parent_asin": "parent_asin",
	"product_codes_upc": "upc",
	"product_codes_partnumber": "partnumber",
	"freq_bought_together": "freq_brought_together",
	"variation_asins": "variation_asins",
	"variation_attribtutes": "variation_attributes",
	"product_group": "product_group",
	"number_of_items": "number_of_items",
	"package_length": "package_length",
	"package_width": "package_width",
	"package_height": "package_height",
	"package_weight": "package_weight",
	"package_quantity": "package_quantity",
	"package_dimension": "package_dimention",
	"model": "model",
	"item_length": "length_length",
	"item_breadth": "length_breadth",
	"item_height": "length_height",
	"item_weight": "length_weight",
	"length_dimension": "length_dimension",
	"size": "size",
	"color": "color",
	"locale": "locale",
	"amz_monthly_sold": "amz_monthly_sold",
	"amz_monthly_sold_date": "amz_monthly_sold_date",
	"desc_feature": "desc_feature",
	"desc_feature1": "desc_feature_1",
	"desc_feature2": "desc_feature_2",
	"desc_feature3": "desc_feature_3",
	"desc_feature4": "desc_feature_4",
	"desc_feature5": "desc_feature_5",
}

def mirror_details_to_item(doc, item_detail):
	"""The Market Intelligence tab reads the Item's own fields, but the sync
	only ever populated their Item Details counterparts - so the tab stayed
	blank even for items whose Item Details row synced perfectly.
	"""
	for source, target in ITEM_DETAIL_TO_ITEM.items():
		value = item_detail.get(source)
		if value in (None, ""):
			continue
		doc.set(target, value)
		mark_system_field_modified(doc, target)

def extract_image_names(prod):
	"""Keepa returns imagesCSV on some responses and a list of {l, m} dicts
	on others - live IN-domain queries only carry the latter, so both shapes
	have to be handled or the item ends up with no images at all.
	"""
	images_csv = prod.get("imagesCSV")
	if images_csv:
		return [img.strip() for img in images_csv.split(',') if img.strip()]

	images_list = []
	for img_obj in prod.get("images") or []:
		if isinstance(img_obj, dict):
			img_file = img_obj.get("l") or img_obj.get("m")
			if img_file:
				images_list.append(img_file)
		elif isinstance(img_obj, str) and img_obj.strip():
			images_list.append(img_obj.strip())
	return images_list

def apply_amazon_image_urls(doc, images_list):
	"""amz_image_urls is the Item's own child table. The sync already built
	these URLs for doc.image / custom_image1..5 but never filled the table,
	so the grid always rendered "No rows".
	"""
	if not images_list:
		return
	doc.set("amz_image_urls", [])
	for idx, image_name in enumerate(images_list):
		doc.append("amz_image_urls", {
			"image_url": "https://images-na.ssl-images-amazon.com/images/I/" + image_name,
			"sequence": idx + 1,
		})
	mark_system_field_modified(doc, "amz_image_urls")

def resolve_oos_percent(prod):
	"""B4 - Keepa's 30-day out-of-stock percentage for the NEW offer.

	It lives in the raw `stats` block as a plain percentage (4 means 4%). The
	library's stats_parsed divides price-like values by 100, so the same figure
	shows up there as 0.04 - read the raw block to avoid a 100x error. Values
	are per csv index; index 1 is NEW. -1 means "not reported".
	"""
	stats = (prod or {}).get("stats") or {}
	oos = stats.get("outOfStockPercentage30") or stats.get("outOfStockPercentage90")
	if not isinstance(oos, (list, tuple)) or len(oos) < 2:
		return None
	value = oos[1]  # NEW
	if not isinstance(value, (int, float)) or value < 0:
		return None
	return float(value)

def mark_synced(doc, prod=None):
	"""B3/B4 - stamp freshness and derive the stock-state flag.

	amz_last_synced records that we tried; amz_last_successful_sync records
	when we last actually came back with a usable price. The gap between them
	is what makes silently-failing syncs visible.
	"""
	oos_percent = resolve_oos_percent(prod)
	if oos_percent is not None:
		doc.amz_oos_percent = oos_percent
		mark_system_field_modified(doc, "amz_oos_percent")

	got_price = bool(doc.get("amz_best_price"))

	# Near-permanent out of stock is the cleaner discontinued signal; fall back
	# to "we got nothing at all this time" for the plain no-offer case.
	if oos_percent is not None and oos_percent >= 99:
		doc.amz_data_status = "Out of Stock / Discontinued"
	elif not got_price:
		doc.amz_data_status = "Refresh Failed"
	else:
		doc.amz_data_status = "Matched"

	doc.amz_last_synced = today()
	if got_price:
		doc.amz_last_successful_sync = today()
		mark_system_field_modified(doc, "amz_last_successful_sync")

	mark_system_field_modified(doc, "amz_data_status")
	mark_system_field_modified(doc, "amz_last_synced")

def flag_sync_failure(doc, identifier, status, reason):
	"""A failed Keepa call used to be logged as "Invalid ASIN" and swallowed,
	so a network blip was indistinguishable from a genuinely bad ASIN and the
	item saved looking fine with no Amazon data. Record what actually happened
	and surface it, without blocking the save - staff still need to save photos
	and counts when Keepa is unreachable.
	"""
	doc.amz_data_status = status
	mark_system_field_modified(doc, "amz_data_status")
	frappe.log_error(
		title=f"Keepa sync failed for {identifier}: {status}",
		message=f"{reason}\n\n{frappe.get_traceback()}",
	)
	if not frappe.flags.in_test and not frappe.flags.in_patch:
		frappe.msgprint(
			_("Amazon data could not be refreshed ({0}). The item was saved without it.").format(status),
			indicator="orange",
			alert=True,
		)

def apply_price_history(doc, avg30, avg90, avg180, lowest, highest):
	"""avg30/avg90/avg180/lowest/highest were only ever written onto Item
	Details, never mirrored onto the Item's own tracked fields, so the
	Pricing & Margin tab stayed blank even on items that synced cleanly.
	"""
	if avg30:
		doc.custom_sales_30days = avg30.get("SALES")
		doc.list_price_30days = avg30.get("LISTPRICE")
		doc.new_30days = avg30.get("NEW")
		for f in ("custom_sales_30days", "list_price_30days", "new_30days"):
			mark_system_field_modified(doc, f)
	if avg90:
		doc.custom_sales_90days = avg90.get("SALES")
		doc.list_price_90days = avg90.get("LISTPRICE")
		doc.new_90days = avg90.get("NEW")
		for f in ("custom_sales_90days", "list_price_90days", "new_90days"):
			mark_system_field_modified(doc, f)
	if avg180:
		doc.custom_sales_180days = avg180.get("SALES")
		doc.list_price_180days = avg180.get("LISTPRICE")
		doc.new_180days = avg180.get("NEW")
		for f in ("custom_sales_180days", "list_price_180days", "new_180days"):
			mark_system_field_modified(doc, f)
	if lowest:
		new_lowest = lowest.get("NEW")
		if new_lowest and len(new_lowest) == 2:
			doc.new_lowest = new_lowest[1]
			mark_system_field_modified(doc, "new_lowest")
		lowest_listprice = lowest.get("LISTPRICE")
		if lowest_listprice and len(lowest_listprice) == 2:
			doc.list_price_lowest = lowest_listprice[1]
			mark_system_field_modified(doc, "list_price_lowest")
	if highest:
		new_highest = highest.get("NEW")
		if new_highest and len(new_highest) == 2:
			doc.new_highest = new_highest[1]
			mark_system_field_modified(doc, "new_highest")
		highest_listprice = highest.get("LISTPRICE")
		if highest_listprice and len(highest_listprice) == 2:
			doc.list_price_highest = highest_listprice[1]
			mark_system_field_modified(doc, "list_price_highest")

def resolve_reviews(prod, stats_parsed):
	"""A4.3/B3.1 - reviews_rating/reviews_count were read from the raw csv
	array, which came back empty even for items with an active rating
	history. stats_parsed.current carries the same RATING/COUNT_REVIEWS
	values, already scaled, so prefer that and fall back to the raw csv
	only if stats didn't have it.
	"""
	current = (stats_parsed or {}).get("current") or {}
	rating = current.get("RATING")
	count = current.get("COUNT_REVIEWS")

	if rating is None or count is None:
		csv_data = prod.get("csv") or []
		if count is None and len(csv_data) >= 18 and csv_data[17]:
			count = csv_data[17][-1]
		if rating is None and len(csv_data) >= 17 and csv_data[16]:
			rating = csv_data[16][-1] / 10

	# Keepa's rescaling leaves float noise (3.5999999999999996), and this
	# lands in a Data field, so it would render verbatim on the form.
	if rating is not None:
		rating = round(rating, 1)

	return rating, count

def latest_monthly_sold(prod):
	"""B5 - Keepa does not always send the scalar `monthlySold`.

	On the IN domain it frequently comes back null while the real figure sits in
	`monthlySoldHistory`, a flat Keepa history array of [minute, value, minute,
	value, ...]. Verified live on B074Z6B35N: monthlySold was null while the
	history tail read [..., 7513496, -1, 7518540, 50, 7581292, -1] - i.e. the
	last *real* value is 50, which is the figure Keepa's own UI shows, and the
	trailing -1 is "not reported for this period" (the same -1-means-no-data
	convention as the price fields). Reading only the scalar is why the form
	showed 0.

	Walk the history backwards and take the most recent non-negative value.
	"""
	scalar = prod.get("monthlySold")
	if isinstance(scalar, (int, float)) and scalar >= 0:
		return int(scalar)

	hist = prod.get("monthlySoldHistory") or []
	# values sit at the odd indices; step back two at a time
	for i in range(len(hist) - 1, 0, -2):
		value = hist[i]
		if isinstance(value, (int, float)) and value >= 0:
			return int(value)
	return None

def apply_monthly_sold(item_detail, prod):
	"""B1.3 / B5"""
	monthly_sold = latest_monthly_sold(prod)
	# Don't blank a previously captured figure just because this pull had none -
	# same reasoning as apply_best_price().
	if monthly_sold is not None or not item_detail.get("amz_monthly_sold"):
		item_detail.amz_monthly_sold = monthly_sold
	last_sold_update = prod.get("lastSoldUpdate")
	if last_sold_update:
		epoch_time = (last_sold_update + 21564000) * 60000
		item_detail.amz_monthly_sold_date = datetime.datetime.utcfromtimestamp(epoch_time / 1000).strftime("%Y-%m-%d")

def set_within_limit(doc, fieldname, value):
	"""Assign a Keepa string without letting its length block the whole save.

	Amazon strings are arbitrarily long. A `Data` field is capped at 140
	characters, and Frappe rejects the entire document with "Value too big"
	rather than trimming - so one long parentTitle made an Item unsaveable,
	which also blocks shop-floor staff from saving photos or counts on it.
	Reported live on erp.luckybee.in for B08MXJYB2V.

	The seven fields this touches have been widened to Small Text (no cap), so
	normally nothing is trimmed. This stays as a backstop for any capped field
	that slips through - reference/keyword data losing its tail is always
	preferable to an item nobody can save. Trimming is logged so it is visible
	rather than silent.
	"""
	if value is None:
		doc.set(fieldname, None)
		return

	value = str(value)
	df = doc.meta.get_field(fieldname)
	# Only Data-like fields carry a length cap; Small/Long Text do not.
	limit = (df.length or 140) if df and df.fieldtype == "Data" else None

	if limit and len(value) > limit:
		frappe.logger("keepa").info(
			f"Trimmed {doc.doctype}.{fieldname} from {len(value)} to {limit} chars"
		)
		value = value[:limit]

	doc.set(fieldname, value)

def apply_keyword_fields(item_detail, prod):
	"""B2.1"""
	item_detail.amz_item_highlights = prod.get("itemHighlights")
	item_detail.amz_recommended_uses = prod.get("recommendedUsesForProduct")
	specific_uses = prod.get("specificUsesForProduct")
	item_detail.amz_specific_uses = ", ".join(specific_uses) if isinstance(specific_uses, (list, tuple)) else specific_uses
	item_detail.amz_product_benefit = prod.get("productBenefit")
	set_within_limit(item_detail, "amz_pattern", prod.get("pattern"))
	set_within_limit(item_detail, "amz_style", prod.get("style"))
	materials = prod.get("materials")
	set_within_limit(item_detail, "amz_material",
					 ", ".join(materials) if isinstance(materials, (list, tuple)) else (materials or prod.get("material")))
	product_type = prod.get("type")
	set_within_limit(item_detail, "amz_type",
					 ", ".join(product_type) if isinstance(product_type, (list, tuple)) else product_type)
	set_within_limit(item_detail, "amz_parent_title", prod.get("parentTitle"))
	set_within_limit(item_detail, "amz_included_components", prod.get("includedComponents"))
	set_within_limit(item_detail, "amz_url_slug", prod.get("urlSlug"))

def build_search_keywords(item_detail):
	"""B2.2 - concatenate the 11 keyword fields into one de-duplicated,
	comma-joined field for daily use on the Item.
	"""
	parts = [
		item_detail.amz_item_highlights, item_detail.amz_recommended_uses,
		item_detail.amz_specific_uses, item_detail.amz_product_benefit,
		item_detail.amz_pattern, item_detail.amz_style, item_detail.amz_material,
		item_detail.amz_type, item_detail.amz_parent_title,
		item_detail.amz_included_components, item_detail.amz_url_slug,
	]

	words = []
	seen = set()
	for part in parts:
		if not part:
			continue
		for word in re.split(r"[,\s/]+", str(part)):
			cleaned = word.strip(".-_").lower()
			if not cleaned or cleaned in STOP_WORDS or cleaned in seen:
				continue
			if cleaned.isdigit():
				# bare counts ("1 - Piece ...") are noise, not search terms
				continue
			seen.add(cleaned)
			words.append(cleaned)

	return ", ".join(words)

def sync_keepa_item(doc, event):
	before_keepa_fields = {df.fieldname: doc.get(df.fieldname) for df in doc.meta.fields if df.fieldname}
	savepoint = f"sync_keepa_item_{doc.name}"
	frappe.db.savepoint(savepoint)
	try:
		_sync_keepa_item_internal(doc, event)
	except Exception:
		# B3.2 - the Item Details write and the Item-side field writes must
		# land together or not at all, otherwise Item Details ends up fresh
		# while the Item stays stale (or vice versa).
		frappe.db.rollback(save_point=savepoint)
		raise
	finally:
		for fieldname, before_val in before_keepa_fields.items():
			if doc.get(fieldname) != before_val:
				mark_system_field_modified(doc, fieldname)

def _sync_keepa_item_internal(doc, event):
	accesskey = frappe.conf.get("keepa_api_key")
	if not accesskey:
		frappe.log_error("Missing Keepa API key in site_config.json")
		return
	# The library defaults to a 10s timeout, but an offers=20 query (needed for
	# Buy Box pricing) routinely takes 7-9s and was timing out mid-sync.
	api = keepa.Keepa(accesskey, timeout=60.0)
	if doc.custom_asin_no:
		ASIN = [doc.custom_asin_no]
		if ASIN:
			if not frappe.db.exists('Item Details', {'asin_no': doc.custom_asin_no}):
				item_det = frappe.new_doc('Item Details')
				item_det.asin_no = doc.custom_asin_no
				item_det.save(ignore_permissions=True)
			if frappe.db.exists('Item Details', {'asin_no': doc.custom_asin_no}):
				item_detail = frappe.get_doc('Item Details', {'asin_no': doc.custom_asin_no})
			try:
				products = api.query(ASIN, stats=30, rating=True, update=0, domain="IN", history=1, offers=20)
			except Exception as e:
				flag_sync_failure(doc, doc.custom_asin_no, "Refresh Failed", f"Keepa query failed: {e}")
				return
			if not products or not isinstance(products[0], dict):
				flag_sync_failure(doc, doc.custom_asin_no, "No Amazon Match", "Keepa returned no product for this ASIN.")
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
							n_doc.insert(ignore_permissions=True)
						doc.brand = brand_name
						mark_system_field_modified(doc, "brand")

					images_list = extract_image_names(prod)

					if images_list:
						doc.image = "https://images-na.ssl-images-amazon.com/images/I/" + images_list[0]
						mark_system_field_modified(doc, "image")
					apply_amazon_image_urls(doc, images_list)

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

					stats_parsed = prod.get("stats_parsed")

					rating, review_count = resolve_reviews(prod, stats_parsed)
					if review_count is not None:
						doc.reviews_count = review_count
						mark_system_field_modified(doc, "reviews_count")
					if rating is not None:
						doc.reviews_rating = str(rating)
						mark_system_field_modified(doc, "reviews_rating")

					apply_monthly_sold(item_detail, prod)
					apply_keyword_fields(item_detail, prod)

					item_detail.parent_asin = prod.get("parentAsin")
					category_tree = []
					category_tree_dict = {}
					if prod.get('categoryTree'):
						category_tree = [c.get("name") for c in prod.get('categoryTree') if isinstance(c, dict) and c.get("name")]
						category_tree_dict = {c["catId"]: c["name"] for c in prod.get('categoryTree') if isinstance(c, dict) and "catId" in c and "name" in c}

					if category_tree:
						doc.category_sub = category_tree[-1]
						doc.categories_tree = ", ".join(category_tree)
						mark_system_field_modified(doc, "category_sub")
						mark_system_field_modified(doc, "categories_tree")
					if category_tree_dict and prod.get('rootCategory'):
						doc.category_root = category_tree_dict.get(prod.get('rootCategory'))
						mark_system_field_modified(doc, "category_root")

					ean_list = prod.get('eanList')
					if ean_list:
						doc.ean = ean_list[0]
						mark_system_field_modified(doc, "ean")

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
							item_detail.variation_attribtutes = f"{attr_dict[0].get('dimension')}: {attr_dict[0].get('value')}"
					
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
						if (item_l / 10) > 0 and (item_l / 10) > 0 and (item_w / 10) > 0:
							item_detail.length_dimension = f"{item_detail.item_length} x {item_detail.item_breadth} x {item_detail.item_height} cm (= {item_dimension} cm\u00b3)"
					
					item_detail.item_weight = prod.get('itemWeight')
					item_detail.size = prod.get('size')
					item_detail.color = prod.get('color')
					item_detail.desc_feature = prod.get("description") or ""
					if hasattr(doc, "desc_feature"):
						doc.desc_feature = prod.get("description") or ""
						mark_system_field_modified(doc, "desc_feature")
					item_detail.title = prod.get("title") or ""
					doc.title = prod.get("title") or ""
					mark_system_field_modified(doc, "title")
					
					features = prod.get('features') or []
					for f_idx in range(min(5, len(features))):
						setattr(item_detail, f"desc_feature{f_idx+1}", features[f_idx])
						if hasattr(doc, f"desc_feature_{f_idx+1}"):
							setattr(doc, f"desc_feature_{f_idx+1}", features[f_idx])
							mark_system_field_modified(doc, f"desc_feature_{f_idx+1}")

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
							doc.new_current = current.get("NEW")
							mark_system_field_modified(doc, "last_price")
							mark_system_field_modified(doc, "new_current")
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

						apply_price_history(doc, avg30, avg90, avg180, lowest, highest)

					apply_best_price(doc, resolve_best_price(stats_parsed))

					doc.amz_search_keywords = build_search_keywords(item_detail)
					mark_system_field_modified(doc, "amz_search_keywords")
				if doc.ean:
					item_detail.ean = doc.ean
				mirror_details_to_item(doc, item_detail)
				mark_synced(doc, prod)
				item_detail.save(ignore_permissions=True)
				doc.custom_item_detail = item_detail.name

	elif doc.ean:
		EAN = [doc.ean]
		if EAN:
			if not doc.custom_asin_no:
				if not frappe.db.exists('Item Details', {'ean': doc.ean}):
					item_det = frappe.new_doc('Item Details')
					item_det.ean = doc.ean
					item_det.save(ignore_permissions=True)
			if frappe.db.exists('Item Details', {'ean': doc.ean}):
				item_detail = frappe.get_doc('Item Details', {'ean': doc.ean})
			try:
				products = api.query(EAN, stats=30, rating=True, update=0, domain="IN", history=1, product_code_is_asin=False, offers=20)
			except Exception as e:
				flag_sync_failure(doc, doc.ean, "Refresh Failed", f"Keepa query failed: {e}")
				return

			if not products or not isinstance(products, list) or not isinstance(products[0], dict):
				flag_sync_failure(doc, doc.ean, "No Amazon Match", "Keepa returned no product for this EAN.")
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
							n_doc.insert(ignore_permissions=True)
						doc.brand = brand_name
					else:
						doc.brand = brand_name

					images_list = extract_image_names(prod)
					if images_list:
						doc.image = "https://images-na.ssl-images-amazon.com/images/I/" + images_list[0]
					apply_amazon_image_urls(doc, images_list)

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
					doc.custom_asin_no = prod.get("asin") or doc.custom_asin_no
					mark_system_field_modified(doc, "custom_asin_no")
					item_detail.url_amazon = f'https://www.amazon.in/dp/{doc.custom_asin_no}'

					stats_parsed = prod.get("stats_parsed")

					rating, review_count = resolve_reviews(prod, stats_parsed)
					if review_count is not None:
						doc.reviews_count = review_count
						mark_system_field_modified(doc, "reviews_count")
					if rating is not None:
						doc.reviews_rating = str(rating)
						mark_system_field_modified(doc, "reviews_rating")

					apply_monthly_sold(item_detail, prod)
					apply_keyword_fields(item_detail, prod)

					item_detail.parent_asin = prod.get("parentAsin")
					category_tree = []
					category_tree_dict = {}
					if prod.get('categoryTree'):
						category_tree = [c.get("name") for c in prod.get('categoryTree') if isinstance(c, dict) and c.get("name")]
						category_tree_dict = {c["catId"]: c["name"] for c in prod.get('categoryTree') if isinstance(c, dict) and "catId" in c and "name" in c}

					if category_tree:
						doc.category_sub = category_tree[-1]
						doc.categories_tree = ", ".join(category_tree)
						mark_system_field_modified(doc, "category_sub")
						mark_system_field_modified(doc, "categories_tree")
					if category_tree_dict and prod.get('rootCategory'):
						doc.category_root = category_tree_dict.get(prod.get('rootCategory'))
						mark_system_field_modified(doc, "category_root")
					
					ean_list = prod.get('eanList')
					if ean_list and not doc.ean:
						doc.ean = ean_list[0]
						mark_system_field_modified(doc, "ean")

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
							item_detail.package_dimension = f"{item_detail.package_length} x {item_detail.package_width} x {item_detail.package_height} cm (= {pkg_dimension}) cm\u00b3"
					
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
					mark_system_field_modified(doc, "title")

					features = prod.get('features') or []
					for f_idx in range(min(5, len(features))):
						setattr(item_detail, f"desc_feature{f_idx+1}", features[f_idx])

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
							doc.new_current = current.get("NEW")
							mark_system_field_modified(doc, "last_price")
							mark_system_field_modified(doc, "new_current")
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

						apply_price_history(doc, avg30, avg90, avg180, lowest, highest)

					apply_best_price(doc, resolve_best_price(stats_parsed))

					doc.amz_search_keywords = build_search_keywords(item_detail)
					mark_system_field_modified(doc, "amz_search_keywords")

					if doc.custom_asin_no:
						item_detail.asin_no = doc.custom_asin_no
					mirror_details_to_item(doc, item_detail)
					mark_synced(doc, prod)
					item_detail.save(ignore_permissions=True)
				# frappe.msgprint(_("Item(s) has been synced with keepa"))
	
	elif doc.get("custom_url") or doc.get("custom_fsn_no"):
		if doc.get("custom_url"):
			if not frappe.db.exists('Item Details', {'url': doc.get('custom_url')}):
				item_det = frappe.new_doc('Item Details')
				item_det.url = doc.get('custom_url')
				item_det.fsn_no = doc.get('custom_fsn_no')
				item_det.save()
			if frappe.db.exists('Item Details', {'fsn_no': doc.get('custom_fsn_no')}):
				item_detail = frappe.get_doc('Item Details', {'fsn_no': doc.get('custom_fsn_no')})
		if doc.get("custom_fsn_no"):
			if not frappe.db.exists('Item Details', {'fsn_no': doc.get('custom_fsn_no')}):
				item_det = frappe.new_doc('Item Details')
				item_det.url = doc.get('custom_url')
				item_det.fsn_no = doc.get('custom_fsn_no')
				item_det.save(ignore_permissions=True)
			if frappe.db.exists('Item Details', {'fsn_no': doc.get('custom_fsn_no')}):
				item_detail = frappe.get_doc('Item Details', {'fsn_no': doc.get('custom_fsn_no')})

		category_names = frappe.db.get_list("Item Category", fields=['category_name'], pluck='category_name')

		if doc.get("custom_url"):
			fsn = extract_pid_with_regex(doc.get('custom_url'))
		else:
			fsn = doc.get('custom_fsn_no')

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
				cat.insert(ignore_permissions=True)
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
		item_detail.fsn_no = doc.get('custom_fsn_no')
		item_detail.flipkart_dis_per =data['discount']
		item_detail.spec_html_data = str(data['general'])
		item_detail.save(ignore_permissions=True)
		doc.custom_item_detail=item_detail.name

