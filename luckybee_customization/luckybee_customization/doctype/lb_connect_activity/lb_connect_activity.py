"""One social or review action claimed by a customer.

Points post only on approval, and only once. The plan asks for a quality check
on reels specifically, but the same gate is applied to every type: the caps that
stop the mechanic being farmed only mean something if somebody decides what
counts, and a Google review that was never posted is as farmable as a bad reel.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from luckybee_customization.api.connect_loyalty import (
	award_points,
	preview_activity_points,
)


class LBConnectActivity(Document):
	def validate(self):
		if self.status == "Approved":
			self._price_it()
		if not self.is_new():
			before = self.get_doc_before_save()
			if before and before.status == "Approved" and self.status != "Approved":
				# Points already in the ledger are not silently withdrawn - the
				# entry is real and the customer may have spent against it.
				frappe.throw(_(
					"This activity has already paid out {0} points. Reverse it with "
					"a correcting entry rather than editing the status back."
				).format(before.points_awarded))

	def on_update(self):
		"""Write the ledger row after the record exists.

		Not in validate: the entry cites this activity as its source, and on a
		new document there is nothing yet for that link to point at.
		"""
		if self.status != "Approved" or not self.points_awarded:
			return
		if self._already_paid():
			return
		award_points(
			self.customer, self.points_awarded,
			_("{0} - {1}").format(self.activity_type, self.name),
			source_type="LB Connect Activity", source_name=self.name)

	def _already_paid(self):
		"""Approval can be saved more than once; the points are paid once."""
		return bool(frappe.db.exists("Loyalty Point Entry", {
			"invoice_type": "LB Connect Activity", "invoice": self.name}))

	def _price_it(self):
		if self.points_awarded:
			return
		plan = preview_activity_points(
			self.customer, self.activity_type,
			reel_views=self.reel_views or 0,
			activity_date=self.activity_date,
			exclude=self.name,
		)
		if plan.get("blocked") or not plan.get("points"):
			frappe.throw(
				_("No points can be awarded: {0}").format(
					" ".join(plan.get("notes") or [_("monthly cap reached.")])),
				title=_("Monthly cap reached"))
		self.points_awarded = plan["points"]
