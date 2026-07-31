import unittest
import frappe
from luckybee_customization.api.mobile_forms import find_item_for_mobile, fetch_keepa_photo
from luckybee_customization.api.stock_recount import get_stock_recount_context, submit_stock_recount
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

        # Tests that set custom_asin_no trigger the real sync_keepa_item hook (it runs in
        # before_save regardless of whether validate_role_field_permissions later blocks the
        # save), which creates/reuses an "Item Details" row for that ASIN. Left uncleaned, that
        # row's .item link points at this run's (now-deleted) item, and the next test run - which
        # reuses the same hardcoded test ASIN - resaves that same stale row via
        # frappe.db.exists({'asin_no': ...}) and hits a dangling Link validation error. Reproduced
        # live (intermittent "Could not find Item: <name>" failures on repeat runs).
        frappe.db.delete("Item Details", {"asin_no": ["in", ["B01NXYZ", "B0MATCHOK1"]]})
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

        # Floor staff updates allowed field lb_primary_image
        item_doc.lb_primary_image = "https://example.com/floor_photo.jpg"

        # Simulate sync_keepa_item running in before_save and updating title + brand on doc,
        # exactly as the real hook does: it mutates the field AND calls
        # mark_system_field_modified so validate_role_field_permissions knows this change
        # wasn't made by the saving user. (There is no reliable way to infer "was this field
        # submitted by the client" from frappe.form_dict - Web Form saves never populate a
        # "doc" key there - so mark_system_field_modified is the only exemption mechanism.)
        from luckybee_customization.item_hooks import mark_system_field_modified
        item_doc.title = "Keepa Synced Product Title"
        mark_system_field_modified(item_doc, "title")
        if not frappe.db.exists("Brand", "Keepa Test Brand"):
            frappe.get_doc({"doctype": "Brand", "brand": "Keepa Test Brand"}).insert(ignore_permissions=True)
        item_doc.brand = "Keepa Test Brand"
        mark_system_field_modified(item_doc, "brand")

        # Save document - should NOT throw PermissionError for Keepa's title/brand changes because
        # they're marked as system-modified, even though Floor Staff isn't allowed to edit them directly
        try:
            item_doc.save(ignore_permissions=True)
        except frappe.PermissionError as e:
            self.fail(f"False PermissionError triggered by server hook modification: {e}")

        # Now simulate Floor Staff illegitimately modifying custom_mrp themselves (not hook-driven,
        # not marked system-modified) - the whitelist must still block this
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

    def test_validate_role_field_permissions_matching_staff(self):
        frappe.get_roles = lambda *args, **kwargs: ["Matching Staff"]

        item_doc = frappe.get_doc("Item", self.created_item_name)

        # Modify custom_asin_no (allowed for Matching Staff) - should not throw
        item_doc.custom_asin_no = "B0MATCHOK1"
        try:
            item_doc.save(ignore_permissions=True)
        except frappe.PermissionError:
            self.fail("validate_role_field_permissions raised PermissionError unexpectedly for Matching Staff modifying custom_asin_no")

        # Reload a fresh copy from DB
        item_doc = frappe.get_doc("Item", self.created_item_name)
        # Modify custom_mrp (forbidden for Matching Staff) - should throw PermissionError
        item_doc.custom_mrp = 400.0
        with self.assertRaises(frappe.PermissionError):
            item_doc.save(ignore_permissions=True)

    def test_validate_role_field_permissions_owner_supervisor_bypass(self):
        # Form 5 (All-in-one) relies on Owner-Supervisor being a full bypass role -
        # confirm it can edit a field that's on NO individual staff role's whitelist
        # (description isn't editable by Floor/Trusted/Matching/Stock-take Staff).
        frappe.get_roles = lambda *args, **kwargs: ["Owner-Supervisor"]

        item_doc = frappe.get_doc("Item", self.created_item_name)
        item_doc.description = "Set by Owner-Supervisor via Form 5"
        item_doc.custom_asin_no = "B0OWNERBYPASS"
        item_doc.custom_mrp = 1234.0
        try:
            item_doc.save(ignore_permissions=True)
        except frappe.PermissionError:
            self.fail("validate_role_field_permissions raised PermissionError unexpectedly for Owner-Supervisor (bypass role)")

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


