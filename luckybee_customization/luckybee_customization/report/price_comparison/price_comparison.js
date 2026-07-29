frappe.query_reports["Price Comparison"] = {
    "filters": [
        {
            "fieldname": "include_amazon_benchmarks",
            "label": __("Include Amazon Benchmarks"),
            "fieldtype": "Select",
            "options": "Yes\nNo",
            "default": "Yes",
            "reqd": 1
        },
        {
            "fieldname": "custom_category",
            "label": __("LB Category"),
            "fieldtype": "Link",
            "options": "Item Group"
        },
        {
            "fieldname": "item_code",
            "label": __("Item Code"),
            "fieldtype": "Link",
            "options": "Item"
        }
    ]
};
