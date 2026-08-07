"""Phase 2 section 3 - Product Builder.

Assembles a publishable product from whatever source is available, while
tracking how reliable each piece is. The rule that shapes everything here:
data taken from the physical product is publishable, data borrowed from a
similar item is a draft needing review - so nothing copied from a reference is
ever silently presented as exact.
"""

import frappe
from frappe import _

# Section 3.3 - what may be copied at each relationship level. The looser the
# relationship, the less is safe to take. Anything absent from a relationship's
# list is deliberately NOT copied, because it belongs to the other product:
# another brand's price and reviews are not ours to inherit, and a different
# variation's size is simply wrong for this one.
SYNC_RULES = {
	"Exact match": {
		# Everything, with nothing held back - the spec's own wording is
		# "Nothing; it is the real product", so this list has to be the union
		# of every other relationship's or it would quietly withhold something.
		"fields": ["category", "sub_category", "specs", "dimensions", "keywords",
				   "description", "features", "brand", "price", "reviews",
				   "images", "type"],
		"note": "It is the real product, so everything is safe.",
	},
	"Same product, different brand": {
		"fields": ["category", "sub_category", "specs", "dimensions", "keywords", "type"],
		"note": "Brand, price and reviews belong to the other brand.",
	},
	"Same brand, different variation - size": {
		"fields": ["brand", "category", "sub_category", "description", "features",
				   "reviews", "keywords", "images"],
		"note": "Price and exact dimensions differ by size.",
	},
	"Same brand, different variation - color": {
		"fields": ["brand", "category", "sub_category", "description", "features",
				   "reviews", "keywords", "images", "price", "dimensions"],
		"note": "Only the colour attribute itself differs.",
	},
	"Same sub-category only": {
		"fields": ["category", "sub_category", "keywords", "type"],
		"note": "A categorisation hint and nothing more.",
	},
}

# A brand website or catalogue is a different kind of source: trusted for what
# the product IS, never for what it sells for or what shoppers thought of it.
WEB_SOURCE_RULES = {
	"fields": ["specs", "dimensions", "description", "features", "keywords"],
	"note": "Brand sources are never trusted for price or reviews.",
}

# Section 3.4 - what has to be Confirmed before an item may leave Draft.
PUBLISH_ESSENTIALS = ("item_name", "custom_luckybee_brand", "custom_mrp")


@frappe.whitelist()
def get_sync_plan(relationship):
	"""What a given relationship permits - shown to staff before anything is
	copied, so the decision is visible rather than buried in code.
	"""
	rule = SYNC_RULES.get(relationship)
	if not rule:
		return {"relationship": relationship, "fields": [], "note":
				_("Choose a relationship to see what can be copied.")}
	return {
		"relationship": relationship,
		"fields": rule["fields"],
		"excluded": sorted(
			{f for r in SYNC_RULES.values() for f in r["fields"]} - set(rule["fields"])
		),
		"note": rule["note"],
	}


def _mark(doc, source, confidence):
	"""Stamp provenance. Everything pulled from a reference is 'Approximate'
	and needs review - section 3.3 requires it be marked, not just copied.
	"""
	if doc.meta.has_field("pb_data_source"):
		doc.pb_data_source = source
	if doc.meta.has_field("pb_confidence"):
		doc.pb_confidence = confidence
	if doc.meta.has_field("pb_publish_status") and confidence != "Confirmed":
		doc.pb_publish_status = "Draft"


