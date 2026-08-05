"""Re-align the Item form into three columns and group like fields together.

Almost every value on this form is 6-12 characters - a rate, a percentage, a
rating, a count, a size, a colour. Laid out one or two per row they left most of
a wide screen empty and pushed the form several scrolls long. This patch gives
the short-value sections three columns and merges sections that were asking the
same question in three places (benchmark prices / reviews, sync status /
demand / sales rank, categories / keywords).

Ordering note: Item carries an `Item-main-field_order` property setter, and
Meta.sort_fields() gives that priority over every custom field's `insert_after`
when it names every field (frappe/model/meta.py). So moving fields here means
rewriting that list - setting insert_after alone would have changed nothing
visible. insert_after is still set on the breaks we create, as the fallback for
a site whose field_order gets invalidated.

Re-runnable: every step is create-or-update, and the field order is recomputed
from the live meta each time.
"""

import json

import frappe

# (fieldname, insert_after, label) - layout-only Column Breaks. The label, where
# given, renders as a heading above that column.
NEW_COLUMN_BREAKS = [
	("cb_performance_3", "lb_days_since_receipt", None),
	("cb_classification_3", "lb_sub_category", None),
	("cb_identifiers_3", "custom_asin_no", None),
	("cb_receiving_3", "lb_mrp_confirmed", None),
	("cb_cost_3", "valuation_rate", None),
	("cb_margin_3", "amz_delta_pct", None),
	("cb_amz_list_price", "custom_section_break_i4z5t", "List Price"),
	("cb_amz_rank", "new_highest", "Current & Sales Rank"),
	("cb_amz_data_3", "amz_monthly_sold_date", None),
	("cb_categories_3", "product_category", None),
	("cb_attributes_3", "size", None),
	("cb_codes_3", "amazon_url", None),
	("cb_inventory_2", "weight_per_unit", None),
	("cb_inventory_3", "weight_uom", None),
]

# Breaks left over once their sections were merged. Layout-only fields, no data.
SURPLUS_BREAKS = [
	"sec_amz_benchmark_history",
	"custom_section_break_tzswc",
	"custom_column_break_sgw08",
	"custom_section_break_keepa_features",
	"sec_demand_signals",
	"column_break_demand_signals",
	"sec_categories_keywords",
]

# Several sections were rendering as an unlabelled rule across the form.
SECTION_LABELS = {
	"custom_section_break_dbyew": "Item Prices",
	"custom_section_break_aswln": "Cost & MRP",
	"custom_section_break_poj2b": "Computed Margins",
	"sec_amz_benchmark_current": "Amazon Benchmark & Reviews",
	"custom_section_break_i4z5t": "AMZ Price & Rank History",
	"custom_section_break_keepa_desc": "Amazon Data & Demand",
	"custom_section_break_end_keepa": "Listing Content",
	"custom_section_break_ggx7o": "Categories & Keywords",
	"custom_section_break_wukac": "Amazon Images",
	"custom_section_break_ayvbe": "Codes & Links",
}

# The merged benchmark section is the item's price reference - no reason to
# hide it behind a collapsed header any more.
SECTIONS_TO_EXPAND = ["sec_amz_benchmark_current"]

