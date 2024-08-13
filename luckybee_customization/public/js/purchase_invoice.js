frappe.ui.form.on('Purchase Invoice', {
    custom_search_and_insert_item(frm,cdt,cdn) {
        let purchase =frm.doc.custom_custom_purchase_item;
            if (purchase[0].custom_box_number || purchase[0].custom_asin || purchase[0].custom_ean){frm.doc.custom_is_asin =1}
            else if (purchase[0].custom_fsn){frm.doc.custom_is_fsn =1}
            else { 
                // frm.doc.custom_non_asin =1
                frm.set_value("custom_non_asin",1)
            
            }

       if(!frm.doc.supplier){frappe.msgprint('Please select supplier')}
        else if (frm.doc.custom_custom_purchase_item) {
            cur_frm.clear_table("items");
            

            if (frm.doc.custom_is_asin === 1) {
                // fetch is it enable or disable
                for (let obj of frm.doc.custom_custom_purchase_item) {
                        frappe.call({
                            method: "luckybee_customization.overrides.asin_purchase_invoice.search_and_insert_item",
                            args: {
                                'doc': frm.doc,
                                'description': obj.description_of_good_and_services,
                                'hsn': obj.hsnsac != null ? obj.hsnsac : "",
                                'qty': obj.quantity != null ? obj.quantity : 0,
                                'rate': obj.rate != null ? obj.rate : 0,
                                'per': obj.per != null ? obj.per : "",
                                // 'disc_perc': obj.disc_ != null ? obj.disc_ : "",
                                // 'disc': obj.disc != null ? obj.disc : "",
                                // 'gst': obj.gst != null ? obj.gst : "",
                                'mrp': obj.mrp != null ? obj.mrp :0,
                                'lrp': obj.lrp != null ? obj.lrp : "",
                                'brand': obj.brand != null ? obj.brand : "",
                                'group': obj.group != null ? obj.group : "",
                                'category': obj.category != null ? obj.category : "",
                                'sub_category': obj.sub_category != null ? obj.sub_category : "",
                                'custom_asin': obj.custom_asin != null ? obj.custom_asin : "",
                                'custom_box_number': obj.custom_box_number != null ? obj.custom_box_number : "",
                                "custom_ean": obj.custom_ean != null ? obj.custom_ean : "",
                                "disc": obj.disc != null ? flt(obj.disc) : 0

                            },
                            freeze: true,
                            freeze_message: "loading items...",
                            callback: function (r) {
                                if (r.message) {
                                    var item_row = cur_frm.add_child("items");
                                    item_row.item_code = r.message.item_code;
                                    item_row.item_name = r.message.item_name;
                                    item_row.qty = r.message.qty;
                                    item_row.uom = r.message.uom;
                                    item_row.rate = r.message.rate;
                                    item_row.amount = r.message.amount;
                                    item_row.custom_reviewsrating = r.message.reviews_rating;
                                    item_row.custom_reviews_count = r.message.custom_reviews_count;
                                    item_row.custom_last_purchase_rate=r.message.last_purchase_rate
                                    item_row.custom_new_current = r.message.new_current;
                                    item_row.custom_mrp=r.message.mrp;
                                    item_row.custom_box_number = r.message.custom_box_number;
                                    item_row.custom_asin = r.message.custom_asin;
                                    item_row.custom_ppmumrpdap='PASP'
                                    calculate_lrp_and_apply_discount(frm,cdt,cdn,item_row)
    
                                    // item_row.rate = r.message.rate;
                                    cur_frm.refresh_fields("items");
                                    for (let item of cur_frm.doc.custom_custom_purchase_item) {
                                        if (item.description_of_good_and_services === r.message.item_name) {
                                            item.custom_reviewsrating = r.message.reviews_rating;
                                        }
                                    }
                                }
                            }
                        });
                    }
                    let fi = frm.doc.custom_custom_purchase_item[0];
                    if (fi.custom_asin == null && fi.custom_ean == null) {
                        let fields = [];
                    }
                
               }
                
                
            // ---------------------------------fsn code------------------------------------------
            else if(frm.doc.custom_fsn===1){frappe.msgprint("FSN")}
            
        //    ------------------------------------------------------- non asin code-----------------------------------------------------------------------------
            else {
                for (let obj of frm.doc.custom_custom_purchase_item) {
					console.log("non asin mmethod is calling")
                    frappe.call({
                        method: "luckybee_customization.overrides.purchase_invoice.search_and_insert_item",
                        args: {
                            'doc': frm.doc,
                            'description': obj.description_of_good_and_services,
                            'hsn': obj.hsnsac != null ? obj.hsnsac : "",
                            'qty': obj.quantity != null ? obj.quantity : 0,
                            'rate': obj.rate != null ? obj.rate : 0,
                            'per': obj.per != null ? obj.per : 0,
                            'disc_perc': obj.disc_ != null ? flt(obj.disc_) : 0,
                            'disc': obj.disc != null ? flt(obj.disc) : 0,
                            'gst': obj.gst != null ? obj.gst : "",
                            'mrp': obj.mrp != null ? obj.mrp : 0,
                            'lrp': obj.lrp != null ? obj.lrp : 0,
                            'brand': obj.brand != null ? obj.brand : "",
                            'group': obj.group != null ? obj.group : "",
                            'category': obj.category != null ? obj.category : "",
                            'sub_category': obj.sub_category != null ? obj.sub_category : ""
                        },
                        freeze: true,
                        freeze_message: "loading items...",
                        callback: function (r) {
                            console.log(r.message, "r.message-------------");
                            if (r.message) {
                                console.log(r.message, "r.message-------------");
                                var item_row = cur_frm.add_child("items");
                                item_row.item_code = r.message.item_code;
                                item_row.item_name = r.message.item_name;
                                item_row.qty = r.message.qty;
                                item_row.uom = r.message.uom;
                                item_row.rate = r.message.rate;
                                item_row.amount = r.message.amount;
                                item_row.custom_last_purchase_rate=r.message.last_purchase_rate;
                                item_row.custom_mrp=r.message.custom_mrp;

                                cur_frm.refresh_fields("items");
                               
                            }
                        }
                    });
                }
                
            }
        }
    },

    // ----------------------------filter formula name ---------------------------
    setup: function (frm) {
        frm.fields_dict['items'].grid.get_field('custom_ppmumrpdap').get_query = function(doc, cdt, cdn) {
            var child = locals[cdt][cdn];
            // Convert reviews_rating to a number before comparison
            // var reviewsRating = parseFloat(child.custom_reviewsrating);
           
             if (child.custom_asin) {
                return {
                    filters: [
                        [`name`, '=',`PASP`]
                    ]
                };
            } 
            if (!child.custom_asin) {
                // Return a different set of options when reviews_rating is less than or equal to 3
                return {
                    filters: [
                        [`name`, 'in', [`MRPD`,`PPMU`]]
                    ]
                };
            }
        };
    }
});


