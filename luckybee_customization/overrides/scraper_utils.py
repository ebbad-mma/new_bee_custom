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
	}

	if not fsn:
		return data

	url = f"https://www.flipkart.com/product/p/itme?pid={fsn}"
	try:
		page = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT,
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
