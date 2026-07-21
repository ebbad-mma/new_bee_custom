frappe.provide('frappe.views');

frappe.ready(function() {
    if (frappe.views.DashboardView) {
        let original_setup_page = frappe.views.DashboardView.prototype.setup_page;
        frappe.views.DashboardView.prototype.setup_page = function() {
            if (this.doctype === 'Sales Analysis') {
                this.hide_page_form = false;
                console.log("Dashboard master filter initializing for Sales Analysis!");
            }
            
            original_setup_page.call(this);
            
            // In DashboardView, this.doctype holds the dashboard name (e.g. 'Sales Analysis')
            if (this.doctype === 'Sales Analysis') {
                if (this.page && this.page.page_form) {
                    this.page.page_form.removeClass('hide');
                    console.log("Removed hide class from page_form");
                }
                
                let view = this;
                
                // Add custom fields
                this.page.add_field({
                    fieldname: 'master_from_date',
                    label: __('From Date'),
                    fieldtype: 'Date',
                    default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
                    change: function() {
                        update_dashboard_charts(view);
                    }
                });
                
                this.page.add_field({
                    fieldname: 'master_to_date',
                    label: __('To Date'),
                    fieldtype: 'Date',
                    default: frappe.datetime.get_today(),
                    change: function() {
                        update_dashboard_charts(view);
                    }
                });
            }
        };

        let original_render_dashboard_charts = frappe.views.DashboardView.prototype.render_dashboard_charts;
        frappe.views.DashboardView.prototype.render_dashboard_charts = function() {
            original_render_dashboard_charts.call(this);
            
            if (this.doctype === 'Sales Analysis') {
                // Trigger initial fetch
                setTimeout(() => {
                    update_dashboard_charts(this);
                }, 500);
            }
        };
    }
});

function update_dashboard_charts(view) {
    if (!view.page.fields_dict.master_from_date || !view.page.fields_dict.master_to_date) return;
    
    let from_date = view.page.fields_dict.master_from_date.get_value();
    let to_date = view.page.fields_dict.master_to_date.get_value();
    
    if (from_date && to_date && view.chart_group && view.chart_group.widgets) {
        view.chart_group.widgets.forEach(widget => {
            if (widget.chart_doc && widget.fetch) {
                if (widget.chart_doc.chart_type === 'Report') {
                    if (!widget.filters) widget.filters = {};
                    widget.filters.from_date = from_date;
                    widget.filters.to_date = to_date;
                    widget.fetch_and_update_chart();
                } else {
                    let args = { from_date: from_date, to_date: to_date };
                    widget.fetch(widget.filters, true, args).then(() => {
                        widget.update_chart_object();
                    });
                }
            }
        });
    }
}
