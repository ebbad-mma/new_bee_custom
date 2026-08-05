"""Show the Lucky Bee photos as pictures, not as file paths.

lb_images is a grid of Attach Image rows, and a grid cell can only print the
stored value - so the Product Images section showed a column of
"/private/files/capture_2026...jpg" strings and no way to tell what had actually
been photographed without opening every row. Same problem the Amazon images had,
and the same fix: a read-only HTML field above the table renders the thumbnails
(see public/js/item.js), plus an Image field on the child row so an expanded row
shows its picture too.
"""

import frappe

from luckybee_customization.patches.keepa_intelligence_fields import field


def execute():
	print("Executing Patch: lucky_bee_image_gallery...")

	# Above the grid, below the primary image - the pictures are the point of
	# this section, so they come before the table that lists them.
	field("Item", "lb_image_gallery", "lb_primary_image",
	      fieldtype="HTML", label="Photos")

	# Shows the picture when a grid row is expanded into its form view.
	field("Lucky Bee Images", "image_preview", "image",
	      fieldtype="Image", label="Preview", options="image")

	frappe.clear_cache(doctype="Item")
	frappe.clear_cache(doctype="Lucky Bee Images")
	frappe.db.commit()
	print("Patch lucky_bee_image_gallery completed successfully.")
