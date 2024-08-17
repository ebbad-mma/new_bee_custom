import frappe
from luckybee_customization.woocommerce.publish_item import get_woocommerce_settings
from frappe.utils import cint
from woocommerce import API


def test(doc,method=None):
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

    # Example data for webhook update
    data = {
        "status": "active",
        "delivery_url":'https://bee.tranqwality.com/api/method/luckybee_customization.luckybee_customization.woocommerce.sync_orders_from_woocom.get_orders'
    }

    # Example: Update a specific webhook (change '7' to your desired webhook ID)
    webhook_id = 7
    # response = wcapi.put(f"webhooks/{webhook_id}", data).json()
    response = wcapi.get(f"webhooks/{webhook_id}").json()
    frappe.throw(f"{response}")

    # Example: Logging response
    frappe.log_error("Webhook_status_update", f"{response}")

    return "Success: status update"