@frappe.whitelist()
def sync_from_reference(item_code, relationship=None):
	"""Pull comparable data from the reference ASIN, filtered by relationship.

	Returns what it applied and what it deliberately withheld, so the staff
	member can see the difference rather than wondering why a field stayed
	empty.
	"""
	if not frappe.has_permission("Item", "write", doc=item_code):
		frappe.throw(_("Not permitted to edit this item."), frappe.PermissionError)

	doc = frappe.get_doc("Item", item_code)
	relationship = relationship or doc.get("pb_reference_relationship")
	asin = doc.get("pb_reference_asin")

	if not asin:
		return {"status": "error", "message": _("Set a Reference ASIN first.")}
	if not relationship:
		return {"status": "error", "message": _("Choose how the reference relates to this product.")}

	rule = SYNC_RULES.get(relationship)
	if not rule:
		return {"status": "error", "message": _("Unknown relationship.")}

	allowed = set(rule["fields"])

	from luckybee_customization.api.mobile_forms import fetch_keepa_preview

	# Reuses the existing Keepa path rather than adding a second way of talking
	# to them; it already degrades gracefully when Keepa is slow or out of
	# tokens, which must not block the builder.
	preview = fetch_keepa_preview(asin) or {}

	applied, withheld = [], []

	def maybe(field_key, fieldname, value):
		if not value:
			return
		if field_key not in allowed:
			withheld.append(field_key)
			return
		if doc.meta.has_field(fieldname):
			doc.set(fieldname, value)
			applied.append(fieldname)

	# Only what a preview call can actually supply. The heavier pulls (specs,
	# dimensions, features) come from the full sync once an ASIN is set for
	# real, and are governed by the same `allowed` set.
	maybe("description", "description", preview.get("title"))
	maybe("price", "custom_mrp", preview.get("price"))

	# An exact match is the real product, so it may simply take the ASIN and
	# use the ordinary Keepa sync from then on.
	if relationship == "Exact match" and doc.meta.has_field("custom_asin_no") and not doc.get("custom_asin_no"):
		doc.custom_asin_no = asin
		applied.append("custom_asin_no")

	confidence = "Confirmed" if relationship == "Exact match" else "Approximate"
	_mark(doc, "Amazon reference", confidence)

	doc.save()
	frappe.db.commit()

	return {
		"status": "ok",
		"relationship": relationship,
		"applied": applied,
		"withheld": sorted(set(withheld)),
		"confidence": confidence,
		"note": rule["note"],
	}


@frappe.whitelist()
def sync_from_flipkart(item_code):
	"""Pull from the reference Flipkart URL. Same provenance rules apply."""
	if not frappe.has_permission("Item", "write", doc=item_code):
		frappe.throw(_("Not permitted to edit this item."), frappe.PermissionError)

	doc = frappe.get_doc("Item", item_code)
	url = doc.get("pb_reference_flipkart_url")
	if not url:
		return {"status": "error", "message": _("Paste a Flipkart URL first.")}

	from luckybee_customization.overrides.scraper_utils import extract_pid_with_regex, scrape

	fsn = extract_pid_with_regex(url) or (url.strip() if "/" not in url else None)
	if not fsn:
		return {"status": "error", "message": _("Could not find a pid= code in that URL.")}

	data = scrape(fsn)
	if not data.get("title"):
		return {"status": "error", "message": _("Flipkart returned nothing for that code.")}

	applied = []
	if doc.meta.has_field("description") and data.get("description"):
		doc.description = data["description"]
		applied.append("description")
	# MRP, not the current selling price - the label's SAVE line depends on it.
	if doc.meta.has_field("custom_mrp") and (data.get("mrp") or data.get("price")):
		doc.custom_mrp = data.get("mrp") or data.get("price")
		applied.append("custom_mrp")

	# Section 3.5: the images are recorded as reference and never published.
	from luckybee_customization.overrides.scraper_utils import set_images
	set_images(doc, data.get("multiple_images"))

	_mark(doc, "Flipkart reference", "Approximate")
	doc.save()
	frappe.db.commit()

	return {
		"status": "ok",
		"fsn": fsn,
		"applied": applied,
		"confidence": "Approximate",
		"note": _("Flipkart data is a reference - review before publishing."),
	}


@frappe.whitelist()
def check_publish_readiness(item_code):
	"""Section 3.4 publish gate.

	Reports rather than blocks: staff need to know what is missing, and a hard
	block on save would stop them recording partial data at all.
	"""
	doc = frappe.get_doc("Item", item_code)

	missing = [
		doc.meta.get_label(f) or f
		for f in PUBLISH_ESSENTIALS
		if doc.meta.has_field(f) and not doc.get(f)
	]

	blockers = list(missing)
	if doc.meta.has_field("pb_confidence") and doc.get("pb_confidence") == "Placeholder":
		blockers.append(_("Confidence is still Placeholder"))
	# Section 3.5 - a reference image must never stand in as the product photo.
	if doc.meta.has_field("pb_needs_own_photos") and doc.get("pb_needs_own_photos"):
		blockers.append(_("Still needs its own photographs"))

	return {
		"item_code": item_code,
		"ready": not blockers,
		"blockers": blockers,
		"publish_status": doc.get("pb_publish_status"),
	}
