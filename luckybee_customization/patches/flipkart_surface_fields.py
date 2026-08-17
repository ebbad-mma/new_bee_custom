"""Changes.docx A4 and A5 - bring the Flipkart record onto the Item form.

A5's point is that Item Details is a deep archive nobody opens mid-sale. The
figures a person actually weighs when deciding a price have to be on the Item
itself. So the Flipkart data the scraper already pulls is surfaced here, in the
places the document names, and Item Details keeps its copy as the archive.

A4's selling-decision block is an HTML field rather than stored values: our
price, the Amazon price and the Flipkart price all change independently, and a
stored verdict would be wrong the moment any one of them moved.
"""

import frappe

from luckybee_customization.patches.keepa_intelligence_fields import field


def execute():
	print("Executing Patch: flipkart_surface_fields...")

	# --- A4: the selling-decision block --------------------------------------
	# First thing in the benchmark section, directly above the prices it
	# compares - a verdict sitting below its own evidence reads as a footnote.
	field("Item", "lb_price_decision", "sec_amz_benchmark_current",
		  fieldtype="HTML", label="Selling Decision")

	# --- A5: Flipkart Benchmark, on the Pricing tab, collapsed ---------------
	field("Item", "sec_fk_benchmark", "fk_last_synced",
		  fieldtype="Section Break", label="Flipkart Benchmark",
		  collapsible=1)

	field("Item", "fk_rating", "sec_fk_benchmark",
		  fieldtype="Float", label="Flipkart Rating", precision="1", read_only=1)

	field("Item", "fk_ratings_count", "fk_rating",
		  fieldtype="Int", label="Flipkart Ratings Count", read_only=1)

	field("Item", "cb_fk_benchmark", "fk_ratings_count", fieldtype="Column Break")

	field("Item", "fk_reviews_count", "cb_fk_benchmark",
		  fieldtype="Int", label="Flipkart Reviews Count", read_only=1)

	field("Item", "fk_discount_pct", "fk_reviews_count",
		  fieldtype="Percent", label="Flipkart Discount %", read_only=1)

	# --- A5: Flipkart title, in Listing Content ------------------------------
	field("Item", "fk_title", "custom_section_break_end_keepa",
		  fieldtype="Small Text", label="Flipkart Title", read_only=1,
		  description="The listing title as it appears on Flipkart.")

	# --- A5: Flipkart images, below the Amazon ones --------------------------
	# Mirrors the Amazon pattern the document points at: a gallery to look at,
	# then the URLs behind it. The child table is Amazon's - it is a plain
	# url/sequence row and a second identical doctype would only add a
	# migration to maintain.
	field("Item", "sec_fk_images", "amz_image_urls",
		  fieldtype="Section Break", label="Flipkart Images", collapsible=1)

	field("Item", "fk_image_gallery", "sec_fk_images",
		  fieldtype="HTML", label="Flipkart Images")

	field("Item", "fk_image_urls", "fk_image_gallery",
		  fieldtype="Table", label="Flipkart Image URLs",
		  options="Amazon Image URLs", read_only=1,
		  description="Reference only - Flipkart's photographs are not ours to publish.")

	# --- A5: the deep-scrape data, its own section, separate from Amazon -----
	field("Item", "sec_fk_data", "fk_image_urls",
		  fieldtype="Section Break", label="Flipkart Product Data", collapsible=1)

	field("Item", "fk_highlights", "sec_fk_data",
		  fieldtype="Small Text", label="Flipkart Highlights", read_only=1)

	field("Item", "fk_variants", "fk_highlights",
		  fieldtype="Small Text", label="Flipkart Variants", read_only=1,
		  description="Other sizes and colours Flipkart lists for this product.")

	field("Item", "cb_fk_data", "fk_variants", fieldtype="Column Break")

	field("Item", "fk_specifications", "cb_fk_data",
		  fieldtype="Long Text", label="Flipkart Specifications", read_only=1)

	field("Item", "fk_detail_sections", "fk_specifications",
		  fieldtype="Long Text", label="Flipkart Detail Tabs", read_only=1,
		  description="Showcase, Description, Warranty, Manufacturer info and the rest.")

	frappe.clear_cache(doctype="Item")
