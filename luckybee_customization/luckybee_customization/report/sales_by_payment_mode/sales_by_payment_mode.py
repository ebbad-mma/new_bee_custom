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
							sip.mode_of_payment,
							SUM(sip.amount) AS total_amount
						FROM 
							`tabSales Invoice` AS si 
						LEFT JOIN
							`tabSales Invoice Payment` AS sip ON si.name = sip.parent
						WHERE si.posting_date BETWEEN %(from_date)s AND %(to_date)s AND si.status='Paid'
						GROUP BY 
							sip.mode_of_payment
						ORDER BY
							total_amount DESC;
						""" ,({"from_date":str(from_date),"to_date":str(to_date)}),as_dict=1)

	data=[i for i in data if i.mode_of_payment is not None]
	frappe.log_error("data",data)
	return data
	

	
def get_columns(filters):
	columns = [
		 {
			"label":_("Amount"),
			"fieldname": "total_amount",       # filedname should match with the values in SELECT clause of query
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label":_("Mode Of Payment"),
			"fieldname": "mode_of_payment",
			"fieldtype": "Data",          # link field will redirect the user to the source doctype
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
		datasets[0]['values'].append(i.get('total_amount'))
		labels.append(i.get('mode_of_payment'))
	
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