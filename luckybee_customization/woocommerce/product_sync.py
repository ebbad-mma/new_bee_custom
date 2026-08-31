"""Push products to WooCommerce on the mapping agreed with the storefront developer.

    Item Code      -> sku                    Item Group -> category
    Item Name      -> name                   EAN        -> global_unique_id (GTIN)
    Description    -> description            MRP        -> regular_price
    Stock (Stores) -> stock_quantity         Selling    -> sale_price

publish_item() predates that agreement and does not implement it: it sends the
ASIN as the SKU (empty on most items), reads the category from lb_sub_category
(empty on all 8,020), uses Amazon's title as the product name, never sends the
GTIN, and creates any Woo category it cannot find - which is how a second,
duplicate taxonomy would appear on the storefront. This is the replacement.

Three rules that are not obvious:

  * Categories are looked up, never created. Ashish's structure is the contract
    and Mizanur has already built it exactly; a category we cannot find means
    the item is misfiled on our side, so the item is skipped and reported rather
    than inventing a home for it.
  * WooCommerce ignores a sale_price that is not strictly below regular_price.
    ~113 items have no MRP, or a selling price at or above it, so for those the
    selling price becomes the regular price and no sale price is sent - rather
    than publishing a product with a silently ignored discount.
  * The Item is written with db_set, not save(). Item's before_save chain calls
    sync_keepa_item, so saving on every publish would fire a Keepa lookup per
    product and hit the rate limit long before the catalogue was through.
"""

import json
import time

import frappe
from frappe.utils import cint, flt
from woocommerce import API

from luckybee_customization.category_taxonomy import STRUCTURE
from luckybee_customization.woocommerce.publish_item import get_woocommerce_settings

STOCK_WAREHOUSE = "Stores - SR"
SELLING_PRICE_LIST = "Standard Selling"

VALID_CATEGORIES = {s for subs in STRUCTURE.values() for s in subs}


def _client():
	settings = get_woocommerce_settings()
	return API(
		url=settings["woocommerce_url"],
		consumer_key=settings["api_key"],
		consumer_secret=settings["api_secret"],
		verify_ssl=cint(settings.get("verify_ssl")) == 1,
		wp_api=True,
		version="wc/v3",
		timeout=120,
	)


def fetch_category_map(wcapi):
	"""name (lowercased) -> WooCommerce category id, for every category in the store.

	Raises rather than returning a partial map. The store is on shared hosting
	that intermittently answers 504, and an empty map makes every single item
	skip with "no WooCommerce category" - which reads like a catalogue-wide data
	problem instead of one failed HTTP call. Better to stop and say so.
	"""
	import html
	import time as _time

	mapping, page = {}, 1
	while page <= 10:
		batch, last_status = None, None
		for attempt in range(3):
			resp = wcapi.get("products/categories", params={"per_page": 100, "page": page})
			last_status = resp.status_code
			if resp.status_code == 200:
				try:
					batch = resp.json()
					break
				except ValueError:
					batch = None
			_time.sleep(2 * (attempt + 1))

		if batch is None:
			raise frappe.ValidationError(
				f"Could not read WooCommerce categories (page {page}, "
				f"last status {last_status}). Aborting rather than syncing "
				"products into the wrong categories."
			)
		if not batch:
			break
		for c in batch:
			mapping[html.unescape(c["name"]).strip().lower()] = c["id"]
		page += 1

	if not mapping:
		raise frappe.ValidationError(
			"WooCommerce returned no product categories. The store must have "
			"the agreed category structure before products can be synced."
		)
	return mapping


def _stock(item_code):
	qty = frappe.db.get_value(
		"Bin", {"item_code": item_code, "warehouse": STOCK_WAREHOUSE}, "actual_qty"
	)
	return int(flt(qty))


