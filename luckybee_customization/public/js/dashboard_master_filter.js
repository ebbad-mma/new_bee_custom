$(document).on('page-change', function() {
    let route = frappe.get_route();
    if (route[0] === 'dashboard-view' && route[1] === 'Sales Analysis') {
        setTimeout(function() {
            let view = frappe.container.page.page_view;
            if (!view || !view.page) return;

            // In Frappe 15/16, Dashboard View hides page_form. We unhide it.
            if (view.page.page_form) {
                view.page.page_form.removeClass('hide');
            }

            // Add custom fields if not already added
            if (!view.page.fields_dict.master_from_date) {
                view.page.add_field({
                    fieldname: 'master_from_date',
                    label: __('From Date'),
                    fieldtype: 'Date',
                    default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
                    change: function() {
                        update_dashboard_charts(view);
                    }
                });
                view.page.add_field({
                    fieldname: 'master_to_date',
                    label: __('To Date'),
                    fieldtype: 'Date',
                    default: frappe.datetime.get_today(),
                    change: function() {
                        update_dashboard_charts(view);
                    }
                });
                
                // trigger initial fetch with defaults
                setTimeout(() => update_dashboard_charts(view), 500);
            }
        }, 200); // Wait for page to initialize
    }
});

function update_dashboard_charts(view) {
    let from_date = view.page.fields_dict.master_from_date.get_value();
    let to_date = view.page.fields_dict.master_to_date.get_value();
    
    if (from_date && to_date && view.chart_group && view.chart_group.widgets) {
        view.chart_group.widgets.forEach(widget => {
            if (widget.chart_doc && widget.fetch) {
                // If it's a Report chart, it expects filters.from_date
                if (widget.chart_doc.chart_type === 'Report') {
                    if (!widget.filters) widget.filters = {};
                    widget.filters.from_date = from_date;
                    widget.filters.to_date = to_date;
                    widget.fetch_and_update_chart();
                } else {
                    // For standard charts, we can pass args
                    let args = { from_date: from_date, to_date: to_date };
                    widget.fetch(widget.filters, true, args).then(() => {
                        widget.update_chart_object();
                    });
                }
            }
        });
    }
}
