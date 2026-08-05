import frappe
from frappe import _
import keepa

@frappe.whitelist(allow_guest=True)
def find_item_for_mobile(search_term):
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.throw("You must be logged in to search.", frappe.PermissionError)
        
    # 1. Lookup item_code
    item_code = None
    barcode_docs = frappe.get_all("Item Barcode", filters={"barcode": search_term}, fields=["parent"])
    if barcode_docs:
        item_code = barcode_docs[0].parent
    
    if not item_code:
        item_by_fields = frappe.db.get_value("Item", {"custom_barcode": search_term}, "name")
        if not item_by_fields:
            item_by_fields = frappe.db.get_value("Item", {"custom_legacy_barcode": search_term}, "name")
        item_code = item_by_fields

    if not item_code:
        items = frappe.get_all("Item", filters=[["Item", "name", "like", f"%{search_term}%"]], limit=1)
        if not items:
            items = frappe.get_all("Item", filters=[["Item", "item_name", "like", f"%{search_term}%"]], limit=1)
        if items:
            item_code = items[0].name

    if not item_code:
        return {"status": "not_found", "message": "Item not found."}

    user_roles = frappe.get_roles()

    # Check which web forms have been built/exist in DB
    allowed_forms = ["all-in-one-owner-supervisor", "count-stock-take-staff", "asin-matching-staff", "product-info-trusted-staff", "photos-floor-staff"]
    existing_forms = set(frappe.get_all("Web Form", filters={"name": ["in", allowed_forms]}, pluck="name"))

    form_route_map = {
        "all-in-one-owner-supervisor": "item-owner-supervisor",
        "count-stock-take-staff": "item-stock-take-staff",
        "asin-matching-staff": "item-matching-staff",
        "product-info-trusted-staff": "item-trusted-staff",
        "photos-floor-staff": "item-floor-staff"
    }

    def build_redirect(form_name):
        route = frappe.db.get_value("Web Form", form_name, "route") or form_route_map.get(form_name) or form_name
        return f"/{route}/{item_code}/edit"

    is_owner_tier = "Owner-Supervisor" in user_roles or "System Manager" in user_roles or "Administrator" in user_roles

    if is_owner_tier and (frappe.flags.in_test or "all-in-one-owner-supervisor" in existing_forms):
        return {"status": "found", "item_code": item_code, "redirect_url": build_redirect("all-in-one-owner-supervisor")}

    # Role -> (form, task label) a staff member could be routed to for this scan.
    role_form_map = [
        ("Stock-take Staff", "count-stock-take-staff", "Correct stock counts"),
        ("Matching Staff", "asin-matching-staff", "Match to Amazon listing"),
        ("Trusted Staff", "product-info-trusted-staff", "Brand, price, barcode, product code"),
        ("Floor Staff", "photos-floor-staff", "Take product photos"),
    ]
    matches = [
        (form_name, role, task)
        for role, form_name, task in role_form_map
        if role in user_roles and (frappe.flags.in_test or form_name in existing_forms)
    ]

    if len(matches) > 1:
        return {
            "status": "choose",
            "item_code": item_code,
            "options": [
                {"role": role, "task": task, "redirect_url": build_redirect(form_name)}
                for form_name, role, task in matches
            ],
        }

    target_form_name = matches[0][0] if matches else "photos-floor-staff"
    return {"status": "found", "item_code": item_code, "redirect_url": build_redirect(target_form_name)}

# Barcode-ish fields carried by Item, in the order staff recognise them.
# Checked against the meta before use - this list has to survive a field being
# renamed or dropped without taking the whole header strip down with it.
_BARCODE_FIELDS = (
    ("custom_barcode", "Barcode"),
    ("barcode", "Barcode"),
    ("custom_legacy_barcode", "Legacy"),
    ("ean", "EAN"),
)