def _prices(item):
	"""(regular_price, sale_price or None) - see the sale_price rule above."""
	selling = flt(
		frappe.db.get_value(
			"Item Price",
			{"item_code": item.name, "price_list": SELLING_PRICE_LIST, "selling": 1},
			"price_list_rate",
		)
	) or flt(item.standard_rate)
	mrp = flt(item.custom_mrp)

	if mrp and selling and selling < mrp:
		return mrp, selling
	# No MRP, or the selling price is not below it - publish one honest price.
	return (selling or mrp), None


# --- content -----------------------------------------------------------------
# The storefront showed the title, the short description and the description as
# three copies of the same sentence, because 7,326 of 8,020 items have a
# `description` that is literally their `item_name`. Repeating the title is
# worse than saying nothing, so an item with no real content now sends no
# description at all rather than an echo.

MAX_SHORT_DESCRIPTION = 300


def _feature_bullets(item_code):
	"""The Amazon/Keepa feature bullets held on Item Details, if any."""
	name = frappe.db.get_value("Item Details", {"item": item_code})
	if not name:
		return []
	details = frappe.get_doc("Item Details", name)
	return [
		text.strip()
		for text in (getattr(details, f"desc_feature{i}", None) for i in range(1, 7))
		if text and text.strip()
	]


def _descriptions(item):
	"""(description, short_description) - either may be empty."""
	bullets = _feature_bullets(item.name)

	own = (item.description or "").strip()
	# Strip the wrapper Frappe's text editor adds before comparing.
	plain = own.replace("<p>", "").replace("</p>", "").replace("<br>", " ").strip()
	# Not just the item name: some rows carry the item CODE as their description,
	# which is how "B000FI8ER8" was published as a product description. Anything
	# this short is a label, not a description, whatever it happens to match.
	echoes = {
		(item.item_name or "").strip().lower(),
		(item.name or "").strip().lower(),
	}
	own_is_title = plain.lower() in echoes or len(plain) < 20

	if bullets:
		description = "<ul>" + "".join(f"<li>{b}</li>" for b in bullets) + "</ul>"
		short = bullets[0]
		if len(short) > MAX_SHORT_DESCRIPTION:
			short = short[:MAX_SHORT_DESCRIPTION].rsplit(" ", 1)[0] + "..."
		return description, short

	if own and not own_is_title:
		short = plain[:MAX_SHORT_DESCRIPTION].rsplit(" ", 1)[0] + ("..." if len(plain) > MAX_SHORT_DESCRIPTION else "")
		return own, short

	return "", ""


# --- weight, size, brand, tags, attributes -----------------------------------
# package_weight is in GRAMS and the package_* dimensions in CENTIMETRES, read
# off real values (a shuttlecock tube at 82, a water purifier at 6380). Woo is
# sent kilograms and centimetres, its defaults - the store's units must agree.

def _shipping(item):
	out = {}
	grams = flt(item.package_weight)
	if grams > 0:
		out["weight"] = f"{grams / 1000.0:.3f}"
	dims = {
		"length": flt(item.package_length),
		"width": flt(item.package_width),
		"height": flt(item.package_height),
	}
	if any(v > 0 for v in dims.values()):
		out["dimensions"] = {k: (f"{v:.1f}" if v > 0 else "") for k, v in dims.items()}
	return out


# amz_search_keywords is a comma-separated bag straight off Amazon and carries
# tokens no shopper would search for - bare punctuation, and machine categories
# like "sport_activity_glove". Cleaned rather than passed through.
MAX_TAGS = 10


def _tags(item):
	seen, tags = set(), []
	for raw in (item.amz_search_keywords or "").split(","):
		tag = raw.strip().strip("()+-.").strip()
		if len(tag) < 3 or "_" in tag or not any(c.isalpha() for c in tag):
			continue
		# Amazon's keyword bag also contains the product slug
		# ("spaces-exotica-occasions-cotton-bathrobe"). That is a URL, not
		# something a shopper would ever click as a tag.
		if tag.count("-") >= 2:
			continue
		key = tag.lower()
		if key in seen:
			continue
		seen.add(key)
		tags.append({"name": tag})
		if len(tags) >= MAX_TAGS:
			break
	return tags


