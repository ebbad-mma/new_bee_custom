"""Flipkart product scraping (Phase 2 section 1).

Repaired, not rewritten from scratch: the previous build keyed every field on
Flipkart's obfuscated CSS class names (VU-ZEz, Nx9bqj CxhGGd, r2CdBx, XQDdHH,
yeLeBC). Those are build artefacts that change on every Flipkart deploy, and
diagnosis showed all five matching zero elements while the page itself came
back fine - HTTP 200, 1.7MB, the real product - so the scraper was silently
returning empties rather than being blocked.

Swapping in today's class names would have worked until the next deploy and
then failed identically. This reads Flipkart's schema.org ld+json block
instead: a published contract carrying name, brand, price, rating, rating
count, images, description, category and sku. Structural fallbacks cover what
ld+json does not expose (MRP, discount, spec tables), and every one of them is
optional - a missing spec table must never cost us the title and price.
"""

import json
import re

import frappe
import requests
from bs4 import BeautifulSoup as bs

# Flipkart serves the same markup either way (verified), but identifying
# ourselves honestly is the polite default and costs nothing.
# A User-Agent alone is a weak disguise: a real browser sends a dozen more
# headers, and their absence is one of the cheapest bot signals to key on.
# Flipkart serves datacenter IPs a bot-check page rather than an error, so this
# is worth getting right before concluding the address itself is blocked.
_HEADERS = {
	"User-Agent": (
		"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
		"(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
	),
	"Accept": (
		"text/html,application/xhtml+xml,application/xml;q=0.9,"
		"image/avif,image/webp,image/apng,*/*;q=0.8"
	),
	"Accept-Language": "en-IN,en-GB;q=0.9,en;q=0.8",
	"Accept-Encoding": "gzip, deflate, br",
	"Upgrade-Insecure-Requests": "1",
	"Sec-Fetch-Dest": "document",
	"Sec-Fetch-Mode": "navigate",
	"Sec-Fetch-Site": "none",
	"Sec-Fetch-User": "?1",
	"Cache-Control": "max-age=0",
	"Connection": "keep-alive",
}

# Flipkart answers a reachable caller in well under a second, so a long timeout
# only ever punishes the failure case - and on a host Flipkart drops packets
# from, every save sat frozen for the full 25 seconds before giving up.
_TIMEOUT = 8


def _proxies():
	"""Optional outbound proxy, for hosts Flipkart refuses to answer.

	Flipkart drops traffic from datacenter ranges silently - the connection
	times out rather than being refused - so a server that works everywhere
	else still cannot fetch a product page. Routing just this request through a
	proxy is the only fix available in code; everything else is a hosting
	decision.

	Unset means direct, which is what a machine Flipkart already serves wants.
	"""
	proxy = frappe.conf.get("flipkart_proxy")
	return {"http": proxy, "https": proxy} if proxy else None


def _timeout():
	"""How long to wait for Flipkart.

	8 seconds is right for a direct connection - Flipkart answers a reachable
	caller in well under a second, so a longer wait only punishes the failure
	case, and on a blocked host every save sat frozen for the full timeout.

	A proxy is a different story: it adds a hop, and the residential proxies
	that Flipkart actually serves are routinely slow enough to blow through 8
	seconds on a first request. So the default rises when one is configured -
	otherwise turning the proxy on would swap "blocked" for "times out", which
	looks identical from the item form. Override with flipkart_timeout in
	site_config.json.
	"""
	configured = frappe.conf.get("flipkart_timeout")
	if configured:
		try:
			return float(configured)
		except (TypeError, ValueError):
			pass
	return 25.0 if frappe.conf.get("flipkart_proxy") else _TIMEOUT


def extract_discount(discount_text):
	"""Numeric part of a discount string, e.g. "66% off" -> "66"."""
	if not discount_text:
		return None
	discount_percentage = re.search(r"\d+", str(discount_text))
	return discount_percentage.group() if discount_percentage else None


def extract_pid_with_regex(url):
	"""FSN is the `pid` parameter's value.

	Keyed strictly on pid=, never a pattern match, because the same URL also
	carries lid=LSTSHOHFCB4WYHQDDY4EUH2ME - which contains the FSN as a
	substring plus extra characters and would silently produce a wrong code.
	"""
	if not url:
		return None
	match = re.search(r"pid=([^&]+)", url)
	return match.group(1) if match else None


