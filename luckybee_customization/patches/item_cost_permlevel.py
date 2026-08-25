"""Hide cost, margin and supplier data from roles that have no business seeing it.

A role grants access to a document, not to a field, so "can edit products but
cannot see what we paid" is not expressible with roles alone - which is why the
WooCommerce contractor could open an item and read every figure on it. Field
level permissions are the only mechanism for this.

Everything below moves to permlevel 1, and only the roles listed keep access.
Deliberately NOT included: valuation_method and delivered_by_supplier. They read
as sensitive by name but are configuration rather than commercial data, and
moving valuation_method risks disturbing stock behaviour for no privacy gain.

A consequence worth recording. Frappe does not refuse a save that touches a
protected field - it silently resets that field to its stored value
(validate_higher_perm_levels -> reset_values_if_no_permlevel_access). So when a
floor-staff photo save triggers calculate_margins, the recalculated cost and
margin are discarded rather than written. Nothing is corrupted, the stored
figures stand, and the next save by anyone on the list below refreshes them. The
alternative - leaving cost readable by everyone - is worse.
"""

import frappe

from luckybee_customization.item_field_security import enforce_item_field_permlevels


def execute():
	print("Executing Patch: item_cost_permlevel...")
	# The same routine runs from after_migrate, which is what makes it stick -
	# fixtures re-import after patches and would otherwise undo it.
	changed = enforce_item_field_permlevels()
	print(f"  applied: {changed}")