def _attributes(item):
	"""Brand, colour, size and so on as visible product attributes.

	Brand goes here rather than into Woo's own brand taxonomy, which only exists
	from WooCommerce 9.6 and cannot be confirmed on this store - the settings
	endpoint times out. An attribute works on every version.
	"""
	pairs = [
		# First, so the condition badge and the "Fresh only" filter have a
		# predictable attribute to read.
		("Condition", item.get("lb_condition")),
		("Brand", item.custom_luckybee_brand or item.brand),
		("Colour", item.color),
		("Size", item.size),
		("Manufacturer", item.manufacturer),
		("Model", item.model),
	]
	attributes, position = [], 0
	for label, value in pairs:
		value = (value or "").strip()
		if not value or value.lower() == "none":
			continue
		attributes.append({
			"name": label,
			"position": position,
			"visible": True,
			"variation": False,
			"options": [value],
		})
		position += 1
	return attributes


# WooCommerce validates global_unique_id as a real GTIN and rejects the WHOLE
# product if it is not one. Our fallback used custom_barcode, which for
# Amazon-sourced items is the ASIN ("B07M7F1VPT") because the purchase-invoice
# import copies the item code into it - so a barcode that is not a barcode was
# taking the product down with it. Checked properly here, check digit included.

GTIN_LENGTHS = (8, 12, 13, 14)


def _valid_gtin(value):
	digits = (value or "").strip()
	if not digits.isdigit() or len(digits) not in GTIN_LENGTHS:
		return False
	body, check = digits[:-1], int(digits[-1])
	total = 0
	for i, ch in enumerate(reversed(body)):
		total += int(ch) * (3 if i % 2 == 0 else 1)
	return (10 - total % 10) % 10 == check


def _gtin(item):
	for candidate in (item.ean, item.custom_barcode):
		if _valid_gtin(candidate):
			return (candidate or "").strip()
	return ""


# --- Amazon price comparison --------------------------------------------------
# The storefront shows "Amazon price today - checked <date>" and hides the
# comparison once the figure goes stale. Both halves have to travel: a date with
# no price says nothing, and a price with no date invites treating a months-old
# figure as today's.
#
# NOTE: amz_last_successful_sync is a Date, not a Datetime - there is no time of
# day stored anywhere in the catalogue, so "checked 31 Aug" is the most precise
# statement we can truthfully make.

# Ashish set the storefront comparison window at 30 days (2026-08-31). This is
# deliberately NOT the same as flag_stale_amazon_data's 90-day sweep: that marks
# data we distrust generally, while this is the narrower question of whether a
# figure is current enough to make a public price claim against.
#
# Enforced here as well as in the theme, on purpose. The sync is periodic, so a
# product synced today and not touched again would sit in WooCommerce with a
# months-old figure attached - the theme must check the date too. Dropping the
# meta at source means a stale comparison cannot be rendered even if it does not.
PRICE_COMPARISON_MAX_AGE_DAYS = 30


