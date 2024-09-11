// Copyright (c) 2024, bizmap technologies pvt ltd and contributors
// For license information, please see license.txt

// frappe.ui.form.on('Product Finder', {
// 	refresh(frm) {
// 		// your code here
// 	}
// })

// frappe.ui.form.on('Product Finder Response', {
// 	create_item(frm, cdt,cdn) {
// 		var row =  locals[cdt][cdn];

// 		if (frm.doc.item){
// 			frappe.call({
// 				args: {
// 					item : frm.doc.item,
// 					asin: row.asin_no
// 				},
// 				method: "luckybee_customization.luckybee_customization.doctype.product_finder.update_item_pf.update_item",
// 				callback: function(r){
// 					frappe.set_route("Form", "Item", frm.doc.item)
// 				}
// 			})
// 		}
// 		else{
// 			frappe.new_doc("Item", {custom_asin_no : row.asin_no, item_group: 'All Item Groups'});			
// 		}
		
// 	}
// })


frappe.ui.form.on('Product Finder', {
    create_selected_items: function(frm) {
            let selected = frm.get_selected();
			let item_to_be_update=frm.doc.item
            console.log("Selected rows:", selected);

            // Check if any rows are selected
            if (selected.product_finder_response && selected.product_finder_response.length > 0 && selected.product_finder_response && selected.product_finder_response.length ===1) {
                let itemName = selected.product_finder_response.map(row_name => {
                    let row = locals['Product Finder Response'][row_name];
                    console.log("bb",row.asin_no)
                    return row.title;
                });
                console.log("Box Numbers:",itemName);
				
                // Filter the items to remove those that do not have the same box number
                let items_to_keep = frm.doc.product_finder_response.filter(item => {
					return itemName.includes(item.title);
					});
					let titles = items_to_keep.map(item => item.title);
					frm.set_value('selected_item',titles[0])
					console.log("tit",titles[0])
				// let selected_item=items_to_keep['']
               console.log("create item",items_to_keep)
			   frappe.call({
				method: 'luckybee_customization.overrides.product_finder.update_item',
				args: {
					create_items:items_to_keep,
					selected_item:titles,
					item_to_be_update:item_to_be_update || ""},
				// disable the button until the request is completed
				btn: $('.primary-action'),
				// freeze the screen until the request is completed
				freeze: true,
				callback: (r) => {
					// on success
					console.log(r.message.item_name,"lll")
					// cur_frm.save()
					frappe.set_route('Form','Item',r.message.item_name)
					window.location.reload()
				},
				error: (r) => {
					// on error
				}
			})
            }
			else if (selected.product_finder_response && selected.product_finder_response.length > 1){frappe.throw("You can create only one item. Please select a single item.")}
             else {
                frappe.throw("Please First Select Any Item")
            }
        
    }
});