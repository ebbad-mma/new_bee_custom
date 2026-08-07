import frappe


def get_context(context):
	"""Price check page - open to customers, richer for signed-in staff.

	Guests are served by `lookup_product_public`, which never returns stock. A
	signed-in member of staff additionally gets stock in hand, fetched by a
	second call to the ordinary staff endpoint. The split is decided here only
	for what the page renders; the security boundary is in the API itself, so a
	guest hitting the staff endpoint directly is still refused.
	"""
	context.title = "Price Check"
	context.no_cache = 1
	context.is_staff = (
		frappe.session.user != "Guest"
		and frappe.has_permission("Item", "read")
	)
	return context
