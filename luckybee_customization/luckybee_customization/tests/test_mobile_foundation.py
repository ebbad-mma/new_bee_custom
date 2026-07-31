import unittest
import frappe
from luckybee_customization.api.mobile_forms import find_item_for_mobile, fetch_keepa_photo
from luckybee_customization.item_hooks import validate_role_field_permissions

class TestMobileFoundation(unittest.TestCase):
    def setUp(self):
        self.original_get_roles = frappe.get_roles
        self.item_code = "Test-Mobile-Item-1"
        
        # Find if item already exists by item_code
        existing = frappe.db.get_value("Item", {"item_code": self.item_code}, "name")
        if existing:
            frappe.db.delete("Item Barcode", {"parent": existing})
            frappe.db.delete("Item", {"name": existing})
            frappe.db.commit()

        item = frappe.new_doc("Item")
        item.item_code = self.item_code
        item.item_name = "Test Mobile Item 1"
        item.item_group = "All Item Groups"
        item.stock_uom = "Nos"
        item.insert(ignore_permissions=True)
        self.item = item
        self.created_item_name = item.name

        # Ensure it has a barcode in the child table
        self.item.set("barcodes", [])
        self.item.append("barcodes", {"barcode": "TESTSCAN_FOUNDATION_999", "uom": "Nos", "type": "Supplier"})
        self.item.save(ignore_permissions=True)

    def tearDown(self):
        # Restore mock resolver & form_dict
        frappe.get_roles = self.original_get_roles
        frappe.form_dict = frappe._dict()

        # Cleanup using the tracked doc name
        if hasattr(self, "created_item_name"):
            frappe.db.delete("Item Barcode", {"parent": self.created_item_name})
            frappe.db.delete("Item", {"name": self.created_item_name})
            frappe.db.commit()

    def test_find_item_for_mobile(self):
        # 1. Test item not found
        res_not_found = find_item_for_mobile("NONEXISTENTBARCODE")
        self.assertEqual(res_not_found["status"], "not_found")

        # Test routing for Stock-take Staff
        frappe.get_roles = lambda *args, **kwargs: ["Stock-take Staff"]
        res_stock = find_item_for_mobile("TESTSCAN_FOUNDATION_999")
        self.assertEqual(res_stock["status"], "found")
        self.assertEqual(res_stock["item_code"], self.created_item_name)
        self.assertEqual(res_stock["redirect_url"], f"/item-stock-take-staff/{self.created_item_name}/edit")

        # Test routing for Floor Staff
        frappe.get_roles = lambda *args, **kwargs: ["Floor Staff"]
        res_floor = find_item_for_mobile("TESTSCAN_FOUNDATION_999")
        self.assertEqual(res_floor["redirect_url"], f"/item-floor-staff/{self.created_item_name}/edit")

        # Test routing for Trusted Staff
        frappe.get_roles = lambda *args, **kwargs: ["Trusted Staff"]
        res_trusted = find_item_for_mobile("TESTSCAN_FOUNDATION_999")
        self.assertEqual(res_trusted["redirect_url"], f"/item-trusted-staff/{self.created_item_name}/edit")

        # Test routing for Owner-Supervisor
        frappe.get_roles = lambda *args, **kwargs: ["Owner-Supervisor"]
        res_owner = find_item_for_mobile("TESTSCAN_FOUNDATION_999")
        self.assertEqual(res_owner["redirect_url"], f"/item-owner-supervisor/{self.created_item_name}/edit")

    def test_validate_role_field_permissions_floor_staff(self):
        # Test that Floor Staff cannot edit standard item fields like cost/mrp, but can edit images
        frappe.get_roles = lambda *args, **kwargs: ["Floor Staff"]

        item_doc = frappe.get_doc("Item", self.created_item_name)
        
        # 1. Modify allowed field (lb_primary_image) - should not throw
        item_doc.lb_primary_image = "https://example.com/test.jpg"
        try:
            item_doc.save(ignore_permissions=True)
        except frappe.PermissionError:
            self.fail("validate_role_field_permissions raised PermissionError unexpectedly for allowed field lb_primary_image")

        # Reload a fresh copy from DB
        item_doc = frappe.get_doc("Item", self.created_item_name)
        # 2. Modify forbidden field (custom_mrp) - should throw PermissionError
        item_doc.custom_mrp = 250.0
        with self.assertRaises(frappe.PermissionError):
            item_doc.save(ignore_permissions=True)

        # Reload a fresh copy from DB
        item_doc = frappe.get_doc("Item", self.created_item_name)
        # 3. Modify unlisted field (description) - true whitelist must block this with PermissionError
        item_doc.description = "Unallowed edit by floor staff"
        with self.assertRaises(frappe.PermissionError):
            item_doc.save(ignore_permissions=True)

    def test_validate_role_field_permissions_keepa_hook_coexistence(self):
        # Simulate Floor Staff role
        frappe.get_roles = lambda *args, **kwargs: ["Floor Staff"]

        item_doc = frappe.get_doc("Item", self.created_item_name)
        
        # Simulate incoming web request payload (Floor Staff submitted lb_primary_image only)
        import json
        frappe.form_dict = frappe._dict({
            "doc": json.dumps({
                "name": self.created_item_name,
                "lb_primary_image": "https://example.com/floor_photo.jpg"
            })
        })

        # Floor staff updates allowed field lb_primary_image
        item_doc.lb_primary_image = "https://example.com/floor_photo.jpg"

        # Simulate sync_keepa_item running in before_save and updating title + custom_luckybee_brand on doc
        item_doc.title = "Keepa Synced Product Title"
        item_doc.custom_luckybee_brand = "Keepa LB Brand"

        # Save document - should NOT throw PermissionError for Keepa's title/brand changes because Floor Staff only submitted lb_primary_image
        try:
            item_doc.save(ignore_permissions=True)
        except frappe.PermissionError as e:
            self.fail(f"False PermissionError triggered by server hook modification: {e}")

        # Now simulate Floor Staff illegitimately adding custom_mrp to their submitted request payload
        frappe.form_dict = frappe._dict({
            "doc": json.dumps({
                "name": self.created_item_name,
                "lb_primary_image": "https://example.com/floor_photo.jpg",
                "custom_mrp": 888.0
            })
        })
        frappe.clear_cache(doctype="Item")
        item_doc = frappe.get_doc("Item", self.created_item_name)
        item_doc.lb_primary_image = "https://example.com/floor_photo.jpg"
        item_doc.custom_mrp = 888.0

        with self.assertRaises(frappe.PermissionError):
            item_doc.save(ignore_permissions=True)

    def test_validate_role_field_permissions_trusted_staff(self):
        frappe.get_roles = lambda *args, **kwargs: ["Trusted Staff"]

        item_doc = frappe.get_doc("Item", self.created_item_name)
        
        # Modify custom_mrp (allowed for Trusted Staff) - should not throw
        item_doc.custom_mrp = 300.0
        try:
            item_doc.save(ignore_permissions=True)
        except frappe.PermissionError:
            self.fail("validate_role_field_permissions raised PermissionError unexpectedly for Trusted Staff modifying custom_mrp")

        # Reload a fresh copy from DB
        item_doc = frappe.get_doc("Item", self.created_item_name)
        # Modify custom_asin_no (forbidden for Trusted Staff) - should throw PermissionError
        item_doc.custom_asin_no = "B01NXYZ"
        with self.assertRaises(frappe.PermissionError):
            item_doc.save(ignore_permissions=True)

        # Reload a fresh copy from DB
        item_doc = frappe.get_doc("Item", self.created_item_name)
        # Modify lb_category_type (forbidden for Trusted Staff) - should throw PermissionError
        item_doc.lb_category_type = "Category 2 - Standard"
        with self.assertRaises(frappe.PermissionError):
            item_doc.save(ignore_permissions=True)

        # Reload a fresh copy from DB
        item_doc = frappe.get_doc("Item", self.created_item_name)
        # Modify lb_lot_ref (forbidden for Trusted Staff) - should throw PermissionError
        item_doc.lb_lot_ref = "LOT-2026-99"
        with self.assertRaises(frappe.PermissionError):
            item_doc.save(ignore_permissions=True)

    def test_validate_role_field_permissions_desk_save_and_direct_save(self):
        # Simulate Floor Staff user
        frappe.get_roles = lambda *args, **kwargs: ["Floor Staff"]

        # 1. Direct Python save (no form_dict payload, submitted_fields is None)
        frappe.form_dict = frappe._dict()
        frappe.clear_cache(doctype="Item")
        item_doc = frappe.get_doc("Item", self.created_item_name)
        item_doc.custom_mrp = 777.0
        with self.assertRaises(frappe.PermissionError):
            item_doc.save(ignore_permissions=True)

        # 2. Desk save simulation (frappe.form_dict has "action": "Save" and "doc": json.dumps(doc_dict, default=str))
        import json
        doc_dict = item_doc.as_dict()
        doc_dict["custom_mrp"] = 999.0
        frappe.form_dict = frappe._dict({
            "action": "Save",
            "doc": json.dumps(doc_dict, default=str)
        })
        frappe.clear_cache(doctype="Item")
        item_doc = frappe.get_doc("Item", self.created_item_name)
        item_doc.custom_mrp = 999.0

        with self.assertRaises(frappe.PermissionError):
            item_doc.save(ignore_permissions=True)