# Each block is one section, in its new order, starting with its Section Break.
# A block must list every field currently sitting in that stretch of the form;
# anything found in between and not listed is reported and parked at the end of
# the block rather than being silently moved somewhere else.
BLOCKS = [
	# --- Tab 1: Details ---------------------------------------------------
	# Units sold | how long ago | what it's worth.
	[
		"sec_performance",
		"lb_units_30d", "lb_units_90d", "lb_units_180d", "lb_units_365d",
		"custom_column_break_igjrb",
		"lb_days_cover", "lb_days_since_sale", "lb_days_since_receipt",
		"cb_performance_3",
		"lb_sell_through", "lb_stock_value", "lb_velocity_band",
	],
	# Legacy group/category trio | the LB replacements | brand.
	[
		"sec_classification",
		"custom_group", "custom_category", "custom_sub_category",
		"custom_column_break_yhsp1",
		"lb_category_type", "lb_sub_category",
		"cb_classification_3",
		"custom_luckybee_brand", "custom_last_supplier",
	],
	# Our barcodes | Amazon's | tax codes.
	[
		"sec_identifiers",
		"custom_barcode", "custom_legacy_barcode",
		"custom_column_break_2jft9",
		"custom_asin_no",
		"cb_identifiers_3",
		"gst_hsn_code", "is_nil_exempt", "is_non_gst",
	],
	# Primary image, then the thumbnails (lucky_bee_image_gallery), then the
	# grid they come from. Full width - these are pictures, not short values.
	[
		"sec_product_images",
		"lb_primary_image", "lb_image_gallery", "lb_images",
	],
	[
		"sec_receiving_capture",
		"lb_data_status",
		"custom_column_break_jgktw",
		"lb_mrp_confirmed",
		"cb_receiving_3",
		"lb_received_captured_on",
	],
	# --- Tab 2: Pricing & Margin -----------------------------------------
	# What we paid | what it's worth now | what we sell it at.
	[
		"custom_section_break_aswln",
		"lb_actual_cost", "last_purchase_rate",
		"custom_column_break_dlaim",
		"custom_mrp", "valuation_rate",
		"cb_cost_3",
		"max_discount", "lb_lot_ref",
	],
	# Three percentages, one per column.
	[
		"custom_section_break_poj2b",
		"lb_margin_pct",
		"custom_column_break_m76wp",
		"amz_delta_pct",
		"cb_margin_3",
		"mrp_discount_pct",
	],
	# Was three separate sections (benchmark current, benchmark history,
	# reviews) holding nine short numbers between them - all of it is "what
	# Amazon says this is worth", so it is now one section, three columns.
	[
		"sec_amz_benchmark_current",
		"amz_best_price", "amz_best_price_source",
		"column_break_amz_benchmark_current",
		"amz_buybox_current", "amz_buybox_30d", "amz_price_drop_30d",
		"column_break_amz_benchmark_history",
		"reviews_rating", "reviews_count",
	],
	# 16 near-identical AMZ price/rank readings. Split by what they measure and
	# labelled per column, otherwise they are impossible to scan.
	[
		"custom_section_break_i4z5t",
		"cb_amz_list_price",
		"list_price_30days", "list_price_90days", "list_price_180days",
		"list_price_lowest", "list_price_highest",
		"column_break_nyaqj",
		"new_current", "new_30days", "new_90days", "new_180days",
		"new_lowest", "new_highest",
		"cb_amz_rank",
		"last_price", "custom_sales_30days", "custom_sales_90days",
		"custom_sales_180days",
	],
	# --- Tab 3: Market Intelligence --------------------------------------
	# Sync status | demand | rank, was three sections of two or three fields.
	[
		"custom_section_break_keepa_desc",
		"amz_data_status", "amz_last_synced", "amz_last_successful_sync",
		"custom_column_break_s0ind",
		"amz_oos_percent", "amz_monthly_sold", "amz_monthly_sold_date",
		"cb_amz_data_3",
		"sales_rank", "sales_rank_ref", "sales_rank_sub",
	],
	# Category text and the keywords that go with it, in one place.
	[
		"custom_section_break_ggx7o",
		"category_root", "category_sub",
		"custom_column_break_tdlyi",
		"categories_tree", "product_group", "product_category",
		"cb_categories_3",
		"amz_search_keywords",
	],
	# Maker | what it looks like | how it's identified.
	[
		"section_break_zlmj",
		"manufacturer", "model",
		"custom_column_break_xibxd",
		"color", "size", "variation_attributes",
		"cb_attributes_3",
		"brand", "ean", "custom_last_supplier_purchase_rate",
	],
	[
		"custom_section_break_ayvbe",
		"parent_asin", "variation_asins",
		"custom_column_break_n2l3q",
		"partnumber", "upc",
		"cb_codes_3",
		"listed_since", "amazon_url", "locale",
	],
	# --- Tab 4: Inventory & Operations -----------------------------------
	[
		"inventory_valuation_section",
		"weight_per_unit",
		"cb_inventory_2",
		"weight_uom",
		"cb_inventory_3",
		"is_stock_item", "sync_with_woocommerce",
	],
]


