var elem_list = null;

var list_length= 0;
var allow_barcode_print = false;
frappe.ui.form.on('Goods Received Note - GRN', {
	purchase_invoice(frm) {
	    frm.doc.custom_index = 0;
	    
	    console.log("purchase invoice triggered", frm.doc.custom_index);
	    frappe.call({
	        method: "luckybee_customization.luckybee_customization.api.GRN.get_fields",
	        args: {"purchase_invoice" : frm.doc.purchase_invoice},
	        callback: function(r) {
	            elem_list= r["message"]['res_list'];
	            
	            list_length = elem_list.length;
	            frm.doc.custom_count = `${frm.doc.custom_index + 1} of ${list_length}`;
	            let elem = elem_list[frm.doc.custom_index];
	            
	            let is_asin = r['message']['is_asin'];
	            if (is_asin == "0"){
	                console.log("is not asin");
	                frm.doc.purchase = "Non Asin"
	                frm.doc.mrp = elem['custom_mrp'];
	            }
	            else{
	                console.log("is asin");
	                frm.doc.purchase = "Asin"
	                frm.doc.mrp = elem['mrp'];
	            }
	            
	            frm.doc.product = elem['item_code'];
	            frm.doc.custom_box_number = elem['custom_box_number'];
	            frm.doc.custom_asin_number = elem['custom_asin'];
	            frm.doc.custom_item_name = elem['item_name'];
	            frm.doc.custom_image = elem['image'];
	            
	            frm.doc.custom_description = elem['description']
	            frm.doc.purchase_quantity = elem['qty'];
	            frm.doc.received_quantity = elem['received_qty'];
	            frm.doc.custom_brand = elem['brand'];
	            
	            frm.doc.custom_rate = elem['rate'];
	            frm.doc.ean = elem['ean'];
	            frm.doc.subcategory = elem['subcategory'];
	            let image_field_name = "custom_image_"
	            for (var i = 1; i < elem['images'].length; i++) {
                    let field_name = `${image_field_name}${i+1}`;
                    frm.set_value(field_name, elem['images'][i]);
                }
	            frm.refresh();
	           // frm.save();
	           //console.log(elem[0]);
	            
	        }
	        
	    })
	},
	custom_next(frm){

	    allow_barcode_print = false;
	    console.log("next triggered", frm.doc.custom_index);
	    if (frm.doc.custom_index < list_length-1){
	        frm.doc.custom_index = frm.doc.custom_index + 1;
	        frm.doc.custom_count = `${frm.doc.custom_index + 1} of ${list_length}`;
	        let elem= elem_list[frm.doc.custom_index];
            frm.doc.product = elem['item_code'];
            frm.doc.custom_box_number = elem['custom_box_number'];
            frm.doc.custom_asin_number = elem['custom_asin'];
            frm.doc.custom_item_name = elem['item_name'];
            frm.doc.custom_image = elem['image'];
            frm.doc.custom_description = elem['description'];
            frm.doc.purchase_quantity = elem['qty'];
            frm.doc.received_quantity = elem['received_qty'];
            frm.doc.custom_brand = elem['brand'];
            frm.doc.mrp = elem['custom_mrp'];
            frm.doc.custom_rate = elem['rate'];
            frm.doc.ean = elem['ean'];
            frm.doc.subcategory = elem['subcategory'];
            frm.doc.custom_image = elem['image'];
            
            let image_field_name = "custom_image_";
            for (var i = 1; i < elem['images'].length; i++) {
                let field_name = `${image_field_name}${i+1}`;
                frm.set_value(field_name, elem['images'][i]);
            }
            frm.refresh();
            // window.scroll()
            console.log("index: ", frm.doc.custom_index);
	    }
	    else{
	        frappe.msgprint("All items completed");
	    }
	    
	},
	custom_previous(frm){
	    console.log("previous triggered", frm.doc.custom_index);
	    if (frm.doc.custom_index > 0){
	        frm.doc.custom_index = frm.doc.custom_index - 1;
	        frm.doc.custom_count = `${frm.doc.custom_index + 1} of ${list_length}`;
	        let elem= elem_list[frm.doc.custom_index];
            frm.doc.product = elem['item_code'];
            frm.doc.custom_box_number = elem['custom_box_number'];
            frm.doc.custom_asin_number = elem['custom_asin'];
            frm.doc.custom_item_name = elem['item_name'];
            frm.doc.custom_image = elem['image'];
            frm.doc.custom_description = elem['description']
            frm.doc.purchase_quantity = elem['qty'];
            frm.doc.received_quantity = elem['received_qty'];
            frm.doc.custom_brand = elem['brand'];
            frm.doc.mrp = elem['custom_mrp'];
            frm.doc.custom_rate = elem['rate'];
            frm.doc.ean = elem['ean'];
            frm.doc.subcategory = elem['subcategory'];
            frm.doc.custom_image = elem['image'];
            let image_field_name = "custom_image_"
            for (var i = 1; i < elem['images'].length; i++) {
                let field_name = `${image_field_name}${i+1}`;
                frm.set_value(field_name, elem['images'][i]);
            }
            frm.refresh();
            console.log("index: ", frm.doc.custom_index);
	    }
	    else{
	        frappe.msgprint("No previous item");
	    }
	},
	quality_check(frm){
	    if (frm.doc.quality_check == "No"){
	       frappe.new_doc("Quality Checks", {purchase_invoice : frm.doc.purchase_invoice, item_code:frm.doc.product}, 
	       doc => {doc.out_of = frm.doc.received_quantity;
	       doc.refresh();
	           console.log("inside callback", doc.out_of);
	       }
	       );
	    }
	},
	custom_save(frm){
	   // frm.save();
	   if (frm.doc.quality_check != "" && frm.doc.received_quantity != ""){
    	   let item_name = elem_list[frm.doc.custom_index]['name'];
    	    frappe.call({
    	        method: "luckybee_customization.luckybee_customization.api.GRN.update_data",
    	        args: {"doc":frm.doc,'item_name':item_name},
    	        callback: function(r){
    	            console.log(r);
    	            allow_barcode_print=true;
    	        }
    	    });
	   }
	   else{
	       frappe.msgprint("Mark Mandetory fields, Received quantity and Quality check");
	   }
	},
	print_barcode(frm) {
	    if (allow_barcode_print){
    	    var item_code = frm.doc.product;
    		var barcodeWindow = window.open('');
    		barcodeWindow.document.write('<svg id="barcode"></svg>');
    		
    		JsBarcode(barcodeWindow.document.getElementById("barcode"), item_code, {
                    height: 50,
                    text: frm.rate,
                    displayValue: true // Whether to display the human-readable value below the barcode
                });
            
            barcodeWindow.print();
            barcodeWindow.close();
	        
	    }
	  else{
	      frappe.msgprint("Please save the Item before printing barcode");
	  }
	}
})