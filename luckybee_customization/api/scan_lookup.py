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
from frappe.utils import flt

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
	}