def _amazon_meta(item):
	"""Inputs for the "cheaper than Amazon today" badge - never the verdict.

	The badge has to be computed at render time, because a stored "we are
	cheaper" flag becomes a false claim the moment Amazon moves. So this sends
	the facts and lets the storefront decide.

	Condition 1 of the badge spec - "genuinely the same product, matched ASIN,
	not an approximate reference" - is enforced here rather than left to the
	theme: without our own matched ASIN and a Matched status, nothing is sent at
	all, so the page has no figures to build a comparison from.
	"""
	if not (item.get("custom_asin_no") or "").strip():
		return []
	if item.get("amz_data_status") != "Matched":
		return []
	checked = item.get("amz_last_successful_sync")
	price = flt(item.get("amz_best_price"))
	if not checked or price <= 0:
		return []

	from frappe.utils import date_diff, nowdate

	if date_diff(nowdate(), checked) > PRICE_COMPARISON_MAX_AGE_DAYS:
		return []

	meta = [
		{"key": "lb_amz_price", "value": f"{price:.2f}"},
		{"key": "lb_amz_price_checked_on", "value": str(checked)},
		{"key": "lb_amz_match", "value": "exact"},
	]
	# Flipkart, for the optional "cheaper than online today" variant - same three
	# conditions, against whichever competitor price is lower.
	fk = flt(item.get("fk_price"))
	if fk > 0 and item.get("fk_data_status") == "Matched" and item.get("fk_last_synced"):
		meta += [
			{"key": "lb_fk_price", "value": f"{fk:.2f}"},
			{"key": "lb_fk_price_checked_on", "value": str(item.get("fk_last_synced"))},
		]
	return meta


def build_payload(item, category_map, include_images=True, require_image=True):
	"""The WooCommerce product body for one Item, or (None, reason) if it cannot go."""
	if item.item_group not in VALID_CATEGORIES:
		return None, f"item_group '{item.item_group}' is not in the agreed structure"

	category_id = category_map.get(item.item_group.strip().lower())
	if not category_id:
		return None, f"no WooCommerce category named '{item.item_group}'"

	regular, sale = _prices(item)
	if not regular:
		return None, "no price"

	# Ashish's rule: a product with no photograph does not go on the storefront.
	# This is a skip, not a failure - the item is fine, it just has nothing to
	# show, and it will publish itself on a later run once a photo is added.
	if require_image and not (item.image or "").strip():
		return None, "no photo"

	description, short_description = _descriptions(item)

	payload = {
		"type": "simple",
		"status": "publish",
		"sku": item.name,
		# item_name is the purchase-invoice line - an internal record, not fit to
		# publish. The Website Title replaces it as soon as one exists. Amazon's
		# own title is never used here: reusing their sentence is duplicate
		# content and their copyright, which is why it lives in search terms only.
		"name": (item.get("lb_website_title") or "").strip() or item.item_name or item.name,
		"description": description,
		"short_description": short_description,
		"categories": [{"id": category_id}],
		"regular_price": f"{regular:.2f}",
		"manage_stock": True,
		"stock_quantity": _stock(item.name),
	}
	payload.update(_shipping(item))
	tags = _tags(item)
	if tags:
		payload["tags"] = tags
	attributes = _attributes(item)
	if attributes:
		payload["attributes"] = attributes
	meta = _amazon_meta(item)
	terms = (item.get("lb_search_terms") or "").strip()
	if terms:
		# Indexed for search, never displayed - see section 1.5 of the spec.
		meta.append({"key": "lb_search_terms", "value": terms[:2000]})
	if meta:
		payload["meta_data"] = meta
	if sale:
		payload["sale_price"] = f"{sale:.2f}"

	# Woo 9.2+ exposes GTIN/UPC/EAN/ISBN as global_unique_id, and validates it.
	gtin = _gtin(item)
	if gtin:
		payload["global_unique_id"] = gtin

	# Every image we hold is hotlinked from Amazon or Flipkart and Woo downloads
	# on import, so this stores a copy of marketplace photography. Ashish decided
	# to publish them as they are for now and replace them later.
	if include_images and item.image:
		payload["images"] = [{"src": item.image}]

	return payload, None


