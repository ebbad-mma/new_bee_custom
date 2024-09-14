// Copyright (c) 2024, bizmap technologies pvt ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Total Purchase By Category"] = {
	"filters": [

		// {
		// 	"fieldname": "time",
		// 	"label": __("Time"),
		// 	"fieldtype": "Select",
		// 	"default":"",
		// 	"options": [
		// 		{ "value":null},
		// 		{ "value": "Daily", "label": __("Daily") },
		// 		{ "value": "Weekly", "label": __("Weekly") },
		// 		{ "value": "Monthly", "label": __("Monthly") },
		// 		{ "value": "Yearly", "label": __("Yearly") },
		// 		{ "value": "Custom", "label": __("Custom") }
		// 	]
		// }

		{
			'label':'From Date',
			'fieldname':'from_date',
			'fieldtype':'Date',
			"reqd": 1,                   // Make field required will limit the record or data in the report
			'width':80
		},
		{
			'label':'To Date',
			'fieldname':'to_date',
			'fieldtype':'Date',
			"reqd": 1,
			'width':80
		}


	]
};