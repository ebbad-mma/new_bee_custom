"""Phase 2 section 3 - Product Builder capture fields.

For products with no Amazon or Flipkart match, whose data lives on a brand
site, in a catalogue, or on a similar product's listing. The organising
principle from the spec: every field records WHERE it came from and HOW
confident we are, so approximate data is never published as though it were
exact.

The catalogue link fields (pb_linked_catalogue, pb_catalogue_page_ref) already
exist from the section 2 work and are not repeated here.
"""

import frappe

from luckybee_customization.patches.keepa_intelligence_fields import field

# Section 3.3 - how much of a reference listing may be copied depends entirely
# on how related it is. Stored on the Item so the sync logic and the reviewer
# both read the same declaration.
RELATIONSHIP_OPTIONS = "\n".join([
	"",
	"Exact match",
	"Same product, different brand",
	"Same brand, different variation - size",
	"Same brand, different variation - color",
	"Same sub-category only",
])

# Section 3.4
SOURCE_OPTIONS = "\n".join([
	"",
	"Own inspection",
	"Brand website",
	"Brand catalogue",
	"Amazon reference",
	"Flipkart reference",
	"Similar product",
	"Manual",
])

CONFIDENCE_OPTIONS = "\n".join([
	"",
	"Confirmed",
	"Approximate",
	"Placeholder",
])

PUBLISH_STATUS_OPTIONS = "\n".join([
	"Draft",
	"Ready to Publish",
])


def execute():
	print("Executing Patch: product_builder_fields...")

	# Its own tab: this is a distinct way of working, used only when there is no
	# ASIN/FSN match, and folding it into an existing tab would put it in front
	# of staff who never need it.
	field("Item", "tab_product_builder", "custom_supplier_history_tab",
		  fieldtype="Tab Break", label="Product Builder")

	# --- 3.1 reference sources -------------------------------------------
	field("Item", "sec_pb_reference", "tab_product_builder",
		  fieldtype="Section Break", label="Reference Sources",
		  description="Where the data for this product is being taken from. "
					  "Nothing here is published as-is.")

	field("Item", "pb_reference_asin", "sec_pb_reference",
		  fieldtype="Data", label="Reference ASIN",
		  description="A comparable Amazon product. What gets copied depends on the relationship below.")

	field("Item", "pb_reference_relationship", "pb_reference_asin",
		  fieldtype="Select", label="Reference Relationship",
		  options=RELATIONSHIP_OPTIONS,
		  description="How related the reference is. The looser it is, the less is copied.")

	field("Item", "column_break_pb_reference", "pb_reference_relationship",
		  fieldtype="Column Break")

	field("Item", "pb_reference_flipkart_url", "column_break_pb_reference",
		  fieldtype="Data", label="Reference Flipkart URL",
		  description="Paste the full URL - the FSN is taken from the pid= parameter.")

	field("Item", "pb_reference_weblink", "pb_reference_flipkart_url",
		  fieldtype="Data", label="Reference Web Link",
		  description="Brand site or other source. Trusted for specs and description, never for price or reviews.")

	# --- 3.5 photo rule ---------------------------------------------------
	field("Item", "sec_pb_photos", "pb_reference_weblink",
		  fieldtype="Section Break", label="Reference Photos")

	field("Item", "pb_reference_photos", "sec_pb_photos",
		  fieldtype="Attach", label="Reference Photo",
		  description="Reference only - copyrighted, and may not match the returns-lot item we hold. "
					  "Never published. Own photos go in the Product Images section.")

	field("Item", "pb_needs_own_photos", "pb_reference_photos",
		  fieldtype="Check", label="Needs Own Photos", read_only=1,
		  description="Set automatically while the item has no photograph of its own.")

	# --- 3.4 source & confidence -----------------------------------------
	field("Item", "sec_pb_provenance", "pb_needs_own_photos",
		  fieldtype="Section Break", label="Source & Confidence")

	field("Item", "pb_data_source", "sec_pb_provenance",
		  fieldtype="Select", label="Data Source", options=SOURCE_OPTIONS)

	field("Item", "pb_confidence", "pb_data_source",
		  fieldtype="Select", label="Confidence", options=CONFIDENCE_OPTIONS)

	field("Item", "column_break_pb_provenance", "pb_confidence",
		  fieldtype="Column Break")

	field("Item", "pb_publish_status", "column_break_pb_provenance",
		  fieldtype="Select", label="Publish Status", options=PUBLISH_STATUS_OPTIONS,
		  default="Draft",
		  description="Stays Draft until the essentials are Confirmed from a reliable source.")

	field("Item", "pb_review_notes", "pb_publish_status",
		  fieldtype="Small Text", label="Review Notes",
		  description="What still needs checking before this is published.")

	frappe.clear_cache(doctype="Item")
