"""Luckybee Connect - loyalty programme configuration and referral fields.

From Luckybee-Loyalty-Referral-Plan.docx. The plan's organising decision is that
purchases, content, reviews and referrals all pay out in one currency, so this
deliberately builds on ERPNext's own Loyalty Point Entry rather than a parallel
ledger: a balance split across two tables is one nobody can explain at the
counter, and native redemption reads that table.

ERPNext's collection_factor is a divisor, not a percentage - points are
`amount / factor`. So the plan's 2/3/4% become 50, 33.33 and 25. The example in
the plan checks out: a 2,000 bill at Gold earns 2000/33.333 = 60 points.
"""

import frappe

from luckybee_customization.patches.keepa_intelligence_fields import field

PROGRAM = "Luckybee Connect"

# tier name, 12-month spend threshold, earn rate as a percentage
TIERS = [
	("Silver Connect", 0, 2.0),
	("Gold Connect", 15000, 3.0),
	("Platinum Connect", 50000, 4.0),
]


def execute():
	print("Executing Patch: connect_loyalty_setup...")

	company = frappe.db.get_value("Company", {}, "name")

	if frappe.db.exists("Loyalty Program", PROGRAM):
		prog = frappe.get_doc("Loyalty Program", PROGRAM)
	else:
		prog = frappe.new_doc("Loyalty Program")
		prog.loyalty_program_name = PROGRAM
		prog.from_date = frappe.utils.today()

	prog.loyalty_program_type = "Multiple Tier Program"
	# 1 Connect Point = Rs1 of redemption value.
	prog.conversion_factor = 1
	# "Points earned in a given month are valid for 12 months from the date
	# earned." ERPNext stamps each entry's expiry from this.
	prog.expiry_duration = 12
	prog.auto_opt_in = 1
	prog.company = company
	if not prog.expense_account:
		prog.expense_account = frappe.db.get_value(
			"Account", {"company": company, "is_group": 0,
						"account_name": ["like", "%Administrative Expenses%"]}, "name")
	if not prog.cost_center:
		prog.cost_center = frappe.db.get_value(
			"Cost Center", {"company": company, "is_group": 0}, "name")

	prog.set("collection_rules", [])
	for tier_name, min_spent, pct in TIERS:
		prog.append("collection_rules", {
			"tier_name": tier_name,
			"min_spent": min_spent,
			"collection_factor": round(100.0 / pct, 6),
		})

	prog.flags.ignore_permissions = True
	prog.save() if not prog.is_new() else prog.insert(ignore_permissions=True)

	# --- referral, on the Customer ------------------------------------------
	# Our own fields rather than POS Awesome's posa_referral_code: that app is
	# being retired, its fields hold no data (0 of 1,930 customers), and the
	# referral rules here are not the ones it implements.
	field("Customer", "sec_lb_connect", "loyalty_program_tier",
		  fieldtype="Section Break", label="Luckybee Connect")

	field("Customer", "lb_referral_code", "sec_lb_connect",
		  fieldtype="Data", label="Referral Code", unique=1, read_only=1,
		  description="Share this code. The referrer earns once the new "
					  "customer's first bill crosses the threshold.")

	field("Customer", "lb_referred_by", "lb_referral_code",
		  fieldtype="Link", label="Referred By", options="Customer",
		  description="Who introduced this customer. Set once, at signup.")

	field("Customer", "cb_lb_connect", "lb_referred_by", fieldtype="Column Break")

	field("Customer", "lb_first_purchase_date", "cb_lb_connect",
		  fieldtype="Date", label="First Purchase Date", read_only=1,
		  description="Starts the 12-month window on the referrer's ongoing share.")

	field("Customer", "lb_referral_bonus_paid", "lb_first_purchase_date",
		  fieldtype="Check", label="Referral Bonus Paid", read_only=1,
		  description="The one-off joining bonus. Paid once, never again.")

	frappe.clear_cache(doctype="Customer")
	frappe.db.commit()