def _to_number(value):
	"""Flipkart prices arrive as 2700, "2,700" or "₹2,700" depending on source."""
	if value is None:
		return 0
	if isinstance(value, (int, float)):
		return value
	digits = re.sub(r"[^\d.]", "", str(value))
	if not digits:
		return 0
	try:
		return float(digits) if "." in digits else int(digits)
	except ValueError:
		return 0


def _product_ld_json(soup):
	"""The schema.org Product node, or {} if the page has none."""
	for block in soup.find_all("script", type="application/ld+json"):
		try:
			payload = json.loads(block.string or block.get_text())
		except Exception:
			continue
		for node in (payload if isinstance(payload, list) else [payload]):
			if isinstance(node, dict) and node.get("@type") == "Product":
				return node
	return {}


def _breadcrumbs(soup):
	"""Category trail from the BreadcrumbList node - Flipkart's own hierarchy."""
	for block in soup.find_all("script", type="application/ld+json"):
		try:
			payload = json.loads(block.string or block.get_text())
		except Exception:
			continue
		for node in (payload if isinstance(payload, list) else [payload]):
			if isinstance(node, dict) and node.get("@type") == "BreadcrumbList":
				names = []
				for entry in node.get("itemListElement") or []:
					item = entry.get("item")
					name = item.get("name") if isinstance(item, dict) else entry.get("name")
					if name:
						names.append(name)
				# first crumb is "Home", last is the product itself
				return names[1:-1] if len(names) > 2 else names
	return []


def _mrp_and_discount(raw_html, selling_price):
	"""MRP and discount are not in ld+json, so read the embedded state.

	Falls back to deriving the discount rather than leaving it blank when only
	the MRP is found.
	"""
	mrp = 0
	match = re.search(r'"mrp"\s*:\s*(\d+)', raw_html)
	if match:
		mrp = _to_number(match.group(1))

	discount = None
	match = re.search(r'"discount"\s*:\s*"?(\d+)', raw_html)
	if match:
		discount = match.group(1)
	elif mrp and selling_price and mrp > selling_price:
		discount = str(int(round((mrp - selling_price) / mrp * 100)))

	return mrp, discount


def _specifications(soup):
	"""Best-effort spec tables, keyed on structure rather than class names.

	Flipkart lays specs out as a heading followed by rows of label/value pairs.
	Returns {} when nothing is recognisable - callers treat specs as optional,
	and a missing spec table must never cost us the title and price.
	"""
	specs = {}
	try:
		for table in soup.find_all("table"):
			# The group heading is usually the nearest preceding heading-ish node.
			heading = table.find_previous(["h2", "h3", "div"])
			group = (heading.get_text(strip=True)[:40] if heading else "General") or "General"
			rows = {}
			for tr in table.find_all("tr"):
				cells = tr.find_all(["td", "th"])
				if len(cells) >= 2:
					key = cells[0].get_text(strip=True)
					val = cells[1].get_text(" ", strip=True)
					if key:
						rows[key] = val
			if rows:
				specs.setdefault(group, {}).update(rows)
	except Exception:
		return {}
	return specs


# --- Flipkart's embedded page state -------------------------------------
#
# Changes.docx A5 asks for the full product record - photos, variants,
# highlights, every detail tab - and none of that is in the schema.org block the
# rest of this module reads. It is in window.__INITIAL_STATE__, a ~650KB JSON
# blob of widget data.
#
# Keying on that blob rather than on CSS class names is the point: the widgets
# are addressed by `widgetType` ("atlas_product_details",
# "atlas_multimedia_inline_slider"), which is Flipkart's own stable vocabulary,
# not the obfuscated build-artefact class names that made the previous scraper
# fail on every deploy. Each extractor below is independently optional - a
# missing widget costs that one group, never the whole scrape.

_STATE_RE = re.compile(r"window\.__INITIAL_STATE__\s*=\s*({.*?});?\s*</script>", re.S)

# Flipkart serves image URLs as templates: .../image/{@width}/{@height}/...
_IMAGE_SIZE = "1500"


