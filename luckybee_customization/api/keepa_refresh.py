"""B7 - on-demand "Refresh Amazon Data" for a single Item.

Re-pulls Keepa for this item's ASIN, updates both the Item and its Item Details
row, refreshes amz_best_price and stamps the sync date - the same path the
nightly sync uses, so there is exactly one implementation of the Keepa mapping
to keep correct.
"""

import frappe
from frappe import _

REFRESH_ROLES = {
	"Owner-Supervisor",
	"Item Manager",
	"Stock Manager",
	"System Manager",
	"Administrator",
}


@frappe.whitelist()
def refresh_amazon_data(item_code):
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	if not (set(frappe.get_roles()) & REFRESH_ROLES):
		frappe.throw(_("You do not have permission to refresh Amazon data."), frappe.PermissionError)

	# A Keepa pull costs tokens and rewrites pricing fields, so require write
	# access to this specific document, not merely one of the roles above.
	if not frappe.has_permission("Item", "write", doc=item_code):
		frappe.throw(_("You do not have permission to edit this item."), frappe.PermissionError)

	doc = frappe.get_doc("Item", item_code)

	if not doc.get("custom_asin_no"):
		return {"status": "skipped", "message": _("This item has no ASIN to look up.")}

	if not frappe.conf.get("keepa_api_key"):
		return {"status": "error", "message": _("Keepa API key is not configured.")}

	# sync_keepa_item runs on before_save, so a plain save re-pulls and writes
	# both doctypes inside its existing savepoint (B6). Doing it this way means
	# the button cannot drift from the nightly behaviour.
	try:
		doc.save()
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(
			title=f"Manual Amazon refresh failed for {item_code}",
			message=f"{e}\n\n{frappe.get_traceback()}",
		)
		return {"status": "error", "message": _("Amazon data could not be refreshed. Nothing was changed.")}

	doc.reload()
	return {
		"status": "ok",
		"amz_data_status": doc.get("amz_data_status"),
		"amz_best_price": doc.get("amz_best_price"),
		"amz_last_synced": doc.get("amz_last_synced"),
		"amz_last_successful_sync": doc.get("amz_last_successful_sync"),
	}
