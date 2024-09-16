import frappe

from frappe import _

def execute(filters=None):
	columns,data = get_columns(filters),get_data(filters)
	chart=get_chart_data(data)

	return columns, data,None,chart


	

def get_data(filters):
	from_date =filters.from_date
	to_date =filters.to_date
	data = frappe.db.sql("""
				SELECT 
					item.custom_category,
					ABS(SUM(stock.stock_value_difference)) AS total_valuation_rate
				FROM
					`tabStock Ledger Entry` AS stock
				LEFT JOIN
					`tabItem` AS item ON stock.item_code = item.name
				WHERE
					stock.voucher_type = 'Sales Invoice' 
					AND stock.posting_date BETWEEN %(from_date)s AND %(to_date)s
					AND item.custom_category IS NOT NULL
					AND item.custom_category <> ''
				GROUP BY
					item.custom_category
				ORDER BY
					total_valuation_rate DESC;
			""", {"from_date": str(from_date), "to_date": str(to_date)}, as_dict=1)


	# data = [{**x,**{"net_balance":x.total_deposited_amount-x.total_purchase_cost,"outstanding_deposit":0}} for x in data]
	
	frappe.log_error("data",data)
	return data
	

	
def get_columns(filters):
	columns = [
		 {
			"label":_("Category"),
			"fieldname": "custom_category",     
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label":_("Total Sales"),
			"fieldname": "total_valuation_rate",
			"fieldtype": "Float",         
			"width": 200,
		}
		]
	
	return columns


def get_chart_data(data):
	frappe.log_error("chartdata",data)
	if not data:
		return None
	labels=[]
	datasets=[{'values':[]}]
	for i in data:
		datasets[0]['values'].append(i.get('total_valuation_rate'))
		labels.append(i.get('custom_category'))
	
	chart={
		'data':{
			'labels':labels,
			'datasets':datasets
		},
		'type':'bar',
		'height':300
	}
	frappe.log_error("datasets",datasets)
	frappe.log_error("labels",labels)
	return chart