def _page_state(html):
	"""The parsed __INITIAL_STATE__ blob, or {} if it is absent/unparseable."""
	match = _STATE_RE.search(html or "")
	if not match:
		return {}
	try:
		return json.loads(match.group(1))
	except Exception:
		return {}


def _slots(state):
	"""[(widget_type, widget_data)] for every widget on the page, in order."""
	out = []
	try:
		slots = state["multiWidgetState"]["widgetsData"]["slots"]
	except Exception:
		return out
	for slot in slots:
		widget = (slot.get("slotData") or {}).get("widget") or {}
		widget_type = (widget.get("tracking") or {}).get("widgetType")
		if widget_type:
			out.append((widget_type, widget.get("data") or {}))
	return out


def _slot_data(state, widget_type):
	for found_type, data in _slots(state):
		if found_type == widget_type:
			return data
	return {}


def _dls_pairs(node, pairs=None):
	"""Label/value rows out of Flipkart's DLS tree.

	A row is {label_0: {value: {text: "Brand"}}, label_1: {value: {text:
	["FnS"]}}} - the key is a string, the value is a list of strings. Walking for
	that shape rather than for fixed paths keeps this working when Flipkart
	nests the same row one level deeper on another page.
	"""
	if pairs is None:
		pairs = []
	if isinstance(node, dict):
		key = _dls_text(node.get("label_0"))
		value = _dls_text(node.get("label_1"))
		if key and value:
			pairs.append((key, value))
		for child in node.values():
			_dls_pairs(child, pairs)
	elif isinstance(node, list):
		for child in node:
			_dls_pairs(child, pairs)
	return pairs


def _dls_text(node):
	"""The text of a DLS label node, whether it holds a string or a list."""
	if not isinstance(node, dict):
		return ""
	text = ((node.get("value") or {}).get("text")) if isinstance(node.get("value"), dict) else None
	if isinstance(text, str):
		return text.strip()
	if isinstance(text, list):
		return ", ".join(str(t).strip() for t in text if str(t).strip())
	return ""


def _dls_texts(node, out=None):
	"""Every text leaf under a node, in document order."""
	if out is None:
		out = []
	if isinstance(node, dict):
		for key, value in node.items():
			if key == "text":
				if isinstance(value, str) and value.strip():
					out.append(value.strip())
				elif isinstance(value, list):
					out.extend(str(v).strip() for v in value if str(v).strip())
			else:
				_dls_texts(value, out)
	elif isinstance(node, list):
		for value in node:
			_dls_texts(value, out)
	return out


def _state_images(state):
	"""Product photos, largest size, in the order Flipkart shows them.

	Deliberately only the multimedia slider. The advertisement carousel sitting
	next to it in the same blob is full of rukmini.flixcart.com URLs too - for
	other sellers' products - so a blanket "collect every image URL" would file
	competitors' photos as ours.
	"""
	data = _slot_data(state, "atlas_multimedia_inline_slider")
	if not data:
		return []

	urls = []

	def collect(node):
		if isinstance(node, dict):
			for key, value in node.items():
				if isinstance(value, str) and "flixcart.com/image/" in value:
					urls.append(value)
				else:
					collect(value)
		elif isinstance(node, list):
			for value in node:
				collect(value)

	collect(data)

	seen = set()
	out = []
	for url in urls:
		url = url.replace("{@width}", _IMAGE_SIZE).replace("{@height}", _IMAGE_SIZE)
		if url not in seen:
			seen.add(url)
			out.append(url)
	return out


def _state_variants(state):
	"""Every variant Flipkart offers, from the colour and size swatches.

	contentTitle carries the variant's label ("CBLACK/FTWWHT", "5.5") and
	contentType says whether it is in stock, which matters: a size that is out of
	stock everywhere is not a variant worth chasing.
	"""
	variants = []
	seen = set()

	for widget_type, data in _slots(state):
		if widget_type not in ("atlas_swatch_attribute", "atlas_swatch_image"):
			continue

		# "Selected Color:" / "Select Size" - names the group the swatches belong to.
		heading = ""
		for text in _dls_texts(data):
			if text.lower().startswith(("select", "selected")):
				heading = text.rstrip(":").replace("Selected", "").replace("Select", "").strip()
				break

		def collect(node):
			if isinstance(node, dict):
				tracking = (node.get("tracking") or {}) if isinstance(node.get("tracking"), dict) else {}
				title = (tracking.get("contentTitle") or "").strip()
				if title and title not in ("N", "NA"):
					content_type = tracking.get("contentType") or ""
					key = (heading, title)
					if key not in seen:
						seen.add(key)
						variants.append({
							"attribute": heading or "Variant",
							"value": title,
							"in_stock": 0 if "OutOfStock" in content_type else 1,
						})
				for value in node.values():
					collect(value)
			elif isinstance(node, list):
				for value in node:
					collect(value)

		collect(data)

	return variants


