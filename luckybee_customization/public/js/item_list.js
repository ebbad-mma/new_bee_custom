frappe.listview_settings['Item'] = {
    onload: function(listview) {
        listview.page.add_inner_button(__('Received, Not Documented'), function() {
            listview.filter_area.clear();
            listview.filter_area.add([
                ['Item', 'lb_data_status', 'in', ['Needs Receiving Capture', 'Partial']]
            ]);
        });
    }
};
