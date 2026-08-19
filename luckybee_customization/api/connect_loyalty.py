"""Luckybee Connect - points beyond purchases, and referral payouts.

From Luckybee-Loyalty-Referral-Plan.docx.

Everything writes to ERPNext's Loyalty Point Entry. The plan is explicit that
purchases, content, reviews and referrals share one currency, so they share one
ledger: a balance split across two tables cannot be explained at the counter,
and native redemption only reads that one.

Purchases are handled by ERPNext itself from the programme's collection rules.
This module covers what ERPNext has no concept of - social posts, reviews, and
referrals - plus the caps that stop those being farmed.
"""

import frappe
from frappe import _
from frappe.utils import add_months, add_days, flt, getdate, today

PROGRAM = "Luckybee Connect"

# --- Part 2: social and review ------------------------------------------
ACTIVITY_POINTS = {
	"Instagram Post": 200,
	"Instagram Reel": 500,
	"Google Review": 100,
}

# Per-type monthly limits, so one channel cannot be spammed.
ACTIVITY_MONTHLY_CAP = {
	"Instagram Post": 2,
	"Instagram Reel": 2,
	"Google Review": 1,
}

# Reel reach bonus - views within 7 days of posting.
REEL_REACH_BONUS = [
	(50000, 1500),
	(20000, 800),
	(5000, 300),
]

# "Combined monthly cap: max 1,000 points/month from social + review actions per
# customer, so the mechanic can't be farmed with low-effort spam content."
SOCIAL_MONTHLY_POINT_CAP = 1000

# --- Part 3: referral -----------------------------------------------------
REFERRAL_JOINING_POINTS = 150
REFERRAL_MIN_FIRST_BILL = 3000
REFERRAL_ONGOING_PCT = 1.0
REFERRAL_ONGOING_MONTHS = 12


def _program():
	return PROGRAM if frappe.db.exists("Loyalty Program", PROGRAM) else None


def award_points(customer, points, reason, source_type="Sales Invoice",
				 source_name=None, purchase_amount=0):
	"""Write points into the shared ledger.

	purchase_amount stays 0 for everything here. It is what ERPNext totals to
	decide a customer's tier, and a referral bonus or an Instagram post is not
	spend - counting it would promote people up the tiers for posting photos.

	invoice_type is mandatory on the ledger but is a plain Link to DocType, so
	each row points at whatever actually caused it - the activity record for a
	post, the invoice for a referral. Stamping "Sales Invoice" on an Instagram
	post to satisfy the field would make the ledger unauditable.
	"""
	points = int(round(flt(points)))
	if points <= 0:
		return None

	program = _program()
	if not program:
		frappe.throw(_("The {0} loyalty programme is not set up.").format(PROGRAM))

	entry = frappe.new_doc("Loyalty Point Entry")
	entry.loyalty_program = program
	entry.customer = customer
	entry.loyalty_points = points
	entry.purchase_amount = purchase_amount
	entry.posting_date = today()
	# Mirrors the purchase rule: valid 12 months from the date earned.
	entry.expiry_date = add_days(add_months(today(), 12), -1)
	entry.company = frappe.db.get_value("Loyalty Program", program, "company")
	entry.discretionary_reason = reason
	entry.invoice_type = source_type
	if source_name:
		entry.invoice = source_name
	entry.flags.ignore_permissions = True
	entry.insert(ignore_permissions=True)
	return entry.name


def _month_bounds(on=None):
	d = getdate(on or today())
	start = d.replace(day=1)
	return start, add_days(add_months(start, 1), -1)


def social_points_this_month(customer, on=None):
	"""Points already earned this month from social and review activity."""
	start, end = _month_bounds(on)
	total = frappe.db.sql(
		"""SELECT COALESCE(SUM(points_awarded), 0) FROM `tabLB Connect Activity`
		   WHERE customer = %s AND docstatus < 2 AND status = 'Approved'
			 AND activity_date BETWEEN %s AND %s""",
		(customer, start, end))[0][0]
	return int(total or 0)


def activity_count_this_month(customer, activity_type, on=None, exclude=None):
	start, end = _month_bounds(on)
	conditions = ["customer = %s", "activity_type = %s", "docstatus < 2",
				  "status = 'Approved'", "activity_date BETWEEN %s AND %s"]
	params = [customer, activity_type, start, end]
	if exclude:
		conditions.append("name != %s")
		params.append(exclude)
	return frappe.db.sql(
		f"SELECT COUNT(*) FROM `tabLB Connect Activity` WHERE {' AND '.join(conditions)}",
		params)[0][0]


def reel_reach_bonus(views):
	"""The first threshold the view count clears, highest first."""
	views = int(flt(views))
	for threshold, bonus in REEL_REACH_BONUS:
		if views >= threshold:
			return bonus
	return 0


@frappe.whitelist()
def preview_activity_points(customer, activity_type, reel_views=0, activity_date=None,
							exclude=None):
	"""What this activity would pay, and why - shown before anyone approves it.

	Reported rather than silently trimmed: a staff member approving a reel needs
	to see that the customer has already hit the monthly ceiling, otherwise the
	award looks arbitrary.
	"""
	base = ACTIVITY_POINTS.get(activity_type, 0)
	bonus = reel_reach_bonus(reel_views) if activity_type == "Instagram Reel" else 0
	gross = base + bonus

	notes = []
	per_type_cap = ACTIVITY_MONTHLY_CAP.get(activity_type)
	used = activity_count_this_month(customer, activity_type, activity_date, exclude)
	if per_type_cap is not None and used >= per_type_cap:
		return {"points": 0, "gross": gross, "base": base, "reach_bonus": bonus,
				"blocked": True,
				"notes": [_("Already at the monthly limit of {0} for {1}.").format(
					per_type_cap, activity_type)]}

	already = social_points_this_month(customer, activity_date)
	room = max(SOCIAL_MONTHLY_POINT_CAP - already, 0)
	net = min(gross, room)
	if net < gross:
		notes.append(_("Trimmed to the {0}-point monthly cap ({1} already earned).").format(
			SOCIAL_MONTHLY_POINT_CAP, already))
	if bonus:
		notes.append(_("Includes a {0}-point reach bonus.").format(bonus))

	return {"points": net, "gross": gross, "base": base, "reach_bonus": bonus,
			"blocked": net <= 0, "notes": notes,
			"used_this_month": already, "cap": SOCIAL_MONTHLY_POINT_CAP}


