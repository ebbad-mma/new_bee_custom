frappe.query_reports["Product Velocity"] = {
    "filters": [
        {
            "fieldname": "lb_velocity_band",
            "label": __("Velocity Band"),
            "fieldtype": "Select",
            "options": "\nFast\nHealthy\nSlow\nDead\nNever Sold"
        },
        {
            "fieldname": "item_code",
            "label": __("Item Code"),
            "fieldtype": "Link",
            "options": "Item"
        }
    ]
};
