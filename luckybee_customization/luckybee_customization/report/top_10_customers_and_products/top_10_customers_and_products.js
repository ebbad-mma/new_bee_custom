
frappe.query_reports["Top 10 Customers and Products"] = {
	"filters": [

		{
			'label':'From Date',
			'fieldname':'from_date',
			'fieldtype':'Date',
			'default': frappe.datetime.month_start(),
			"reqd": 1,                 
			'width':80
		},
		{
			'label':'To Date',
			'fieldname':'to_date',
			'fieldtype':'Date',
			"reqd": 1,
			'width':80
		},
		{
			'label': 'Category',
			'fieldname': 'category',
			'fieldtype': 'Select',
			'default': frappe.datetime.month_end(),
			'options': [ 
				{"value": "Customer", "label": __("Customer")},
				{"value": "Product", "label": __("Product")}
			],
			'reqd': 1,
			'width': 80
		}
		


	]
};