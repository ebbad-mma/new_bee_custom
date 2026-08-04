import frappe

# custom_category is a Link to Item Group, but 656 items carried values that
# never existed as groups - so Frappe's link validation rejected every save on
# those items, blocking stock counts, photo capture and ASIN matching alike.

# Typos with an unambiguous existing group. Everything here scored >= 0.92
# similarity and means the same thing.
TYPO_REMAP = {
    "Curtain": "Curtains",
    "Car Accessories": "Car  Accessories",
    "Building & Block Toys": "Building  Block Toys",
    "Building Block Toys": "Building  Block Toys",
    "Dressup & Pretend Play": "Dress Up & Pretend Play",
    "Racks Shelves & Drawers": "Racks, Shelves & Drawers",
    "Kitchen Toola": "Kitchen Tools",
    "Boxes, Basket & Bins": "Boxes, Baskets & Bins",
    "Boxes,Baskets&Bins": "Boxes, Baskets & Bins",
    "Bikes, Trikes & Rideons": "Bikes, Trikes & Ride-Ons",
    "Arts & Craft": "Arts & Crafts",
}

# Not real categories - clear rather than enshrine as Item Groups.
JUNK_VALUES = ["0", "TEST", "Kitch"]

def execute():
    print("Executing Patch: lb_category_orphan_cleanup...")

    remapped = 0
    for bad, good in TYPO_REMAP.items():
        if not frappe.db.exists("Item Group", good):
            print(f"  skip {bad!r}: target {good!r} no longer exists")
            continue
        count = frappe.db.count("Item", {"custom_category": bad})
        if count:
            frappe.db.set_value("Item", {"custom_category": bad}, "custom_category", good,
                                update_modified=False)
            remapped += count

    cleared = 0
    for junk in JUNK_VALUES:
        count = frappe.db.count("Item", {"custom_category": junk})
        if count:
            frappe.db.set_value("Item", {"custom_category": junk}, "custom_category", None,
                                update_modified=False)
            cleared += count

    frappe.db.commit()

    # Whatever is still orphaned is a genuine category the business uses; create
    # it so the link resolves and the item becomes saveable again.
    orphans = frappe.db.sql("""
        SELECT DISTINCT i.custom_category
        FROM `tabItem` i
        LEFT JOIN `tabItem Group` g ON g.name = i.custom_category
        WHERE i.custom_category IS NOT NULL AND i.custom_category != '' AND g.name IS NULL
    """, pluck=True)

    parent = frappe.db.get_value("Item Group", {"is_group": 1, "parent_item_group": ""}, "name") or "All Item Groups"

    created = 0
    for value in orphans:
        doc = frappe.new_doc("Item Group")
        doc.item_group_name = value
        doc.parent_item_group = parent
        doc.is_group = 0
        doc.insert(ignore_permissions=True)
        created += 1

    frappe.db.commit()
    print(f"Patch lb_category_orphan_cleanup completed successfully "
          f"({remapped} items remapped, {cleared} cleared, {created} item groups created).")
