"""Jinja helpers exposed to print formats.

Print formats run in Frappe's restricted Jinja sandbox, which offers
frappe.db.get_value / frappe.db.sql / frappe.utils but not arbitrary Python -
so anything needing a library (the label's barcode rendering, for one) has to
be surfaced explicitly here and registered via the `jinja` hook.
"""

import frappe


def lb_label_data(item_code):
	"""Everything the product label print format needs, including the barcode
	SVG, which cannot be produced from Jinja alone.
	"""
	from luckybee_customization.api.product_label import get_label_data

	return get_label_data(item_code)


def lb_barcode_svg(code, module_height=8.0):
	"""Bare <svg> for a code. Returns "" rather than raising - a label with no
	barcode still prints, a traceback loses the run.
	"""
	from luckybee_customization.api.product_label import get_barcode_svg

	return get_barcode_svg(code, module_height=module_height)