def _column_break(fieldname, insert_after, label=None):
	name = frappe.db.get_value("Custom Field", {"dt": "Item", "fieldname": fieldname})
	if name:
		doc = frappe.get_doc("Custom Field", name)
	else:
		if not frappe.get_meta("Item").get_field(insert_after):
			print(f"  ! skipping {fieldname}: anchor {insert_after} not on Item")
			return
		doc = frappe.new_doc("Custom Field")
		doc.dt = "Item"
		doc.fieldname = fieldname
		doc.insert_after = insert_after
	doc.fieldtype = "Column Break"
	doc.label = label
	doc.module = "luckybee_customization"
	doc.save(ignore_permissions=True)


def _delete_break(fieldname):
	name = frappe.db.get_value("Custom Field", {"dt": "Item", "fieldname": fieldname})
	if not name:
		return
	fieldtype = frappe.db.get_value("Custom Field", name, "fieldtype")
	if fieldtype not in ("Section Break", "Column Break"):
		# Refuse to delete anything that could be holding data.
		print(f"  ! not deleting {fieldname}: fieldtype is {fieldtype}, not a break")
		return
	frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)


def _rearrange(order, block, fieldtypes):
	"""Rewrite one section in the order `block` gives, in place.

	Scope is deliberately the section itself - from its Section Break up to the
	next Section or Tab Break that the block does not claim (a merged section
	claims the ones it absorbs). Block members currently living elsewhere - a
	break we just created, or a field pulled in from a merged section - are
	moved in. Anything found inside the section that the block does not name is
	kept, at the end, and reported: a field must never be silently relocated
	into a different section.
	"""
	section = block[0]
	if section not in order:
		print(f"  ! skipping block {section}: not on Item")
		return order

	present = [f for f in block if f in order]
	missing = [f for f in block if f not in order]
	if missing:
		print(f"  ! {section}: not on Item, skipped - {', '.join(missing)}")

	claimed = set(block)
	anchor = order.index(section)

	end = anchor + 1
	while end < len(order):
		fieldname = order[end]
		if fieldtypes.get(fieldname) in ("Section Break", "Tab Break") and fieldname not in claimed:
			break
		end += 1

	strays = [f for f in order[anchor + 1 : end] if f not in claimed]
	if strays:
		print(f"  ! {section}: unlisted fields kept in the last column - {', '.join(strays)}")

	moved = set(present) | set(strays)
	rest = [f for f in order if f not in moved]
	position = len([f for f in order[:anchor] if f not in moved])
	return rest[:position] + present + strays + rest[position:]


def _apply_field_order():
	meta = frappe.get_meta("Item", cached=False)
	order = [df.fieldname for df in meta.fields]
	fieldtypes = {df.fieldname: df.fieldtype for df in meta.fields}
	before = set(order)

	for block in BLOCKS:
		order = _rearrange(order, block, fieldtypes)

	# A reorder must never add or drop a field.
	assert set(order) == before, "field_order lost or gained fields"
	assert len(order) == len(set(order)), "field_order has duplicates"

	value = json.dumps(order)
	existing = frappe.db.exists(
		"Property Setter", {"doc_type": "Item", "doctype_or_field": "DocType", "property": "field_order"}
	)
	if existing:
		frappe.db.set_value("Property Setter", existing, "value", value)
	else:
		frappe.make_property_setter(
			{
				"doctype": "Item",
				"doctype_or_field": "DocType",
				"property": "field_order",
				"value": value,
				"property_type": "Data",
			},
			is_system_generated=False,
			validate_fields_for_doctype=False,
		)


def execute():
	print("Executing Patch: three_column_field_alignment...")

	for fieldname, insert_after, label in NEW_COLUMN_BREAKS:
		_column_break(fieldname, insert_after, label)

	for fieldname in SURPLUS_BREAKS:
		_delete_break(fieldname)

	for fieldname, label in SECTION_LABELS.items():
		name = frappe.db.get_value("Custom Field", {"dt": "Item", "fieldname": fieldname})
		if name:
			frappe.db.set_value("Custom Field", name, "label", label)

	for fieldname in SECTIONS_TO_EXPAND:
		name = frappe.db.get_value("Custom Field", {"dt": "Item", "fieldname": fieldname})
		if name:
			frappe.db.set_value("Custom Field", name, "collapsible", 0)

	frappe.clear_cache(doctype="Item")
	_apply_field_order()
	frappe.clear_cache(doctype="Item")
	frappe.db.commit()
	print("Patch three_column_field_alignment completed successfully.")