// ------------for amazon price rule-----------------------

function calculate_lrp_and_apply_discount(frm, cdt, cdn, d) {
    console.log(d,"--------------d")
    let purchase_price_as_percent_of_online_price = (parseFloat(d.rate) / d.custom_new_current) * 100;
    console.log("purchase_price_as_percent_of_online_price",purchase_price_as_percent_of_online_price)
    let discountPercentage = 0;

    if (d.custom_reviews_count > 50) {
        console.log("gratear than 50")
        if (purchase_price_as_percent_of_online_price > 5 && purchase_price_as_percent_of_online_price <= 20) {
            console.log("5 and 20")
            discountPercentage =parseFloat(d.custom_reviewsrating) <= 2 ? 45 : (parseFloat(d.custom_reviewsrating) <= 3 ? 55 : (parseFloat(d.custom_reviewsrating) <= 4 ? 60 : 65));
        }  else if (purchase_price_as_percent_of_online_price > 20 && purchase_price_as_percent_of_online_price <= 30) {
            console.log("20 and 30")
            discountPercentage = parseFloat(d.custom_reviewsrating) <= 2 ? 50 : (parseFloat(d.custom_reviewsrating) <= 3 ? 55 : (parseFloat(d.custom_reviewsrating) <= 4 ? 65 : 70));
        } else if  (purchase_price_as_percent_of_online_price > 30 && purchase_price_as_percent_of_online_price <= 40) {
            console.log("30 and 40")
            discountPercentage = parseFloat(d.custom_reviewsrating) <= 2 ? 60 : (parseFloat(d.custom_reviewsrating) <= 3 ? 65 : (parseFloat(d.custom_reviewsrating) <= 4 ? 70 : 75));
        } else if (purchase_price_as_percent_of_online_price > 40 && purchase_price_as_percent_of_online_price <= 50) {
            console.log("40 and 50")
            discountPercentage = parseFloat(d.custom_reviewsrating) <= 2 ? 65 : (parseFloat(d.custom_reviewsrating) <= 3 ? 70 : (parseFloat(d.custom_reviewsrating) <= 4 ? 75 : 80));
        } else if (purchase_price_as_percent_of_online_price > 50 && purchase_price_as_percent_of_online_price <= 60) {
            console.log("50 and 60")
            discountPercentage = parseFloat(d.custom_reviewsrating) <= 2 ? 70 : (parseFloat(d.custom_reviewsrating) <= 3 ? 75 : (parseFloat(d.custom_reviewsrating) <= 4 ? 80 : 85));
        } else if (purchase_price_as_percent_of_online_price > 60 && purchase_price_as_percent_of_online_price <= 70) {
            console.log("60 and 70")
            discountPercentage = parseFloat(d.custom_reviewsrating) <= 2 ? 80 : (parseFloat(d.custom_reviewsrating) <= 3 ? 80 : (parseFloat(d.custom_reviewsrating) <= 4 ? 85 : 85));
        } else if (purchase_price_as_percent_of_online_price > 70 && purchase_price_as_percent_of_online_price <= 80)  {
            console.log("70 and 80")
            discountPercentage = parseFloat(d.custom_reviewsrating) <= 2 ? 80 : (parseFloat(d.custom_reviewsrating) <= 3 ? 85 : (parseFloat(d.custom_reviewsrating) <= 4 ? 90 : 90));
        } else if (purchase_price_as_percent_of_online_price > 80 && purchase_price_as_percent_of_online_price <= 90) {
            console.log("80 and 90")
            discountPercentage = parseFloat(d.custom_reviewsrating) <= 2 ? 90 : (parseFloat(d.custom_reviewsrating) <= 3 ? 90 : (parseFloat(d.custom_reviewsrating) <= 4 ? 95 : 95));
        } else {
            discountPercentage = 100;
        }
    } 
    else if(d.custom_reviews_count <=50){
        if (purchase_price_as_percent_of_online_price > 5 && purchase_price_as_percent_of_online_price <= 20) {
            discountPercentage = 55;
        } else if (purchase_price_as_percent_of_online_price > 20 && purchase_price_as_percent_of_online_price <= 30) {
            discountPercentage = 55;
        } else if (purchase_price_as_percent_of_online_price > 30 && purchase_price_as_percent_of_online_price <= 40) {
            discountPercentage = 65;
        } else if (purchase_price_as_percent_of_online_price > 40 && purchase_price_as_percent_of_online_price <= 50) {
            discountPercentage = 70;
        } else if (purchase_price_as_percent_of_online_price > 50 && purchase_price_as_percent_of_online_price <= 60) {
            discountPercentage = 75;
        } else if (purchase_price_as_percent_of_online_price > 60 && purchase_price_as_percent_of_online_price <= 70) {
            discountPercentage = 80;
        } else if (purchase_price_as_percent_of_online_price > 70 && purchase_price_as_percent_of_online_price <= 80){
            discountPercentage = 85;
        } else if (purchase_price_as_percent_of_online_price > 80 && purchase_price_as_percent_of_online_price <= 90){
            discountPercentage = 90;
        } else {
            discountPercentage = 100;
        }
    }
    

    let lrpValue = (d.custom_new_current * discountPercentage) / 100;
    console.log("pehle wale lrp",lrpValue)
    if (typeof lrpValue === 'number' && !Number.isInteger(lrpValue)) {
        let int_lrp = Math.floor(lrpValue);
        if (int_lrp % 10 === 9) {
            lrpValue = int_lrp;
        } else {
            let stringValue = int_lrp.toString();
            let modifiedString = stringValue.slice(0, -1) + '9';
            lrpValue = parseFloat(modifiedString);
        }
    }
    let discount_on_margin=lrpValue-d.rate
    let margin=(discount_on_margin/d.rate*100)
    let discount_on_mrp = d.custom_mrp - lrpValue;
    let dis = (discount_on_mrp * 100) / d.custom_mrp;
    let custom_discount = Math.round(dis / 10) * 10;
    frappe.model.set_value(cdt, cdn, 'custom_discount', custom_discount);
   
    
    console.log("lrpvalue",lrpValue)
    console.log("discount_on_margin",discount_on_margin)
    console.log("percentage",discountPercentage)
    console.log("margin",margin)
    console.log("ratings",d.custom_reviewsrating)
    console.log(d.custom_reviews_count)
    d.custom_lrp=lrpValue
    d.custom_percentage=discountPercentage
    d.custom_margin=margin
    d.custom_discount=custom_discount
}




