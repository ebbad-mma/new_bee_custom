// Copyright (c) 2024, yog and contributors
// For license information, please see license.txt

frappe.ui.form.on('Amazon Pricing Rule', {
    refresh: function(frm) {
      frm.add_custom_button('Reset Table', () => {
        // Clear the existing rows in the amazon_pricing child table
        frm.clear_table('amazon_pricing');
  
        // Iterate through the default_amazon_price_rule and add the rows to amazon_pricing
        frm.doc.default_amazon_price_rule.forEach(row => {
          let newRow = frm.add_child('amazon_pricing');
          Object.assign(newRow, row);
        });
  
        // Refresh the field to display the updated table
        frm.refresh_field('amazon_pricing');
  
        // Save the form to persist the changes
        frm.save();
      });
    }
  });
  


// Function for child table
frappe.ui.form.on('Amazon Pricing', {
    lower_purchase_price_as__of_online_price: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
		setRangeDisplay(frm,row,cdt,cdn)
    },
    upper_purchase_price_as__of_online_price: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
		setRangeDisplay(frm,row,cdt,cdn)
    }
});






// HELPER FUNCTION TO MAKE RANGR OF UPPER LIMIT AND LOWER LIMIT 
function setRangeDisplay(frm,row,cdt,cdn) {
    const upperLimit = row.upper_purchase_price_as__of_online_price;
    const lowerLimit =row.lower_purchase_price_as__of_online_price;

    if (upperLimit && lowerLimit) {
		let range= `${lowerLimit} to ${upperLimit}`
		frappe.model.set_value(cdt, cdn, 'range_purchase_price_as__of_online_price', range);
    } 
}