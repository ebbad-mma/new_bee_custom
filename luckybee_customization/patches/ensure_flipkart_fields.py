
import frappe

from luckybee_customization.patches.keepa_intelligence_fields import field


def execute():
	print("Executing Patch: ensure_flipkart_fields...")

	field("Item", "custom_fsn_no", "ean",
		  fieldtype="Data", label="FSN No",
		  description="Flipkart's product code. Taken from the pid= parameter "
					  "when a full Flipkart URL is pasted above.")

	field("Item", "custom_url", "custom_column_break_n2l3q",
		  fieldtype="Small Text", label="Flipkart URL",
		  description="Paste the full Flipkart product URL - the FSN is read "
					  "from the pid= parameter, not from lid=.")

	frappe.clear_cache(doctype="Item")
