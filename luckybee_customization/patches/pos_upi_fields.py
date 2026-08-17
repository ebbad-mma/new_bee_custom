"""UPI payee details on the POS Profile.

Kept on the profile rather than in site config so a second till or company can
have its own payee later without a code change - and so the value is editable by
someone with POS Manager access instead of needing a deployment.
"""

import frappe

from luckybee_customization.patches.keepa_intelligence_fields import field

# Supplied by the owner for the Lucky Bee till. Only ever used to seed a profile
# that has no UPI ID yet - never to overwrite one someone has set.
DEFAULT_VPA = "Q155392155@ybl"
DEFAULT_PAYEE = "LuckyBee"


def execute():
	print("Executing Patch: pos_upi_fields...")

	field("POS Profile", "sec_lb_upi", "disable_rounded_total",
	      fieldtype="Section Break", label="UPI Payment")

	field("POS Profile", "lb_upi_id", "sec_lb_upi",
	      fieldtype="Data", label="UPI ID",
	      description="The shop's UPI ID (e.g. name@bank). The payment QR at the "
	                  "till is generated from this - never from the browser.")

	field("POS Profile", "lb_upi_payee_name", "lb_upi_id",
	      fieldtype="Data", label="UPI Payee Name",
	      description="The name the customer sees in their UPI app when they scan.")

	for name in frappe.get_all("POS Profile", pluck="name"):
		current = frappe.db.get_value("POS Profile", name, "lb_upi_id")
		if not current:
			frappe.db.set_value("POS Profile", name, {
				"lb_upi_id": DEFAULT_VPA,
				"lb_upi_payee_name": DEFAULT_PAYEE,
			})
			print(f"  seeded UPI details on POS Profile {name}")

	frappe.clear_cache(doctype="POS Profile")
	frappe.db.commit()
	print("Patch pos_upi_fields completed successfully.")
