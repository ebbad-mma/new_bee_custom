frappe.ui.form.on('Purchase Invoice', {

    validate:function(frm){
        if (frm.doc.custom_is_asin==1 || frm.doc.custom_is_fsn==1){
        sortChildTable(frm)
        }
    },

    custom_search_and_insert_item(frm,cdt,cdn) {
        let purchase =frm.doc.custom_custom_purchase_item;
            if (purchase[0].custom_asin || purchase[0].custom_ean){frm.set_value('custom_is_asin',1)}
            else if (purchase[0].custom_fsn){frm.set_value('custom_is_fsn',1)}
            else { 
                {frm.set_value('custom_non_asin',1)}
            
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
                                "disc": obj.disc != null ? flt(obj.disc) : 0,
                                'disc1': obj.disc_ != null ? flt(obj.disc_) : 0,
                                'disc2': obj.disc2 != null ? flt(obj.disc2) : 0,
                                'disc3': obj.disc3 != null ? flt(obj.disc3) : 0,
                                "amount": obj.amount != null ? flt(obj.amount) : 0,
                                "item_index": obj.idx

                            },
                            freeze: true,
                            freeze_message: "loading items...",
                            callback: function (r) {
                                if (r.message) {
                                    let pp_after_disc_cal=pp_after_disc(r.message.rate, r.message.disc1,r.message.disc2, r.message.disc3)
                                    let cu_mrp=0
                                    if(flt(r.message.mrp)<=0){cu_mrp=flt(r.message.rate)}
                                    console.log("R MESSAGE",r.message)
                                    var item_row = cur_frm.add_child("items");
                                    item_row.custom_item_index=r.message.item_index;
                                    item_row.idx=r.message.item_index;
                                    item_row.item_code = r.message.item_code;
                                    item_row.item_name = r.message.item_name;
                                    item_row.qty = r.message.qty;
                                    item_row.uom = r.message.uom;
                                    item_row.rate =pp_after_disc_cal;
                                    item_row.amount = r.message.amount;
                                    item_row.custom_reviewsrating = r.message.reviews_rating;
                                    item_row.custom_reviews_count = r.message.custom_reviews_count;
                                    item_row.custom_last_purchase_rate=r.message.last_purchase_rate
                                    item_row.custom_asp = r.message.new_current;
                                    item_row.custom_avg_30 = r.message.avg_30;
                                    item_row.custom_avg_90 = r.message.avg_90;
                                    item_row.custom_mrp=cu_mrp;
                                    item_row.custom_box_number = r.message.custom_box_number;
                                    item_row.custom_asin = r.message.custom_asin;
                                    item_row.custom_ppmumrpdap='PASP'
                                    item_row.custom_disc_=flt(r.message.disc1);
                                    item_row.custom_disc2=flt(r.message.disc2);
                                    item_row.custom_disc3=flt(r.message.disc3);
                                    item_row.custom_disc=r.message.gst_disc;
                                    item_row.item_tax_template=r.message.gst_template;                                    ;
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
            else if(frm.doc.custom_is_fsn===1){for (let obj of frm.doc.custom_custom_purchase_item) {
                console.log("FSN Is calling")
                frappe.call({
                    method: "luckybee_customization.overrides.Fsn.search_and_insert_item",
                    args: {
                        'doc': frm.doc,
                        'description': obj.description_of_good_and_services,
                        'fsn': obj.custom_fsn != null ? obj.custom_fsn : "",
                        'qty': obj.quantity != null ? obj.quantity : 0,
                        'rate': obj.rate != null ? obj.rate : 0,
                        'per': obj.per != null ? obj.per : 0,
                        'mrp': obj.mrp != null ? obj.mrp : 0,
                        'lrp': obj.lrp != null ? obj.lrp : 0,
                        'item_index': obj.idx
                    },
                    freeze: true,
                    freeze_message: "loading items...",
                    callback: function (r) {
                        // console.log(r.message, "r.message-------------");
                        if (r.message) {
                            console.log(r.message, "r.message-------------");
                            var item_row = cur_frm.add_child("items");
                            item_row.item_code = r.message.item_code;
                            item_row.item_name = r.message.item_name;
                            item_row.qty = r.message.qty;
                            item_row.uom = r.message.uom;
                            item_row.custom_mrp=r.message.custom_mrp;
                            item_row.custom_item_index=r.message.item_index;
                            item_row.idx=r.message.item_index;

                            cur_frm.refresh_fields("items");
                           
                        }
                    }
                });
            }
            
        }
            
        //    ------------------------------------------------------- non asin code-----------------------------------------------------------------------------
        else if(frm.doc.custom_non_asin===1){console.log("non",frm.doc.custom_non_asin)
                for (let obj of frm.doc.custom_custom_purchase_item) {
                    console.log("obj",obj)
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
                            'disc1': obj.disc_ != null ? flt(obj.disc_) : 0,
                            'disc2': obj.disc2 != null ? flt(obj.disc2) : 0,
                            'disc3': obj.disc3 != null ? flt(obj.disc3) : 0,
                            'disc': obj.disc != null ? flt(obj.disc) : 0,
                            'gst': obj.gst != null ? obj.gst : "",
                            'mrp': obj.mrp != null ? obj.mrp : 0,
                            'lrp': obj.lrp != null ? obj.lrp : 0,
                            'brand': obj.brand != null ? obj.brand : "",
                            'group': obj.group != null ? obj.group : "",
                            'category': obj.category != null ? obj.category : "",
                            'sub_category': obj.sub_category != null ? obj.sub_category : "",
                            'item_index': obj.idx
                        },
                        freeze: true,
                        freeze_message: "loading items...",
                        callback: function (r) {
                            console.log(r.message, "r.message-------------");
                            console.log("Item Index",r.message.item_index)
                            if (r.message) {
                                console.log("custsttsts0",r.message.custom_mrp)
                                let pp_after_disc_cal=pp_after_disc(r.message.rate, r.message.disc1,r.message.disc2, r.message.disc3)
                                console.log("dissdsdd",pp_after_disc_cal)
                                let cu_mrp=0
                                {if(flt(r.message.custom_mrp)<=0){cu_mrp=flt(r.message.rate)}}
                                
                                console.log('[cu mrp]',cu_mrp)
                                console.log(r.message, "r.message-------------");
                                var item_row = cur_frm.add_child("items");
                                item_row.item_code = r.message.item_code;
                                item_row.item_name = r.message.item_name;
                                item_row.qty = r.message.qty;
                                item_row.uom = r.message.uom;
                                item_row.rate = pp_after_disc_cal;
                                item_row.amount = r.message.amount;
                                item_row.custom_last_purchase_rate=r.message.last_purchase_rate;
                                item_row.custom_mrp=cu_mrp;
                                item_row.custom_disc_=flt(r.message.disc1);
                                item_row.custom_disc2=flt(r.message.disc2);
                                item_row.custom_disc3=flt(r.message.disc3);
                                item_row.custom_disc=r.message.gst_disc;
                                item_row.item_tax_template=r.message.gst_template; 
                                item_row.custom_item_index=r.message.item_index; 
                                item_row.idx=r.message.item_index; 

                                cur_frm.refresh_fields("items");
                                for (let item of frm.doc.custom_custom_purchase_item) {
                                    // console.log("ppppppppppppppppppppppppppppppppp",item.description_of_good_and_services ,r.message.item_name)
                                    if (item.description_of_good_and_services === r.message.item_name) {
                                        item.custom_synced =1;
                                        // cur_frm.refresh_fields("custom_custom_purchase_item");
                                    }
                                }
                               
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
    let result=0;
    console.log("Result",result)
    console.log("custom_asp",d.custom_asp)
    console.log("custom_avg_30",d.custom_avg_30)
    console.log("custom_avg_90",d.custom_avg_90)
    if (d.custom_asp > 0) {
        result = d.custom_asp;
    } else if(d.custom_avg_30 > 0){
        result = d.custom_avg_30 ;
    }
    else if(d.custom_avg_90>0){result = d.custom_avg_90 ;}
    else{result=0}
    console.log("final Result",result)
    if(result>0){
    let purchase_price_as_percent_of_online_price = (parseFloat(d.rate) /result) * 100;
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
        console.log("hhhahahhhahahahahahhahahah")
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
    

    let lrpValue = (result * discountPercentage) / 100;
    console.log(discountPercentage,"appp")
    console.log("pehle wale lrp",lrpValue)

        // Ensure lrpValue is an integer
        lrpValue = Math.floor(lrpValue);
        
        // Adjust lrpValue to end with 9
        if (lrpValue % 10 !== 9) {
            lrpValue = Math.floor(lrpValue / 10) * 10 + 9;
    }
    let discount_on_margin=lrpValue-d.rate
    let margin=(discount_on_margin/d.rate*100)
    let discount_on_mrp = result - lrpValue;
    let dis = (discount_on_mrp * 100) / result;
    let custom_discount = Math.round(dis / 10) * 10;
    // frappe.model.set_value(cdt, cdn, 'custom_discount', custom_discount);
   
    
    console.log("lrpvaluenenwewe",lrpValue)
   
    d.custom_lrp=lrpValue
    d.custom_percentage=discountPercentage
    d.custom_margin=margin
    d.custom_discount=custom_discount

    // Refresh the field if necessary
    frm.refresh_field('items');
}}


// ------------------helper function to calculate ppmu------------------
function calculatePPMU(d,cdt, cdn) {
        if (!d.custom_percentage) {
            frappe.model.set_value(cdt, cdn, 'custom_ppmumrpdap', '');
            frappe.throw("Please first apply percentage for item");
        } else {
            // Calculate the initial LRP value
            let markup=d.rate*d.custom_percentage/100
            console.log('markup',markup)
            let lrpValue = flt(d.rate) + flt(markup)
            console.log('LRP value before converting PPMU:', lrpValue);

            // Ensure lrpValue is an integer
            lrpValue = Math.floor(lrpValue);

            // Adjust lrpValue to end with 9
            if (lrpValue % 10 !== 9) {
                lrpValue = Math.floor(lrpValue / 10) * 10 + 9;
            }
            console.log('LRP value after converting PPMU:', lrpValue);

            let discount_on_mrp = d.custom_mrp - lrpValue;
            let dis = (discount_on_mrp * 100) / d.custom_mrp;
            let custom_discount = Math.round(dis);

            // If the discount is less than 15%, adjust the LRP to give a 15% discount
            console.log("Custom discount:", custom_discount);
            if (custom_discount < 15) {
                console.log("Discount is less than 15%");
                lrpValue = Math.floor(d.custom_mrp * 0.85);

                // Adjust lrpValue to end with 9
                if (lrpValue % 10 !== 9) {
                    if (d.rate<=200){lrpValue=lrpValue}
                    else{lrpValue = Math.floor(lrpValue / 10) * 10 + 9;}
                    
                }

                // Recalculate the discount after adjusting lrpValue
                discount_on_mrp = d.custom_mrp - lrpValue;
                dis = (discount_on_mrp * 100) / d.custom_mrp;
                custom_discount = Math.round(dis);
                console.log("Custom discount after adjustment:", custom_discount);
            }

            // Update values in the Frappe model
            frappe.model.set_value(cdt, cdn, 'custom_lrp', lrpValue);
            frappe.model.set_value(cdt, cdn, 'custom_discount', custom_discount);
            frappe.model.set_value(cdt, cdn, 'custom_margin', d.custom_percentage);
    }
}


// -----------------------------helper function to calculate MRPD--------------
function calculateMRPD(d,cdt, cdn) {

    if (!d.custom_percentage) {
        frappe.model.set_value(cdt, cdn, 'custom_ppmumrpdap', '');
        frappe.throw("Please first apply percentage for item");
    } else {
        // Calculate discount and LRP value
        let discount = (flt(d.custom_mrp) * flt(d.custom_percentage) / 100);
        let lrpValue = d.custom_mrp - discount;
        console.log("LRP before adjustment:", lrpValue);

        // Ensure lrpValue is an integer and ends with 9
        lrpValue = Math.floor(lrpValue);
        if (lrpValue % 10 !== 9) {
            lrpValue = Math.floor(lrpValue / 10) * 10 + 9;
        }
        console.log("LRP after adjustment to end with 9:", lrpValue);

        let discount_on_mrp = d.custom_mrp - lrpValue;
        let dis = (discount_on_mrp * 100) / d.custom_mrp;
        let custom_discount = Math.round(dis);

        // If the discount is less than 15%, adjust the LRP to give a 15% discount
        if (custom_discount < 15) {
            lrpValue = Math.floor(d.custom_mrp * 0.85);

            // Ensure lrpValue ends with 9
            if (lrpValue % 10 !== 9) {
                if (d.rate<=200){lrpValue=lrpValue}
                else{lrpValue = Math.floor(lrpValue / 10) * 10 + 9;}
                
            }

            // Recalculate the discount after adjusting lrpValue
            discount_on_mrp = d.custom_mrp - lrpValue;
            dis = (discount_on_mrp * 100) / d.custom_mrp;
            custom_discount = Math.round(dis);
        }

        // Calculate margin
        let discount_on_margin = lrpValue - d.rate;
        let margin = (discount_on_margin / d.rate) * 100;

        // Update values in the Frappe model
        frappe.model.set_value(cdt, cdn, 'custom_discount', custom_discount);
        frappe.model.set_value(cdt, cdn, 'custom_margin', margin);
        frappe.model.set_value(cdt, cdn, 'custom_lrp', lrpValue);
    }
}



// ---------------------helper function to sort item table after insert----------------------
function sortChildTable(frm) {
    // Get the child table data
    let items = frm.doc.items;

    // Sort the child table data by custom_item_index
    items.sort((a, b) => (a.custom_item_index || 0) - (b.custom_item_index || 0));
    console.log("item after sort",items)
    
    frm.clear_table('items');
    items.forEach(item => {
        // Add a new row to the child table
        let newRow = frm.add_child('items');

        for (let key in item) {
            if (item.hasOwnProperty(key) && key !== 'name') { 
                newRow[key] = item[key];
            }
        }
    });

    // Refresh the field to show the updated data
    frm.refresh_field('items'); 
}




// ------------------------------print item barcode------------------------calculation for non asin-----------------

frappe.ui.form.on('Purchase Invoice Item', {

    // #for amazom lrp calculate based on asp
    custom_asp(frm,cdt,cdn){
        var d = locals[cdt][cdn];
        calculate_lrp_and_apply_discount(frm, cdt, cdn, d)
    }
        ,
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
            calculatePPMU(d,cdt, cdn) 
        }
        
        else if (d.custom_ppmumrpdap === 'MRPD') {
            calculateMRPD(d,cdt, cdn)
        }
        
    },

    custom_percentage:function(frm,cdt,cdn){
        let d=locals[cdt][cdn]
        if(d.custom_ppmumrpdap==="PPMU"){
            calculatePPMU(d,cdt, cdn)
        }
        if (d.custom_ppmumrpdap === 'MRPD') {
            calculateMRPD(d,cdt, cdn)
        }

    }
    // ------------------------comment for now---------------------

    // custom_changediscount: function(frm, cdt, cdn) {
    //     let d = locals[cdt][cdn];
    // if(d.custom_ppmumrpdap=='PPMU'){
    //     let disc_per=d.custom_changediscount/100
    //     console.log("disc_perc",disc_per)
    //     let lrpValue=d.custom_mrp-((disc_per*d.custom_mrp)/100)
    //     console.log("lrp",lrpValue)
    //     lrpValue = Math.floor(lrpValue);
    //     let margin = lrpValue - d.rate;
    //     let marginPercentage = (margin / lrpValue) * 100;
    //     marginPercentage = marginPercentage.toFixed(2); // Round to 2 decimal places
    //     frappe.model.set_value(cdt, cdn, 'custom_lrp', lrpValue);
    //     frappe.model.set_value(cdt, cdn, 'custom_margin',marginPercentage); }
    // if(d.custom_ppmumrpdap=='MRPD'){
    //     let disc_per=d.custom_changediscount/100
    //     console.log("disc_perc",disc_per)
    //     let dis_lrp=d.custom_mrp*disc_per
    //     let lrpValue=d.custom_mrp-dis_lrp
    //     console.log("lrp",lrpValue)
    //     lrpValue = Math.floor(lrpValue);
    //     let margin = ((d.custom_mrp - lrpValue) / d.custom_mrp) * 100;
    //     frappe.model.set_value(cdt, cdn, 'custom_lrp', lrpValue);
    //     frappe.model.set_value(cdt, cdn, 'custom_margin',margin); }

        
    // }

    // ------------------------comment for now-----------------------
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
        sortChildTable(frm)
        frm.set_value('custom_ppmumrpd',null)
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


// ----------------------calculate purchase price after discount----------------


function pp_after_disc(rate, disc1, disc2, disc3) {
    // Convert the rate to a number
    let finalRate = parseFloat(rate);

    // Calculate the purchase price by applying all discounts sequentially
    if (disc1) {
        finalRate *= (1 - disc1 / 100);
        console.log("After 1st discount:", finalRate);
        console.log("1stdisc",disc1)
    }

    if (disc2) {
        finalRate *= (1 - disc2 / 100);
        console.log("After 2nd discount:", finalRate);
        console.log("2nddisc",disc2)
    }

    if (disc3) {
        finalRate *= (1 - disc3 / 100);
        console.log("After 3rd discount:", finalRate);
        console.log("3rddisc",disc3)
    }

    return finalRate.toFixed(2); // Return the final rate rounded to two decimal places
}
