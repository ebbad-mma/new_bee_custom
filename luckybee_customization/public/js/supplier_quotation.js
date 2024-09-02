frappe.ui.form.on('Supplier Quotation', {
    custom_search_and_insert_item(frm,cdt,cdn) {
        let purchase =frm.doc.custom_supplier_quotation_item;
            // console.log(purchase[0].custom_box_number)
            if (purchase[0].custom_box_number || purchase[0].custom_asin || purchase[0].custom_ean){frm.doc.custom_is_asin =1
            }

       if(!frm.doc.supplier){frappe.msgprint('Please select supplier')}
        else if (frm.doc.custom_supplier_quotation_item) {
            cur_frm.clear_table("items");
            // cur_frm.doc.insert(ignore_permission=true)

            if (frm.doc.custom_is_asin ==1) {
                for (let obj of frm.doc.custom_supplier_quotation_item) {
                    frappe.call({
                        method: "luckybee_customization.overrides.supplier_quotation.search_and_insert_item",
                        args: {
                            'doc': frm.doc,
                            'description': obj.description_of_good_and_services,
                            'hsn': obj.hsnsac != null ? obj.hsnsac : "",
                            'qty': obj.quantity != null ? obj.quantity : 0,
                            'rate': obj.rate != null ? obj.rate : 0,
                            'per': obj.per != null ? obj.per : "",
                            'disc1': obj.disc_ != null ? flt(obj.disc_) : 0,
                            'disc2': obj.disc2 != null ? flt(obj.disc2) : 0,
                            'disc3': obj.disc3 != null ? flt(obj.disc3) : 0,
                            'disc': obj.disc != null ? flt(obj.disc) : 0,
                            'mrp': obj.mrp != null ? obj.mrp : "",
                            'brand': obj.brand != null ? obj.brand : "",
                            'group': obj.group != null ? obj.group : "",
                            'category': obj.category != null ? obj.category : "",
                            'sub_category': obj.sub_category != null ? obj.sub_category : "",
                            'custom_asin': obj.custom_asin != null ? obj.custom_asin : "",
                            'custom_box_number': obj.custom_box_number != null ? obj.custom_box_number : "",
                            "custom_ean": obj.custom_ean != null ? obj.custom_ean : "",
                            "custom_synced": obj.custom_synced != null ? obj.custom_synced :"0",
                            "amount": obj.amount != null ? obj.amount :"0"
                        },
                        freeze: true,
                        freeze_message: "loading items...",
                        callback: function (r) {
                            if (r.message.item_code) {
                                console.log("custsttsts0",r.message.custom_mrp)
                                let pp_after_disc_cal=pp_after_disc(r.message.rate, r.message.disc1,r.message.disc2, r.message.disc3)
                                console.log("dissdsdd",pp_after_disc_cal)
                                let cu_mrp=0
                                if (r.message.mrp){if(r.message.mrp<=0){cu_mrp=pp_after_disc_cal}else{cu_mrp= r.message.mrp}}
                                console.log('[cu mrp]',cu_mrp)
                                console.log("r message",r)
                                var item_row = cur_frm.add_child("items");
                                item_row.item_code = r.message.item_code;
                                item_row.item_name = r.message.custom_amzon_item_name;
                                item_row.qty = r.message.qty;
                                item_row.uom = r.message.uom;
                                item_row.rate = pp_after_disc_cal;
                                item_row.amount = r.message.amount;
                                item_row.custom_reviewsrating = r.message.reviews_rating;
                                item_row.custom_reviews_count = r.message.custom_reviews_count;
                                item_row.custom_last_purchase_rate=r.message.last_purchase_rate
                                item_row.custom_new_current = r.message.new_current;
                                item_row.custom_avg_30 = r.message.avg_30;
                                item_row.custom_avg_90 = r.message.avg_90;
                                item_row.custom_mrp=cu_mrp;
                                item_row.custom_disc_=flt(r.message.disc1);
                                item_row.custom_disc2=flt(r.message.disc2);
                                item_row.custom_disc3=flt(r.message.disc3);
                                item_row.custom_disc=r.message.gst_disc;
                                // item_row.item_tax_template=r.message.gst_template;
                                item_row.custom_box_number = r.message.custom_box_number;
                                item_row.custom_asin = r.message.custom_asin;
                                item_row.custom_ppmumrpdap='PASP';
                                item_row.brand=r.message.brand;
                                item_row.description=r.message.item_name;
                                item_row.image_view=r.message.custom_image1
                                // item_row.conversion_factor=1
                                calculate_lrp_and_apply_discount(frm,cdt,cdn,item_row)
                                // console.log("checkkkkk",item_row.item_name)
                                // item_row.rate = r.message.rate;
                                cur_frm.refresh_fields("items");
                                if (frm.is_new()) {
                                    // Set the company currency
                                    frm.set_value('company','Samyak Resources');
                                    console.log("save form first tie")
                                    // Save the form
                                    frm.save();
                                }
                                // cur_frm.save();
                                for (let item of cur_frm.doc.custom_supplier_quotation_item) {
                                    if (item.description_of_good_and_services === r.message.item_name) {
                                        item.custom_synced =1;
                                        // cur_frm.refresh_fields("items");
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
        //    ------------------------------------------------------- non asin code-----------------------------------------------------------------------------
            // else {
            //     for (let obj of frm.doc.custom_custom_purchase_item) {
			// 		console.log("non asin mmethod is calling")
            //         frappe.call({
            //             method: "luckybee_customization.luckybee_customization.doctype.purchase_invoice.search_and_insert_item",
            //             args: {
            //                 'doc': frm.doc,
            //                 'description': obj.description_of_good_and_services,
            //                 'hsn': obj.hsnsac != null ? obj.hsnsac : "",
            //                 'qty': obj.quantity != null ? obj.quantity : 0,
            //                 'rate': obj.rate != null ? obj.rate : 0,
            //                 'per': obj.per != null ? obj.per : 0,
            //                 'disc_perc': obj.disc_ != null ? flt(obj.disc_) : 0,
            //                 'disc': obj.disc != null ? flt(obj.disc) : 0,
            //                 'gst': obj.gst != null ? obj.gst : "",
            //                 'mrp': obj.mrp != null ? obj.mrp : 0,
            //                 'lrp': obj.lrp != null ? obj.lrp : 0,
            //                 'brand': obj.brand != null ? obj.brand : "",
            //                 'group': obj.group != null ? obj.group : "",
            //                 'category': obj.category != null ? obj.category : "",
            //                 'sub_category': obj.sub_category != null ? obj.sub_category : ""
            //             },
            //             freeze: true,
            //             freeze_message: "loading items...",
            //             callback: function (r) {
            //                 console.log(r.message, "r.message-------------");
            //                 if (r.message) {
            //                     console.log(r.message, "r.message-------------");
            //                     var item_row = cur_frm.add_child("items");
            //                     item_row.item_code = r.message.item_code;
            //                     item_row.item_name = r.message.item_name;
            //                     item_row.qty = r.message.qty;
            //                     item_row.uom = r.message.uom;
            //                     item_row.rate = r.message.rate;
            //                     item_row.amount = r.message.amount;
            //                     item_row.custom_last_purchase_rate=r.message.last_purchase_rate

            //                     cur_frm.refresh_fields("items");
                               
            //                 }
            //             }
            //         });
            //     }
                
            // }   ------------------end non asin
        }
    }
});




// ------------for amazon price rule-----------------------

function calculate_lrp_and_apply_discount(frm, cdt, cdn, d) {
    console.log(d,"--------------d")
    let result=0;
    // console.log("Result",result)
    // console.log("custom_asp",d.custom_asp)
    // console.log("custom_avg_30",d.custom_avg_30)
    // console.log("custom_avg_90",d.custom_avg_90)
    if (d.custom_new_current > 0) {
        result = d.custom_new_current;
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
    d.custom_margin_in_amount=discount_on_margin

    // Refresh the field if necessary
    frm.refresh_field('items');
}}



// -----------------------------------------decision maker----------------------------------------------------------


frappe.ui.form.on('Supplier Quotation', {
	custom_get_total_margin(frm) {
		frappe.call({
            method:"luckybee_customization.overrides.supplier_quotation.get_total_margin",
            args: {
                sq_items:frm.doc.items,
                name:frm.doc.name
            },
            // disable the button until the request is completed
            btn: $('.primary-action'),
            // freeze the screen until the request is completed
            freeze: true,
            callback: (r) => {
                // on success
                window.location.reload();
            },
            error: (r) => {
                // on error
            }
        })
	}
})



// ----------------------------get box items------------------------------
frappe.ui.form.on('Supplier Quotation', {
    custom_create_po_for_selected_box_items: function(frm) {
            let selected = frm.get_selected();
            console.log("Selected rows:", selected);

            // Check if any rows are selected
            if (selected.custom_decision_maker && selected.custom_decision_maker.length > 0) {
                let boxNumbers = selected.custom_decision_maker.map(row_name => {
                    let row = locals['Decision Maker'][row_name];
                    console.log("bb",row.box_number)
                    return row.box_number;
                });

                console.log("Box Numbers:",boxNumbers);

                // Filter the items to remove those that do not have the same box number
                let items_to_keep = frm.doc.items.filter(item => {
                    return boxNumbers.includes(item.custom_box_number);
                });

               console.log(items_to_keep)
                let current=new Date()
                console.log(current.getDate())
            //    CREATE PURCHASE ORDER
               frappe.db.insert({
                doctype: 'Purchase Order',
                supplier:frm.doc.supplier,
                transaction_date:frappe.datetime.nowdate(),
                items:items_to_keep,
                schedule_date:frappe.datetime.nowdate()
            }).then(doc => {
                console.log(doc);
                frappe.msgprint("PO Created Sucessfully")
                frm.save('Submit');
                frappe.open_in_new_tab = true;
                frappe.set_route('Form','Purchase Order',doc.name)
            })
            
            }
             else {
                frappe.msgprint("Please First Select Box")
            }
        
    }
});




// ----------------------hide delete button globally from decision maker-----------------------
// frappe.ui.form.on('Supplier Quotation', {
//     refresh: function(frm) {
//         frm.set_df_property('custom_decision_maker', 'cannot_delete_rows', true); 
//         frm.set_df_property('custom_decision_maker', 'cannot_add_rows', true); 
//         frm.set_df_property('items', 'cannot_add_rows', true); 
//         frm.set_df_property('items', 'cannot_add_multiple_rows', true); 
        
//         setTimeout(function() {
//             // Hide the button that contains "Add Multiple"
//             $("button:contains('Add Multiple')").css("display", "none");
//             $(document).ready(function() {
//                 // Hide the second button with the class "grid-upload"
//                 $(".grid-upload").eq(1).css("display", "none");
//             });
            
//         }, 1000); // Adjust the delay as necessary
//     }
// });




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