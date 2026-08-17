app_name = "luckybee_customization"
app_title = "Luckybee Customization"
app_publisher = "yog"
app_description = "ITEMS"
app_email = "yog@solutions.com"
app_license = "mit"
# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/luckybee_customization/css/luckybee_customization.css"
app_include_js = [
    "/assets/luckybee_customization/js/dashboard_master_filter.js",
    # Read-only product lookup - loaded across Desk so staff can scan from
    # wherever they happen to be (Ctrl/Cmd+Shift+F).
    "/assets/luckybee_customization/js/scan_lookup.js",
]

# include js, css files in header of web template
# web_include_css = "/assets/luckybee_customization/css/luckybee_customization.css"
# web_include_js = "/assets/luckybee_customization/js/luckybee_customization.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "luckybee_customization/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}
page_js = {
    # Adds the "Show UPI QR" button to ERPNext's own POS payment screen.
    "point-of-sale": "public/js/pos_upi_qr.js"
}

# include js in doctype views
doctype_js = {
    "Purchase Invoice" : "public/js/purchase_invoice.js",
    "Item" : "public/js/item.js",
    'Goods Received Note - GRN' : "public/js/Grn.js",
    'Item Details' : "public/js/item_details.js",
    'Supplier Quotation' : "public/js/supplier_quotation.js",
    'Sales Invoice' : "public/js/sales_invoice.js"
}
doctype_list_js = {
    "Item": "public/js/item_list.js"
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "luckybee_customization/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# The product label needs a server-rendered barcode, which the restricted Jinja
# sandbox in print formats cannot produce on its own.
jinja = {
	"methods": [
		"luckybee_customization.jinja_methods.lb_label_data",
		"luckybee_customization.jinja_methods.lb_barcode_svg",
	]
}

# Installation
# ------------

# before_install = "luckybee_customization.install.before_install"
# after_install = "luckybee_customization.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "luckybee_customization.uninstall.before_uninstall"
# after_uninstall = "luckybee_customization.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "luckybee_customization.utils.before_app_install"
# after_app_install = "luckybee_customization.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "luckybee_customization.utils.before_app_uninstall"
# after_app_uninstall = "luckybee_customization.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "luckybee_customization.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
    "cron": {
        "0 */2 * * *": [
            "luckybee_customization.woocommerce.update_webhook_status.update_webhook_status_by_scheduler"
        ]
    },
    "daily": [
        "luckybee_customization.jobs.refresh_velocity",
        # B4 - "Stale" is an age-based state that becomes true with the passage
        # of time, so it needs a sweep rather than being decided at sync time.
        "luckybee_customization.jobs_keepa.flag_stale_amazon_data"
    ],
    "hourly": [
        "luckybee_customization.overrides.item_utils.update_item_in_woocom",
        # B2 - drains the ASIN-matched backlog a bounded batch at a time. Keepa
        # refills at a fixed token rate, so a full sweep spans many hours; this
        # is resumable by design and stops cleanly when tokens run low.
        "luckybee_customization.jobs_keepa.bulk_keepa_sync_scheduled"
    ]
}

# Testing
# -------

# before_tests = "luckybee_customization.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "luckybee_customization.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "luckybee_customization.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["luckybee_customization.utils.before_request"]
# after_request = ["luckybee_customization.utils.after_request"]

# Job Events
# ----------
# before_job = ["luckybee_customization.utils.before_job"]
# after_job = ["luckybee_customization.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"luckybee_customization.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

doc_events = {
    "Item": {
		"before_save": [
			"luckybee_customization.overrides.item.sync_keepa_item",
			"luckybee_customization.item_hooks.calculate_margins",
			"luckybee_customization.item_hooks.validate_role_field_permissions",
			"luckybee_customization.receiving.recompute_status"
		],
		"on_update": "luckybee_customization.overrides.item_utils.check_image"
        },
        "Purchase Receipt": {
		"on_submit": "luckybee_customization.receiving.flag_items"
        },
        "Purchase Invoice": {
		"on_submit": "luckybee_customization.overrides.bin.update_stock_in_hand",
		"before_submit": "luckybee_customization.overrides.bin.set_warehouse_and_update_stock",
		"on_update": "luckybee_customization.overrides.bin.enqueue_create_item_price"
        },
        "Sales Invoice": {
		# 5.3 - on validate, not on_submit: the cashier should be stopped while
		# the bill is still open and fixable, not as they take payment.
		"validate": "luckybee_customization.api.pos_attribution.require_salesperson",
		"on_submit": "luckybee_customization.overrides.sales_invoice.update_stock_in_hand_in_item_master_on_si_submit"
        },
        "Purchase Order": {
		"on_submit": "luckybee_customization.overrides.purchase_order.remove_unselected_item_from_item_master"
        }
        # "Branch": {
		# "validate": "luckybee_customization.overrides.test.test"
		# # "validate": "luckybee_customization.woocommerce.test2.test"
        # }
    }





fixtures = [
     {
        "dt": "Custom Field",
        "or_filters": [
            [
                "module", "in", ["luckybee_customization"]
            ],
            [
                "dt", "=", "Item"
            ]
        ]
    },
     {
        "dt": "Property Setter",
        "or_filters": [
            [
                "module", "in", ["luckybee_customization"]
            ],
            [
                "doc_type", "=", "Item"
            ]
        ]
    },
     {
        "dt": "Amazon Pricing Rule"
        
    },
      {
        "dt": "Web Form",
        "filters": [
            ["name", "in", ["photos-floor-staff", "product-info-trusted-staff", "asin-matching-staff", "count-stock-take-staff", "all-in-one-owner-supervisor"]]
        ]
      }
    ]