# ---------------------------------------------------------------------------
# Part 3 - referral
# ---------------------------------------------------------------------------

def _bill_value(doc):
	"""What the customer actually spent, ignoring points they redeemed.

	Redeemed points are store credit, not new spend. Paying a referrer 1% of a
	bill settled with the referrer's own points would let the pair recycle the
	same balance between them.
	"""
	return flt(doc.grand_total) - flt(doc.get("loyalty_amount") or 0)


def handle_referral(doc, method=None):
	"""On a submitted sale, pay whatever the referrer is owed.

	Two separate things, per the plan: a one-off joining bonus once the new
	customer's first bill clears the bar, and 1% of their spend for the twelve
	months after that first purchase.
	"""
	if doc.get("is_return") or not doc.get("customer"):
		return

	customer = frappe.db.get_value(
		"Customer", doc.customer,
		["name", "lb_referred_by", "lb_first_purchase_date", "lb_referral_bonus_paid"],
		as_dict=True)
	if not customer:
		return

	amount = _bill_value(doc)

	# Stamp the first purchase date whether or not there is a referrer - it is
	# the customer's own history, and it starts the referral window.
	if not customer.lb_first_purchase_date and amount > 0:
		frappe.db.set_value("Customer", doc.customer, "lb_first_purchase_date",
							doc.posting_date, update_modified=False)
		customer.lb_first_purchase_date = doc.posting_date

	referrer = customer.lb_referred_by
	if not referrer or referrer == doc.customer:
		return

	# --- the one-off joining bonus ---------------------------------------
	if not customer.lb_referral_bonus_paid and amount >= REFERRAL_MIN_FIRST_BILL:
		award_points(
			referrer, REFERRAL_JOINING_POINTS,
			_("Referral bonus - {0}'s first purchase").format(doc.customer),
			source_type="Sales Invoice", source_name=doc.name)
		frappe.db.set_value("Customer", doc.customer, "lb_referral_bonus_paid", 1,
							update_modified=False)

	# --- the ongoing share, for 12 months from their first purchase -------
	# Measured from the first purchase rather than from the referral being
	# registered: the plan ties the window to when the customer started buying.
	#
	# Only once the referral has actually qualified. The plan gates the joining
	# bonus behind a Rs3,000 first bill because that "filters for real,
	# meaningful first purchases rather than token ones" - and paying the
	# ongoing 1% on purchases made before that bar is cleared would let a
	# referrer earn indefinitely from someone who never made a real purchase,
	# which is the outcome the bar exists to prevent.
	qualified = frappe.db.get_value("Customer", doc.customer, "lb_referral_bonus_paid")
	if qualified and customer.lb_first_purchase_date:
		window_ends = add_months(getdate(customer.lb_first_purchase_date),
								 REFERRAL_ONGOING_MONTHS)
		if getdate(doc.posting_date) <= window_ends:
			share = amount * REFERRAL_ONGOING_PCT / 100.0
			if share >= 1:
				award_points(
					referrer, share,
					_("Referral share - {0}% of {1}'s purchase {2}").format(
						REFERRAL_ONGOING_PCT, doc.customer, doc.name),
					source_type="Sales Invoice", source_name=doc.name)


@frappe.whitelist()
def generate_referral_code(customer):
	"""A short, unique code the customer can read out or type into WhatsApp."""
	import re

	existing = frappe.db.get_value("Customer", customer, "lb_referral_code")
	if existing:
		return existing

	base = re.sub(r"[^A-Za-z0-9]", "", (customer or "").upper())[:6] or "LBEE"
	for attempt in range(50):
		suffix = frappe.utils.random_string(4).upper()
		code = f"{base}{suffix}"[:12]
		if not frappe.db.exists("Customer", {"lb_referral_code": code}):
			frappe.db.set_value("Customer", customer, "lb_referral_code", code,
								update_modified=False)
			return code
	frappe.throw(_("Could not generate a unique referral code."))


@frappe.whitelist()
def connect_summary(customer):
	"""Balance, tier and referral standing - what the Care number reads out."""
	from erpnext.accounts.doctype.loyalty_program.loyalty_program import (
		get_loyalty_program_details_with_points,
	)

	program = _program()
	details = {}
	if program:
		try:
			details = get_loyalty_program_details_with_points(
				customer, loyalty_program=program, silent=True) or {}
		except Exception:
			details = {}

	referred = frappe.get_all("Customer", filters={"lb_referred_by": customer},
							  fields=["name", "lb_referral_bonus_paid"])
	return {
		"customer": customer,
		"tier": details.get("tier_name"),
		"points_balance": int(flt(details.get("loyalty_points"))),
		"rupee_value": flt(details.get("loyalty_points")) * flt(
			details.get("conversion_factor") or 1),
		"referral_code": frappe.db.get_value("Customer", customer, "lb_referral_code"),
		"people_referred": len(referred),
		"referrals_converted": sum(1 for r in referred if r.lb_referral_bonus_paid),
		"social_points_this_month": social_points_this_month(customer),
		"social_monthly_cap": SOCIAL_MONTHLY_POINT_CAP,
	}
