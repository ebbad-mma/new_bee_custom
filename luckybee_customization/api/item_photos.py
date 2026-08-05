"""A3/A4 - server side of the three-section mobile photo capture.

The Lucky Bee Images child-table grid was four taps per photo (add row, pick
type, attach, set sequence) and let staff file a photo under the wrong type.
This exposes a small API so the form can present three labelled sections
(Out Box / In Box / Product), each with its own capture button that files the
photo into the right section automatically.

Photos are persisted immediately rather than staged in the grid and left to a
separate Save - on a phone, a half-filled form that gets backgrounded loses
the lot. Every write goes through doc.save() as the real session user, so
item_hooks.validate_role_field_permissions still applies: Floor Staff may only
touch lb_images / lb_primary_image, and anything else is rejected exactly as
before.
"""

import frappe
from frappe import _

SECTIONS = ("Out Box", "In Box", "Product")

# Mirrors the mobile forms' own role gate. Stock-take Staff is deliberately
# absent - that role edits no Item fields at all.
PHOTO_ROLES = {
	"Floor Staff",
	"Trusted Staff",
	"Owner-Supervisor",
	"System Manager",
	"Administrator",
}

MAX_PER_SECTION = 5


def _check_photo_role():
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)
	if not (set(frappe.get_roles()) & PHOTO_ROLES):
		frappe.throw(_("You do not have permission to edit photos."), frappe.PermissionError)


def _serialise(doc):
	"""Return photos grouped by section, plus which one is primary."""
	primary = doc.get("lb_primary_image")
	grouped = {section: [] for section in SECTIONS}
	for row in doc.get("lb_images") or []:
		section = row.get("photo_section")
		if section not in grouped:
			# Rows captured before photo_section existed - surface them under
			# Product rather than hiding them, so nothing looks lost.
			section = "Product"
		grouped[section].append({
			"name": row.name,
			"image": row.image,
			"is_primary": bool(primary and row.image == primary),
		})
	return {
		"sections": SECTIONS,
		"photos": grouped,
		"primary_image": primary,
		"max_per_section": MAX_PER_SECTION,
	}


@frappe.whitelist()
def get_item_photos(item_code):
	_check_photo_role()
	return _serialise(frappe.get_doc("Item", item_code))


@frappe.whitelist(methods=["POST"])
def add_item_photo(item_code, section, file_url):
	"""Attach an already-uploaded file to a section."""
	_check_photo_role()

	if section not in SECTIONS:
		frappe.throw(_("Unknown photo section."))
	if not file_url:
		frappe.throw(_("No file was provided."))

	doc = frappe.get_doc("Item", item_code)

	existing = [r for r in (doc.get("lb_images") or []) if r.get("photo_section") == section]
	if len(existing) >= MAX_PER_SECTION:
		frappe.throw(_("You can add at most {0} photos to {1}.").format(MAX_PER_SECTION, section))

	doc.append("lb_images", {
		"image": file_url,
		"photo_section": section,
		"sequence": len(existing) + 1,
	})

	# First Product photo becomes primary automatically - the common case is a
	# single product shot, and staff should not have to make a second decision.
	if section == "Product" and not doc.get("lb_primary_image"):
		doc.lb_primary_image = file_url

	doc.save()
	frappe.db.commit()
	return _serialise(doc)


@frappe.whitelist(methods=["POST"])
def delete_item_photo(item_code, row_name):
	_check_photo_role()

	doc = frappe.get_doc("Item", item_code)
	rows = doc.get("lb_images") or []
	target = next((r for r in rows if r.name == row_name), None)
	if not target:
		frappe.throw(_("That photo is no longer on this item."))

	removed_url = target.image
	doc.set("lb_images", [r for r in rows if r.name != row_name])

	# Never leave lb_primary_image pointing at a photo that no longer exists.
	if removed_url and doc.get("lb_primary_image") == removed_url:
		remaining = [r for r in doc.get("lb_images") or []
					 if r.get("photo_section") == "Product" and r.image]
		doc.lb_primary_image = remaining[0].image if remaining else None

	doc.save()
	frappe.db.commit()
	return _serialise(doc)


@frappe.whitelist(methods=["POST"])
def set_primary_image(item_code, file_url):
	_check_photo_role()

	doc = frappe.get_doc("Item", item_code)
	product_urls = {r.image for r in (doc.get("lb_images") or [])
					if r.get("photo_section") == "Product" and r.image}
	if file_url not in product_urls:
		# Guard against a stale page setting a primary that isn't a Product photo.
		frappe.throw(_("Only a Product photo can be the primary image."))

	doc.lb_primary_image = file_url
	doc.save()
	frappe.db.commit()
	return _serialise(doc)
