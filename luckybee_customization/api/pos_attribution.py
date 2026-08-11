"""Phase 2 section 5 - salesperson attribution and the customer summary panel.

Deliberately POS-agnostic. POS Next's version-16 branch is 463 commits behind
its version-15 branch and was built against a beta of v16, so which till this
eventually runs on is an open question. Everything here talks to native ERPNext
records - the Sales Person master and the Sales Team child table - so it holds
whether the front end ends up being POS Next, POS Awesome or the stock POS.
"""

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def list_salespersons(pos_profile=None):
	"""The floor team, for the clickable name boxes section 5.3 asks for.

	Group nodes are excluded: "Sales Team" and its like are tree scaffolding,
	not people who sell things.
	"""
	rows = frappe.get_all(
		"Sales Person",
		filters={"enabled": 1, "is_group": 0},
		fields=["name", "sales_person_name", "lb_short_code"],
		order_by="sales_person_name",
	)
	return [
		{
			"name": r.name,
			"label": r.sales_person_name or r.name,
			"short_code": r.get("lb_short_code") or "",
		}
		for r in rows
	]


@frappe.whitelist()
def resolve_salesperson(code):
	"""Short code -> Sales Person, for keypad entry at the till.

	Falls back to the record name so a cashier who types the full name is not
	told they are wrong.
	"""
	code = (code or "").strip()
	if not code:
		return None

	name = frappe.db.get_value("Sales Person",
							   {"lb_short_code": code, "enabled": 1, "is_group": 0},
							   ["name", "sales_person_name"], as_dict=True)
	if not name:
		name = frappe.db.get_value("Sales Person",
								   {"name": code, "enabled": 1, "is_group": 0},
								   ["name", "sales_person_name"], as_dict=True)
	if not name:
		return None
	return {"name": name.name, "label": name.sales_person_name or name.name}


def require_salesperson(doc, method=None):
	"""Section 5.3 - a POS bill cannot complete without a seller recorded.

	Hooked on validate rather than on_submit so the cashier is stopped while the
	bill is still open and fixable, not at the moment they try to take payment.

	Enforcement is per POS Profile and off by default. The Sales Person master
	currently holds one group node and no people, so switching this on globally
	would refuse every sale at the counter - the roster has to exist first.
	"""
	if not doc.get("is_pos"):
		return
	if not doc.get("pos_profile"):
		return
	if not frappe.db.get_value("POS Profile", doc.pos_profile, "lb_require_salesperson"):
		return

	has_seller = any(
		row.get("sales_person") for row in (doc.get("sales_team") or [])
	)
	if not has_seller:
		frappe.throw(
			_("Choose the floor salesperson who made this sale before completing the bill."),
			title=_("Salesperson required"),
		)


@frappe.whitelist()
def customer_purchase_summary(customer, limit=8):
	"""Section 5.2 - the compact history panel shown when a customer is identified.

	Date and amount only, most recent first, with the invoice name so the till
	can open the bill when an amount is clicked. Kept brief on purpose: the spec
	calls for a quick reference at the counter, not a report.
	"""
	if not customer:
		return {"customer": None, "invoices": []}

	if not frappe.has_permission("Sales Invoice", "read"):
		frappe.throw(_("Not permitted to view sales history."), frappe.PermissionError)

	rows = frappe.get_all(
		"Sales Invoice",
		filters={"customer": customer, "docstatus": 1},
		fields=["name", "posting_date", "grand_total", "status"],
		order_by="posting_date desc, creation desc",
		limit=int(limit),
	)

	total_spent = frappe.db.sql(
		"""SELECT SUM(grand_total) FROM `tabSales Invoice`
		   WHERE customer=%s AND docstatus=1""", (customer,))[0][0]

	return {
		"customer": customer,
		"customer_name": frappe.db.get_value("Customer", customer, "customer_name"),
		"invoices": [
			{
				"invoice": r.name,
				"date": r.posting_date,
				"amount": flt(r.grand_total),
				"status": r.status,
			}
			for r in rows
		],
		"lifetime_value": flt(total_spent),
		"visit_count": frappe.db.count("Sales Invoice",
									   {"customer": customer, "docstatus": 1}),
	}


@frappe.whitelist()
def attribution_coverage():
	"""How much of the sales history carries a salesperson.

	Reported rather than assumed: section 5.3's warning is that unattributed
	sales cannot be analysed later, so it is worth being able to see the gap
	closing once enforcement is switched on.
	"""
	total = frappe.db.count("Sales Invoice", {"docstatus": 1, "is_pos": 1})
	attributed = frappe.db.sql(
		"""SELECT COUNT(DISTINCT st.parent) FROM `tabSales Team` st
		   JOIN `tabSales Invoice` si ON si.name = st.parent
		   WHERE st.parenttype='Sales Invoice' AND si.docstatus=1
			 AND si.is_pos=1 AND IFNULL(st.sales_person,'') <> ''""")[0][0]
	return {
		"pos_invoices": total,
		"attributed": attributed,
		"unattributed": total - attributed,
		"coverage_pct": round(100.0 * attributed / total, 2) if total else 0.0,
		"salespersons_configured": frappe.db.count(
			"Sales Person", {"enabled": 1, "is_group": 0}),
	}