// ------------------------------print item barcode------------------------

frappe.ui.form.on('Purchase Invoice Item', {
    custom_print_barcode(frm,cdt,cdn) {
		// your code here
		var d = locals[cdt][cdn];
		var item_code = d.item_code;
		var barcodeWindow = window.open('');
		barcodeWindow.document.write('<svg id="barcode"></svg>');
		
		JsBarcode(barcodeWindow.document.getElementById("barcode"), item_code, {
                height: 50,
                text: d.rate,
                displayValue: true // Whether to display the human-readable value below the barcode
            });
        
        barcodeWindow.print();
        barcodeWindow.close();
	},
    custom_ppmumrpdap: function(frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        
        if (d.custom_ppmumrpdap === 'PPMU') {
            if(!d.custom_percentage){
                frappe.model.set_value(cdt, cdn, 'custom_ppmumrpdap','')
                frappe.throw("please first apply percentage for item")}
            else{
            let custom_percentage=(d.custom_percentage/100)*d.rate
            let lrpValue =custom_percentage + d.rate;
            if (typeof lrpValue === 'number' && !Number.isInteger(lrpValue)) {
            let int_lrp = Math.floor(lrpValue);
            if (int_lrp % 10 === 9) {
                lrpValue = int_lrp;
            } else {
                console.log("int_lrp",int_lrp)
                let stringValue = int_lrp.toString();
                let modifiedString = stringValue.slice(0, -1) + '9';
                lrpValue = parseFloat(modifiedString);
                console.log("lrppp",lrpValue)
            }
        }

            let discount_on_mrp = d.custom_mrp - lrpValue;
            let dis = (discount_on_mrp * 100) / d.custom_mrp;
            let custom_discount = Math.round(dis / 10) * 10;

            // #calculate margin
            let discount_on_margin = lrpValue - d.rate;
            let margin = (discount_on_margin / d.rate * 100);
            
            frappe.model.set_value(cdt, cdn, 'custom_lrp', lrpValue);
            frappe.model.set_value(cdt, cdn, 'custom_discount', custom_discount);
            frappe.model.set_value(cdt, cdn, 'custom_margin',margin);
        }} else if (d.custom_ppmumrpdap === 'MRPD') {
            if(!d.custom_percentage){
                frappe.model.set_value(cdt, cdn, 'custom_ppmumrpdap','')
                frappe.throw("please first apply percentage for item")}
            else{
            // Apply logic for MRPD
            let discount = (d.custom_mrp * d.custom_percentage / 100);
            let lrpValue = d.custom_mrp - discount;
             if (typeof lrpValue === 'number' && !Number.isInteger(lrpValue)) {
            let int_lrp = Math.floor(lrpValue);
            if (int_lrp % 10 === 9) {
                lrpValue = int_lrp;
                console.log("intr",lrpValue)
            } else {
                let stringValue = int_lrp.toString();
                let modifiedString = stringValue.slice(0, -1) + '9';
                lrpValue = parseFloat(modifiedString);
                console.log("llll",lrpValue)
            }
        }
            let discount_on_margin = lrpValue - d.rate;
            console.log("discount_on_margin",discount_on_margin)
            let margin = (discount_on_margin / d.rate * 100);
            console.log("margin",margin)
            let discount_on_mrp = d.custom_mrp - lrpValue;
            let custom_discount = Math.round((discount_on_mrp * 100) / d.custom_mrp);
          
            frappe.model.set_value(cdt, cdn, 'custom_discount', custom_discount);
            frappe.model.set_value(cdt, cdn, 'custom_margin', margin);
            frappe.model.set_value(cdt, cdn, 'custom_lrp', lrpValue);
        }}
    },

    custom_percentage: function(frm, cdt, cdn) {
        let d = locals[cdt][cdn];

        function applyDiscount(discountPercentage, frm, cdt, cdn) {
            let lrpValue = (d.custom_new_current * discountPercentage) / 100;
             if (typeof lrpValue === 'number' && !Number.isInteger(lrpValue)) {
            let int_lrp = Math.floor(lrpValue);
            if (int_lrp % 10 === 9) {
                lrpValue = int_lrp;
            } else {
                let stringValue = int_lrp.toString();
                let modifiedString = stringValue.slice(0, -1) + '9';
                lrpValue = parseFloat(modifiedString);
            }
        }
            let discount_on_margin = lrpValue - d.rate;
            let margin = (discount_on_margin / d.rate * 100);
            let discount_on_mrp = d.custom_mrp - lrpValue;
            let dis = (discount_on_mrp * 100) / d.custom_mrp;
            let custom_discount = Math.round(dis / 10) * 10;
            frappe.model.set_value(cdt, cdn, 'custom_discount', custom_discount);
           
            frappe.model.set_value(cdt, cdn, 'custom_lrp', lrpValue);
            frappe.model.set_value(cdt, cdn, 'custom_percentage', discountPercentage);
            frappe.model.set_value(cdt, cdn, 'custom_margin', margin);
        }

        if (d.custom_ppmumrpdap === 'PASP') {
            applyDiscount(d.custom_percentage, frm, cdt, cdn);
        }}
})



// -------------------------Change Type of Field----------------------
frappe.ui.form.on('Custom Purchase Item', {
    refresh: function(frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        
        // Change the field type to 'Select' dynamically
        frm.fields_dict[d.custom_formula].df.fieldtype = 'Select';
        frm.refresh_field(d.custom_formula);
    }
});


// -----------------------apply percentage and formula ppmu/mrpd in child table for non asin item----------------
frappe.ui.form.on('Purchase Invoice', {
    custom_percentage: function(frm) {
        let main_percentage = frm.doc.custom_percentage;
        frm.doc.items.forEach(function(item) {
            frappe.model.set_value(item.doctype, item.name, 'custom_percentage', main_percentage);
        });

        frm.refresh_field('items');
    },
    custom_ppmumrpd: function(frm) {
        let custom_ppmumrpd = frm.doc.custom_ppmumrpd;

        frm.doc.items.forEach(function(item) {
            frappe.model.set_value(item.doctype, item.name, 'custom_ppmumrpdap', custom_ppmumrpd);
        });

        frm.refresh_field('items');
    }
});