@frappe.whitelist()
def sync_items(item_codes, include_images=True, dry_run=False, require_image=True):
	"""Publish or update the given items. Returns a per-item result."""
	if isinstance(item_codes, str):
		item_codes = json.loads(item_codes)
	include_images = cint(include_images) == 1 if not isinstance(include_images, bool) else include_images
	dry_run = cint(dry_run) == 1 if not isinstance(dry_run, bool) else dry_run
	require_image = cint(require_image) == 1 if not isinstance(require_image, bool) else require_image

	wcapi = _client()
	category_map = fetch_category_map(wcapi)
	results = {"published": [], "updated": [], "skipped": [], "failed": []}

	for code in item_codes:
		item = frappe.get_doc("Item", code)
		payload, reason = build_payload(item, category_map, include_images, require_image)
		if not payload:
			results["skipped"].append({"item": code, "reason": reason})
			continue

		if dry_run:
			results["published"].append({"item": code, "payload": payload})
			continue

		existing = item.get("woocommerce_product_id")
		if not existing:
			# The slug is the web address and is PERMANENT once published:
			# changing it breaks every existing link and loses the ranking. So it
			# is sent on creation only and never on an update, however the title
			# is later edited.
			slug = (item.get("lb_url_slug") or "").strip()
			if slug:
				payload["slug"] = slug
		resp = _send(wcapi, "put" if existing else "post",
					 f"products/{existing}" if existing else "products", payload)
		try:
			body = resp.json()
		except ValueError:
			results["failed"].append({"item": code, "status": resp.status_code,
									  "error": resp.text[:200]})
			continue

		if resp.status_code in (200, 201) and body.get("id"):
			# db_set, not save() - see the module docstring on sync_keepa_item.
			# Guarded because publish_item writes custom_product_url, which does
			# not exist on Item: a plain attribute assignment there is silently
			# dropped, but db_set writes SQL and would fail on every product.
			writes = {"woocommerce_product_id": body["id"], "custom_published": 1,
					  "custom_product_url": body.get("permalink")}
			for field, value in writes.items():
				if frappe.db.has_column("Item", field):
					item.db_set(field, value, update_modified=False)
			bucket = "updated" if existing else "published"
			results[bucket].append({"item": code, "woo_id": body["id"],
									"url": body.get("permalink")})
		elif body.get("code") == "product_invalid_sku":
			# The product exists in Woo but we have no id for it locally - a
			# partial run, or a product created by hand. Adopt it rather than
			# failing forever: SKU is the item code and is unique, so the match
			# is unambiguous.
			found = wcapi.get("products", params={"sku": code}).json()
			if found and isinstance(found, list) and found[0].get("id"):
				woo_id = found[0]["id"]
				retry = wcapi.put(f"products/{woo_id}", payload)
				rbody = retry.json()
				if retry.status_code in (200, 201) and rbody.get("id"):
					if frappe.db.has_column("Item", "woocommerce_product_id"):
						item.db_set("woocommerce_product_id", woo_id, update_modified=False)
					if frappe.db.has_column("Item", "custom_published"):
						item.db_set("custom_published", 1, update_modified=False)
					results["updated"].append({"item": code, "woo_id": woo_id,
											   "url": rbody.get("permalink"),
											   "note": "adopted existing product"})
					continue
			results["failed"].append({"item": code, "status": resp.status_code,
									  "error": str(body)[:200]})
		else:
			results["failed"].append({"item": code, "status": resp.status_code,
									  "error": str(body)[:200]})

	frappe.db.commit()
	return results


# --- whole-catalogue run ------------------------------------------------------
# 7,550 products against a store that has answered a single request in 38
# seconds, and 504'd three times running, is a multi-hour job. It cannot be one
# HTTP call and it must survive being interrupted, so it follows the same shape
# as the Keepa sweep: bounded batches, resumable with no bookkeeping doctype,
# and a clean stop rather than an exception when it runs out of time.

REQUEST_RETRIES = 3
RETRY_BACKOFF_SECONDS = 4
THROTTLE_SECONDS = 0.4
DEFAULT_BATCH = 250
MAX_RUNTIME_SECONDS = 45 * 60


def _send(wcapi, method, path, payload):
	"""POST/PUT with retries on 5xx. 4xx is the store's answer, not a failure to
	deliver, so it comes straight back - a duplicate SKU must reach the caller."""
	resp = None
	for attempt in range(REQUEST_RETRIES):
		resp = getattr(wcapi, method)(path, payload)
		if resp.status_code < 500:
			return resp
		time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
	return resp


