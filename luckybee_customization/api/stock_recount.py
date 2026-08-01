import frappe
from frappe import _
from frappe.utils import flt, nowdate, nowtime

from erpnext.stock.utils import get_stock_balance

# Only these two warehouses are exposed to the mobile Count form - matches the
# spec exactly ("no location/rack/bin"). Do not widen this without a deliberate
# decision: this whole flow writes real stock via Stock Reconciliation.
ALLOWED_WAREHOUSES = ["Stores - SR", "Finished Goods - SR"]

RECOUNT_ROLES = {"Stock-take Staff", "Owner-Supervisor", "System Manager", "Administrator"}


def _check_recount_role():
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)
	if not (set(frappe.get_roles()) & RECOUNT_ROLES):
		frappe.throw(_("You do not have permission to recount stock."), frappe.PermissionError)


def _get_recount_eligibility(item_code):
	item = frappe.db.get_value(
		"Item",
		item_code,
		["is_stock_item", "has_serial_no", "has_batch_no", "disabled", "item_name", "stock_uom"],
		as_dict=True,
	)
	if not item:
		return {"is_eligible": False, "reason": _("Item not found.")}
	if item.disabled:
		return {"is_eligible": False, "reason": _("This item is disabled.")}
	if not item.is_stock_item:
		return {"is_eligible": False, "reason": _("This item is not a stock item.")}
	if item.has_serial_no or item.has_batch_no:
		return {
			"is_eligible": False,
			"reason": _("This item uses serial/batch tracking and cannot be recounted from the mobile form. Please use Desk."),
		}
	return {"is_eligible": True, "reason": None, "item_name": item.item_name, "stock_uom": item.stock_uom}


@frappe.whitelist(allow_guest=True)
def get_stock_recount_context(item_code):
	_check_recount_role()

	eligibility = _get_recount_eligibility(item_code)
	warehouses = []
	if eligibility["is_eligible"]:
		for warehouse in ALLOWED_WAREHOUSES:
			if not frappe.db.exists("Warehouse", warehouse):
				continue
			qty = get_stock_balance(item_code, warehouse)
			warehouses.append({"warehouse": warehouse, "current_qty": flt(qty)})

	return {
		"is_eligible": eligibility["is_eligible"],
		"reason": eligibility.get("reason"),
		"item_name": eligibility.get("item_name"),
		"stock_uom": eligibility.get("stock_uom"),
		"warehouses": warehouses,
	}


@frappe.whitelist(allow_guest=True)
def submit_stock_recount(item_code, warehouse, new_qty):
	_check_recount_role()

	if warehouse not in ALLOWED_WAREHOUSES:
		frappe.throw(_("Invalid warehouse for stock recount."))

	eligibility = _get_recount_eligibility(item_code)
	if not eligibility["is_eligible"]:
		frappe.throw(eligibility["reason"])

	# frappe.utils.flt() never raises - it silently returns 0.0 for unparseable input, which
	# would make garbage input indistinguishable from a deliberate "set stock to 0". Validate
	# with float() first, which does raise, before handing off to flt() for the real value.
	if new_qty is None or new_qty == "":
		frappe.throw(_("Invalid quantity."))
	try:
		float(new_qty)
	except (TypeError, ValueError):
		frappe.throw(_("Invalid quantity."))
	new_qty = flt(new_qty)
	if new_qty < 0:
		frappe.throw(_("Quantity cannot be negative."))

	current_qty = flt(get_stock_balance(item_code, warehouse))

	if abs(new_qty - current_qty) < 0.0001:
		return {"status": "no_change", "current_qty": current_qty}

	company = frappe.db.get_value("Warehouse", warehouse, "company") or frappe.defaults.get_global_default("company")

	# Stock-take Staff is granted a narrow Custom DocPerm on Stock Reconciliation
	# (read/write/create/submit only, no cancel/amend/delete - see
	# count_webform.py) specifically so this runs as the real session user.
	#
	# An earlier version of this function instead ran as Administrator via
	# frappe.set_user() (Stock-take Staff had zero Stock Reconciliation permission,
	# by design) to get past a frappe.has_permission("Stock Reconciliation", "write",
	# throw=True) check buried inside ERPNext's get_stock_balance_for(). That was
	# unsafe: frappe.set_user() overwrites frappe.local.session.sid (the actual
	# session/cookie token) with the username string, not just .user, and restoring
	# only .user afterward - or even .user and .sid - still left the real browser
	# session corrupted, logging the calling user out after the very next request.
	# Reproduced live twice (including after attempting to restore .sid). Granting
	# real permission for this one doctype avoids needing any impersonation at all.
	try:
		sr = frappe.new_doc("Stock Reconciliation")
		sr.purpose = "Stock Reconciliation"
		sr.company = company
		sr.posting_date = nowdate()
		sr.posting_time = nowtime()
		sr.append("items", {
			"item_code": item_code,
			"warehouse": warehouse,
			"qty": new_qty,
		})
		sr.insert()
		sr.submit()
	except frappe.ValidationError:
		raise
	except Exception as e:
		frappe.log_error(f"Stock recount failed for {item_code} in {warehouse}: {e}")
		frappe.throw(_("Could not update stock. Nothing was changed - please try again or contact your supervisor."))

	return {
		"status": "success",
		"stock_reconciliation": sr.name,
		"previous_qty": current_qty,
		"new_qty": new_qty,
	}
