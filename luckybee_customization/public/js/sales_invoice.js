// Triggered when the 'item_code' field is changed in the 'Sales Invoice Item' child table
frappe.ui.form.on('Sales Invoice Item', {
    item_code: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        // Fetch the custom MRP of the selected item
        frappe.db.get_value('Item', row.item_code, 'custom_mrp').then(r => {
            if (r.message) {
                console.log(r.message.custom_mrp);
                frappe.model.set_value(cdt, cdn, 'custom_mrp', r.message.custom_mrp);
                
                // Recalculate the total MRP whenever an item is selected or its MRP is updated
                calculate_total_mrp(frm);
            }
        });
    },items_add: function(frm) {
        calculate_total_mrp(frm);
    },
    items_remove: function(frm) {
        calculate_total_mrp(frm);
    }
});


// Function to calculate the total MRP for all items
function calculate_total_mrp(frm) {
    let total_mrp = 0;

    // Loop through each row in the items child table
    frm.doc.items.forEach(row => {
        if (row.custom_mrp) {
            total_mrp += parseFloat(row.custom_mrp);
        }
    });

    // Set the recalculated total MRP
    frm.set_value('custom_total_mrp', total_mrp);
    frm.refresh_field('items'); // Refresh the child table field to ensure it's updated
}