def _state_highlights(state):
	"""The "Product highlights" grid, as key/value pairs."""
	return _dls_pairs(_slot_data(state, "atlas_product_details"))


def _state_detail_sections(state):
	"""The "All details" tabs: Specifications, Description, Warranty and the rest.

	Returned as {tab name: [(key, value)]} plus a "Description" entry for the
	prose block, which has no key/value shape.
	"""
	sections = {}

	# Matched on prefix, not on an exact name: the same widget arrives as
	# "atlas_rich_product_details_vertical_list" on one product and
	# "atlas_rich_product_details" on another, and its inner key is
	# "rpd_tab_showcase_vertical_list_0" or
	# "rpd_tab_feature_descricption_manufacture_layout_1" (Flipkart's typo, not
	# ours). Pinning either exactly means half the catalogue returns nothing.
	for widget_type, data in _slots(state):
		if not widget_type.startswith("atlas_rich_product_details"):
			continue

		for key, node in (data.get("dlsData") or {}).items():
			if not key.startswith("rpd_tab"):
				continue

			pairs = _dls_pairs(node)
			if pairs:
				sections.setdefault("Specifications", []).extend(
					p for p in pairs if p not in sections.get("Specifications", [])
				)

			# The prose block is the longest text leaf; spec values are short.
			texts = [t for t in _dls_texts(node) if len(t) > 200]
			if texts:
				longest = max(texts, key=len)
				if len(longest) > len(sections.get("Description", "")):
					sections["Description"] = longest

	return sections


def _state_ratings(state):
	"""Rating value, ratings count and reviews count.

	Flipkart publishes all three as numbers in the page context, which is both
	more precise and less fragile than the "based on 14 ratings" sentence the
	rating widget renders.
	"""
	try:
		pr = state["multiWidgetState"]["pageDataResponse"]["pageContext"][
			"fdpEventTracking"]["events"]["psi"]["pr"]
	except Exception:
		return None, None, None
	return pr.get("rating"), pr.get("ratingsCount"), pr.get("reviewsCount")