class TestStockRecount(unittest.TestCase):
    """Form 4 (Stock-take Staff) - highest risk of the mobile forms since it writes
    real stock via Stock Reconciliation. Uses real Stock Reconciliation submissions
    against disposable test items/warehouses, not mocks."""

    WAREHOUSE = "Stores - SR"
    COMPANY = "Samyak Resources"

    def setUp(self):
        self.original_get_roles = frappe.get_roles
        frappe.set_user("Administrator")

        # This site's Item doctype autonames via naming_series (STOITEM.YYYY.), which
        # overwrites both .name and .item_code on insert to the generated series value -
        # whatever string is assigned to item_code beforehand is discarded. Must read the
        # real identifier back from item.name after insert() rather than assume it.
        item = frappe.new_doc("Item")
        item.item_name = "Test Recount Item"
        item.item_group = "All Item Groups"
        item.stock_uom = "Nos"
        item.is_stock_item = 1
        item.insert(ignore_permissions=True)
        self.item = item
        self.item_code = item.name

        serial_item = frappe.new_doc("Item")
        serial_item.item_name = "Test Recount Serial Item"
        serial_item.item_group = "All Item Groups"
        serial_item.stock_uom = "Nos"
        serial_item.is_stock_item = 1
        serial_item.has_serial_no = 1
        serial_item.serial_no_series = "TRSI-.####"
        serial_item.insert(ignore_permissions=True)
        self.serial_item_code = serial_item.name

        # Establish a realistic baseline (qty + valuation), matching how a real item
        # would already have stock before anyone ever recounts it - a from-zero
        # reconciliation with no cost basis is a different, correctly-rejected case.
        self.reco_docs = []
        baseline = frappe.new_doc("Stock Reconciliation")
        baseline.purpose = "Stock Reconciliation"
        baseline.company = self.COMPANY
        baseline.posting_date = frappe.utils.nowdate()
        baseline.posting_time = frappe.utils.nowtime()
        baseline.append("items", {"item_code": self.item_code, "warehouse": self.WAREHOUSE, "qty": 10, "valuation_rate": 50})
        baseline.insert(ignore_permissions=True)
        baseline.submit()
        self.reco_docs.append(baseline.name)

    def tearDown(self):
        frappe.get_roles = self.original_get_roles
        frappe.set_user("Administrator")

        for name in frappe.get_all("Stock Reconciliation", filters={"name": ["in", self.reco_docs]}, pluck="name"):
            doc = frappe.get_doc("Stock Reconciliation", name)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("Stock Reconciliation", name, force=True, ignore_permissions=True)

        for code in [self.item_code, self.serial_item_code]:
            if frappe.db.exists("Item", code):
                frappe.delete_doc("Item", code, force=True, ignore_permissions=True)
        frappe.db.delete("Bin", {"item_code": ["in", [self.item_code, self.serial_item_code]]})
        frappe.db.commit()

    def test_eligibility(self):
        frappe.get_roles = lambda *args, **kwargs: ["Stock-take Staff"]

        ctx = get_stock_recount_context(self.item_code)
        self.assertTrue(ctx["is_eligible"])
        warehouses = {w["warehouse"]: w["current_qty"] for w in ctx["warehouses"]}
        self.assertEqual(warehouses.get(self.WAREHOUSE), 10.0)

        serial_ctx = get_stock_recount_context(self.serial_item_code)
        self.assertFalse(serial_ctx["is_eligible"])

    def test_role_enforcement(self):
        frappe.get_roles = lambda *args, **kwargs: ["Trusted Staff"]
        with self.assertRaises(frappe.PermissionError):
            submit_stock_recount(self.item_code, self.WAREHOUSE, 20)

    def test_invalid_input_rejected(self):
        frappe.get_roles = lambda *args, **kwargs: ["Stock-take Staff"]

        with self.assertRaises(frappe.ValidationError):
            submit_stock_recount(self.item_code, self.WAREHOUSE, -5)

        with self.assertRaises(frappe.ValidationError):
            submit_stock_recount(self.item_code, "Not A Real Warehouse", 5)

        with self.assertRaises(frappe.ValidationError):
            submit_stock_recount(self.serial_item_code, self.WAREHOUSE, 5)

    def test_functional_recount(self):
        frappe.get_roles = lambda *args, **kwargs: ["Stock-take Staff"]

        result = submit_stock_recount(self.item_code, self.WAREHOUSE, 3)
        self.assertEqual(result["status"], "success")
        self.reco_docs.append(result["stock_reconciliation"])

        bin_qty = frappe.db.get_value("Bin", {"item_code": self.item_code, "warehouse": self.WAREHOUSE}, "actual_qty")
        self.assertEqual(bin_qty, 3.0)

        # Same qty again - must not create a redundant Stock Reconciliation
        no_op = submit_stock_recount(self.item_code, self.WAREHOUSE, 3)
        self.assertEqual(no_op["status"], "no_change")

        reco_count = frappe.db.count("Stock Reconciliation", {"name": ["in", self.reco_docs]})
        self.assertEqual(reco_count, len(self.reco_docs))
