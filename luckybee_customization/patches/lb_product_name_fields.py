"""The name fields from the Product Names spec.

An item needs several names because a label, a web page and a URL each want
something different, and none of them can be the purchase-invoice line name we
currently hold in item_name - that is an internal record, not publishable.

  lb_short_name     ~40 chars, for the barcode label
  lb_website_title  the customer-facing SEO title
  lb_url_slug       the web address - PERMANENT once the product is published
  lb_search_terms   marketplace-style phrasing, indexed but never displayed

Short Name, Website Title and Slug are left empty here: the spec has them
drafted by the AI enrichment pipeline and approved by a person before publishing,
and that pipeline is a separate piece of work. The sync uses them the moment they
appear and falls back to item_name until then, so nothing waits on the AI.

lb_search_terms IS backfilled, because it needs no AI at all - the spec says it
holds the marketplace phrasing we already pull from Keepa, and we have an Amazon
title on 7,975 items. That phrasing must live ONLY here: using it as the visible
product title would be duplicate content and their copyrighted sentence, which is
the whole point of section 1.3.
"""

import frappe

FIELDS = [
	{
		"fieldname": "lb_short_name",
		"label": "Short Name",
		"fieldtype": "Data",
		"length": 40,
		"insert_after": "item_name",
		"description": "Tight, staff-readable, ~30-40 characters. Prints on the barcode label.",
	},
	{
		"fieldname": "lb_website_title",
		"label": "Website Title",
		"fieldtype": "Small Text",
		"insert_after": "lb_short_name",
		"description": "Customer-facing SEO title, built from brand, model, type and specs. "
					   "Must be our own wording - never Amazon's or Flipkart's title string.",
	},
	{
		"fieldname": "lb_url_slug",
		"label": "URL Slug",
		# Small Text, not Data, purely for storage reasons: Item carries 236
		# custom fields and its varchar columns already use 64,400 of MySQL's
		# 65,535-byte row limit, so another varchar cannot be added. TEXT costs
		# only a pointer in-row. Any new field on Item now has to be text-typed.
		"fieldtype": "Small Text",
		"insert_after": "lb_website_title",
		"description": "Web address, lowercase and hyphenated. PERMANENT once published - "
					   "changing it breaks existing links and loses search ranking.",
	},
	{
		"fieldname": "lb_search_terms",
		"label": "Search / Reference Terms",
		"fieldtype": "Small Text",  # see the note on lb_url_slug
		"insert_after": "lb_url_slug",
		"description": "Marketplace-style phrasing so exact-title searchers find us. "
					   "Indexed by the website, never shown as the product name.",
	},
]


def execute():
	print("Executing Patch: lb_product_name_fields...")

	created = []
	for spec in FIELDS:
		if frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": spec["fieldname"]}):
			continue
		doc = {"doctype": "Custom Field", "dt": "Item",
			   "module": "luckybee_customization", **spec}
		frappe.get_doc(doc).insert(ignore_permissions=True)
		created.append(spec["fieldname"])
	print(f"  fields created: {created or 'none (already present)'}")

	# Backfill the search terms from the marketplace phrasing we already hold.
	# Bulk UPDATE, not save() - Item's before_save chain calls sync_keepa_item.
	frappe.db.sql(
		"""
		UPDATE `tabItem`
		SET lb_search_terms = TRIM(CONCAT_WS(' ', IFNULL(title, ''),
											 IFNULL(amz_search_keywords, '')))
		WHERE IFNULL(lb_search_terms, '') = ''
		  AND (IFNULL(title, '') != '' OR IFNULL(amz_search_keywords, '') != '')
		"""
	)
	frappe.db.commit()
	frappe.clear_cache(doctype="Item")
	filled = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabItem` WHERE IFNULL(lb_search_terms,'') != ''"""
	)[0][0]
	print(f"  search terms backfilled on {filled} items")
