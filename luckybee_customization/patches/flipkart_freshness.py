"""Changes.docx A5 - Flipkart price freshness, mirroring the Amazon handling.

A last-synced date on its own only tells you when we last asked. Amazon carries
a status alongside it - Matched, Stale, Refresh Failed - so a figure that can no
longer be trusted says so rather than leaving the reader to work out what a date
three weeks old implies. The document asks for the same on Flipkart, and part B
leans on it: a stale competitor price must not quietly drive a pricing verdict.
"""

import frappe

from luckybee_customization.patches.keepa_intelligence_fields import field

FK_STATUS_OPTIONS = "\n".join([
	"Not Fetched",
	"Matched",
	"Stale",
	"Refresh Failed",
])


def execute():
	print("Executing Patch: flipkart_freshness...")

	field("Item", "fk_data_status", "fk_last_synced",
		  fieldtype="Select", label="Flipkart Data Status",
		  options=FK_STATUS_OPTIONS, default="Not Fetched", read_only=1,
		  description="Stale means the price is older than the freshness window "
					  "and should not be trusted for a pricing decision.")

	# Anything already carrying a price has been fetched at least once; the daily
	# sweep will age it into Stale from there. Without this every existing item
	# would sit at "Not Fetched" while plainly holding Flipkart data.
	frappe.db.sql("""
		UPDATE `tabItem`
		SET fk_data_status = 'Matched'
		WHERE IFNULL(fk_data_status,'') IN ('', 'Not Fetched')
		  AND IFNULL(fk_price, 0) <> 0
	""")
	frappe.db.commit()
	frappe.clear_cache(doctype="Item")
