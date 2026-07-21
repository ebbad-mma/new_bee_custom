frappe.provide('frappe.views');

frappe.ready(function() {
    if (frappe.views.DashboardView) {
        let original_setup_page = frappe.views.DashboardView.prototype.setup_page;
        frappe.views.DashboardView.prototype.setup_page = function() {
            original_setup_page.call(this);
            
            // In DashboardView, this.doctype holds the dashboard name (e.g. 'Sales Analysis')
            if (this.doctype === 'Sales Analysis') {
                let view = this;
                
                // Add a "Set Filters" button to match the v14 layout
                this.page.add_inner_button(__('Set Filters'), function() {
                    if (!view.master_filter_dialog) {
                        view.master_filter_dialog = new frappe.ui.Dialog({
                            title: __('Set Default Filters'),
                            fields: [
                                {
                                    label: 'From Date',
                                    fieldname: 'master_from_date',
                                    fieldtype: 'Date',
                                    reqd: 1,
                                    default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
                                },
                                {
                                    label: 'To Date',
                                    fieldname: 'master_to_date',
                                    fieldtype: 'Date',
                                    reqd: 1,
                                    default: frappe.datetime.get_today()
                                },
                                {
                                    label: 'Limit',
                                    fieldname: 'master_limit',
                                    fieldtype: 'Int',
                                    reqd: 1,
                                    default: 5
                                }
                            ],
                            primary_action_label: __('Set'),
                            primary_action: (values) => {
                                update_dashboard_charts(view, values);
                                view.master_filter_dialog.hide();
                            }
                        });
                    }
                    view.master_filter_dialog.show();
                });
            }
        };

        let original_render_dashboard_charts = frappe.views.DashboardView.prototype.render_dashboard_charts;
        frappe.views.DashboardView.prototype.render_dashboard_charts = function() {
            original_render_dashboard_charts.call(this);
            
            if (this.doctype === 'Sales Analysis') {
                // Initialize default values on page load
                setTimeout(() => {
                    let default_values = {
                        master_from_date: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
                        master_to_date: frappe.datetime.get_today(),
                        master_limit: 5
                    };
                    update_dashboard_charts(this, default_values);
                }, 1000);
            }
        };
    }
});

function update_dashboard_charts(view, values) {
    let from_date = values.master_from_date;
    let to_date = values.master_to_date;
    let limit = values.master_limit;
    
    if (from_date && to_date && view.chart_group && view.chart_group.widgets) {
        view.chart_group.widgets.forEach(widget => {
            if (widget.chart_doc && widget.fetch) {
                // If it's a Report chart, it expects filters on the widget.filters object
                if (widget.chart_doc.chart_type === 'Report') {
                    if (!widget.filters) widget.filters = {};
                    widget.filters.from_date = from_date;
                    widget.filters.to_date = to_date;
                    if (limit) widget.filters.limit = limit;
                    widget.fetch_and_update_chart();
                } else {
                    // For standard charts, we pass the custom filters in the args object
                    let args = { 
                        from_date: from_date, 
                        to_date: to_date,
                        limit: limit
                    };
                    widget.fetch(widget.filters, true, args).then(() => {
                        widget.update_chart_object();
                    });
                }
            }
        });
    }
}
