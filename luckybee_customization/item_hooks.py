import frappe

def mark_system_field_modified(doc, fieldname):
    if not getattr(doc, "flags", None):
        doc.flags = frappe._dict()
    if getattr(doc.flags, "system_modified_fields", None) is None:
        doc.flags.system_modified_fields = set()
    doc.flags.system_modified_fields.add(fieldname)

def get_price(item_code, price_list):
    r = frappe.db.sql("""
        SELECT price_list_rate
        FROM `tabItem Price`
        WHERE item_code=%s AND price_list=%s AND price_list_rate > 0
        ORDER BY valid_from DESC
        LIMIT 1
    """, (item_code, price_list))
    return float(r[0][0]) if r else 0.0

def true_cost(doc):
    lpr = float(doc.last_purchase_rate) if doc.last_purchase_rate else 0.0
    ip = get_price(doc.name, "Standard Buying")
    mrp = float(doc.custom_mrp) if doc.custom_mrp else 0.0

    if ip and mrp and abs(ip - mrp) < 0.01:
        # MRP loaded as cost - reject buying Item Price and fall back to last_purchase_rate
        return lpr or None

    return ip or lpr or None

def calculate_margins(doc, method=None):
    selling = get_price(doc.name, "Standard Selling")
    cost = true_cost(doc)

    if selling and cost:
        doc.lb_margin_pct = round((selling - cost) / cost * 100.0, 2)
        doc.lb_actual_cost = cost
    else:
        doc.lb_margin_pct = None
        doc.lb_actual_cost = cost or None

    mark_system_field_modified(doc, "lb_margin_pct")
    mark_system_field_modified(doc, "lb_actual_cost")

    try:
        amz = float(doc.last_price) if doc.last_price else 0.0
    except (ValueError, TypeError):
        amz = 0.0

    if amz and selling:
        doc.amz_delta_pct = round((selling - amz) / amz * 100.0, 2)
    else:
        doc.amz_delta_pct = None

    mark_system_field_modified(doc, "amz_delta_pct")

    mrp = float(doc.custom_mrp) if doc.custom_mrp else 0.0
    if mrp and selling:
        doc.mrp_discount_pct = round((mrp - selling) / mrp * 100.0, 2)
    else:
        doc.mrp_discount_pct = None

    mark_system_field_modified(doc, "mrp_discount_pct")


def validate_role_field_permissions(doc, method=None):
    if doc.is_new():
        return

    # Check session user roles
    user_roles = set(frappe.get_roles())
    
    # Bypass for super users or managers
    bypass_roles = {"Administrator", "System Manager", "Owner-Supervisor", "Item Manager", "Stock Manager"}
    if user_roles & bypass_roles:
        return

    staff_roles = {"Floor Staff", "Trusted Staff", "Matching Staff", "Stock-take Staff"}
    active_staff_roles = user_roles & staff_roles
    
    # If the user has none of the custom staff roles, default to standard Frappe permissions
    if not active_staff_roles:
        return

    # Define strict WHITELIST of allowed editable fields per role
    role_allowed_fields = {
        "Floor Staff": {
            "lb_images",
            "lb_primary_image",
        },
        "Trusted Staff": {
            "custom_luckybee_brand",
            "custom_mrp",
            "ean",
            "default_manufacturer_part_no",
            "lb_images",
            "lb_primary_image",
        },
        "Matching Staff": {
            "custom_asin_no",
        },
        "Stock-take Staff": set()  # Form 4 uses Stock Reconciliation API, no direct Item edits allowed
    }

    # Aggregate allowed fields for user's active staff roles
    user_allowed_fields = set()
    for role in active_staff_roles:
        user_allowed_fields.update(role_allowed_fields.get(role, set()))

    doc_before = doc.get_doc_before_save()
    if not doc_before:
        return

    # Compare doc vs doc_before for fields on Item
    modified_fields = []
    ignored_system_fields = {
        "modified", "modified_by", "creation", "owner", "docstatus", "idx",
        "_comments", "_assign", "_liked_by", "_user_tags", "_doc_before_save", "__islocal", "name",
        "lb_actual_cost", "lb_margin_pct", "amz_delta_pct", "mrp_discount_pct", "lb_data_status"
    }

    meta_fields = {df.fieldname: df.fieldtype for df in doc.meta.fields}

    for fieldname, fieldtype in meta_fields.items():
        if fieldname in ignored_system_fields:
            continue
        
        if fieldtype == "Table":
            if fieldname == "lb_images":
                before_images = doc_before.get("lb_images") or []
                after_images = doc.get("lb_images") or []
                if len(before_images) != len(after_images):
                    modified_fields.append("lb_images")
                else:
                    for i1, i2 in zip(before_images, after_images):
                        if i1.image != i2.image or getattr(i1, "photo_section", None) != getattr(i2, "photo_section", None):
                            modified_fields.append("lb_images")
                            break
            elif fieldname == "barcodes":
                before_barcodes = doc_before.get("barcodes") or []
                after_barcodes = doc.get("barcodes") or []
                if len(before_barcodes) != len(after_barcodes):
                    modified_fields.append("barcodes")
                else:
                    for b1, b2 in zip(before_barcodes, after_barcodes):
                        if b1.barcode != b2.barcode or getattr(b1, "type", None) != getattr(b2, "type", None) or getattr(b1, "barcode_type", None) != getattr(b2, "barcode_type", None):
                            modified_fields.append("barcodes")
                            break
        else:
            if doc.get(fieldname) != doc_before.get(fieldname):
                modified_fields.append(fieldname)

    # Fields marked as modified by server hooks during before_save (e.g. sync_keepa_item)
    system_modified = getattr(doc.flags, "system_modified_fields", set())

    # Reject any modified field that is NOT system-modified and NOT in user_allowed_fields.
    # Do not try to infer "was this submitted by the client" from frappe.form_dict: it only
    # holds a "doc" payload for Desk-style client.save() calls. Web Form saves (the real path
    # staff use) call frappe.website.doctype.web_form.web_form.accept with a "data"/"web_form"
    # payload instead, so that inference silently treated every hook-driven-looking field as
    # "not submitted" and skipped the whitelist check entirely - verified live: a Trusted Staff
    # user could overwrite `title` (not in their whitelist) via the real save path. Every field
    # change a legitimate server hook makes is already covered by system_modified_fields
    # (sync_keepa_item marks its own fields via an outer try/finally over all doc fields), so
    # this check needs no other exemption.
    for fieldname in modified_fields:
        if fieldname in system_modified:
            # Field was modified by a server-side hook (e.g. sync_keepa_item or calculate_margins), not client submission
            continue

        if fieldname not in user_allowed_fields:
            label = doc.meta.get_label(fieldname) or fieldname
            frappe.throw(
                f"You do not have permission to edit field: {label} ({fieldname})",
                frappe.PermissionError
            )

