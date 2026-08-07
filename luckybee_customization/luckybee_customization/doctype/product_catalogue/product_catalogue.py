import frappe
from frappe import _
from frappe.model.document import Document


class ProductCatalogue(Document):
	def validate(self):
		self.validate_source()
		self.validate_dates()

	def validate_source(self):
		"""A catalogue nobody can trace back to a brand or a supplier is not much
		use as a data source, which is the whole point of storing it (spec 2).
		"""
		if not self.brand and not self.supplier:
			frappe.throw(_("Set a Brand or a Supplier so staff can find this catalogue later."))

		if self.catalogue_type == "Brand" and not self.brand:
			frappe.throw(_("A Brand catalogue needs the Brand set."))

		if self.catalogue_type == "Importer / Supplier" and not self.supplier:
			frappe.throw(_("An Importer / Supplier catalogue needs the Supplier set."))

	def validate_dates(self):
		if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
			frappe.throw(_("Valid From cannot be after Valid To."))

	def before_insert(self):
		if not self.date_uploaded:
			self.date_uploaded = frappe.utils.today()


@frappe.whitelist()
def get_latest_catalogue(brand=None, supplier=None):
	"""Spec 2.3 - "the latest [brand] catalogue", which is the lookup staff
	actually perform when building a product.
	"""
	filters = {}
	if brand:
		filters["brand"] = brand
	if supplier:
		filters["supplier"] = supplier
	if not filters:
		return None

	rows = frappe.get_all(
		"Product Catalogue",
		filters=filters,
		fields=["name", "catalogue_title", "brand", "supplier",
				"date_uploaded", "catalogue_file"],
		order_by="date_uploaded desc, modified desc",
		limit=1,
	)
	return rows[0] if rows else None