def pending_items(limit=None):
	"""Publishable items with no WooCommerce id yet.

	Resumable by construction: the id is written as each product lands, so
	running this again simply picks up where the last run stopped. No progress
	table to keep in step.
	"""
	names = frappe.db.sql(
		"""
		SELECT name FROM `tabItem`
		WHERE disabled = 0
		  AND IFNULL(woocommerce_product_id, '') = ''
		  AND IFNULL(image, '') != ''
		  AND item_group IN %(groups)s
		ORDER BY item_group, name
		""",
		{"groups": tuple(VALID_CATEGORIES)},
		pluck=True,
	)
	return names[: int(limit)] if limit else names


def run_catalogue_sync(batch_size=DEFAULT_BATCH, include_images=True, max_items=None):
	"""Publish everything still outstanding, a batch at a time."""
	started = time.time()
	totals = {"published": 0, "updated": 0, "skipped": 0, "failed": 0,
			  "batches": 0, "stopped_early": None}
	problems = []

	outstanding = pending_items(max_items)
	totals["candidates"] = len(outstanding)

	for start in range(0, len(outstanding), int(batch_size)):
		if time.time() - started > MAX_RUNTIME_SECONDS:
			# Out of time, not out of work. The next run resumes here.
			totals["stopped_early"] = "time limit reached"
			break

		batch = outstanding[start : start + int(batch_size)]
		try:
			result = sync_items(batch, include_images=include_images)
		except Exception as e:
			# A failure to read categories aborts the whole run by design -
			# carrying on would file products under nothing.
			totals["stopped_early"] = f"{type(e).__name__}: {str(e)[:150]}"
			break

		for key in ("published", "updated", "skipped", "failed"):
			totals[key] += len(result[key])
		problems.extend(result["failed"][:5] + result["skipped"][:5])
		totals["batches"] += 1
		time.sleep(THROTTLE_SECONDS)

	totals["remaining"] = len(pending_items())
	totals["minutes"] = round((time.time() - started) / 60.0, 1)
	frappe.log_error(
		title="WooCommerce catalogue sync finished",
		message=frappe.as_json({"totals": totals, "sample_problems": problems[:20]}),
	)
	return totals


@frappe.whitelist()
def enqueue_catalogue_sync(batch_size=DEFAULT_BATCH, include_images=True, max_items=None):
	"""Start the run in the background - it is far longer than a web request."""
	frappe.enqueue(
		"luckybee_customization.woocommerce.product_sync.run_catalogue_sync",
		queue="long",
		timeout=MAX_RUNTIME_SECONDS + 600,
		batch_size=batch_size,
		include_images=include_images,
		max_items=max_items,
	)
	return {"queued": True, "outstanding": len(pending_items()),
			"note": "Resumable - run again to continue where it stops."}


@frappe.whitelist()
def catalogue_sync_status():
	"""How much of the catalogue is published."""
	publishable = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabItem`
		   WHERE disabled = 0 AND IFNULL(image, '') != ''
			 AND item_group IN %(groups)s""",
		{"groups": tuple(VALID_CATEGORIES)},
	)[0][0]
	no_photo = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabItem`
		   WHERE disabled = 0 AND IFNULL(image, '') = ''
			 AND item_group IN %(groups)s""",
		{"groups": tuple(VALID_CATEGORIES)},
	)[0][0]
	linked = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabItem`
		   WHERE disabled = 0 AND IFNULL(woocommerce_product_id, '') != ''""",
	)[0][0]
	return {
		"publishable": publishable,
		"published": linked,
		"remaining": len(pending_items()),
		"held_back_no_photo": no_photo,
		"outside_structure": frappe.db.count("Item", {"disabled": 0})
		- publishable - no_photo,
	}
