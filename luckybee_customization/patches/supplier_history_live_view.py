import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from luckybee_customization.patches.keepa_intelligence_fields import field

def execute():
    print("Executing Patch: supplier_history_live_view...")

    # Read-only table rendered from submitted Purchase Invoices, sitting where
    # the old child grid was.
    field("Item", "custom_supplier_history_html", "custom_supplier_history",
          fieldtype="HTML", label="Supplier History")

    # The child table stays in place (its 1 row is not worth destroying) but is
    # hidden - it was never populated by the normal purchase flow, so leaving it
    # visible just shows an empty grid next to the real data.
    make_property_setter("Item", "custom_supplier_history", "hidden", "1", "Check")

    # The heading used to come from the Table field's own label; an HTML field
    # renders no label at all. This section holds nothing but the supplier
    # history, so naming it gives a native section heading instead.
    make_property_setter("Item", "section_break_xili", "label", "Supplier History", "Data")

    frappe.clear_cache(doctype="Item")
    frappe.db.commit()
    print("Patch supplier_history_live_view completed successfully.")
