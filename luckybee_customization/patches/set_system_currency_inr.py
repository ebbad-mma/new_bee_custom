"""A6 - make the INR fix actually reach production.

The MRP field rendered as "USD 1,020.00" because the portal builds
sysdefaults.currency from System Settings.currency (frappe/website/utils.py),
which had never been set, so the client-side formatter fell through to its
hardcoded "USD". Global Defaults already said INR, but that is not what the
portal reads.

Setting it by hand fixes one site only - it is a settings value, so a code
deploy does not carry it. Confirmed against the restored production database:
System Settings.currency was still empty there even after the deploy, meaning
staff were still seeing USD on the mobile forms. Doing it as a patch is what
makes the fix travel.
"""

import frappe


def execute():
	print("Executing Patch: set_system_currency_inr...")

	current = frappe.db.get_single_value("System Settings", "currency")
	if current:
		print(f"  System Settings.currency already set to {current} - leaving alone")
		return

	# Prefer whatever Global Defaults already says, so this cannot quietly
	# switch the currency on a site that legitimately uses something else.
	target = frappe.db.get_single_value("Global Defaults", "default_currency") or "INR"
	if not frappe.db.exists("Currency", target):
		print(f"  Currency {target} not found - skipping")
		return

	settings = frappe.get_single("System Settings")
	settings.currency = target
	settings.save(ignore_permissions=True)
	frappe.db.commit()
	frappe.clear_cache()
	print(f"  System Settings.currency set to {target}")
