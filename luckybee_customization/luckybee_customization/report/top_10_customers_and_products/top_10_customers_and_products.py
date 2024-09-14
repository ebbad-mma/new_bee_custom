import frappe

from frappe import _

def execute(filters=None):
	data=get_data(filters)
	category=filters.category
	if category=='Customer':
		columns=get_columns_for_customers(filters)
		chart=get_chart_data_for_customers(data)
	if category=='Product':
		columns=get_columns_for_product(filters)
		chart=get_chart_data_for_products(data)

	return columns, data , None,chart



	

def get_data(filters):
	from_date =filters.from_date
	to_date =filters.to_date
	category=filters.category
	if category=='Customer':
		data=frappe.db.sql("""
							SELECT 
								si.customer AS customer_name,
								SUM(si.total_qty) AS total_quantity,
								SUM(si.total) AS total_amount
							FROM 
								`tabSales Invoice` AS si
							WHERE 
								si.posting_date BETWEEN %(from_date)s AND %(to_date)s AND si.status='Paid'
							GROUP BY  
								si.customer
							ORDER BY 
								Total_Amount DESC
							LIMIT 10;
							""",({"from_date":str(from_date),"to_date":str(to_date)}),as_dict=1)

	if category=='Product':
		data=frappe.db.sql("""
								SELECT 
								item.item_name AS item_name,
								ABS(SUM(stock.stock_value_difference)) AS AMOUNT,
								ABS(SUM(stock.actual_qty)) AS QTY
							FROM
								`tabStock Ledger Entry` AS stock
							LEFT JOIN
								`tabItem` AS item ON stock.item_code = item.name
							WHERE
								(stock.voucher_type = 'Sales Invoice')
								AND stock.posting_date BETWEEN %(from_date)s  AND %(to_date)s
							GROUP BY
								item.item_name
							ORDER BY 
								QTY DESC
							LIMIT 10;""",({"from_date":str(from_date),"to_date":str(to_date)}),as_dict=1)
		data = [d for d in data if d.get('item_name') is not None]
	return data
	

	
def get_columns_for_customers(filters):
	columns = [
		 {
			"label":_("Customer Name"),
			"fieldname": "customer_name",      
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label":_("QTY"),
			"fieldname": "total_quantity",
			"fieldtype": "Float",          
			"width": 200,
		},
		{
			"label":_("Amount"),
			"fieldname": "total_amount",
			"fieldtype": "Float",          
			"width": 200,
		}
		]
	
	return columns


def get_columns_for_product(filters):
	columns = [
		 {
			"label":_("Item Name"),
			"fieldname": "item_name",       
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label":_("QTY"),
			"fieldname": "QTY",
			"fieldtype": "Float",          
			"width": 200,
		},
		{
			"label":_("Amount"),
			"fieldname": "AMOUNT",
			"fieldtype": "Float",        
			"width": 200,
		}
		]
	
	return columns

#this function is used to create chart for customer(top 10)
def get_chart_data_for_customers(data):
    if not data:
        return None
    
    labels = []
    amount = []
    qty = []
    
    for i in data:
        labels.append(i.get('customer_name'))
        amount.append(i.get('total_amount'))
        qty.append(i.get('total_quantity'))
    
    datasets = [
        {
            'name': 'Amount',
            'type': 'bar',
            'values': amount,
            'bar_percentage': 0.6,
            'yaxis': 'y'
        },
        {
            'name': 'Quantity',
            'type': 'bar',
            'values': qty,
            'bar_percentage': 0.6,  # Adjust as needed
            'yaxis': 'y2'
        }
    ]
    
    chart = {
        'data': {
            'labels': labels,
            'datasets': datasets
        },
        'type': 'bar',
        'height': 300
    }
    
    return chart


#this function is used to create chart for products(top 10)
def get_chart_data_for_products(data):
    if not data:
        return None
    
    labels = []
    amount = []
    qty = []
    
    for i in data:
        labels.append(i.get('item_name'))
        amount.append(i.get('AMOUNT'))
        qty.append(i.get('QTY'))
    
    datasets = [
        {
            'name': 'Amount',
            'type': 'bar',
            'values': amount,
            'bar_percentage': 0.6,
            'yaxis': 'y'
        },
        {
            'name': 'Quantity',
            'type': 'bar',
            'values': qty,
            'bar_percentage': 0.6,  # Adjust as needed
            'yaxis': 'y2'
        }
    ]
    
    chart = {
        'data': {
            'labels': labels,
            'datasets': datasets
        },
        'type': 'bar',
        'height': 300
    }
    
    return chart