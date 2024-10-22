frappe.query_reports["Total Purchase By Category"] = {
    "filters": [
        {
            'label': 'From Date',
            'fieldname': 'from_date',
            'fieldtype': 'Date',
            'default': frappe.datetime.month_start(),
            "reqd": 1,               
            'width': 80
        },
        {
            'label': 'To Date',
            'fieldname': 'to_date',
            'fieldtype': 'Date',
            'default': frappe.datetime.month_end(),
            "reqd": 1,
            'width': 80
        }
    ]
};
