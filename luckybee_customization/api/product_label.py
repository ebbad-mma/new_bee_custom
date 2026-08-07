"""Phase 2 section 4 - the two-zone product label.

Left zone is for staff (vertical barcode + the readable ID), right zone is for
the customer (short name, OUR PRICE as the hero, struck MRP and SAVE).

The barcode is rendered server-side as SVG rather than drawn by JavaScript in
the print view. A print dialog does not wait for scripts, so a JS barcode is
a coin toss between a printed label and a blank strip; an SVG that is already
in the HTML always prints.
"""

import io

import frappe
from frappe import _
from frappe.utils import flt

# 50mm x 25mm. Everything in the print format is sized against these, so the
# one place to change if the stock changes is here.
LABEL_WIDTH_MM = 50
LABEL_HEIGHT_MM = 25


def _barcode_class_for(code):
	"""Our own labels are Code 128; a purely numeric 13-digit supplier code is
	an EAN-13 and should be encoded as one so a retail scanner reads it back
	identically.
	"""
	code = (code or "").strip()
	if len(code) == 13 and code.isdigit():
		return "ean13", code
	return "code128", code


@frappe.whitelist()
def get_barcode_svg(code, module_height=8.0):
	"""Return bare <svg> markup for a code, or empty string if it cannot encode.

	Never raises: a label with no barcode is still worth printing (the readable
	ID is right beside it), whereas a traceback loses the whole print run.
	"""
	code = (code or "").strip()
	if not code:
		return ""

	try:
		import barcode
		from barcode.writer import SVGWriter

		symbology, value = _barcode_class_for(code)
		cls = barcode.get_barcode_class(symbology)
		buf = io.BytesIO()
		cls(value, writer=SVGWriter()).write(
			buf,
			options={
				"module_height": flt(module_height),
				# The readable ID is printed separately and styled, so suppress
				# the library's own caption.
				"font_size": 0,
				"text_distance": 0,
				"quiet_zone": 1.0,
				"module_width": 0.22,
			},
		)
		svg = buf.getvalue().decode("utf-8")
	except Exception as e:
		frappe.log_error(f"Barcode render failed for {code}: {e}", "Product Label")
		return ""

	# Strip the XML prolog/doctype - this gets inlined into an HTML page, and a
	# second <?xml?> declaration mid-document is invalid.
	idx = svg.find("<svg")
	return svg[idx:] if idx != -1 else ""


def _selling_price(item_code):
	rows = frappe.db.sql(
		"""SELECT price_list_rate FROM `tabItem Price`
		   WHERE item_code=%s AND price_list='Standard Selling' AND price_list_rate > 0
		   ORDER BY valid_from DESC LIMIT 1""",
		(item_code,),
	)
	return flt(rows[0][0]) if rows else 0.0


def _label_code(item_code):
	"""Whatever code the item actually has - spec 4.2 is explicit that there is
	no forced conversion between L##### and LX#####.
	"""
	meta = frappe.get_meta("Item")
	for fieldname in ("custom_barcode", "custom_legacy_barcode"):
		if meta.has_field(fieldname):
			value = frappe.db.get_value("Item", item_code, fieldname)
			if value:
				return value

	row = frappe.db.get_value(
		"Item Barcode", {"parent": item_code, "parenttype": "Item"}, "barcode",
		order_by="idx asc")
	# Falling back to the item code keeps every label scannable even where no
	# barcode was ever assigned.
	return row or item_code


@frappe.whitelist()
def get_label_data(item_code):
	"""Everything the label needs, computed once so preview and print agree."""
	if not frappe.has_permission("Item", "read", doc=item_code):
		frappe.throw(_("Not permitted to view this item."), frappe.PermissionError)

	item = frappe.db.get_value(
		"Item", item_code, ["name", "item_name", "custom_mrp"], as_dict=True)
	if not item:
		frappe.throw(_("Item not found."))

	our_price = _selling_price(item_code)
	mrp = flt(item.custom_mrp)
	code = _label_code(item_code)

	# Spec 4.2: every label carries a SAVE line so none look full price. Only
	# meaningful when the MRP is genuinely higher than what we charge.
	save_amount = round(mrp - our_price, 2) if (mrp and our_price and mrp > our_price) else 0.0

	return {
		"item_code": item.name,
		# "Item Print Name" - the short name, not the long Amazon title.
		"item_name": item.item_name or item.name,
		"code": code,
		"our_price": our_price,
		"mrp": mrp,
		"save_amount": save_amount,
		"barcode_svg": get_barcode_svg(code),
		"width_mm": LABEL_WIDTH_MM,
		"height_mm": LABEL_HEIGHT_MM,
	}
