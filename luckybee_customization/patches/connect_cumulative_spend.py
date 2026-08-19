"""A visible cumulative-spend figure on the Customer.

The referral now qualifies on cumulative spend crossing Rs3,000 rather than on
one bill reaching it, so the running total is something staff and the customer
will ask about ("how far off am I?"). It is written on every sale rather than
computed on demand so it can be listed, filtered and reported on.

The stored value is a mirror, never the source of truth - qualification is
decided from the invoices themselves, so a cancelled or amended bill cannot
leave a customer permanently qualified on a total that no longer exists.
"""

import frappe

from luckybee_customization.patches.keepa_intelligence_fields import field


def execute():
	print("Executing Patch: connect_cumulative_spend...")

	field("Customer", "lb_referral_spend", "lb_first_purchase_date",
		  fieldtype="Currency", label="Spend Toward Referral", read_only=1,
		  description="Cumulative spend inside the 12-month window from the "
					  "first purchase. The referral qualifies when this crosses "
					  "the threshold.")

	frappe.clear_cache(doctype="Customer")
