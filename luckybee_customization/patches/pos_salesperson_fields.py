"""Phase 2 section 5.3 - salesperson attribution at the till.

A floor salesperson always helps the customer and the cashier bills, so the
seller is not the biller. Attribution has to be captured at the moment of sale:
section 5.3 is explicit that sales never attributed cannot be analysed
afterwards, and right now not one invoice in the system carries a salesperson.

The requirement is deliberately built on ERPNext's native Sales Person master
and its Sales Team table rather than a free-text name, because per-salesperson
grouping is the whole point and free text makes that impossible.
"""

import frappe

from luckybee_customization.patches.keepa_intelligence_fields import field


def execute():
	print("Executing Patch: pos_salesperson_fields...")

	# Section 5.3 asks for selection fast enough not to slow a busy counter.
	# A short code typed at the keypad is quicker than picking a name off a
	# list, and unlike the name it does not get longer as the team grows.
	field("Sales Person", "lb_short_code", "sales_person_name",
		  fieldtype="Data", label="Short Code", unique=1,
		  description="Typed at the till to select this salesperson quickly. "
					  "Keep it short - two or three characters.")

	# Mandatory is the requirement, but a hard block with an empty Sales Person
	# master would stop every bill on the first day. This switch lets the roster
	# be built first and enforcement turned on deliberately, per profile.
	field("POS Profile", "lb_require_salesperson", "disabled",
		  fieldtype="Check", label="Require Salesperson On Every Sale",
		  description="Blocks completing a bill until a floor salesperson is "
					  "chosen. Add your Sales Person records first, or the till "
					  "will refuse every sale.")

	frappe.clear_cache(doctype="Sales Person")
	frappe.clear_cache(doctype="POS Profile")
