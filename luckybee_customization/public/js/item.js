frappe.ui.form.on('Item', {
    refresh(frm){
        // Check if the custom_item_detail field has a value
        if (frm.doc.custom_item_detail) {
            // Add custom button
            frm.add_custom_button(__('Go to item details'), function() {
                // Set the Frappe route
                frappe.set_route('Form', 'Item Details', frm.doc.custom_item_detail);
            });
        }

        // PRODUCT FINDER
        frm.add_custom_button("Create Product Finder", async function() {
            try {
                // Initialize color variable
                let color = null;
                let size = null;
                let model = null;
                let part_number = null;

                // Check if 'Item Details' exists for the given item name
                const amazon_exists = frappe.db.exists('Item Details',null, {'item': frm.doc.name});
                const flipkart_exists = frappe.db.exists('Item Details',null, {'item': frm.doc.name});
                // console.log("exis",exists)
                
                
                if (amazon_exists) {
                    // Fetch the 'Item Details' document for the given item name
                    const id_data = await frappe.db.get_doc('Item Details',null, {'item': frm.doc.name});
                    color = id_data.color;
                    size = id_data.size;
                    model = id_data.model;
                    part_number = id_data.product_codes_partnumber;
                }
                if (flipkart_exists) {
                    // Fetch the 'Item Details' document for the given item name
                    const id_data = await frappe.db.get_doc('Item Details',null, {'item': frm.doc.name});
                    model = id_data.model_flipkart;
                }

                // Create a new 'Product Finder' document with the necessary fields
                let new_doc = frappe.new_doc("Product Finder", {
                    item: frm.doc.name,
                    title: frm.doc.item_name,
                    brand: frm.doc.brand,
                    size: size ,
                    model: model ,
                    part_number: part_number ,
                    color: color ,
                    root_category: frm.doc.custom_category_root ,
                    sub_category: frm.doc.custom_category_sub
                });

                console.log("Return of new_doc", new_doc);
            } catch (error) {
                console.error("An error occurred while creating Product Finder:", error);
            }
        });



        // PUBLISH ITEM 
        if (! frm.doc.custom_published)
        {frm.add_custom_button("Publish Item", function(){            
            frappe.call({
                args: {
                    doc : frm.doc
                },
                method: "luckybee_customization.woocommerce.publish_item.publish_item",
                freeze: true,
                freeze_message: "Publishing item...",
                        
                callback: function(r){
                    cur_frm.refresh()
                    window.location.reload()
                    frappe.msgprint(r.message)
                }
            })
        })}

        // UNPUBLISH ITEM 
        else{
            frm.add_custom_button("Unpublish Item", function(){
                frappe.call({
                    args: {
                        doc : frm.doc
                    },
                    method: "luckybee_customization.woocommerce.publish_item.unpublish_item",
                    callback: function(r){
                        
                        window.location.reload()
                        frappe.msgprint(r.message)
                    }
                })
            })  
        }
    }
})