def scrape(fsn):
	"""Return the Flipkart data block for an FSN.

	Every key the caller indexes is always present, with a usable empty value,
	so a partial page can never raise a KeyError mid-save and block a staff
	member from saving the item.
	"""
	data = {
		"title": "",
		"price": 0,
		"mrp": 0,
		"categories": [],
		"rating": 0,
		"ratings": "",
		"reviews": "",
		"discount": None,
		"seller": "",
		"seller_rating": "",
		"image_url": "",
		"multiple_images": [],
		"specifications": {},
		"product_details": {},
		"general": "",
		"highlights": [],
		"description": "",
		"availability": "",
		"brand": "",
		# A5 - the deep record, from the embedded page state.
		"variants": [],
		"detail_sections": {},
		"ratings_count": None,
		"reviews_count": None,
	}

	if not fsn:
		return data

	url = f"https://www.flipkart.com/product/p/itme?pid={fsn}"
	try:
		page = requests.get(url, headers=_HEADERS, timeout=_timeout(),
							proxies=_proxies())
		page.raise_for_status()
	except Exception as e:
		# Network problems must not block the save - the item still needs its
		# photos and counts recording.
		frappe.log_error(f"Flipkart fetch failed for {fsn}: {e}", "Flipkart Scraper")
		return data

	soup = bs(page.content, "html.parser")
	product = _product_ld_json(soup)

	if not product:
		# Distinguish the two causes that look identical from the outside: a
		# genuine markup change, versus Flipkart handing this host a bot-check
		# page. Both arrive as HTTP 200 with no product block, so the response
		# itself has to be described or the next person guesses too.
		page_title = ""
		try:
			if soup.title and soup.title.string:
				page_title = soup.title.string.strip()[:120]
		except Exception:
			pass
		body_text = " ".join((soup.get_text(" ", strip=True) or "").split())[:300]

		frappe.log_error(
			f"No schema.org Product block for FSN {fsn}.\n"
			f"HTTP status: {page.status_code}\n"
			f"Final URL:   {page.url}\n"
			f"Bytes:       {len(page.content)}\n"
			f"Page title:  {page_title!r}\n"
			f"Body starts: {body_text!r}\n\n"
			f"A real product page is typically >100KB and titled with the "
			f"product name. A short page, a login/captcha title, or a redirect "
			f"away from /p/ means this host is being challenged rather than "
			f"served - which is an IP problem, not a parsing one.",
			"Flipkart Scraper",
		)
		return data

	data["title"] = product.get("name") or ""
	data["description"] = product.get("description") or ""

	brand = product.get("brand")
	data["brand"] = brand.get("name") if isinstance(brand, dict) else (brand or "")

	offers = product.get("offers") or {}
	if isinstance(offers, list):
		offers = offers[0] if offers else {}
	data["price"] = _to_number(offers.get("price"))
	data["availability"] = (offers.get("availability") or "").rsplit("/", 1)[-1]

	rating = product.get("aggregateRating") or {}
	data["rating"] = _to_number(rating.get("ratingValue"))
	data["ratings"] = str(rating.get("ratingCount") or "")
	data["reviews"] = str(rating.get("reviewCount") or rating.get("ratingCount") or "")

	images = product.get("image")
	if isinstance(images, list):
		data["multiple_images"] = [i for i in images if i]
	elif images:
		data["multiple_images"] = [images]
	data["image_url"] = data["multiple_images"][0] if data["multiple_images"] else ""

	data["categories"] = _breadcrumbs(soup) or (
		[product["category"]] if product.get("category") else []
	)

	data["mrp"], data["discount"] = _mrp_and_discount(page.text, data["price"])

	specs = _specifications(soup)
	data["specifications"] = specs
	data["general"] = str(specs) if specs else ""

	# --- A5: the deep record ------------------------------------------------
	# Everything below is additive and individually optional. ld+json has
	# already given us title, price and brand by this point, so a Flipkart
	# redesign that breaks one of these extractors costs that group alone.
	state = _page_state(page.text)
	if state:
		# The slider carries every photo Flipkart shows; ld+json carries five.
		images = _state_images(state)
		if images:
			data["multiple_images"] = images
			data["image_url"] = images[0]

		data["variants"] = _state_variants(state)
		data["highlights"] = _state_highlights(state)
		data["detail_sections"] = _state_detail_sections(state)

		if data["detail_sections"].get("Specifications") and not specs:
			# Structural spec scraping found nothing - the state blob did.
			data["specifications"] = {"General": dict(data["detail_sections"]["Specifications"])}
			data["general"] = str(data["specifications"])

		if not data["description"] and data["detail_sections"].get("Description"):
			data["description"] = data["detail_sections"]["Description"]

		rating, ratings_count, reviews_count = _state_ratings(state)
		# ld+json omits aggregateRating on plenty of products that do have
		# ratings, so prefer the page context and fall back to what we had.
		if rating is not None:
			data["rating"] = _to_number(rating)
		if ratings_count is not None:
			data["ratings"] = str(ratings_count)
			data["ratings_count"] = ratings_count
		if reviews_count is not None:
			data["reviews"] = str(reviews_count)
			data["reviews_count"] = reviews_count

	return data


def set_images(doc, image_list):
	"""Record scraped images WITHOUT publishing them.

	Phase 2 section 3.5 is explicit: images from Flipkart, a brand site or a
	catalogue are copyrighted and may not even match the returns-lot item we
	actually hold, so they are reference only and must never become the live
	product image. lb_primary_image is the publishable one, so this
	deliberately no longer writes to it - it fills the reference field and
	flags the item as still needing its own photograph.
	"""
	if not image_list:
		return

	meta = doc.meta
	if meta.has_field("pb_reference_photos") and not doc.get("pb_reference_photos"):
		doc.pb_reference_photos = image_list[0]

	if meta.has_field("pb_needs_own_photos") and not doc.get("lb_primary_image"):
		doc.pb_needs_own_photos = 1
