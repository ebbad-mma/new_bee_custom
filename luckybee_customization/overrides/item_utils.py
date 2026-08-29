import frappe


def get_linked_item_details(doc, identifier_filter):
	# Prefer the Item Details record already linked to this item (item is unique on Item Details).
	# Looking up by identifier (ean/asin_no/fsn_no) first and blindly repointing .item onto it can
	# collide with a different record that's already linked to this item, raising a raw MySQL
	# IntegrityError instead of updating the right row.
	existing_for_item = frappe.db.get_value('Item Details', {'item': doc.name})
	if existing_for_item:
		return frappe.get_doc('Item Details', existing_for_item)
	if frappe.db.exists('Item Details', identifier_filter):
		return frappe.get_doc('Item Details', identifier_filter)
	return None

def check_image(doc,method=None):
	# if not doc.custom_image1 and not doc.custom_image2 and not doc.custom_image3 and not doc.custom_image4 and not doc.custom_image5:
	#     image_list=doc.custom_image_list
	#     for i in image_list:
	#         if i.view=='Front view':
	#             doc.db_set('custom_image1',i.image)
	#         else:
	#             doc.db_set('custom_image1',i.image)
	#create item details
	update_stock_in_hand_in_item_master(doc)
	if doc.custom_asin_no:
		item_details = get_linked_item_details(doc, {'asin_no': doc.custom_asin_no})
		if item_details:
			item_details.amazon_item_url = f"https://www.amazon.in/dp/{doc.custom_asin_no}"
			item_details.asin_no = doc.custom_asin_no
			item_details.item = doc.name
			item_details.save(ignore_permissions=True)
	elif doc.ean:
		item_details = get_linked_item_details(doc, {'ean': doc.ean})
		if item_details:
			item_details.ean = doc.ean
			item_details.item = doc.name
			item_details.save(ignore_permissions=True)
	elif doc.get("custom_fsn_no"):
		item_details = get_linked_item_details(doc, {'fsn_no': doc.get("custom_fsn_no")})
		if item_details:
			item_details.flipkart_item_url = f"https://www.flipkart.com/product/p/itme?pid={doc.get('custom_fsn_no')}"
			item_details.fsn_no = doc.get("custom_fsn_no")
			item_details.item = doc.name
			item_details.save(ignore_permissions=True)
	else:
		pass


def update_item_in_woocom():
	"""Hourly: push published items that changed today.

	This used to build its own WooCommerce payload, and it disagreed with the
	mapping agreed with the storefront developer on almost every field: it sent
	the ASIN as the SKU, took categories from category_root and lb_sub_category
	- an Amazon field and one that is empty on all 8,020 items - and passed them
	through get_or_create_category, so any name it could not find was CREATED.
	Left running it would have built a second, duplicate taxonomy beside
	Ashish's and overwritten the correct categories on every product it touched.
	It also pushed doc.image, which is hotlinked marketplace photography we are
	deliberately not publishing.

	It now delegates to product_sync, so there is one payload builder and one
	definition of the mapping. Items outside the agreed category structure are
	skipped there rather than inventing a category for them.
	"""
	from luckybee_customization.woocommerce.product_sync import sync_items

	items = frappe.db.sql(
		"""SELECT name FROM `tabItem`
		   WHERE DATE(modified) = CURDATE() AND custom_published = 1""",
		pluck=True,
	)
	if not items:
		return

	result = sync_items(items, include_images=False)
	if result["failed"] or result["skipped"]:
		frappe.log_error(
			title="WooCommerce hourly sync - items not updated",
			message=frappe.as_json({"failed": result["failed"],
									"skipped": result["skipped"]}),
		)
	return result


# -----------------------HELPER FUNCTION  TO UPDATE STOCK IN HAND FIELD IN ITEM MASTER---------------
def update_stock_in_hand_in_item_master(doc):
	pass

