"""UPI payment QR for the till.

ERPNext's POS collects the payment but has nothing to show the customer to pay
against - the QR already on our invoices is the GST e-invoice one, which is a
tax artefact and not payable. This builds a proper UPI intent QR for the amount
due, so the customer scans and pays from any UPI app.

The payee details come from the POS Profile and never from the caller. That is
deliberate: if the client could pass a VPA, anyone who can open the till page
could point the QR at their own account and collect the shop's takings.
"""

import io
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import flt


def _upi_link(vpa, payee, amount, reference=None):
	"""A UPI intent URL - the string every UPI app understands.

	Amount is fixed into the QR rather than left for the customer to type: a
	blank-amount QR is how you end up with someone paying 100 for a 1,000 bill
	and nobody noticing until the drawer is counted.
	"""
	params = [
		f"pa={quote(vpa, safe='')}",
		f"pn={quote(payee, safe='')}",
		f"am={flt(amount, 2):.2f}",
		"cu=INR",
	]
	if reference:
		# Shows up in the shop's UPI statement, so a payment can be traced back
		# to the bill it settled.
		params.append(f"tn={quote(str(reference)[:50], safe='')}")
	return "upi://pay?" + "&".join(params)


def _qr_svg(data, scale=5):
	import pyqrcode

	buffer = io.BytesIO()
	# Error correction M: still scannable with a thumb over a corner of the
	# screen, without making the code so dense it needs a steady hand.
	pyqrcode.create(data, error="M").svg(
		buffer,
		scale=scale,
		background="#ffffff",
		module_color="#000000",
		quiet_zone=2,
		xmldecl=False,
		svgns=True,
		title=None,
	)
	return buffer.getvalue().decode("utf-8")


@frappe.whitelist()
def get_upi_qr(pos_profile, amount, reference=None):
	"""QR + link for the amount due at the till."""
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Nothing to collect - the amount due is zero."))

	profile = frappe.db.get_value(
		"POS Profile", pos_profile, ["name", "lb_upi_id", "lb_upi_payee_name"], as_dict=True
	)
	if not profile:
		frappe.throw(_("POS Profile {0} not found.").format(pos_profile))

	vpa = (profile.lb_upi_id or "").strip()
	if not vpa:
		frappe.throw(
			_("No UPI ID is set on POS Profile {0}. Add it under UPI Payment.").format(profile.name)
		)

	payee = (profile.lb_upi_payee_name or "").strip() or profile.name
	link = _upi_link(vpa, payee, amount, reference)

	return {
		"link": link,
		"svg": _qr_svg(link),
		"vpa": vpa,
		"payee": payee,
		"amount": amount,
		"amount_formatted": frappe.utils.fmt_money(amount, currency="INR"),
	}
