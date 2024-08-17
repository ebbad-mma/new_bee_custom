import frappe
from woocommerce import API
import traceback

def get_woocommerce_settings():
    # Replace with your method to retrieve WooCommerce settings
    d = frappe.get_doc("WooCommerce Config")
    
    if d.woocommerce_url:
        d.api_secret = d.get_password(fieldname='api_secret')
        return d.as_dict()
    else:
        frappe.throw(_("WooCommerce store URL is not configured in WooCommerce Config"), woocommerceError)

def create_order(order_data):
    # Get WooCommerce settings
    settings = get_woocommerce_settings()
    
    # Initialize WooCommerce API connection
    wcapi = API(
        url=settings['woocommerce_url'],
        consumer_key=settings['api_key'],
        consumer_secret=settings['api_secret'],
        wp_api=True,
        version="wc/v3",
        timeout=1000
    )
    
    try:
        # Make POST request to create order
        response = wcapi.post("orders", order_data)

        # Check for successful response (2xx status code)
        if response.status_code == 201:
            frappe.log_error("ORDER CREATION SUCCESS", f"Order created successfully. Response: {response}")
            return "Success: Order created"
        else:
            frappe.log_error("ORDER CREATION FAILED", f"Failed to create order. Response: {response}")
            return f"Error: Failed to create order. Response: {response}"

    except Exception as e:
        frappe.log_error("ORDER CREATION EXCEPTION", f"Exception occurred: {traceback.format_exc()}")
        return f"Error: Exception occurred during order creation: {str(e)}"

order_data = {
    'payment_method': 'cod',
    'payment_method_title': 'Pay At Store',
    'set_paid': False,
    'billing': {
        'first_name': 'Yog Solutions Test',
        'last_name': 'Com',
        'address_1': 'Appolllo Test',
        'city': 'Indore',
        'state': 'MP',
        'postcode': '452001',
        'country': 'IN',
        'email': '01saloniradhvi@gmail.com',
        'phone': '9926175767'
    },
    'shipping': {
        'first_name': '',
        'last_name': '',
        'address_1': '',
        'city': '',
        'state': '',
        'postcode': '',
        'country': ''
    },
    'line_items': [
        {
            'product_id': 25594,
            'quantity': 1,
            'price': 253.38983,
            'name': 'Kuber Industries 6.5 Ltr Plastic Press-Top, Step-On Push &amp; Pedal Dustbin For Home, Kitchen, Office And Bathroom Garbage…',
            'sku': 'B092DPBB8P',
            'subtotal': '253.39',
            'subtotal_tax': '45.62',
            'total': '253.39',
            'total_tax': '45.62',
            'image': {
                'src': 'https://luckybee.in/wp-content/uploads/2022/06/Kuber-Industries-65-Ltr-Plastic-Push-Pedale-Dustbin-For-Home-Kitchen-Office-And-Bathroom-Garbage-With-LidSetof-2-Black-Cream-0.jpg'
            }
        },
        {
            'product_id': 28522,
            'quantity': 1,
            'price': 209,
            'name': 'Cello Water Bottle Splash FlipTop set, 1000ml, set of 2 PIECES',
            'sku': 'B074KBMYNT',
            'subtotal': '209.00',
            'subtotal_tax': '0.00',
            'total': '209.00',
            'total_tax': '0.00',
            'image': {
                'src': 'https://luckybee.in/wp-content/uploads/2022/06/Cello-Water-Bottle-Splash-FlipTop-set-1000ml-set-of-2-PIECES-0.jpg'
            }
        },
        {
            'product_id': 28133,
            'quantity': 1,
            'price': 2399,
            'name': 'Lifelong Glass Top Gas Stove, 4 Burner Gas Stove, Black (ISI Certified,1 year warranty with Doorstep Service)',
            'sku': 'B077XB2ZZM',
            'subtotal': '2399.00',
            'subtotal_tax': '0.00',
            'total': '2399.00',
            'total_tax': '0.00',
            'image': {
                'src': 'https://luckybee.in/wp-content/uploads/2022/06/Lifelong-Glass-Top-Gas-Stove-4-Burner-Gas-Stove-Black-ISI-Certified1-year-warranty-with-Doorstep-Service-0.jpg'
            }
        }
    ],
    'shipping_lines': [],
    'fee_lines': [],
    'coupon_lines': [],
    'meta_data': [
        {'key': 'is_vat_exempt', 'value': 'no'},
        {'key': 'delivery_type', 'value': 'pickup'},
        {'key': 'pickup_date', 'value': '2024-07-09'},
        {'key': 'pickup_time', 'value': '10:00 - 10:05'}
    ],
    'customer_id': 339,
    'discount_total': '0.00',
    'shipping_total': '0.00',
    'total': '2907.01'
}
# Create the order using the provided data
def test(doc,method=None):
    create_order(order_data)