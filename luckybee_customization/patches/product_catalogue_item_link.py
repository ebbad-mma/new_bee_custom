"""Phase 2 section 2.2 - let an Item record which catalogue its data came from.

Two fields, deliberately named with the pb_ prefix the spec uses for the
Product Builder block (section 3), because that is where they belong once that
work lands - the catalogue link is one of its sources. Creating them here means
the catalogue repository is usable on its own without waiting for the builder.
"""

import frappe

from luckybee_customization.patches.keepa_intelligence_fields import field


def execute():
	print("Executing Patch: product_catalogue_item_link...")

	# Sits with the other sourcing/classification information rather than in
	# the pricing or Amazon blocks - this describes where the data came from.
	field("Item", "sec_product_source", "lb_sub_category",
		  fieldtype="Section Break", label="Product Source", collapsible=1)

	field("Item", "pb_linked_catalogue", "sec_product_source",
		  fieldtype="Link", options="Product Catalogue",
		  label="Source Catalogue")

	field("Item", "pb_catalogue_page_ref", "pb_linked_catalogue",
		  fieldtype="Data", label="Catalogue Page / SKU Ref",
		  description="Where in the catalogue this came from, e.g. \"Page 14, SKU X\".")

	frappe.clear_cache(doctype="Item")
