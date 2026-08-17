"""Changes.docx A1 and A3.

A1 - every code a product has in one place. EAN and FSN were stranded over on
the Market Intelligence tab under Item Attributes, while Barcode, Legacy
Barcode, ASIN and HSN sat together in Details -> Identifiers. They are all
identifiers, so they all live in Identifiers now:

    our codes            marketplace codes        trade codes
    Barcode              ASIN                     EAN
    Legacy Barcode       FSN                      HSN/SAC

A3 - the Pricing tab carried AMZ Best Price and nothing for Flipkart, so the two
competitor prices could not be read side by side. fk_price sits with it, filled
by the FSN scrape (overrides/item.py), plus fk_last_synced so a stale Flipkart
price is visible as such rather than being read as today's.

Ordering works the same way as three_column_field_alignment, whose helpers this
reuses: Item's field_order property setter outranks every field's insert_after,
so a move means rewriting that list.
"""

import frappe

from luckybee_customization.patches.keepa_intelligence_fields import field
from luckybee_customization.patches.three_column_field_alignment import _apply_field_order

BLOCKS = [
	# A1 - all of a product's codes, three columns.
	[
		"sec_identifiers",
		"custom_barcode", "custom_legacy_barcode",
		"custom_column_break_2jft9",
		"custom_asin_no", "custom_fsn_no",
		"cb_identifiers_3",
		"ean", "gst_hsn_code", "is_nil_exempt", "is_non_gst",
	],
	# A3 - Flipkart's price beside Amazon's. The section is no longer
	# Amazon-only, hence the relabel below.
	[
		"sec_amz_benchmark_current",
		"amz_best_price", "amz_best_price_source", "fk_price", "fk_last_synced",
		"column_break_amz_benchmark_current",
		"amz_buybox_current", "amz_buybox_30d", "amz_price_drop_30d",
		"column_break_amz_benchmark_history",
		"reviews_rating", "reviews_count",
	],
]


def execute():
	print("Executing Patch: codes_and_flipkart_price...")

	field("Item", "fk_price", "amz_best_price_source",
	      fieldtype="Currency", label="Flipkart Price",
	      description="Flipkart's current selling price, from the last scrape of the FSN.")

	field("Item", "fk_last_synced", "fk_price",
	      fieldtype="Date", label="Flipkart Last Synced", read_only=1,
	      description="When the Flipkart price above was last read successfully.")

	# EAN's label still said "AMZ EAN" from when it lived on the Amazon tab. It
	# is the product's EAN whichever marketplace it came from. The label lives in
	# a Property Setter as well as on the Custom Field, and the Property Setter
	# is what the form actually renders - setting only the field leaves the old
	# label on screen.
	ean = frappe.db.get_value("Custom Field", {"dt": "Item", "fieldname": "ean"})
	if ean:
		frappe.db.set_value("Custom Field", ean, "label", "EAN")
	if frappe.db.exists("Property Setter", "Item-ean-label"):
		frappe.db.set_value("Property Setter", "Item-ean-label", "value", "EAN")

	benchmark = frappe.db.get_value(
		"Custom Field", {"dt": "Item", "fieldname": "sec_amz_benchmark_current"}
	)
	if benchmark:
		frappe.db.set_value("Custom Field", benchmark, "label", "Marketplace Benchmark & Reviews")

	frappe.clear_cache(doctype="Item")
	_apply_field_order(BLOCKS)
	frappe.clear_cache(doctype="Item")
	frappe.db.commit()
	print("Patch codes_and_flipkart_price completed successfully.")
