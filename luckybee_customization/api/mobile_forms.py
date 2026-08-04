import frappe
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
