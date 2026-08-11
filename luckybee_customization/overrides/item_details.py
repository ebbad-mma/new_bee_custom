"""Guards for the Item Details record.

Item Details is keyed by ASIN (or FSN), not by Item, so a single row is shared
by every item carrying that code - while its own `item` Link points at just one
of them, whichever synced most recently.
"""

import frappe


def clear_dangling_item_link(doc, method=None):
	"""Drop the `item` link when it points at an Item that no longer exists.

	Without this, deleting an ASIN-matched item poisons the shared Item Details
	row: link validation fails on every later save, and because the Keepa sync
	saves the row inside the Item's own save, the failure rolls back the whole
	transaction. The visible symptom is a button that appears to do nothing,
	which is why this cost a diagnosis rather than being obvious.

	Nulling is the right repair rather than repointing at the current item: the
	row belongs to the ASIN and is shared, so no single item owns it.

	Note this cannot be a `validate` hook. Document.save() calls
	_validate_links() *before* run_before_save_methods(), so by the time any
	validate or before_validate handler runs the throw has already happened.
	It has to be called on the loaded doc, before save() is reached.
	"""
	if not doc or not doc.get("item"):
		return doc
	if not frappe.db.exists("Item", doc.item):
		doc.item = None
	return doc
