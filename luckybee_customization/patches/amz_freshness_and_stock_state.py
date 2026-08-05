import frappe

from luckybee_customization.patches.keepa_intelligence_fields import field

# B3/B4 - the sync date existed but was buried, and amz_data_status could not
# tell "we tried and Amazon had no offer" apart from "we never had a match".

# B4's requested set. "Refresh Failed" and "Out of Stock / Discontinued" are the
# new cases; the three existing values are kept so no stored value is orphaned.
# "No Amazon Match" keeps its existing wording rather than the doc's shorthand
# "No Match", again to avoid rewriting rows that already hold it.
DATA_STATUS_OPTIONS = "\n".join([
	"Not Fetched",
	"Matched",
	"Stale",
	"Refresh Failed",
	"Out of Stock / Discontinued",
	"No Amazon Match",
])

# B1 extended the price fallback chain to the 90 and 180 day averages. The
# options list lives in keepa_intelligence_fields.py, but that patch had already
# run, so the live field still rejected the two new sources and every item that
# fell through to them failed to save. Re-assert the full list here.
BEST_PRICE_SOURCE_OPTIONS = "\n".join([
	"",
	"Buy Box: Current",
	"New: Current",
	"Buy Box: 30 days avg.",
	"New: 30 days avg.",
	"New: 90 days avg.",
	"New: 180 days avg.",
	"List Price: Current",
])


def execute():
	print("Executing Patch: amz_freshness_and_stock_state...")

	# B3 - "tried to sync" vs "last actually got real data". The gap between the
	# two is what tells us recent syncs are silently failing.
	field("Item", "amz_last_successful_sync", "amz_last_synced",
		  fieldtype="Date", label="AMZ Last Successful Sync", read_only=1)

	# B4 - Keepa's own out-of-stock percentage. Near 100 means the product is
	# effectively gone, which is a far cleaner discontinued signal than counting
	# repeated -1s.
	field("Item", "amz_oos_percent", "amz_last_successful_sync",
		  fieldtype="Percent", label="AMZ Out of Stock %", read_only=1)

	existing = frappe.db.get_value(
		"Custom Field", {"dt": "Item", "fieldname": "amz_data_status"}, "options")
	if existing != DATA_STATUS_OPTIONS:
		field("Item", "amz_data_status", "amz_last_synced",
			  fieldtype="Select", label="Amazon Data Status",
			  options=DATA_STATUS_OPTIONS)

	existing_source = frappe.db.get_value(
		"Custom Field", {"dt": "Item", "fieldname": "amz_best_price_source"}, "options")
	if existing_source != BEST_PRICE_SOURCE_OPTIONS:
		field("Item", "amz_best_price_source", "column_break_amz_benchmark_current",
			  fieldtype="Select", label="AMZ Best Price Source",
			  options=BEST_PRICE_SOURCE_OPTIONS)

	frappe.clear_cache(doctype="Item")
