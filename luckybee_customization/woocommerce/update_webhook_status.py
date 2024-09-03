import frappe
from luckybee_customization.woocommerce.publish_item import get_woocommerce_settings
from frappe.utils import cint
from woocommerce import API
# Erp@123#456


def update_webhook_status():
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
        "status": "active"  # Change webhook status to 'disabled'
    }

    # Example: Update a specific webhook (change '7' to your desired webhook ID)
    webhook_id = 8
    response = wcapi.put(f"webhooks/{webhook_id}", data).json()

    # Example: Logging response
    frappe.log_error("Webhook_status_update", f"{response}")

    return "Success: status update"


#run by scheduler
def update_webhook_status_by_scheduler():
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
        "status": "active"  # Change webhook status to 'disabled'
    }

    # Example: Update a specific webhook (change '7' to your desired webhook ID)
    webhook_id = 8
    response = wcapi.get(f"webhooks/{webhook_id}").json()
    frappe.throw(f"{response}")
    before_change=response
    if response:
        status=response['status']
        if status!='active':
            response = wcapi.put(f"webhooks/{webhook_id}", data).json()
    # Example: Logging response
    frappe.log_error("Webhook_status_update_SCHE", f"BEFORE CHANGE--->{before_change} \n AFTER CHANGE ---->{response} \n TIME----> {frappe.utils.now()}")

    return "Success: status update"