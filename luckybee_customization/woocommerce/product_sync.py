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


def build_payload(item, category_map, include_images=False):
	"""The WooCommerce product body for one Item, or (None, reason) if it cannot go."""
	if item.item_group not in VALID_CATEGORIES:
		return None, f"item_group '{item.item_group}' is not in the agreed structure"

	category_id = category_map.get(item.item_group.strip().lower())
	if not category_id:
		return None, f"no WooCommerce category named '{item.item_group}'"

	regular, sale = _prices(item)
	if not regular:
		return None, "no price"

	description, short_description = _descriptions(item)

	payload = {
		"type": "simple",
		"status": "publish",
		"sku": item.name,
		"name": item.item_name or item.name,
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
	if sale:
		payload["sale_price"] = f"{sale:.2f}"

	# Woo 9.2+ exposes GTIN/UPC/EAN/ISBN as global_unique_id.
	gtin = (item.ean or item.custom_barcode or "").strip()
	if gtin:
		payload["global_unique_id"] = gtin

	# Off by default: every image we hold is hotlinked from Amazon or Flipkart,
	# and Woo downloads on import - which would put marketplace photography on
	# the storefront as a stored copy. Ashish's call, not a default.
	if include_images and item.image:
		payload["images"] = [{"src": item.image}]

	return payload, None


@frappe.whitelist()
def sync_items(item_codes, include_images=False, dry_run=False):
	"""Publish or update the given items. Returns a per-item result."""
	if isinstance(item_codes, str):
		item_codes = json.loads(item_codes)
	include_images = cint(include_images) == 1 if not isinstance(include_images, bool) else include_images
	dry_run = cint(dry_run) == 1 if not isinstance(dry_run, bool) else dry_run

	wcapi = _client()
	category_map = fetch_category_map(wcapi)
	results = {"published": [], "updated": [], "skipped": [], "failed": []}

	for code in item_codes:
		item = frappe.get_doc("Item", code)
		payload, reason = build_payload(item, category_map, include_images)
		if not payload:
			results["skipped"].append({"item": code, "reason": reason})
			continue

		if dry_run:
			results["published"].append({"item": code, "payload": payload})
			continue

		existing = item.get("woocommerce_product_id")
		resp = (
			wcapi.put(f"products/{existing}", payload)
			if existing
			else wcapi.post("products", payload)
		)
		body = resp.json()

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
