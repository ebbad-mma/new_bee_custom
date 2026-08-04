import frappe
from luckybee_customization.patches.keepa_intelligence_fields import field

def execute():
    print("Executing Patch: amazon_image_gallery_field...")

    # The amz_image_urls grid can only render the URLs as text - Frappe's
    # Image fieldtype has no stored value, so it stays blank in a grid cell.
    # A read-only HTML field above the table renders them as thumbnails.
    field("Item", "amz_image_gallery", "custom_section_break_wukac",
          fieldtype="HTML", label="Amazon Images")

    # Shows the picture when a grid row is expanded into its form view.
    field("Amazon Image URLs", "image_preview", "image_url",
          fieldtype="Image", label="Preview", options="image_url")

    frappe.clear_cache(doctype="Item")
    frappe.clear_cache(doctype="Amazon Image URLs")
    frappe.db.commit()
    print("Patch amazon_image_gallery_field completed successfully.")
