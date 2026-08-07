"""Phase 2 - "Product info on scan" (read-only lookup).

Deliberately separate from the mobile edit forms: this one changes nothing. It
answers "what is this and what do we sell it for" for a member of staff stood
in an aisle with a customer, so it is read-only by construction - there is no
write path in this module at all.

Matches any barcode the edit forms match (L#####, LX#####, or a supplier code),
so staff do not have to think about which kind of label they are pointing at.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import flt
from frappe.utils.html_utils import sanitize_html

# Anyone who can read an Item can look one up. The lookup shows nothing that is
# not already on the Item form, and price checks on the shop floor are the
# entire point.
def _check_lookup_permission(item_code):
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)
	if not frappe.has_permission("Item", "read", doc=item_code):
		frappe.throw(_("Not permitted to view this item."), frappe.PermissionError)


def resolve_item(search_term):
	"""Same resolution order as the mobile scanner, so a code that opens an edit
	form also resolves here.
	"""
	search_term = (search_term or "").strip()
	if not search_term:
		return None

	rows = frappe.get_all(
		"Item Barcode", filters={"barcode": search_term}, fields=["parent"], limit=1)
	if rows:
		return rows[0].parent

	for fieldname in ("custom_barcode", "custom_legacy_barcode"):
		found = frappe.db.get_value("Item", {fieldname: search_term}, "name")
		if found:
			return found

	# Exact code before fuzzy name, so scanning never lands on a near-match.
	# (a scanned code is exact by definition; only typed searches should fuzz)
	if frappe.db.exists("Item", search_term):
		return search_term

	for filters in (
		[["Item", "name", "like", f"%{search_term}%"]],
		[["Item", "item_name", "like", f"%{search_term}%"]],
	):
		items = frappe.get_all("Item", filters=filters, limit=1)
		if items:
			return items[0].name

	return None


def resolve_item_exact(search_term):
	"""Barcode-only resolution for the customer-facing lookup.

	Deliberately not `resolve_item`: that one falls back to a LIKE search on
	name and item_name, which would let anyone walk the whole catalogue - and
	our prices with it - without ever holding a product. Here the caller has to
	present a code that exists, so the lookup only answers for something the
	person is physically standing in front of.
	"""
	search_term = (search_term or "").strip()
	if not search_term:
		return None

	rows = frappe.get_all(
		"Item Barcode", filters={"barcode": search_term}, fields=["parent"], limit=1)
	if rows:
		return rows[0].parent

	for fieldname in ("custom_barcode", "custom_legacy_barcode"):
		found = frappe.db.get_value("Item", {fieldname: search_term}, "name")
		if found:
			return found

	if frappe.db.exists("Item", search_term):
		return search_term

	return None


def _publishable_image(item):
	"""Only a photograph we took and hold ourselves.

	Every image currently on the catalogue is a hotlinked Amazon CDN URL. Those
	are not ours to republish, and Amazon blocks hotlinking anyway, so they
	would break in a customer's hand. Anything remote is therefore withheld and
	the card simply renders without a picture until a real photo is uploaded -
	the same rule `pb_needs_own_photos` tracks on the Item.
	"""
	for candidate in (item.get("lb_primary_image"), item.get("image")):
		if candidate and candidate.startswith(("/files/", "/private/files/")):
			return candidate
	return None


def _selling_price(item_code):
	"""Our Price - the Standard Selling Item Price, which is what the label and
	the till both use.
	"""
	rows = frappe.db.sql(
		"""SELECT price_list_rate FROM `tabItem Price`
		   WHERE item_code=%s AND price_list='Standard Selling' AND price_list_rate > 0
		   ORDER BY valid_from DESC LIMIT 1""",
		(item_code,),
	)
	return flt(rows[0][0]) if rows else 0.0


def _stock_by_warehouse(item_code):
	rows = frappe.db.sql(
		"""SELECT warehouse, actual_qty FROM `tabBin`
		   WHERE item_code=%s AND actual_qty != 0
		   ORDER BY actual_qty DESC""",
		(item_code,), as_dict=True,
	)
	return [{"warehouse": r.warehouse, "qty": flt(r.actual_qty)} for r in rows]


@frappe.whitelist()
def lookup_product(search_term):
	"""Read-only product summary for an in-aisle scan."""
	item_code = resolve_item(search_term)
	if not item_code:
		return {"status": "not_found", "message": _("No product matches that code.")}

	_check_lookup_permission(item_code)

	fields = [
		"name", "item_name", "custom_luckybee_brand", "brand",
		"custom_mrp", "lb_primary_image", "image",
		"custom_group", "custom_category", "lb_sub_category",
		"lb_velocity_band", "lb_days_cover", "disabled",
		"custom_barcode", "custom_legacy_barcode", "custom_asin_no",
		"custom_url", "custom_fsn_no", "amz_best_price", "amz_buybox_current",
		"amz_last_successful_sync", "amz_last_synced", "reviews_rating",
		"reviews_count", "pb_reference_relationship",
		"lb_actual_cost", "lb_margin_pct",
	]
	meta = frappe.get_meta("Item")
	fields = [f for f in fields if meta.has_field(f) or f == "name"]
	item = frappe.db.get_value("Item", item_code, fields, as_dict=True)

	stock = _stock_by_warehouse(item_code)
	our_price = _selling_price(item_code)
	mrp = flt(item.get("custom_mrp"))

	# SAVE is the same figure the label prints, computed the same way, so the
	# aisle and the shelf can never disagree.
	save_amount = round(mrp - our_price, 2) if (mrp and our_price and mrp > our_price) else 0.0

	# Brand: the Lucky Bee field is the one staff maintain; the native `brand`
	# link is Keepa-populated and often blank or an Amazon spelling.
	brand = item.get("custom_luckybee_brand") or item.get("brand") or ""

	return {
		"status": "found",
		"item_code": item.name,
		"item_name": item.item_name,
		"image": item.get("lb_primary_image") or item.get("image") or None,
		"our_price": our_price,
		"mrp": mrp,
		"save_amount": save_amount,
		"stock": stock,
		"total_stock": sum(s["qty"] for s in stock),
		"brand": brand,
		"category": item.get("custom_category") or item.get("custom_group") or "",
		"sub_category": item.get("lb_sub_category") or "",
		"velocity_band": item.get("lb_velocity_band") or "",
		"days_cover": item.get("lb_days_cover"),
		"disabled": bool(item.get("disabled")),
		"codes": _codes(item_code, item),
		"marketplace": _marketplace(item),
		"rating": _rating(item),
		"costing": _costing(item),
	}


def _marketplace(item):
	"""Marketplace price and link, so a customer can check the going rate.

	Links are only ever built from a code we hold - never a search URL - so a
	wrong link cannot land someone on an unrelated product and make our price
	look false. The price is Keepa-cached rather than live, so it carries the
	date it was taken; a figure with no date invites someone to treat a
	fortnight-old price as today's.
	"""
	out = {}

	asin = (item.get("custom_asin_no") or "").strip()
	if asin:
		amazon = {"url": f"https://www.amazon.in/dp/{asin}"}
		price = flt(item.get("amz_best_price")) or flt(item.get("amz_buybox_current"))
		if price:
			amazon["price"] = price
			amazon["as_of"] = item.get("amz_last_successful_sync") or item.get("amz_last_synced")
		out["amazon"] = amazon

	# Nothing carries these yet; the link appears the moment an FSN is entered.
	url = (item.get("custom_url") or "").strip()
	fsn = (item.get("custom_fsn_no") or "").strip()
	if url.startswith("http"):
		out["flipkart"] = {"url": url}
	elif fsn:
		out["flipkart"] = {"url": f"https://www.flipkart.com/product/p/itm?pid={fsn}"}

	return out


def _rating(item):
	"""Star rating, but only where it belongs to this product.

	`reviews_rating` is Keepa data for the item's own ASIN, which is fair to
	show. What must not be shown is a rating inherited from a *reference* ASIN
	that is merely similar - section 3.3 is explicit that reviews belong to the
	other product unless the relationship is an exact match. Publishing a
	neighbouring product's stars to a customer is exactly that mistake.
	"""
	rating = flt(item.get("reviews_rating"))
	if not rating:
		return None

	own_asin = (item.get("custom_asin_no") or "").strip()
	if not own_asin:
		relationship = (item.get("pb_reference_relationship") or "").strip()
		if relationship != "Exact match":
			return None

	return {"rating": rating, "count": int(flt(item.get("reviews_count")))}


# Who may see cost and margin. Kept as a constant rather than inlined so the
# "senior" tier is one edit, and so it is obvious that this is a deliberate
# privilege rather than an accident of who happens to hold Item read.
SENIOR_ROLES = ("Owner-Supervisor", "System Manager")


def _costing(item):
	"""Cost and margin, for on-the-spot discount decisions - senior staff only.

	Withheld unless `lb_actual_cost` is genuinely non-zero. `calculate_margins`
	writes cost and margin together, yet 7,861 items currently carry a margin
	with a zero cost, so the stored margin is a leftover from a cost that is no
	longer there. Rendering those would tell someone with discount authority
	that a product cost nothing and earns 475%, which is worse than showing
	them nothing at all. Once the cost field is backfilled these appear on
	their own.
	"""
	if not (set(frappe.get_roles()) & set(SENIOR_ROLES)):
		return None

	cost = flt(item.get("lb_actual_cost"))
	if not cost:
		return {"available": False,
				"reason": _("Cost is not recorded for this item.")}

	return {
		"available": True,
		"cost": cost,
		"margin_pct": flt(item.get("lb_margin_pct")),
	}


def _codes(item_code, item):
	"""Every code that identifies this unit, for staff reading a label."""
	codes = []
	for row in frappe.get_all("Item Barcode", filters={"parent": item_code},
							  fields=["barcode"], limit=10):
		if row.barcode:
			codes.append(row.barcode)
	for fieldname in ("custom_barcode", "custom_legacy_barcode"):
		value = (item.get(fieldname) or "").strip()
		if value and value not in codes:
			codes.append(value)
	return codes


# Everyone in the shop shares the store's public IP, so this has to clear a busy
# Saturday by a wide margin - 60/hour blocked real customers within minutes.
#
# It is not dropped altogether, because "you need a valid code" is not the guard
# it appears to be: item codes run L10001-L16381 with no gaps, so walking that
# range returns a product every single time and dumps 6,364 prices. This ceiling
# makes a full scrape an hours-long, obvious job rather than a two-minute one,
# while no genuine shopper will come near it.
@frappe.whitelist(allow_guest=True)
@rate_limit(limit=1000, seconds=60 * 60, ip_based=True)
def lookup_product_public(search_term):
	"""Customer-facing scan lookup - no login, and no stock figures.

	A deliberately separate function rather than a flag on `lookup_product`:
	sharing one body would mean a future edit there could widen what the public
	sees without anyone noticing. What a customer may see is enumerated here and
	nowhere else.

	Withheld on purpose: stock on hand, velocity band, days cover and cost. Those
	are commercial intelligence, and published to anyone with a phone they would
	hand a competitor our bestseller list and our reorder timing.
	"""
	item_code = resolve_item_exact(search_term)
	if not item_code:
		return {"status": "not_found", "message": _("No product matches that code.")}

	fields = [
		"name", "item_name", "description", "custom_mrp",
		"lb_primary_image", "image", "custom_asin_no", "custom_url",
		"custom_fsn_no", "amz_best_price", "amz_buybox_current",
		"amz_last_successful_sync", "amz_last_synced", "reviews_rating",
		"reviews_count", "pb_reference_relationship", "disabled",
	]
	meta = frappe.get_meta("Item")
	fields = [f for f in fields if f == "name" or meta.has_field(f)]
	item = frappe.db.get_value("Item", item_code, fields, as_dict=True)

	# A withdrawn line is not something to quote a price on.
	if item.get("disabled"):
		return {"status": "not_found", "message": _("No product matches that code.")}

	our_price = _selling_price(item_code)
	mrp = flt(item.get("custom_mrp"))
	save_amount = round(mrp - our_price, 2) if (mrp and our_price and mrp > our_price) else 0.0

	return {
		"status": "found",
		"item_code": item.name,
		"item_name": item.item_name,
		# Keepa-sourced descriptions are HTML; sanitise before it reaches a public page.
		"description": sanitize_html(item.get("description") or ""),
		"image": _publishable_image(item),
		"our_price": our_price,
		"mrp": mrp,
		"save_amount": save_amount,
		"marketplace": _marketplace(item),
		"rating": _rating(item),
		# Category and brand are deliberately absent: the client's list puts both
		# on the staff side, so they are returned by `lookup_product` only.
	}
