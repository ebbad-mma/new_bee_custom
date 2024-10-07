// Copyright (c) 2024, yog and contributors
// For license information, please see license.txt

frappe.ui.form.on('Amazon Pricing Rule', {
	// refresh: function(frm) {

	// }
});



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