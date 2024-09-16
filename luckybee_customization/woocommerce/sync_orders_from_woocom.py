import frappe
import json
from woocommerce import API
from frappe.utils import cint
from luckybee_customization.woocommerce.update_webhook_status import update_webhook_status
from luckybee_customization.woocommerce.publish_item import get_woocommerce_settings
from frappe import _


#luckybe pass=Erp@123#456
#find customer by email or phone
def customer_by_email_or_phone(email,phone):
	settings = get_woocommerce_settings()
	
	# Check SSL verification setting
	verify_ssl = cint(settings.get('verify_ssl', 1))

	# Initialize WooCommerce API connection
	wcapi = API(
		url=settings['woocommerce_url'],
		consumer_key=settings['api_key'],
		consumer_secret=settings['api_secret'],
		verify_ssl=verify_ssl,
		wp_api=True,
		version="wc/v3",
		timeout=1000
	)	
	if email is not None:
		response = wcapi.get(f"customers?email={email}").json()
	else:
		response = wcapi.get(f"customers?phone={email}").json()
	return response


@frappe.whitelist(allow_guest=True)
def get_orders():
	frappe.log_error("yes i am syncing order")
	try:
		frappe.log_error(f"ORDER CREATED in woocom {frappe.utils.now()}")
		response = frappe.request.data
		response = json.loads(response)
		frappe.log_error("Response data", response)
		billing_details = response['billing']

		# Create customer
		woo_customer = customer_by_email_or_phone(billing_details['email'], billing_details['phone'])
		frappe.log_error(f"cus {woo_customer[0]['id']} {billing_details['email']}-{frappe.utils.now()}")
		try:
			if woo_customer:
				cus_id = woo_customer[0]['id']
				erp_customer = frappe.db.exists('Customer', {'woocommerce_customer_id': cus_id})
				if erp_customer:
					erp_customer = frappe.get_doc('Customer', {'woocommerce_customer_id': cus_id})
					erp_customer.customer_name = billing_details['first_name'] + " " + billing_details['last_name']
					erp_customer.woocommerce_customer_id = cus_id
					erp_customer.save()
					frappe.log_error("customer updated")
				else:
					frappe.log_error("Start customer creation")
					customer_doc = frappe.new_doc("Customer")
					customer_doc.customer_name = billing_details['first_name'] + " " + billing_details['last_name']
					customer_doc.woocommerce_customer_id = cus_id
					customer_doc.customer_group = 'All Customer Groups'
					customer_doc.territory = 'India'
					customer_doc.insert(ignore_permissions=True)
					frappe.log_error("Customer created")
		except Exception as e:
			frappe.log_error(f"Error in customer creation or update: {str(e)}")

		try:
			if not frappe.db.exists('Address', {'woocommerce_id': cus_id}):
				# Create customer address
				frappe.log_error("Start customer address creation")
				cus_ads = frappe.new_doc('Address')
				cus_ads.address_type = 'Billing'
				cus_ads.woocommerce_id = cus_id
				cus_ads.address_line1 = billing_details['address_1']
				cus_ads.address_line2 = billing_details['address_2']
				cus_ads.city = billing_details['city']
				# cus_ads.state = billing_details['state']
				cus_ads.state = 'Madhya Pradesh'
				cus_ads.pincode = billing_details['postcode']
				cus_ads.phone = billing_details['phone']
				cus_ads.email_id = billing_details['email']
				if billing_details['country'] == 'IN':
					cus_ads.country = 'India'
				cus_ads.append('links', {'link_doctype': 'Customer', 'link_name': billing_details['first_name'] + " " + billing_details['last_name']})
				cus_ads.insert(ignore_permissions=True)
				frappe.log_error("Address created")
			else:
				cus_ads = frappe.get_doc('Address', {'woocommerce_id': cus_id})
				cus_ads.address_type = 'Billing'
				cus_ads.custom_woocommerce_customer_id = cus_id
				cus_ads.address_line1 = billing_details['address_1']
				cus_ads.address_line2 = billing_details['address_2']
				cus_ads.city = billing_details['city']
				# cus_ads.state = billing_details['state']
				cus_ads.state = 'Madhya Pradesh'
				cus_ads.pincode = billing_details['postcode']
				cus_ads.phone = billing_details['phone']
				cus_ads.email_id = billing_details['email']
				if billing_details['country'] == 'IN':
					cus_ads.country = 'India'
				cus_ads.append('links', {'link_doctype': 'Customer', 'link_name': billing_details['first_name'] + " " + billing_details['last_name']})
				cus_ads.save()
				frappe.log_error("Address updated")
		except Exception as e:
			frappe.log_error(f"Error in address creation or update: {str(e)}")

		try:
			# Create sales order
			frappe.log_error("Start sales order creation")
			sales_order = frappe.new_doc("Sales Invoice")
			sales_order.customer = billing_details['first_name'] + " " + billing_details['last_name']
			sales_order.custom_payment_request_url = response.get('payment_url')
			# sales_order.base_grand_total = 0
			# sales_order.grand_total = 0
			payment_method = response.get('payment_method')
			if payment_method=='cod':
				sales_order.custom_payment_method ='Cash'
				# sales_order.append('Payments',{'mode_of_payment':'Cash','amount':})

			for item_details in response['line_items']:
				try:
					item_image_url = item_details.get('image', {}).get('src')
					asin_value = None
					for meta in item_details.get('meta_data', []):
						if meta.get('key') == '_amz_asin':
							asin_value = meta.get('value')
							break 
					if not frappe.db.exists('Item', {'item_name': item_details['name']}):
						item_doc = frappe.new_doc("Item")
						item_doc.item_group = "All Groups"
						item_doc.item_code = item_details['name']
						item_doc.item_name = item_details['name']
						item_doc.woocommerce_product_id = item_details['product_id']
						if item_image_url:
							item_doc.image = item_image_url
						if asin_value:
							item_doc.custom_asin_no = asin_value
						item_doc.insert(ignore_permissions=True)
						
					else:
						item_doc = frappe.get_doc('Item', {'item_name': item_details['name']})
						if item_image_url:
							item_doc.image = item_image_url
						if asin_value:
							item_doc.custom_asin_no = asin_value
						item_doc.save()
				except Exception as e:
					frappe.log_error(f"Error in processing item {item_details['name']}: {str(e)}")
			sales_order.append('items', {
			'item_code': item_doc.item_code,
			'qty': item_details['quantity'],
			'rate': item_details['price'],
			'amount': item_details['total'],
			'image': item_image_url})
			due_date = ""
			for data in response['meta_data']:
				if data['key'] == 'pickup_date':
					due_date = data['value']
					sales_order.due_date = frappe.utils.getdate(due_date)
				else:
					sales_order.due_date = frappe.utils.getdate()
			frappe.log_error("delivery date", due_date)
			sales_order.insert(ignore_permissions=True, ignore_mandatory=True)
			frappe.log_error("Order creation", f'{response}')
			update_webhook_status()
		except Exception as e:
			frappe.log_error(f"Error in sales order creation: {str(e)}")

	except Exception as e:
		frappe.log_error(f"Error in get_orders: {str(e)}")
		update_webhook_status()


@frappe.whitelist(allow_guest=True)
def update_order():
	try:
		response = frappe.request.data
		frappe.log_error("Order updated", f"{response}")
	except Exception as e:
		frappe.log_error(f"Error in update_order: {str(e)}")

		