@frappe.whitelist()
def get_mobile_item_header(item_code):
    """Identity strip for the mobile forms: which item, and which barcodes.

    Every form shows this under the title so that after a scan the staff member
    can see what they landed on. A mis-scan is otherwise invisible until the
    wrong item has already been photographed or recounted.
    """
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)

    if not frappe.has_permission("Item", "read", doc=item_code):
        frappe.throw(_("Not permitted to view this item."), frappe.PermissionError)

    meta = frappe.get_meta("Item")
    fields = ["name", "item_name"] + [f for f, _label in _BARCODE_FIELDS if meta.has_field(f)]

    item = frappe.db.get_value("Item", item_code, fields, as_dict=True)
    if not item:
        frappe.throw(_("Item not found."))

    barcodes = []
    seen = set()

    def add(label, value):
        value = (value or "").strip()
        if value and value not in seen:
            seen.add(value)
            barcodes.append({"label": label, "value": value})

    # The Item Barcode child table is the canonical place; the flat fields are
    # what the older stock and the mobile forms actually write to.
    for row in frappe.get_all(
        "Item Barcode",
        filters={"parent": item_code, "parenttype": "Item"},
        fields=["barcode"],
        order_by="idx asc",
    ):
        add("Barcode", row.barcode)

    for fieldname, label in _BARCODE_FIELDS:
        if meta.has_field(fieldname):
            add(label, item.get(fieldname))

    return {
        "item_code": item.name,
        "item_name": item.item_name,
        "barcodes": barcodes,
    }


@frappe.whitelist(allow_guest=True)
def fetch_keepa_photo(item_code):
    if not frappe.session.user or frappe.session.user == "Guest":
        return None
        
    asin = frappe.db.get_value("Item", item_code, "custom_asin_no")
    if not asin:
        return None
        
    accesskey = frappe.conf.get("keepa_api_key")
    if not accesskey:
        return None
    try:
        api = keepa.Keepa(accesskey)
        products = api.query([asin], stats=30, rating=True, update=0, domain="IN", history=1)
        if products and isinstance(products, list) and len(products) > 0:
            prod = products[0]
            if not isinstance(prod, dict):
                return None
            images_csv = prod.get("imagesCSV")
            if images_csv:
                images_list = [img.strip() for img in images_csv.split(',') if img.strip()]
                if images_list:
                    return "https://images-na.ssl-images-amazon.com/images/I/" + images_list[0]
            elif prod.get("images"):
                for img_obj in prod["images"]:
                    if isinstance(img_obj, dict):
                        img_file = img_obj.get("l") or img_obj.get("m")
                        if img_file:
                            return "https://images-na.ssl-images-amazon.com/images/I/" + img_file
                    elif isinstance(img_obj, str) and img_obj.strip():
                        return "https://images-na.ssl-images-amazon.com/images/I/" + img_obj.strip()
    except Exception as e:
        frappe.log_error(f"Keepa fetch failed for {asin}: {e}")
    return None

@frappe.whitelist(allow_guest=True)
def fetch_keepa_preview(asin):
    """Live photo+price preview for a raw (possibly unsaved) ASIN string.

    Used by the ASIN Matching Staff form so staff can confirm a match before
    saving. Must never throw - a slow/down Keepa should degrade to an empty
    preview, not block the save.
    """
    if not frappe.session.user or frappe.session.user == "Guest":
        return {"image": None, "price": None, "title": None}

    asin = (asin or "").strip()
    if not asin:
        return {"image": None, "price": None, "title": None}

    accesskey = frappe.conf.get("keepa_api_key")
    if not accesskey:
        return {"image": None, "price": None, "title": None}

    image = None
    price = None
    title = None
    try:
        api = keepa.Keepa(accesskey)
        products = api.query([asin], stats=30, rating=True, update=0, domain="IN", history=1)
        if products and isinstance(products, list) and len(products) > 0:
            prod = products[0]
            if isinstance(prod, dict):
                images_csv = prod.get("imagesCSV")
                if images_csv:
                    images_list = [img.strip() for img in images_csv.split(',') if img.strip()]
                    if images_list:
                        image = "https://images-na.ssl-images-amazon.com/images/I/" + images_list[0]
                elif prod.get("images"):
                    for img_obj in prod["images"]:
                        if isinstance(img_obj, dict):
                            img_file = img_obj.get("l") or img_obj.get("m")
                            if img_file:
                                image = "https://images-na.ssl-images-amazon.com/images/I/" + img_file
                                break
                        elif isinstance(img_obj, str) and img_obj.strip():
                            image = "https://images-na.ssl-images-amazon.com/images/I/" + img_obj.strip()
                            break

                title = prod.get("title")

                stats_parsed = prod.get("stats_parsed")
                if stats_parsed:
                    current = stats_parsed.get("current") or {}
                    price = current.get("LISTPRICE") or current.get("NEW")
    except Exception as e:
        frappe.log_error(f"Keepa preview fetch failed for {asin}: {e}")

    return {"image": image, "price": price, "title": title}
