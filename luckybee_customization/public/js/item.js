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
        frm.add_custom_button("Create Product Finder", function(){
            var n = frappe.new_doc("Product Finder", {item:frm.doc.name,title: frm.doc.item_name, brand: frm.doc.brand, color:frm.doc.color})
            console.log("return of new_doc", n);
        });

        // PUBLISH ITEM 
        if (! frm.doc.custom_published)
        {frm.add_custom_button("Publish Item", function(){            
            frappe.call({
                args: {
                    doc : frm.doc
                },
                method: "luckybee_customization.woocommerce.publish_item.publish_item",
                        
                callback: function(r){
                    cur_frm.refresh()
                    frm.refresh_fields();
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
                        cur_frm.refresh()
                        frm.refresh_fields();
                        frappe.msgprint(r.message)
                    }
                })
            })  
        }
    }
})


